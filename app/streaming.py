from __future__ import annotations

import asyncio
import contextlib
import hashlib
import json
import mimetypes
import os
import shutil
import subprocess
import sys
import time
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, AsyncIterator, Dict

from anyio import to_thread
from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Query,
    Request,
    Response,
)
from fastapi.responses import (
    StreamingResponse,
    HTMLResponse,
    FileResponse,
    RedirectResponse,
    PlainTextResponse,
)
from sqlalchemy.ext.asyncio import AsyncSession

from .auth import get_current_user
from .config import settings
from .database import get_db
from .models import MediaFile, MediaItem
from .utils import ffprobe_info, decode_token

# -----------------------------------------------------------------------------
# Router
# -----------------------------------------------------------------------------
router = APIRouter(prefix="/stream", tags=["stream"])

# -----------------------------------------------------------------------------
# HLS (placeholder)
# -----------------------------------------------------------------------------
HLS_JOBS: Dict[str, dict] = {}
HLS_STALE_SECONDS = 120


async def cleanup_hls_jobs() -> None:
    now = time.time()
    for fid, job in list(HLS_JOBS.items()):
        if now - job.get("last", now) > HLS_STALE_SECONDS:
            proc = job.get("proc")
            with contextlib.suppress(Exception):
                if proc and proc.poll() is None:  # type: ignore[attr-defined]
                    proc.kill()
            with contextlib.suppress(Exception):
                shutil.rmtree(job.get("dir"), ignore_errors=True)
            HLS_JOBS.pop(fid, None)


# -----------------------------------------------------------------------------
# Executable discovery
# -----------------------------------------------------------------------------
def _first_nonempty(*vals: Optional[str]) -> str:
    for v in vals:
        if v:
            return v
    return ""


def _ff_bin_from_bundle(name: str) -> str:
    try:
        candidates: list[str] = []
        names = [name + (".exe" if os.name == "nt" else ""), name]
        if getattr(sys, "frozen", False):
            if getattr(sys, "_MEIPASS", None):
                base = sys._MEIPASS  # type: ignore
                candidates += [os.path.join(base, n) for n in names]
            exe_dir = os.path.dirname(sys.executable)
            candidates += [os.path.join(exe_dir, n) for n in names]
        candidates += [os.path.abspath(n) for n in names]
        for c in candidates:
            if os.path.exists(c):
                return c
        # Log error info if not found (so it's visible in console)
        if getattr(sys, "frozen", False):
            import logging
            log = logging.getLogger(__name__)
            log.error(f"ffmpeg bundle lookup for '{name}' FAILED: frozen={sys.frozen}, _MEIPASS={getattr(sys, '_MEIPASS', None)}, exe_dir={os.path.dirname(sys.executable) if sys.executable else None}")
            log.error(f"Checked candidates: {candidates}")
            # List what files actually exist in _MEIPASS
            if getattr(sys, "_MEIPASS", None):
                try:
                    import os
                    meipass_files = [f for f in os.listdir(sys._MEIPASS) if f.endswith(('.exe', ''))][:20]
                    log.error(f"Files in _MEIPASS (first 20): {meipass_files}")
                except Exception:
                    pass
    except Exception as e:
        import logging
        log = logging.getLogger(__name__)
        log.debug(f"ffmpeg bundle lookup error: {e}")
    return ""


def ffmpeg_exe() -> str:
    result = _first_nonempty(
        os.getenv("FFMPEG_BIN"),
        os.getenv("FFMPEG_PATH"),
        getattr(settings, "FFMPEG_PATH", None),
        _ff_bin_from_bundle("ffmpeg"),
    ) or "ffmpeg"
    # If result is not absolute and we're frozen, verify it exists
    if getattr(sys, "frozen", False) and not os.path.isabs(result):
        # Try to resolve relative paths in frozen context
        if getattr(sys, "_MEIPASS", None):
            # Try both with and without .exe extension
            for name in [result, result + ".exe"] if not result.endswith(".exe") else [result]:
                meipass_path = os.path.join(sys._MEIPASS, name)  # type: ignore
                if os.path.exists(meipass_path):
                    return meipass_path
        exe_dir = os.path.dirname(sys.executable)
        # Try both with and without .exe extension
        for name in [result, result + ".exe"] if not result.endswith(".exe") else [result]:
            exe_dir_path = os.path.join(exe_dir, name)
            if os.path.exists(exe_dir_path):
                return exe_dir_path
    return result


