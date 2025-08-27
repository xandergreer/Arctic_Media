# app/streaming_hls.py
from __future__ import annotations

import asyncio, contextlib, hashlib, logging, os, shlex, signal, tempfile, time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse, PlainTextResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .auth import get_current_user, ACCESS_COOKIE
from .database import get_db
from .models import MediaItem, MediaFile
from .utils import create_token, decode_token

log = logging.getLogger("hls")

# Routers
router = APIRouter(prefix="/stream", tags=["stream"])
jf_router = APIRouter(prefix="/Videos", tags=["videos"])

# ──────────────────────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────────────────────
HLS_SEG_DUR = 2.0                  # shorter segments → faster transcoding, less buffering
DEFAULT_GOP = 48                   # smaller GOP for faster encoding
CLEANUP_IDLE_SECS = 600

TRANSCODE_ROOT = Path(os.getenv("ARCTIC_TRANSCODE_DIR", tempfile.gettempdir())) / "arctic_hls"
TRANSCODE_ROOT.mkdir(parents=True, exist_ok=True)

MEDIA_ROOT = Path(os.getenv("ARCTIC_MEDIA_ROOT", "")).expanduser()
STREAM_AUDIENCE = "stream-segment"

# ──────────────────────────────────────────────────────────────────────────────
# Job registry
# ──────────────────────────────────────────────────────────────────────────────
@dataclass
class TranscodeJob:
    job_id: str
    item_id: str
    container: str  # "ts" | "fmp4"
    vcodec: str
    acodec: str
    seg_dur: float = HLS_SEG_DUR
    gop: int = DEFAULT_GOP
    workdir: Path = field(default_factory=lambda: Path(
        tempfile.mkdtemp(prefix="arctic_hls_", dir=str(TRANSCODE_ROOT))
    ))
    proc: Optional[asyncio.subprocess.Process] = None
    started_at: float = field(default_factory=time.time)
    last_access: float = field(default_factory=time.time)

    def touch(self) -> None:
        self.last_access = time.time()

_JOBS: Dict[str, TranscodeJob] = {}
_ITEM_JOB: Dict[str, str] = {}

# ──────────────────────────────────────────────────────────────────────────────
# Security helpers
# ──────────────────────────────────────────────────────────────────────────────
def _issue_seg_token(payload: dict, minutes: int = 5) -> str:
    for kwargs in (
        {"expires_minutes": minutes},
        {"minutes": minutes},
        {"expires_in": minutes * 60},
        {"ttl_seconds": minutes * 60},
        {"expires_seconds": minutes * 60},
    ):
        try:
            return create_token(payload, **kwargs)  # type: ignore[arg-type]
        except TypeError:
            continue
    return create_token(payload)

async def ensure_segment_auth(request: Request) -> None:
    tok = request.query_params.get("t")
    if tok:
        with contextlib.suppress(Exception):
            p = decode_token(tok)
            if p.get("aud") == STREAM_AUDIENCE:
                return
    cookie = request.cookies.get(ACCESS_COOKIE)
    if cookie:
        with contextlib.suppress(Exception):
            p = decode_token(cookie)
            if p.get("typ") == "access":
                return
    raise HTTPException(401, "Unauthorized for segment")

# ──────────────────────────────────────────────────────────────────────────────
# Lookups (accept item id or file id)
# ──────────────────────────────────────────────────────────────────────────────
async def _resolve_item_and_src(db: AsyncSession, any_id: str) -> Tuple[MediaItem, MediaFile]:
    item = await db.get(MediaItem, any_id)
    if item:
        mf = (await db.execute(select(MediaFile).where(MediaFile.media_item_id == item.id))).scalars().first()
        if not mf:
            raise HTTPException(404, "Media file missing")
        return item, mf

    mf = await db.get(MediaFile, any_id)
    if mf:
        item = await db.get(MediaItem, mf.media_item_id)
        if not item:
            raise HTTPException(404, "Item not found for file")
        return item, mf

    raise HTTPException(404, "Item or file not found")

async def get_item_and_file(db: AsyncSession, any_id: str) -> Tuple[MediaItem, MediaFile]:
    return await _resolve_item_and_src(db, any_id)

