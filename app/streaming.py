# app/streaming.py
from __future__ import annotations

import os
import mimetypes
import hashlib
import json
import subprocess
import tempfile
import shutil
import asyncio
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from anyio import to_thread
from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from fastapi.responses import (
    StreamingResponse,
    HTMLResponse,
    FileResponse,
    RedirectResponse,
    PlainTextResponse,
)
from sqlalchemy.ext.asyncio import AsyncSession

from .auth import get_current_user
from .database import get_db
from .models import MediaFile, MediaItem

router = APIRouter(prefix="/stream", tags=["stream"])

# ──────────────────────────────────────────────────────────────────────────────
# HLS helpers
# ──────────────────────────────────────────────────────────────────────────────

HLS_JOBS: dict[str, dict] = {}  # file_id -> {"proc": Popen, "dir": Path, "started": float, "last": float}

STALE_SECONDS = 120

async def cleanup_hls_jobs():
    now = time.time()
    for fid, job in list(HLS_JOBS.items()):
        if now - job.get("last", now) > STALE_SECONDS:
            proc = job.get("proc")
            try:
                if proc and proc.poll() is None:
                    proc.kill()
            except Exception:
                pass
            try:
                shutil.rmtree(job.get("dir"), ignore_errors=True)
            except Exception:
                pass
            HLS_JOBS.pop(fid, None)

def _rewrite_master_uris(playlist_text: str, prefix: str) -> str:
    """
    Rewrite relative media-playlist URIs inside the master.m3u8
    so they go through /stream/{id}/hls.
    """
    out = []
    for line in playlist_text.splitlines():
        if line and not line.startswith("#") and not line.startswith("http"):
            line = f"{prefix}/{line}"
        out.append(line)
    return "\n".join(out) + "\n"