def ffprobe_exe() -> str:
    result = _first_nonempty(
        os.getenv("FFPROBE_BIN"),
        os.getenv("FFPROBE_PATH"),
        getattr(settings, "FFPROBE_PATH", None),
        _ff_bin_from_bundle("ffprobe"),
    ) or "ffprobe"
    # If result is not absolute and we're frozen, verify it exists
    if getattr(sys, "frozen", False) and not os.path.isabs(result):
        # Try to resolve relative paths in frozen context
        if getattr(sys, "_MEIPASS", None):
            # Try both with and without .exe extension
            for name in [result, result + ".exe"] if not result.endswith(".exe") else [result]:
                meipass_path = os.path.join(sys._MEIPASS, name)  # type: ignore
                if os.path.exists(meipass_path):
                    return meipass_path
        exe_dir = os.path.dirname(sys.executable)
        # Try both with and without .exe extension
        for name in [result, result + ".exe"] if not result.endswith(".exe") else [result]:
            exe_dir_path = os.path.join(exe_dir, name)
            if os.path.exists(exe_dir_path):
                return exe_dir_path
    return result


# -----------------------------------------------------------------------------
# FFprobe cached probing
# -----------------------------------------------------------------------------
_FFPROBE_CACHE: "OrderedDict[tuple[str, int], dict]" = OrderedDict()
_FFPROBE_LOCK = asyncio.Lock()
_FFPROBE_CACHE_MAX = int(os.getenv("FFPROBE_CACHE_MAX", "256"))