def _resolve_src_path(file_row: MediaFile) -> Path:
    for attr in ("full_path", "path", "file_path", "abs_path"):
        val = getattr(file_row, attr, None)
        if val:
            p = Path(val)
            return p if p.is_absolute() or not MEDIA_ROOT else (MEDIA_ROOT / p)
    ej = getattr(file_row, "extra_json", None) or {}
    for key in ("full_path", "path", "file_path", "abs_path"):
        val = ej.get(key)
        if val:
            p = Path(val)
            return p if p.is_absolute() or not MEDIA_ROOT else (MEDIA_ROOT / p)
    raise HTTPException(500, "MediaFile has no usable disk path")

# ──────────────────────────────────────────────────────────────────────────────
# Job id / lookup
# ──────────────────────────────────────────────────────────────────────────────
def make_job_id(item_id: str, container: str, vcodec: str, acodec: str) -> str:
    h = hashlib.sha1()
    h.update(f"{item_id}|{container}|{vcodec}|{acodec}|{HLS_SEG_DUR}".encode())
    return h.hexdigest()[:16]

async def get_or_create_job(item_id: str, container: str, vcodec: str, acodec: str) -> TranscodeJob:
    job_id = make_job_id(item_id, container, vcodec, acodec)
    job = _JOBS.get(job_id)
    if not job:
        job = TranscodeJob(job_id=job_id, item_id=item_id, container=container, vcodec=vcodec, acodec=acodec)
        _JOBS[job_id] = job
    _ITEM_JOB[item_id] = job_id
    job.touch()
    return job

# ──────────────────────────────────────────────────────────────────────────────
# ffmpeg
# ──────────────────────────────────────────────────────────────────────────────
def ffmpeg_exe() -> str:
    return os.getenv("FFMPEG_BIN", "ffmpeg")

def _needs_ts_annexb(container: str, vcodec: str) -> bool:
    # When copying H.264 into MPEG-TS, ensure Annex B bitstream
    return container == "ts" and vcodec.lower() == "copy"

async def start_or_warm_job(src_path: Path, job: TranscodeJob) -> None:
    job.touch()
    if job.proc and job.proc.returncode is None:
        return

    ext = "m4s" if job.container == "fmp4" else "ts"
    segpat = str(job.workdir / f"seg_%05d.{ext}")
    m3u8_out = str(job.workdir / "ffmpeg.m3u8")

    vcodec = (job.vcodec or "copy").lower()
    acodec = (job.acodec or "aac").lower()

    base = [
        ffmpeg_exe(), "-hide_banner", "-nostdin", "-y",
        "-fflags", "+genpts+discardcorrupt",  # Discard corrupt frames for faster processing
        "-i", str(src_path),
        "-map", "0:v:0", "-map", "0:a:0?", "-map", "-0:s", "-dn", "-sn",
        "-max_muxing_queue_size", "1024",  # Smaller queue for faster processing
        "-vsync", "cfr",
        "-reset_timestamps", "1",
        "-avoid_negative_ts", "make_zero",  # Handle timestamp issues
    ]

    # Always use H.264 for maximum browser compatibility
    vpart = [
        "-c:v", "h264",
        "-preset", os.getenv("FFMPEG_PRESET", "ultrafast"),  # Fastest preset for real-time transcoding
        "-g", str(job.gop), "-keyint_min", str(job.gop),
        "-force_key_frames", f"expr:gte(t,n_forced*{job.seg_dur})",
        "-profile:v", "baseline", "-level", "3.1", "-pix_fmt", "yuv420p",  # Lower profile for faster encoding
        "-crf", "28",  # Lower quality for faster encoding
        "-tune", "fastdecode",  # Optimize for fast decoding
        "-threads", "0",  # Use all available CPU threads
    ]

    # Ensure audio is always AAC for browser compatibility
    apart = [
        "-c:a", "aac",
        "-ac", os.getenv("FFMPEG_AC", "2"),
        "-ar", os.getenv("FFMPEG_AR", "44100"),  # Lower sample rate for faster encoding
        "-b:a", os.getenv("FFMPEG_ABR", "128k"),  # Lower bitrate for faster encoding
        "-aac_coder", "fast",  # Faster AAC encoding
    ]

    hls = [
        "-f", "hls",
        "-hls_time", f"{job.seg_dur}",
        "-hls_list_size", "10",  # Keep more segments in playlist for better buffering
        "-hls_playlist_type", "event",
        "-hls_segment_filename", segpat,
        "-sc_threshold", "0",
        "-hls_flags", "independent_segments+delete_segments",  # Delete old segments to save space
        "-hls_start_number_source", "generic",  # Start from 0 for consistent numbering
    ]
    if job.container == "fmp4":
        hls += [
            "-hls_segment_type", "fmp4", 
            "-hls_fmp4_init_filename", "init.mp4",
            "-master_pl_name", "unused_master.m3u8",
            "-movflags", "+faststart+frag_keyframe+empty_moov",
        ]
    else:
        hls += ["-hls_segment_type", "mpegts"]
        if _needs_ts_annexb(job.container, vcodec):
            hls = ["-bsf:v", "h264_mp4toannexb", *hls]

    cmd = [*base, *vpart, *apart, *hls, m3u8_out]
    log.info("ffmpeg cwd=%s cmd=%s", job.workdir, " ".join(shlex.quote(x) for x in cmd))

    job.proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, cwd=str(job.workdir)
    )

    # If remux fails instantly, fall back to h264 encode
    await asyncio.sleep(0.4)
    if job.proc.returncode is not None and vcodec == "copy":
        stderr = (await job.proc.stderr.read()).decode(errors="ignore")[:2000]
        log.warning("copy pipeline failed; retrying with h264 encode\n%s", stderr)
        job.vcodec = "h264"
        return await start_or_warm_job(src_path, job)

    if job.proc.returncode is not None:
        stderr = (await job.proc.stderr.read()).decode(errors="ignore")[:2000]
        log.error("ffmpeg exited code %s\n%s", job.proc.returncode, stderr)
        raise HTTPException(500, "Transcoder failed to start")