def _spawn_hls_ffmpeg(
    src_path: str,
    out_dir: Path,
    v_bitrate: str = "3500k",
    a_bitrate: str = "160k",
    copy_video: bool = False,
    copy_audio: bool = False,
):
    """
    Jellyfin-like: produce fMP4 HLS into out_dir with single-file segments:
      master.m3u8   (master)
      index.m3u8    (media)
      init.mp4      (init)
      segments.mp4  (all segments via #EXT-X-BYTERANGE)
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    master = out_dir / "master.m3u8"
    media  = out_dir / "index.m3u8"
    seg_one = out_dir / "segments.mp4"         # single media file for all segments
    init_name = "init.mp4"

    args = [
        "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
        "-fflags", "+genpts",
        "-avoid_negative_ts", "make_zero",
        "-i", src_path,
        "-map", "0:v:0", "-map", "0:a:0?",
        # Video
        "-c:v", "copy" if copy_video else "libx264",
        *(["-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.1",
           "-preset", "veryfast", "-crf", "21", "-g", "48", "-sc_threshold", "0"] if not copy_video else []),
        # Audio
        "-c:a", "copy" if copy_audio else "aac",
        *(["-b:a", a_bitrate] if not copy_audio else []),
        # HLS (fMP4 single-file)
        "-f", "hls",
        "-hls_time", "4",
        "-hls_playlist_type", "event",  # or "vod" if you want ENDLIST
        "-hls_segment_type", "fmp4",
        "-hls_flags", "independent_segments+append_list+temp_file+single_file",
        "-hls_fmp4_init_filename", init_name,          # writes init.mp4
        "-hls_segment_filename", str(seg_one),         # writes segments.mp4
        "-master_pl_name", "master.m3u8",
        "-max_muxing_queue_size", "1024",
        str(media),                                    # writes index.m3u8
    ]
    # IMPORTANT: run in the HLS folder so all outputs land there
    return subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=str(out_dir))

def _rewrite_map_uris(playlist_text: str, prefix: str) -> str:
    """
    Rewrite #EXT-X-MAP and any relative media line to go through /stream/{id}/hls.
    In single-file mode, the media lines will just be 'segments.mp4' repeated
    with #EXT-X-BYTERANGE tags above them.
    """
    out_lines = []
    for line in playlist_text.splitlines():
        if line.startswith("#EXT-X-MAP:"):
            line = f'#EXT-X-MAP:URI="{prefix}/init.mp4"'
        elif line and not line.startswith("#") and not line.startswith("http"):
            # 'segments.mp4' or any relative URI
            line = f"{prefix}/{line}"
        out_lines.append(line)
    return "\n".join(out_lines) + "\n"

async def _wait_for_segments(playlist_path: Path, min_segments: int = 2, timeout_s: int = 10):
    """Wait until the playlist has at least min_segments EXTINF lines."""
    start = time.time()
    while time.time() - start < timeout_s:
        try:
            text = playlist_path.read_text(encoding="utf-8", errors="ignore")
            if text.count("#EXTINF:") >= min_segments:
                return
        except FileNotFoundError:
            pass
        await asyncio.sleep(0.1)

def _rewrite_map_uris(playlist_text: str, prefix: str) -> str:
    """
    Make relative paths in .m3u8 resolve through our /stream/{id}/hls route.
    Rewrites #EXT-X-MAP (init.mp4) and segment lines.
    """
    out_lines = []
    for line in playlist_text.splitlines():
        if line.startswith("#EXT-X-MAP:"):
            # Normalize to init.mp4 and prefix it
            if 'URI="' in line:
                # Replace anything inside URI=""
                start = line.index('URI="') + 5
                end = line.find('"', start)
                uri_val = line[start:end] if end != -1 else "init.mp4"
            else:
                uri_val = "init.mp4"
            # Force it to init.mp4 under our prefix
            line = f'#EXT-X-MAP:URI="{prefix}/init.mp4"'
        elif line and not line.startswith("#") and not line.startswith("http"):
            # Segment or media-playlist line; prefix it
            line = f"{prefix}/{line}"
        out_lines.append(line)
    return "\n".join(out_lines) + "\n"

# ──────────────────────────────────────────────────────────────────────────────
# General helpers
# ──────────────────────────────────────────────────────────────────────────────

def _is_8bit_420(pix_fmt: Optional[str]) -> bool:
    return (pix_fmt or "").lower() in {"yuv420p", "yuvj420p"}

def _is_h264_8bit_browser_safe(profile: Optional[str], pix_fmt: Optional[str]) -> bool:
    if not _is_8bit_420(pix_fmt):
        return False
    p = (profile or "").lower()
    return not ("10" in p or "hi10" in p or "4:2:2" in p or "4:4:4" in p)

def _can_copy_video(info: dict, caps: dict) -> bool:
    v = (info.get("vcodec") or "").lower()
    pix = info.get("v_pix_fmt")
    prof = info.get("v_profile")

    if v == "h264":
        return _is_h264_8bit_browser_safe(prof, pix)
    if v in {"hevc", "h265"}:
        return caps.get("mp4_hevc_aac", False) and _is_8bit_420(pix)
    return False

def _parse_range(range_header: Optional[str], file_size: int) -> Tuple[int, int]:
    if not range_header or not range_header.startswith("bytes="):
        return (0, file_size - 1)

    ranges = range_header.replace("bytes=", "").strip()
    if "," in ranges:
        raise HTTPException(status_code=416, detail="Multiple ranges not supported")

    start_s, _, end_s = ranges.partition("-")
    if start_s == "" and end_s == "":
        return (0, file_size - 1)

    if start_s == "":
        length = int(end_s)
        if length <= 0:
            raise HTTPException(status_code=416, detail="Invalid range")
        start = max(0, file_size - length)
        end = file_size - 1
    else:
        start = int(start_s)
        end = file_size - 1 if end_s == "" else int(end_s)
        if start > end or start >= file_size:
            raise HTTPException(status_code=416, detail="Invalid range")
    return (max(0, start), min(end, file_size - 1))

async def _get_file_and_item(db: AsyncSession, file_id: str) -> tuple[MediaFile, Optional[MediaItem]]:
    mf = await db.get(MediaFile, file_id)
    if not mf:
        raise HTTPException(status_code=404, detail="File not found")
    item = await db.get(MediaItem, mf.media_item_id) if mf.media_item_id else None
    return mf, item

# ──────────────────────────────────────────────────────────────────────────────
# Codec & browser detection
# ──────────────────────────────────────────────────────────────────────────────

def ffprobe_streams(path: str) -> dict:
    """Return first video/audio stream info: vcodec, acodec, v_profile, v_pix_fmt, width, height"""
    info = {"vcodec": None, "acodec": None, "v_profile": None, "v_pix_fmt": None, "width": None, "height": None}
    try:
        out = subprocess.check_output(["ffprobe", "-v", "error", "-show_streams", "-of", "json", path])
        data = json.loads(out.decode("utf-8"))
        got_v = got_a = False
        for s in data.get("streams", []):
            ct = s.get("codec_type")
            if ct == "video" and not got_v:
                info["vcodec"] = s.get("codec_name")
                info["v_profile"] = s.get("profile")
                info["v_pix_fmt"] = s.get("pix_fmt")
                info["width"] = s.get("width")
                info["height"] = s.get("height")
                got_v = True
            elif ct == "audio" and not got_a:
                info["acodec"] = s.get("codec_name")
                got_a = True
            if got_v and got_a:
                break
    except Exception:
        pass
    return info

def browser_caps(user_agent: str) -> dict:
    ua = (user_agent or "").lower()
    is_safari = "safari" in ua and "chrome" not in ua and "chromium" not in ua
    is_ios = "iphone" in ua or "ipad" in ua
    is_firefox = "firefox" in ua
    supports = {
        "mp4_h264_aac": True,
        "mp4_hevc_aac": is_safari or is_ios,
        "webm_vp9_opus": not is_safari,
        "ac3_passthrough": False,
        "dts_passthrough": False,
    }
    if is_firefox:
        supports["mp4_hevc_aac"] = False
    return supports

def _is_direct_play_ok(path: str, info: dict, caps: dict) -> bool:
    ext = os.path.splitext(path)[1].lower()
    v = (info.get("vcodec") or "").lower()
    a = (info.get("acodec") or "").lower()
    pix = info.get("v_pix_fmt")
    prof = info.get("v_profile")

    if ext in {".mp4", ".m4v"}:
        if v == "h264" and a in {"aac", "mp3"} and _is_h264_8bit_browser_safe(prof, pix):
            return True
        if v in {"hevc", "h265"} and a in {"aac"} and caps.get("mp4_hevc_aac", False) and _is_8bit_420(pix):
            return True
        return False
    if ext == ".webm":
        return caps["webm_vp9_opus"] and v in {"vp9", "vp8"} and a in {"opus", "vorbis"}
    return False

# ──────────────────────────────────────────────────────────────────────────────
# Remux builder
# ──────────────────────────────────────────────────────────────────────────────

def _remux_cmd(path: str, copy_video: bool, transcode_audio_to_aac: bool):
    args = [
        "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
        "-fflags", "+genpts", "-avoid_negative_ts", "make_zero",
        "-i", path, "-map", "0:v:0", "-map", "0:a:0?",
        "-c:v", "copy" if copy_video else "libx264",
        *(["-pix_fmt", "yuv420p", "-preset", "veryfast", "-crf", "21"] if not copy_video else []),
        "-c:a", "copy" if not transcode_audio_to_aac else "aac",
        *(["-b:a", "160k"] if transcode_audio_to_aac else []),
        "-movflags", "frag_keyframe+empty_moov+faststart",
        "-f", "mp4", "pipe:1",
        "-max_muxing_queue_size", "1024",
    ]
    return args

def _pipe(cmd):
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="FFmpeg not found")
    try:
        while True:
            chunk = proc.stdout.read(64 * 1024)
            if not chunk:
                break
            yield chunk
    finally:
        try:
            proc.kill()
        except Exception:
            pass

# ──────────────────────────────────────────────────────────────────────────────
# Pages
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/{file_id}", response_class=HTMLResponse)
async def player_page(
    file_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    mf, item = await _get_file_and_item(db, file_id)
    path = mf.path
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Missing media file on disk")
    poster = (item.extra_json or {}).get("poster") if item and item.extra_json else None
    return request.app.state.templates.TemplateResponse(
        "player.html",
        {"request": request, "file": mf, "item": item, "poster": poster or "/static/img/placeholder.png",
         "play_url": f"/stream/{file_id}/hls/master.m3u8"},
    )

# ──────────────────────────────────────────────────────────────────────────────
# HLS endpoints
# ──────────────────────────────────────────────────────────────────────────────


# ──────────────────────────────────────────────────────────────────────────────
# Direct file streaming (Range)
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/{file_id}/file")
async def stream_file(
    file_id: str,
    request: Request,
    range: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    mf, _ = await _get_file_and_item(db, file_id)
    path = mf.path
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Missing media file on disk")

    file_stat = os.stat(path)
    file_size = file_stat.st_size
    content_type, _ = mimetypes.guess_type(path)
    content_type = content_type or "application/octet-stream"

    last_mod = datetime.utcfromtimestamp(int(file_stat.st_mtime)).strftime("%a, %d %b %Y %H:%M:%S GMT")
    etag = f'W/"{hashlib.md5(str(file_stat.st_mtime_ns).encode()).hexdigest()}"'

    if request.method == "HEAD":
        return Response(
            status_code=200,
            headers={
                "Content-Type": content_type,
                "Content-Length": str(file_size),
                "Accept-Ranges": "bytes",
                "ETag": etag,
                "Last-Modified": last_mod,
                "Cache-Control": "private, max-age=0, must-revalidate",
            },
        )

    if not range:
        return FileResponse(
            path,
            media_type=content_type,
            filename=os.path.basename(path),
            headers={
                "Accept-Ranges": "bytes",
                "Content-Disposition": f'inline; filename="{os.path.basename(path)}"',
                "ETag": etag,
                "Last-Modified": last_mod,
                "Cache-Control": "private, max-age=0, must-revalidate",
            },
        )

    try:
        start, end = _parse_range(range, file_size)
    except HTTPException as e:
        if e.status_code == 416:
            return Response(
                status_code=416,
                headers={"Content-Range": f"bytes */{file_size}", "Accept-Ranges": "bytes"},
            )
        raise

    chunk_size = 1024 * 1024  # 1 MiB
    length = end - start + 1

    async def _iter_file_async(path: str, start: int, length: int, chunk_size: int, request: Request):
        with open(path, "rb") as f:
            f.seek(start)
            remaining = length
            while remaining > 0:
                if await request.is_disconnected():
                    break
                to_read = min(chunk_size, remaining)
                data = await to_thread.run_sync(f.read, to_read)
                if not data:
                    break
                remaining -= len(data)
                yield data

    headers = {
        "Content-Type": content_type,
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(length),
        "Content-Disposition": f'inline; filename="{os.path.basename(path)}"',
        "ETag": etag,
        "Last-Modified": last_mod,
        "Cache-Control": "private, max-age=0, must-revalidate",
    }
    return StreamingResponse(_iter_file_async(path, start, length, chunk_size, request), status_code=206, headers=headers)

# ──────────────────────────────────────────────────────────────────────────────
# Remux / Auto
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/{file_id}/remux")
async def stream_remux(
    file_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    mf, _ = await _get_file_and_item(db, file_id)
    path = mf.path
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Missing media file on disk")

    info = ffprobe_streams(path)
    caps = browser_caps(request.headers.get("user-agent", ""))

    copy_video = _can_copy_video(info, caps)
    transcode_audio = (info.get("acodec") or "").lower() not in {"aac", "mp3"}

    cmd = _remux_cmd(path, copy_video=copy_video, transcode_audio_to_aac=transcode_audio)
    return StreamingResponse(_pipe(cmd), media_type="video/mp4", headers={"Cache-Control": "no-store"})

@router.get("/{file_id}/auto")
async def stream_auto(
    file_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    mf, _ = await _get_file_and_item(db, file_id)
    path = mf.path
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Missing media file on disk")

    caps = browser_caps(request.headers.get("user-agent", ""))
    info = ffprobe_streams(path)

    # Truly direct-playable? Let /file handle Range.
    if _is_direct_play_ok(path, info, caps):
        return RedirectResponse(url=f"/stream/{file_id}/file", status_code=302)

    # Otherwise, remux (copy video if safe; re-encode audio to AAC if needed).
    copy_video = _can_copy_video(info, caps) and not (request.query_params.get("nocopy", "").lower() in {"1", "true", "yes"})
    transcode_audio = (info.get("acodec") or "").lower() not in {"aac", "mp3"}

    cmd = _remux_cmd(path, copy_video=copy_video, transcode_audio_to_aac=transcode_audio)
    hdr = {"Cache-Control": "no-store", "X-AMS-Path": "remux-copy" if copy_video else "remux-transcode"}
    return StreamingResponse(_pipe(cmd), media_type="video/mp4", headers=hdr)