async def ffprobe_streams(path: str) -> dict:
    empty = {
        "vcodec": None,
        "acodec": None,
        "v_profile": None,
        "v_pix_fmt": None,
        "width": None,
        "height": None,
        "channels": None,
        "bitrate": None,
    }
    try:
        st = os.stat(path)
        key = (path, int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9))))
    except Exception:
        return dict(empty)

    async with _FFPROBE_LOCK:
        if key in _FFPROBE_CACHE:
            info = _FFPROBE_CACHE.pop(key)
            _FFPROBE_CACHE[key] = info
            return dict(info)

    try:
        proc = await asyncio.create_subprocess_exec(
            ffprobe_exe(),
            "-v",
            "error",
            "-show_streams",
            "-of",
            "json",
            path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        try:
            stdout, _ = await asyncio.wait_for(
                proc.communicate(), timeout=float(os.getenv("FFPROBE_TIMEOUT", "3.0"))
            )
        except asyncio.TimeoutError:
            with contextlib.suppress(Exception):
                proc.kill()
            return dict(empty)

        data = json.loads((stdout or b"").decode("utf-8", errors="ignore"))
        info = dict(empty)
        got_v = got_a = False
        for s in data.get("streams", []):
            ct = s.get("codec_type")
            if ct == "video" and not got_v:
                info["vcodec"] = s.get("codec_name")
                info["v_profile"] = s.get("profile")
                info["v_pix_fmt"] = s.get("pix_fmt")
                info["width"] = s.get("width")
                info["height"] = s.get("height")
                try:
                    br = s.get("bit_rate")
                    if br is not None:
                        info["bitrate"] = int(br)
                except Exception:
                    pass
                got_v = True
            elif ct == "audio" and not got_a:
                info["acodec"] = s.get("codec_name")
                try:
                    ch = s.get("channels")
                    if ch is not None:
                        info["channels"] = int(ch)
                except Exception:
                    pass
                got_a = True
            if got_v and got_a:
                break
    except Exception:
        return dict(empty)

    async with _FFPROBE_LOCK:
        _FFPROBE_CACHE[key] = info
        while len(_FFPROBE_CACHE) > _FFPROBE_CACHE_MAX:
            _FFPROBE_CACHE.popitem(last=False)

    return dict(info)


# -----------------------------------------------------------------------------
# Capability helpers
# -----------------------------------------------------------------------------
def _is_8bit_420(pix: Optional[str]) -> bool:
    return (pix or "").lower() in {"yuv420p", "yuvj420p"}


def _is_h264_8bit_browser_safe(profile: Optional[str], pix: Optional[str]) -> bool:
    if not _is_8bit_420(pix):
        return False
    p = (profile or "").lower()
    return not any(x in p for x in ("10", "hi10", "4:2:2", "4:4:4"))


def browser_caps(user_agent: str) -> dict:
    ua = (user_agent or "").lower()
    is_safari = "safari" in ua and "chrome" not in ua and "chromium" not in ua
    is_ios = "iphone" in ua or "ipad" in ua
    is_firefox = "firefox" in ua
    caps = {
        "mp4_h264_aac": True,
        "mp4_hevc_aac": is_safari or is_ios,
        "webm_vp9_opus": not is_safari,
    }
    if is_firefox:
        caps["mp4_hevc_aac"] = False
    return caps


def _can_copy_video(info: dict, caps: dict) -> bool:
    v = (info.get("vcodec") or "").lower()
    pix = info.get("v_pix_fmt")
    prof = info.get("v_profile")
    if v == "h264":
        return _is_h264_8bit_browser_safe(prof, pix)
    if v in {"hevc", "h265"}:
        return caps.get("mp4_hevc_aac", False) and _is_8bit_420(pix)
    return False


def _is_direct_play_ok(path: str, info: dict, caps: dict) -> bool:
    ext = os.path.splitext(path)[1].lower()
    v = (info.get("vcodec") or "").lower()
    a = (info.get("acodec") or "").lower()
    pix = info.get("v_pix_fmt")
    prof = info.get("v_profile")
    if ext in {".mp4", ".m4v"}:
        if v == "h264" and a in {"aac", "mp3"} and _is_h264_8bit_browser_safe(prof, pix):
            return True
        if (
            v in {"hevc", "h265"}
            and a == "aac"
            and caps.get("mp4_hevc_aac", False)
            and _is_8bit_420(pix)
        ):
            return True
        return False
    if ext == ".webm":
        return caps["webm_vp9_opus"] and v in {"vp9", "vp8"} and a in {"opus", "vorbis"}
    return False


# -----------------------------------------------------------------------------
# DB helpers + persistence
# -----------------------------------------------------------------------------
async def _get_file_and_item(
    db: AsyncSession, file_id: str
) -> tuple[MediaFile, Optional[MediaItem]]:
    mf = await db.get(MediaFile, file_id)
    if not mf:
        raise HTTPException(404, "File not found")
    item = await db.get(MediaItem, mf.media_item_id) if mf.media_item_id else None
    return mf, item


async def _maybe_persist_probe(
    db: AsyncSession, mf: MediaFile, path: str, info: dict
) -> None:
    try:
        st = os.stat(path)
    except Exception:
        return
    ext = os.path.splitext(path)[1].lower().lstrip(".") or None
    size_bytes = st.st_size
    want = {
        "container": ext,
        "vcodec": info.get("vcodec") or None,
        "acodec": info.get("acodec") or None,
        "channels": info.get("channels") or None,
        "width": info.get("width") or None,
        "height": info.get("height") or None,
        "bitrate": info.get("bitrate") or None,
        "size_bytes": size_bytes,
    }
    changed = False
    for k, v in want.items():
        if getattr(mf, k, None) != v and v is not None:
            setattr(mf, k, v)
            changed = True
    if changed:
        with contextlib.suppress(Exception):
            await db.flush()
            await db.commit()


# -----------------------------------------------------------------------------
# Range / MOOV helpers
# -----------------------------------------------------------------------------
MIN_INITIAL_BYTES = int(os.getenv("STREAM_MIN_INITIAL_BYTES", str(1024 * 1024)))   # 1MB
MOOV_SCAN_LIMIT = int(os.getenv("STREAM_MOOV_SCAN_LIMIT", str(3 * 1024 * 1024)))   # 3MB
CHUNK_SIZE = int(os.getenv("STREAM_RANGE_CHUNK", str(2 * 1024 * 1024)))
FASTSTART_THRESHOLD = int(os.getenv("STREAM_FASTSTART_THRESHOLD", str(512 * 1024)))        # 512KB
PSEUDO_INITIAL_END = int(os.getenv("STREAM_PSEUDO_INITIAL_END", str(4 * 1024 * 1024 - 1))) # 4MB - 1


def _http_date(ts: float) -> str:
    return datetime.utcfromtimestamp(int(ts)).strftime("%a, %d %b %Y %H:%M:%S GMT")


def _etag(stat) -> str:
    base = f"{getattr(stat,'st_mtime_ns',int(stat.st_mtime*1e9))}-{stat.st_size}"
    return f'W/"{hashlib.md5(base.encode()).hexdigest()}"'


def _guess_ct(path: str) -> str:
    ct, _ = mimetypes.guess_type(path)
    if not ct or ct == "application/octet-stream":
        if path.lower().endswith((".mp4", ".m4v")):
            return "video/mp4"
    if path.lower().endswith((".mp4", ".m4v")):
        return "video/mp4"
    return ct or "application/octet-stream"


def _scan_moov_offset(path: str) -> Optional[int]:
    try:
        with open(path, "rb") as f:
            data = f.read(MOOV_SCAN_LIMIT)
        idx = data.find(b"moov")
        if idx == -1:
            return None
        return idx
    except Exception:
        return None


def _parse_range(range_header: Optional[str], size: int) -> Tuple[int, int, bool]:
    if not range_header or not range_header.startswith("bytes="):
        return 0, size - 1, False
    spec_all = range_header.split("=", 1)[1].strip()
    multi = "," in spec_all
    spec = spec_all.split(",", 1)[0].strip() if multi else spec_all
    if "-" not in spec:
        return 0, size - 1, multi
    start_s, end_s = spec.split("-", 1)
    if start_s == "" and end_s == "":
        return 0, size - 1, multi
    if start_s == "":
        length = int(end_s)
        if length <= 0:
            raise HTTPException(416, "Invalid suffix bytes")
        length = min(length, size)
        return size - length, size - 1, multi
    start = int(start_s)
    if start >= size:
        raise HTTPException(416, "Range start outside file")
    end = size - 1 if end_s == "" else int(end_s)
    if end < start:
        raise HTTPException(416, "Invalid range span")
    end = min(end, size - 1)
    return start, end, multi


async def _iter_range(path: str, start: int, length: int, request: Request):
    with open(path, "rb") as f:
        f.seek(start)
        remaining = length
        while remaining > 0:
            if await request.is_disconnected():
                break
            to_read = min(CHUNK_SIZE, remaining)
            data = await to_thread.run_sync(f.read, to_read)
            if not data:
                break
            remaining -= len(data)
            yield data


# -----------------------------------------------------------------------------
# Auth token helper
# -----------------------------------------------------------------------------
def _auth_token_if_present(token: Optional[str]) -> None:
    if not token:
        return
    try:
        payload = decode_token(token)
        if not payload or payload.get("typ") != "access":
            raise HTTPException(401, "Invalid token")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(401, "Invalid token")


# -----------------------------------------------------------------------------
# Player page
# -----------------------------------------------------------------------------
@router.get("/{file_id}", response_class=HTMLResponse)
async def player_page(
    file_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    mf, item = await _get_file_and_item(db, file_id)
    path = getattr(mf, "path", None)
    if not path or not os.path.isfile(path):
        raise HTTPException(404, "Missing media file on disk")
    poster = (item.extra_json or {}).get("poster") if item and item.extra_json else None
    return request.app.state.templates.TemplateResponse(  # type: ignore[attr-defined]
        "player.html",
        {
            "request": request,
            "file": mf,
            "item": item,
            "poster": poster or "/static/img/placeholder.png",
            "play_url": f"/stream/{file_id}/auto",
        },
    )


# -----------------------------------------------------------------------------
# Direct (Range) streaming (with small-range expansion + pseudo-initial 206)
# -----------------------------------------------------------------------------
@router.get("/{file_id}/file")
async def stream_file(
    file_id: str,
    request: Request,
    range: Optional[str] = Header(None),
    token: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    if token:
        _auth_token_if_present(token)
    else:
        await get_current_user(request=request, db=db)

    mf, _ = await _get_file_and_item(db, file_id)
    path = getattr(mf, "path", None)
    if not path or not os.path.isfile(path):
        raise HTTPException(404, "Missing media file on disk")

    st = os.stat(path)
    size = st.st_size
    ct = _guess_ct(path)
    etag = _etag(st)
    lm = _http_date(st.st_mtime)

    if not range:
        if ct == "video/mp4":
            moov_offset = _scan_moov_offset(path)
            if moov_offset is None or moov_offset > FASTSTART_THRESHOLD:
                end = min(size - 1, PSEUDO_INITIAL_END)
                length = end + 1
                headers = {
                    "Accept-Ranges": "bytes",
                    "Content-Length": str(length),
                    "Content-Range": f"bytes 0-{end}/{size}",
                    "ETag": etag,
                    "Last-Modified": lm,
                    "Cache-Control": "no-transform, private, max-age=0, must-revalidate",
                    "Content-Disposition": f'inline; filename="{os.path.basename(path)}"',
                    "Content-Encoding": "identity",
                    "X-Pseudo-Initial": "1",
                    "X-Moov-Offset": str(moov_offset) if moov_offset is not None else "none",
                }
                return StreamingResponse(
                    _iter_range(path, 0, length, request),
                    status_code=206,
                    headers=headers,
                    media_type=ct,
                )
        headers = {
            "Accept-Ranges": "bytes",
            "Content-Length": str(size),
            "ETag": etag,
            "Last-Modified": lm,
            "Cache-Control": "no-transform, private, max-age=0, must-revalidate",
            "Content-Disposition": f'inline; filename="{os.path.basename(path)}"',
            "Content-Encoding": "identity",
        }
        return FileResponse(path, media_type=ct, headers=headers, filename=os.path.basename(path))

    try:
        start, end, multi = _parse_range(range, size)
    except HTTPException as e:
        if e.status_code == 416:
            return Response(
                status_code=416,
                headers={
                    "Content-Range": f"bytes */{size}",
                    "Accept-Ranges": "bytes",
                    "Content-Encoding": "identity",
                },
            )
        raise
    
    orig_start, orig_end = start, end

    if multi:
        # Expand to at least first 4MB or requested first range end
        end = min(size - 1, max(end, PSEUDO_INITIAL_END))
        print(f"[stream] multi-range requested; collapsing to single 0-{end}")

    requested_len = end - start + 1
    expanded = False
    if start == 0 and requested_len < MIN_INITIAL_BYTES and ct == "video/mp4":
        moov_offset = _scan_moov_offset(path)
        if moov_offset is None or moov_offset > requested_len:
            new_end = min(size - 1, max(end, MIN_INITIAL_BYTES - 1))
            if new_end != end:
                print(f"[stream] expanding initial range {orig_start}-{orig_end} -> 0-{new_end} (moov={moov_offset}, multi={multi})")
                end = new_end
                expanded = True

    length = end - start + 1
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(length),
        "Content-Range": f"bytes {start}-{end}/{size}",
        "ETag": etag,
        "Last-Modified": lm,
        "Cache-Control": "no-transform, private, max-age=0, must-revalidate",
        "Content-Disposition": f'inline; filename="{os.path.basename(path)}"',
        "Content-Encoding": "identity",
        "X-Range-Multi-Requested": "1" if multi else "0",
        "X-Range-Expanded": "1" if expanded else "0",
    }
    return StreamingResponse(
        _iter_range(path, start, length, request),
        status_code=206,
        headers=headers,
        media_type=ct,
    )


@router.head("/{file_id}/file")
async def head_stream_file(
    file_id: str,
    token: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    request: Request = None,
):
    if token:
        _auth_token_if_present(token)
    else:
        await get_current_user(request=request, db=db)
    mf, _ = await _get_file_and_item(db, file_id)
    path = getattr(mf, "path", None)
    if not path or not os.path.isfile(path):
        raise HTTPException(404, "Missing media file on disk")
    st = os.stat(path)
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(st.st_size),
        "ETag": _etag(st),
        "Last-Modified": _http_date(st.st_mtime),
        "Cache-Control": "no-transform, private, max-age=0, must-revalidate",
        "Content-Encoding": "identity",
    }
    return Response(status_code=200, headers=headers)


# -----------------------------------------------------------------------------
# Metadata
# -----------------------------------------------------------------------------
@router.get("/{file_id}/meta")
async def stream_meta(
    file_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    mf, item = await _get_file_and_item(db, file_id)
    duration_s: Optional[float] = None
    try:
        if item and getattr(item, "runtime_ms", None):
            duration_s = float(item.runtime_ms) / 1000.0
    except Exception:
        pass
    try:
        info = ffprobe_info(mf.path)
        if info.get("duration"):
            duration_s = float(info["duration"])
    except Exception:
        pass
    return {
        "file_id": mf.id,
        "item_id": item.id if item else None,
        "duration": duration_s,
    }


# -----------------------------------------------------------------------------
# Remux helpers
# -----------------------------------------------------------------------------
def _pick_audio_map_for_path(
    path: str,
    forced_idx: Optional[int] = None,
    preferred_lang: Optional[str] = None,
) -> str:
    try:
        proc = subprocess.run(
            [
                ffprobe_exe(),
                "-v",
                "quiet",
                "-select_streams",
                "a",
                "-show_entries",
                "stream=index,channels:stream_tags=language,title:disposition=default",
                "-of",
                "json",
                path,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
        data = json.loads((proc.stdout or b"").decode() or "{}")
        streams = data.get("streams", [])
        if forced_idx is not None and streams:
            idx = max(0, min(int(forced_idx), len(streams) - 1))
            return f"0:a:{idx}?"

        pref = (preferred_lang or os.getenv("ARCTIC_PREF_AUDIO_LANG", "eng")).lower()
        lang_alias = {"en": "eng", "eng": "en", "es": "spa", "spa": "es", "fr": "fra", "fra": "fr"}
        prefer = {pref}
        if pref in lang_alias:
            prefer.add(lang_alias[pref])

        def good(s, commentary=True):
            title = (s.get("tags", {}) or {}).get("title", "") or ""
            t = title.lower()
            if not commentary and any(x in t for x in ("commentary", "descriptive", "narration")):
                return False
            return True

        for pos, s in enumerate(streams):
            disp = (s.get("disposition") or {}).get("default")
            lang = (s.get("tags", {}) or {}).get("language", "").lower()
            if int(disp or 0) == 1 and lang in prefer and good(s, commentary=False):
                return f"0:a:{pos}?"
        for pos, s in enumerate(streams):
            lang = (s.get("tags", {}) or {}).get("language", "").lower()
            if lang in prefer and good(s, commentary=False):
                return f"0:a:{pos}?"
        for pos, s in enumerate(streams):
            if int((s.get("disposition") or {}).get("default") or 0) == 1:
                return f"0:a:{pos}?"
        for pos, s in enumerate(streams):
            if (s.get("tags", {}) or {}).get("language", "").lower() in prefer:
                return f"0:a:{pos}?"
        for pos, s in enumerate(streams):
            try:
                if int(s.get("channels") or 0) >= 2:
                    return f"0:a:{pos}?"
            except Exception:
                pass
        if streams:
            return "0:a:0?"
    except Exception:
        pass
    return "0:a:0?"


def _remux_cmd(
    path: str,
    copy_video: bool,
    transcode_audio: bool,
    a_map: str,
) -> list[str]:
    threads = os.getenv("FFMPEG_THREADS", "2")
    args: list[str] = [
        ffmpeg_exe(),
        "-nostdin",
        "-hide_banner",
        "-loglevel",
        "error",
        "-fflags",
        "+genpts",
        "-avoid_negative_ts",
        "make_zero",
        "-i",
        path,
        "-map",
        "0:v:0",
        "-map",
        a_map,
        "-c:v",
        "copy" if copy_video else "libx264",
    ]
    if not copy_video:
        args += [
            "-pix_fmt",
            "yuv420p",
            "-preset",
            os.getenv("FFMPEG_PRESET", "veryfast"),
            "-crf",
            os.getenv("FFMPEG_CRF", "23"),
            "-threads",
            threads,
        ]

    # Lower startup latency
    args += ["-muxdelay", "0", "-muxpreload", "0"]

    args += ["-c:a", "copy" if not transcode_audio else "aac"]
    if transcode_audio:
        args += [
            "-b:a",
            "160k",
            "-af",
            "aresample=async=1:first_pts=0:min_hard_comp=0.100",
        ]

    args += [
        "-movflags",
        "frag_keyframe+empty_moov+faststart",
        "-f",
        "mp4",
        "pipe:1",
        "-max_muxing_queue_size",
        "1024",
    ]
    return args


async def _pipe_async(cmd: list[str]) -> AsyncIterator[bytes]:
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
            creationflags=(0x00004000 if os.name == "nt" else 0),
        )
    except FileNotFoundError as e:
        import logging
        log = logging.getLogger(__name__)
        ffmpeg_path = ffmpeg_exe()
        log.error(f"FFmpeg not found. Attempted path: {ffmpeg_path}, cmd[0]: {cmd[0] if cmd else 'None'}, _MEIPASS: {getattr(sys, '_MEIPASS', None)}")
        raise HTTPException(500, f"FFmpeg not found. Path attempted: {ffmpeg_path}")

    try:
        assert proc.stdout
        chunk = int(os.getenv("STREAM_PIPE_CHUNK", str(256 * 1024)))
        while True:
            data = await proc.stdout.read(chunk)
            if not data:
                break
            yield data
    except asyncio.CancelledError:
        pass
    finally:
        with contextlib.suppress(Exception):
            proc.kill()


# -----------------------------------------------------------------------------
# Remux endpoint
# -----------------------------------------------------------------------------
@router.get("/{file_id}/remux")
async def stream_remux(
    file_id: str,
    request: Request,
    aidx: Optional[int] = Query(None),
    alang: Optional[str] = Query(None),
    token: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    if token:
        _auth_token_if_present(token)
    else:
        await get_current_user(request=request, db=db)

    mf, _ = await _get_file_and_item(db, file_id)
    path = getattr(mf, "path", None)
    if not path or not os.path.isfile(path):
        raise HTTPException(404, "Missing media file on disk")

    info = await ffprobe_streams(path)
    with contextlib.suppress(Exception):
        await _maybe_persist_probe(db, mf, path, info)

    caps = browser_caps(request.headers.get("user-agent", ""))
    copy_video = _can_copy_video(info, caps)
    transcode_audio = (info.get("acodec") or "").lower() not in {"aac", "mp3"}
    a_map = _pick_audio_map_for_path(path, forced_idx=aidx, preferred_lang=alang)
    cmd = _remux_cmd(path, copy_video, transcode_audio, a_map)
    hdr = {
    "Cache-Control": "no-store",
    "Content-Encoding": "identity",
    "Accept-Ranges": "bytes",
    "Content-Disposition": f'inline; filename="{os.path.basename(path)}"',
    "X-AMS-Path": "remux-copy" if copy_video else "remux-transcode",
}
    return StreamingResponse(_pipe_async(cmd), media_type="video/mp4", headers=hdr)


# -----------------------------------------------------------------------------
# Auto decision
# -----------------------------------------------------------------------------
@router.get("/{file_id}/auto")
async def stream_auto(
    file_id: str,
    request: Request,
    aidx: Optional[int] = Query(None),
    alang: Optional[str] = Query(None),
    token: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    if token:
        _auth_token_if_present(token)
    else:
        await get_current_user(request=request, db=db)

    mf, _ = await _get_file_and_item(db, file_id)
    path = getattr(mf, "path", None)
    if not path or not os.path.isfile(path):
        raise HTTPException(404, "Missing media file on disk")

    caps = browser_caps(request.headers.get("user-agent", ""))
    info = await ffprobe_streams(path)
    with contextlib.suppress(Exception):
        await _maybe_persist_probe(db, mf, path, info)

    if _is_direct_play_ok(path, info, caps):
        return RedirectResponse(url=f"/stream/{file_id}/file", status_code=302)

    copy_video = _can_copy_video(info, caps) and request.query_params.get(
        "nocopy", ""
    ).lower() not in {"1", "true", "yes"}
    transcode_audio = (info.get("acodec") or "").lower() not in {"aac", "mp3"}
    a_map = _pick_audio_map_for_path(path, forced_idx=aidx, preferred_lang=alang)
    cmd = _remux_cmd(path, copy_video, transcode_audio, a_map)
    hdr = {
        "Cache-Control": "no-store",
        "X-AMS-Path": "auto-remux-copy" if copy_video else "auto-remux-transcode",
        "Content-Encoding": "identity",
    }
    return StreamingResponse(_pipe_async(cmd), media_type="video/mp4", headers=hdr)


# -----------------------------------------------------------------------------
# Mobile (token-required) direct stream
# -----------------------------------------------------------------------------
@router.get("/{file_id}/mobile")
async def stream_file_mobile(
    file_id: str,
    request: Request,
    range: Optional[str] = Header(None),
    token: Optional[str] = Query(...),
    db: AsyncSession = Depends(get_db),
):
    _auth_token_if_present(token)
    qs = f"?token={token}" if token else ""