# ──────────────────────────────────────────────────────────────────────────────
# Debug endpoint to check file format
# ──────────────────────────────────────────────────────────────────────────────
@router.get("/{item_id}/debug")
async def debug_file_info(
    item_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user),
):
    """Debug endpoint to check file format and compatibility"""
    item, file_row = await get_item_and_file(db, item_id)
    src_path = _resolve_src_path(file_row)
    
    if not src_path.exists():
        return {"error": "File not found", "path": str(src_path)}
    
    # Get basic file info
    stat = src_path.stat()
    suffix = src_path.suffix.lower()
    
    # Check if it's a compatible format for direct serving
    direct_compatible = suffix in ['.mp4', '.webm', '.ogg']
    
    return {
        "file_id": item_id,
        "path": str(src_path),
        "size": stat.st_size,
        "suffix": suffix,
        "direct_compatible": direct_compatible,
        "exists": True
    }

# ──────────────────────────────────────────────────────────────────────────────
# Direct file serving for compatible formats
# ──────────────────────────────────────────────────────────────────────────────
@router.head("/{item_id}/direct")
async def direct_file_head(item_id: str, request: Request, db: AsyncSession = Depends(get_db), user = Depends(get_current_user)):
    """HEAD request for direct file serving to check availability"""
    item, file_row = await get_item_and_file(db, item_id)
    src_path = _resolve_src_path(file_row)
    if not src_path.exists():
        raise HTTPException(404, "Source file missing")

    # Check if file is already browser-compatible
    if src_path.suffix.lower() in ['.mp4', '.webm', '.ogg']:
        return Response(
            status_code=200,
            headers={
                "Content-Type": "video/mp4" if src_path.suffix.lower() == '.mp4' else "video/webm",
                "Content-Length": str(src_path.stat().st_size),
                "Accept-Ranges": "bytes"
            }
        )
    
    raise HTTPException(404, "Direct serving not available for this format")

@router.get("/{item_id}/direct")
async def direct_file_serve(
    item_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user),
):
    """Direct file serving for browser-compatible formats (fastest option)"""
    item, file_row = await get_item_and_file(db, item_id)
    src_path = _resolve_src_path(file_row)
    if not src_path.exists():
        raise HTTPException(404, "Source file missing")

    # Check if file is already browser-compatible
    if src_path.suffix.lower() in ['.mp4', '.webm', '.ogg']:
        return FileResponse(
            src_path,
            media_type="video/mp4" if src_path.suffix.lower() == '.mp4' else "video/webm",
            headers={
                "Cache-Control": "public, max-age=3600",
                "Accept-Ranges": "bytes"
            }
        )
    
    # If not compatible, redirect to progressive fallback
    raise HTTPException(404, "Direct serving not available for this format")

# ──────────────────────────────────────────────────────────────────────────────
# Progressive MP4 fallback endpoint
# ──────────────────────────────────────────────────────────────────────────────
@router.get("/{item_id}/auto")
async def progressive_fallback(
    item_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user),
):
    """Progressive MP4 fallback with guaranteed browser-compatible codecs"""
    item, file_row = await get_item_and_file(db, item_id)
    src_path = _resolve_src_path(file_row)
    if not src_path.exists():
        raise HTTPException(404, "Source file missing")

    # Create a special job for progressive MP4
    job_id = f"prog_{make_job_id(item.id, 'mp4', 'h264', 'aac')}"
    job = _JOBS.get(job_id)
    
    if not job:
        job = TranscodeJob(
            job_id=job_id, 
            item_id=item.id, 
            container="mp4", 
            vcodec="h264", 
            acodec="aac"
        )
        _JOBS[job_id] = job

    # Check if we already have a compatible MP4
    mp4_path = job.workdir / "output.mp4"
    if not mp4_path.exists():
        await start_progressive_job(src_path, job)

    # Wait for the file to be ready
    if not await _wait_for_file(mp4_path, 10.0):
        raise HTTPException(500, "Progressive transcode failed")

    job.touch()
    return FileResponse(
        mp4_path, 
        media_type="video/mp4",
        headers={
            "Cache-Control": "public, max-age=3600",
            "Accept-Ranges": "bytes"
        }
    )

async def start_progressive_job(src_path: Path, job: TranscodeJob) -> None:
    """Start a progressive MP4 transcode with guaranteed browser compatibility"""
    job.touch()
    if job.proc and job.proc.returncode is None:
        return

    output_path = str(job.workdir / "output.mp4")

    cmd = [
        ffmpeg_exe(), "-hide_banner", "-nostdin", "-y",
        "-i", str(src_path),
        "-map", "0:v:0", "-map", "0:a:0?", "-map", "-0:s", "-dn", "-sn",
        "-c:v", "h264",
        "-preset", "veryfast",
        "-profile:v", "high",
        "-level", "4.1",
        "-pix_fmt", "yuv420p",
        "-g", "72",
        "-keyint_min", "72",
        "-sc_threshold", "0",
        "-c:a", "aac",
        "-ac", "2",
        "-ar", "48000",
        "-b:a", "160k",
        "-movflags", "+faststart",
        "-f", "mp4",
        output_path
    ]

    log.info("ffmpeg progressive cwd=%s cmd=%s", job.workdir, " ".join(shlex.quote(x) for x in cmd))

    job.proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, cwd=str(job.workdir)
    )

    if job.proc.returncode is not None:
        stderr = (await job.proc.stderr.read()).decode(errors="ignore")[:2000]
        log.error("progressive ffmpeg exited code %s\n%s", job.proc.returncode, stderr)
        raise HTTPException(500, "Progressive transcode failed")

# ──────────────────────────────────────────────────────────────────────────────
# Helpers: playlist rewrite & file wait
# ──────────────────────────────────────────────────────────────────────────────
async def _wait_for_file(p: Path, timeout_s: float = 5.0, poll: float = 0.05) -> bool:
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        if p.exists() and p.stat().st_size > 0:
            return True
        await asyncio.sleep(poll)
    return p.exists()

def _rewrite_ffmpeg_playlist(job: TranscodeJob, base_url: str, token: Optional[str]) -> str:
    m3u8_path = job.workdir / "ffmpeg.m3u8"
    if not m3u8_path.exists():
        return ""
    q = f"?t={token}" if token else ""
    out, have_type, have_header = [], False, False
    for ln in m3u8_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if ln.startswith("#EXTM3U"):
            have_header = True
            out.append(ln)
            continue
        s = ln.strip()
        if s.startswith("#EXT-X-MAP:"):
            out.append(f'#EXT-X-MAP:URI="{base_url}/init.mp4{q}"')
        elif s.startswith("#EXT-X-PLAYLIST-TYPE:"):
            have_type = True
            out.append("#EXT-X-PLAYLIST-TYPE:EVENT")
        elif s and not s.startswith("#"):
            out.append(f"{base_url}/{s}{q}")
        else:
            out.append(ln)
    if not have_header:
        out.insert(0, "#EXTM3U")
    if not have_type:
        out.insert(1, "#EXT-X-PLAYLIST-TYPE:EVENT")
    return ("\n".join(out) + "\n")

# ──────────────────────────────────────────────────────────────────────────────
# /stream/* endpoints (native)
# ──────────────────────────────────────────────────────────────────────────────
@router.head("/{item_id}/master.m3u8")
async def hls_head_master(item_id: str):
    return Response(status_code=200, headers={"Content-Type": "application/vnd.apple.mpegurl"})

@router.get("/{item_id}/master.m3u8", response_class=PlainTextResponse)
async def hls_master(
    item_id: str,
    request: Request,
    container: str = "fmp4",
    vcodec: str = "copy",
    acodec: str = "aac",
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user),
):
    if container not in ("ts", "fmp4"):
        raise HTTPException(400, "container must be 'ts' or 'fmp4'")

    item, file_row = await get_item_and_file(db, item_id)
    src_path = _resolve_src_path(file_row)
    if not src_path.exists():
        raise HTTPException(404, "Source file missing")

    job = await get_or_create_job(item.id, container, vcodec, acodec)
    await start_or_warm_job(src_path, job)

    # Ensure initial objects exist
    await _wait_for_file(job.workdir / "ffmpeg.m3u8", 5.0)
    if container == "fmp4":
        await _wait_for_file(job.workdir / "init.mp4", 3.0)
        # Wait for fewer segments since we're using faster transcoding
        await _wait_for_file(job.workdir / "seg_00000.m4s", 3.0)
        await _wait_for_file(job.workdir / "seg_00001.m4s", 5.0)  # Wait for second segment
    else:
        await _wait_for_file(job.workdir / "seg_00000.ts", 3.0)
        await _wait_for_file(job.workdir / "seg_00001.ts", 5.0)  # Wait for second segment

    seg_token = _issue_seg_token({"aud": STREAM_AUDIENCE, "item": item.id, "job": job.job_id}, minutes=5)
    base_url = f"{request.base_url}stream/{item.id}/hls/{job.job_id}".rstrip("/")
    manifest = _rewrite_ffmpeg_playlist(job, base_url, seg_token)
    headers = {"Cache-Control": "no-store", "Pragma": "no-cache"}
    return Response(manifest, media_type="application/vnd.apple.mpegurl", headers=headers)

@router.get("/{item_id}/hls/{job_id}/init.mp4")
async def hls_init_segment(item_id: str, job_id: str, request: Request):
    await ensure_segment_auth(request)
    job = _JOBS.get(job_id)
    if not job or job.item_id != item_id:
        raise HTTPException(404)
    job.touch()
    p = job.workdir / "init.mp4"
    if not p.exists() and not await _wait_for_file(p, 5.0):
        raise HTTPException(404)
    return FileResponse(p, media_type="video/mp4", headers={"Cache-Control": "no-store"})

@router.get("/{item_id}/hls/{job_id}/{segment}")
async def hls_segment(item_id: str, job_id: str, segment: str, request: Request):
    await ensure_segment_auth(request)
    job = _JOBS.get(job_id)
    if not job or job.item_id != item_id:
        raise HTTPException(404)
    job.touch()

    if job.container == "ts" and not segment.endswith(".ts"):
        raise HTTPException(400)
    if job.container == "fmp4" and not segment.endswith(".m4s"):
        raise HTTPException(400)

    p = job.workdir / segment
    if not p.exists():
        raise HTTPException(404)
    media_type = "video/mp2t" if job.container == "ts" else "video/iso.segment"
    return FileResponse(p, media_type=media_type, headers={"Cache-Control": "no-store"})

# Legacy shims (some players probe these)
@router.get("/{item_id}/hls/master.m3u8", response_class=PlainTextResponse)
@router.get("/{item_id}/hls/index.m3u8", response_class=PlainTextResponse)
async def legacy_master(item_id: str, request: Request, db: AsyncSession = Depends(get_db), user = Depends(get_current_user)):
    item, _ = await get_item_and_file(db, item_id)
    return await hls_master(item_id=item.id, request=request, container="fmp4", db=db, user=user)

@router.get("/{item_id}/hls/init.mp4")
async def legacy_init(item_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    await ensure_segment_auth(request)
    item, mf = await get_item_and_file(db, item_id)
    real_id = item.id
    job_id = _ITEM_JOB.get(real_id)
    if not job_id:
        src = _resolve_src_path(mf)
        job = await get_or_create_job(real_id, "fmp4", "copy", "aac")
        await start_or_warm_job(src, job)
        job_id = job.job_id
    return await hls_init_segment(item_id=real_id, job_id=job_id, request=request)

@router.get("/{item_id}/hls/{segment}")
async def legacy_segment(item_id: str, segment: str, request: Request, db: AsyncSession = Depends(get_db)):
    await ensure_segment_auth(request)
    item, _ = await get_item_and_file(db, item_id)
    real_id = item.id
    job_id = _ITEM_JOB.get(real_id)
    if not job_id:
        raise HTTPException(404, "No active HLS job")
    return await hls_segment(item_id=real_id, job_id=job_id, segment=segment, request=request)

# ──────────────────────────────────────────────────────────────────────────────
# Emergency cleanup endpoint
# ──────────────────────────────────────────────────────────────────────────────
@router.post("/emergency-cleanup")
async def emergency_cleanup_endpoint(user = Depends(get_current_user)):
    """Emergency endpoint to stop all transcoding jobs and clear registry"""
    await _emergency_cleanup()
    return {"status": "cleanup_complete", "message": "All HLS jobs stopped and cleared"}

# ──────────────────────────────────────────────────────────────────────────────
# Jellyfin-style /Videos/* endpoints (compat)
# ──────────────────────────────────────────────────────────────────────────────
@jf_router.head("/{item_id}/master.m3u8")
async def jf_head_master(item_id: str, request: Request, db: AsyncSession = Depends(get_db), user = Depends(get_current_user)):
    return Response(status_code=200, headers={"Content-Type": "application/vnd.apple.mpegurl"})

@jf_router.get("/{item_id}/master.m3u8", response_class=PlainTextResponse)
async def jf_get_master(
    item_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user),
    segmentContainer: str = Query("mp4", pattern="^(mp4|ts)$"),
    videoCodec: Optional[str] = Query("copy"),
    audioCodec: Optional[str] = Query("aac"),
    Static: Optional[bool] = Query(None),
    playSessionId: Optional[str] = None,
):
    item, mf = await get_item_and_file(db, item_id)
    src = _resolve_src_path(mf)
    container = "fmp4" if segmentContainer == "mp4" else "ts"
    vcodec = (videoCodec or "copy").lower()
    acodec = (audioCodec or "aac").lower()

    job = await get_or_create_job(item.id, container, vcodec, acodec)
    await start_or_warm_job(src, job)

    band = 5_000_000
    lines = [
        "#EXTM3U",
        "#EXT-X-VERSION:7",
        f"#EXT-X-STREAM-INF:BANDWIDTH={band}",
        f"/Videos/{item.id}/hls/{job.job_id}/index.m3u8",
        "",
    ]
    return PlainTextResponse("\n".join(lines), media_type="application/vnd.apple.mpegurl")

@jf_router.get("/{item_id}/hls/{job_id}/index.m3u8", response_class=PlainTextResponse)
async def jf_variant_playlist(item_id: str, job_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    await ensure_segment_auth(request)
    job = _JOBS.get(job_id)
    if not job or job.item_id != item_id:
        raise HTTPException(404)
    job.touch()

    await _wait_for_file(job.workdir / "ffmpeg.m3u8", 5.0)
    if job.container == "fmp4":
        await _wait_for_file(job.workdir / "init.mp4", 5.0)
        await _wait_for_file(job.workdir / "seg_00000.m4s", 5.0)
    else:
        await _wait_for_file(job.workdir / "seg_00000.ts", 5.0)

    seg_token = _issue_seg_token({"aud": STREAM_AUDIENCE, "item": item_id, "job": job_id}, minutes=5)
    base_url = f"{request.base_url}Videos/{item_id}/hls/{job_id}".rstrip("/")
    manifest = _rewrite_ffmpeg_playlist(job, base_url, seg_token)
    return PlainTextResponse(manifest, media_type="application/vnd.apple.mpegurl")

@jf_router.get("/{item_id}/hls/{job_id}/{seg_no}.ts")
@jf_router.get("/{item_id}/hls/{job_id}/{seg_no}.m4s")
async def jf_segment(item_id: str, job_id: str, seg_no: str, request: Request):
    await ensure_segment_auth(request)
    job = _JOBS.get(job_id)
    if not job or job.item_id != item_id:
        raise HTTPException(404)
    job.touch()
    ext = "m4s" if job.container == "fmp4" else "ts"
    p = job.workdir / f"seg_{int(seg_no):05d}.{ext}"
    if not p.exists():
        raise HTTPException(404)
    media_type = "video/iso.segment" if ext == "m4s" else "video/MP2T"
    return FileResponse(p, media_type=media_type, headers={"Cache-Control": "no-store"})

# ──────────────────────────────────────────────────────────────────────────────
# Cleanup task
# ──────────────────────────────────────────────────────────────────────────────
async def _cleanup_loop():
    while True:
        try:
            now = time.time()
            to_remove: list[tuple[str, TranscodeJob]] = []
            for jid, job in list(_JOBS.items()):
                if (now - job.last_access) > CLEANUP_IDLE_SECS:
                    if job.proc and job.proc.returncode is None:
                        with contextlib.suppress(Exception):
                            job.proc.send_signal(signal.SIGINT)
                        try:
                            await asyncio.wait_for(job.proc.wait(), timeout=5)
                        except Exception:
                            with contextlib.suppress(Exception): job.proc.terminate()
                            with contextlib.suppress(Exception): job.proc.kill()
                    with contextlib.suppress(Exception):
                        for fp in job.workdir.glob("*"):
                            with contextlib.suppress(Exception): fp.unlink()
                        job.workdir.rmdir()
                    to_remove.append((jid, job))
            for jid, job in to_remove:
                _JOBS.pop(jid, None)
                if _ITEM_JOB.get(job.item_id) == jid:
                    _ITEM_JOB.pop(job.item_id, None)
        except Exception:
            pass
        await asyncio.sleep(15)

async def _emergency_cleanup():
    """Emergency cleanup to stop all ffmpeg processes and clear jobs"""
    log.warning("Performing emergency cleanup of all HLS jobs")
    
    # Stop all running processes
    for jid, job in list(_JOBS.items()):
        if job.proc and job.proc.returncode is None:
            try:
                job.proc.terminate()
                await asyncio.wait_for(job.proc.wait(), timeout=3)
            except:
                try:
                    job.proc.kill()
                except:
                    pass
    
    # Clear all jobs
    _JOBS.clear()
    _ITEM_JOB.clear()
    
    # Kill any remaining ffmpeg processes (Windows)
    if os.name == 'nt':
        try:
            await asyncio.create_subprocess_exec(
                "taskkill", "/f", "/im", "ffmpeg.exe",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
        except:
            pass

async def start_hls_cleanup_task(app):
    app.state.hls_cleanup_task = asyncio.create_task(_cleanup_loop())

async def stop_hls_cleanup_task(app):
    task = getattr(app.state, "hls_cleanup_task", None)
    if task:
        task.cancel()
        with contextlib.suppress(Exception):
            await task
    await _emergency_cleanup()
