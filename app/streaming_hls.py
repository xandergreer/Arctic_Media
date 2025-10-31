# app/streaming_hls.py
from __future__ import annotations

import asyncio, contextlib, hashlib, logging, math, os, shlex, signal, tempfile, time, shutil, sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse, PlainTextResponse, RedirectResponse, StreamingResponse
from anyio import to_thread
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .auth import get_current_user, ACCESS_COOKIE
from .config import settings
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
CLEANUP_IDLE_SECS = int(os.getenv("ARCTIC_HLS_IDLE_CLEANUP_SECS", "600"))
ORPHAN_MAX_AGE_SECS = int(os.getenv("ARCTIC_HLS_ORPHAN_MAX_AGE_SECS", "3600"))
# Optional soft cap for transcode cache; set ARCTIC_TRANSCODE_MAX_GB to enable size trimming
TRANSCODE_MAX_GB = float(os.getenv("ARCTIC_TRANSCODE_MAX_GB", "0"))

TRANSCODE_ROOT = Path(os.getenv("ARCTIC_TRANSCODE_DIR", tempfile.gettempdir())) / "arctic_hls"
TRANSCODE_ROOT.mkdir(parents=True, exist_ok=True)

MEDIA_ROOT = Path(os.getenv("ARCTIC_MEDIA_ROOT", "")).expanduser()
STREAM_AUDIENCE = "stream-segment"

# Windows process priority hint for ffmpeg to keep UI responsive and allow multiple streams
_WIN_BELOW_NORMAL = 0x00004000 if os.name == 'nt' else 0

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
    v_bitrate: Optional[str] = None   # e.g., "2500k"
    v_height: Optional[int] = None    # e.g., 480, 720, 1080
    a_map: Optional[str] = None       # explicit ffmpeg audio map (e.g., 0:a:0?)
    seg_dur: float = HLS_SEG_DUR
    gop: int = DEFAULT_GOP
    workdir: Path = field(init=False)
    proc: Optional[asyncio.subprocess.Process] = None
    started_at: float = field(default_factory=time.time)
    last_access: float = field(default_factory=time.time)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False, compare=False)

    def __post_init__(self) -> None:
        wd = TRANSCODE_ROOT / self.job_id
        try:
            wd.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        self.workdir = wd

    def touch(self) -> None:
        self.last_access = time.time()
        # Nudge lock file mtime for cross-process staleness detection
        try:
            lf = self.workdir / ".run.lock"
            if lf.exists():
                now = time.time()
                os.utime(lf, (now, now))
        except Exception:
            pass

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
def make_job_id(item_id: str, container: str, vcodec: str, acodec: str, v_bitrate: Optional[str] = None, v_height: Optional[int] = None, a_map: Optional[str] = None) -> str:
    h = hashlib.sha1()
    h.update(f"{item_id}|{container}|{vcodec}|{acodec}|{v_bitrate or ''}|{v_height or 0}|{a_map or ''}|{HLS_SEG_DUR}".encode())
    return h.hexdigest()[:16]

async def get_or_create_job(item_id: str, container: str, vcodec: str, acodec: str, v_bitrate: Optional[str] = None, v_height: Optional[int] = None, a_map: Optional[str] = None) -> TranscodeJob:
    job_id = make_job_id(item_id, container, vcodec, acodec, v_bitrate, v_height, a_map)
    job = _JOBS.get(job_id)
    if not job:
        # If a different job exists for this item, stop it to free resources
        prev_id = _ITEM_JOB.get(item_id)
        if prev_id and prev_id != job_id:
            old = _JOBS.get(prev_id)
            if old:
                try:
                    if old.proc and old.proc.returncode is None:
                        with contextlib.suppress(Exception): old.proc.send_signal(signal.SIGINT)
                        try:
                            await asyncio.wait_for(old.proc.wait(), timeout=3)
                        except Exception:
                            with contextlib.suppress(Exception): old.proc.terminate()
                            with contextlib.suppress(Exception): old.proc.kill()
                    with contextlib.suppress(Exception): shutil.rmtree(old.workdir, ignore_errors=True)
                finally:
                    _JOBS.pop(prev_id, None)
        job = TranscodeJob(job_id=job_id, item_id=item_id, container=container, vcodec=vcodec, acodec=acodec, v_bitrate=v_bitrate, v_height=v_height, a_map=a_map)
        _JOBS[job_id] = job
    _ITEM_JOB[item_id] = job_id
    job.touch()
    return job

# ──────────────────────────────────────────────────────────────────────────────
# ffmpeg
# ──────────────────────────────────────────────────────────────────────────────
def _first_nonempty(*vals: Optional[str]) -> str:
    for v in vals:
        if v:
            return v
    return ""

def _ff_bin_from_bundle(name: str) -> str:
    try:
        cand = []
        names = [name + (".exe" if os.name == 'nt' else ""), name]
        if getattr(sys, "frozen", False):
            if getattr(sys, "_MEIPASS", None):
                base = sys._MEIPASS  # type: ignore[attr-defined]
                cand += [os.path.join(base, n) for n in names]
            exe_dir = os.path.dirname(sys.executable)
            cand += [os.path.join(exe_dir, n) for n in names]
        cand += [os.path.abspath(n) for n in names]
        for p in cand:
            if p and os.path.exists(p):
                return p
    except Exception:
        pass
    return ""

def ffmpeg_exe() -> str:
    # Precedence: env/settings -> bundled -> PATH fallback
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
    # allow either FFPROBE_BIN or FFPROBE_PATH env overrides; also support settings
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

def _pick_audio_map_for_path(src_path: Path, preferred_lang: Optional[str] = None, forced_idx: Optional[int] = None) -> str:
    """Return an ffmpeg -map selector for the best audio stream.

    Prefers language tags 'eng'/'en' when present; otherwise picks the first
    audio stream with channels >= 2 if known; otherwise index 0.
    """
    try:
        import json, subprocess
        probe_cmd = [
            ffprobe_exe(), "-v", "quiet",
            "-show_entries", "stream=index,codec_type,codec_name,channels:stream_tags=language,title:disposition=default",
            "-select_streams", "a",
            "-of", "json", str(src_path)
        ]
        res = subprocess.run(probe_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=5)
        data = json.loads((res.stdout or b"").decode() or "{}")
        streams = data.get("streams", [])
        if forced_idx is not None and streams:
            try:
                pos = max(0, min(int(forced_idx), len(streams)-1))
                return f"0:a:{pos}?"
            except Exception:
                pass
        # Build preferred language set from env
        pref = (preferred_lang or os.getenv("ARCTIC_PREF_AUDIO_LANG", "eng") or "eng").lower().strip()
        _map = {
            "en": "eng", "eng": "en",
            "es": "spa", "spa": "es",
            "de": "deu", "deu": "de",
            "fr": "fra", "fra": "fr",
            "it": "ita", "ita": "it",
            "pt": "por", "por": "pt",
            "ru": "rus", "rus": "ru",
            "ja": "jpn", "jpn": "ja",
            "ko": "kor", "kor": "ko",
            "zh": "zho", "zho": "zh",
        }
        prefer = {pref}
        if pref in _map:
            prefer.add(_map[pref])
        best_pos = None
        # 1) prefer default disposition with preferred language
        for pos, s in enumerate(streams):
            disp = (s.get("disposition") or {}).get("default")
            lang = (s.get("tags", {}) or {}).get("language")
            try:
                if int(disp or 0) == 1 and lang and str(lang).lower() in prefer:
                    best_pos = pos
                    break
            except Exception:
                pass
        # 2) prefer any with preferred language (skip commentary)
        if best_pos is None:
            for pos, s in enumerate(streams):
                lang = (s.get("tags", {}) or {}).get("language")
                title = (s.get("tags", {}) or {}).get("title", "")
                t = str(title or "").lower()
                if ("commentary" in t) or ("descriptive" in t) or ("narration" in t):
                    continue
                if lang and str(lang).lower() in prefer:
                    best_pos = pos
                    break
        # 3) prefer default disposition
        for pos, s in enumerate(streams):
            disp = (s.get("disposition") or {}).get("default")
            try:
                if int(disp or 0) == 1:
                    best_pos = pos
                    break
            except Exception:
                pass
        # 4) any stereo/multichannel
        if best_pos is None:
            for pos, s in enumerate(streams):
                try:
                    if int(s.get("channels") or 0) >= 2:
                        best_pos = pos
                        break
                except Exception:
                    pass
        if best_pos is None:
            # by channels >= 2
            for pos, s in enumerate(streams):
                try:
                    ch = int(s.get("channels") or 0)
                    if ch >= 2:
                        best_pos = pos
                        break
                except Exception:
                    pass
        if best_pos is None and streams:
            best_pos = 0
        if best_pos is None:
            return "0:a:0?"
        return f"0:a:{best_pos}?"
    except Exception:
        return "0:a:0?"

def _needs_ts_annexb(container: str, vcodec: str) -> bool:
    # When copying H.264 into MPEG-TS, ensure Annex B bitstream
    return container == "ts" and vcodec.lower() == "copy"

def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default

def _h264_encoder_args(gop: int, seg_dur: float) -> list[str]:
    """Choose encoder args based on optional hardware flags.

    Env:
      - FFMPEG_HW: one of 'nvenc','qsv','amf','cpu' (default cpu)
      - FFMPEG_PRESET: x264 preset (cpu)
      - FFMPEG_CRF: x264 crf (cpu)
      - FFMPEG_THREADS: thread count (cpu), default 2
      - NVENC_* tuning vars optional
    """
    hw = (os.getenv("FFMPEG_HW", "") or "").lower() or _auto_hw()
    if hw == "nvenc":
        return [
            "-c:v", "h264_nvenc",
            "-preset", os.getenv("NVENC_PRESET", "p5"),
            "-rc", os.getenv("NVENC_RC", "vbr"),
            "-cq", os.getenv("NVENC_CQ", "28"),
            "-b:v", os.getenv("NVENC_BV", "3500k"),
            "-maxrate", os.getenv("NVENC_MAX", "5000k"),
            "-bufsize", os.getenv("NVENC_BUF", "10000k"),
            "-g", str(gop), "-keyint_min", str(gop),
            "-force_key_frames", f"expr:gte(t,n_forced*{seg_dur})",
            "-pix_fmt", "yuv420p",
        ]
    if hw == "qsv":
        return [
            "-c:v", "h264_qsv",
            "-global_quality", os.getenv("QSV_QUALITY", "27"),
            "-look_ahead", os.getenv("QSV_LOOKAHEAD", "0"),
            "-g", str(gop), "-keyint_min", str(gop),
            "-force_key_frames", f"expr:gte(t,n_forced*{seg_dur})",
            "-pix_fmt", "yuv420p",
        ]
    if hw == "amf":
        return [
            "-c:v", "h264_amf",
            "-quality", os.getenv("AMF_QUALITY", "speed"),
            "-g", str(gop), "-keyint_min", str(gop),
            "-force_key_frames", f"expr:gte(t,n_forced*{seg_dur})",
            "-pix_fmt", "yuv420p",
        ]
    # CPU (libx264)
    threads = str(_env_int("FFMPEG_THREADS", 2))
    return [
        "-c:v", "h264",
        "-preset", os.getenv("FFMPEG_PRESET", "ultrafast"),
        "-g", str(gop), "-keyint_min", str(gop),
        "-force_key_frames", f"expr:gte(t,n_forced*{seg_dur})",
        "-profile:v", "baseline", "-level", "3.1", "-pix_fmt", "yuv420p",
        "-crf", os.getenv("FFMPEG_CRF", "28"),
        "-tune", "fastdecode",
        "-threads", threads,
    ]

_AUTO_HW_CACHE: Optional[str] = None

def _auto_hw() -> str:
    global _AUTO_HW_CACHE
    if _AUTO_HW_CACHE is not None:
        return _AUTO_HW_CACHE
    # Probe ffmpeg encoders quickly; if unavailable or fails, fall back to cpu
    try:
        import subprocess
        proc = subprocess.run([ffmpeg_exe(), "-hide_banner", "-encoders"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=2)
        out = (proc.stdout or b"").decode(errors="ignore").lower()
        if "h264_nvenc" in out:
            _AUTO_HW_CACHE = "nvenc"
        elif "h264_qsv" in out:
            _AUTO_HW_CACHE = "qsv"
        elif "h264_amf" in out:
            _AUTO_HW_CACHE = "amf"
        else:
            _AUTO_HW_CACHE = "cpu"
    except Exception:
        _AUTO_HW_CACHE = "cpu"
    return _AUTO_HW_CACHE

async def start_or_warm_job(src_path: Path, job: TranscodeJob) -> None:
    job.touch()
    if job.proc and job.proc.returncode is None:
        return

    # Ensure only one spawn per job at a time (prevents concurrent ffmpeg instances writing same files)
    async with job.lock:
        if job.proc and job.proc.returncode is None:
            return

    # Cross-process spawn guard using a lock file that persists while job is active
    lock_file = job.workdir / ".run.lock"
    try:
        if lock_file.exists():
            # Another worker likely owns the transcoder. Treat as warm and return.
            return
        # Try to acquire by exclusive creation
        fd = os.open(str(lock_file), os.O_CREAT | os.O_EXCL | os.O_RDWR)
        try:
            os.write(fd, str(os.getpid()).encode())
        finally:
            os.close(fd)
    except FileExistsError:
        return

    ext = "m4s" if job.container == "fmp4" else "ts"
    segpat = str(job.workdir / f"seg_%05d.{ext}")
    m3u8_out = str(job.workdir / "ffmpeg.m3u8")

    vcodec = (job.vcodec or "copy").lower()
    acodec = (job.acodec or "aac").lower()

    # Check if source is x265/HEVC - if so, always transcode to H.264
    # For x265 files, we need to transcode to ensure browser compatibility
    if vcodec == "copy":
        # Try to detect x265/HEVC source and force transcode
        try:
            probe_cmd = [
                ffprobe_exe(), "-v", "quiet", "-select_streams", "v:0", 
                "-show_entries", "stream=codec_name", "-of", "csv=p=0", str(src_path)
            ]
            proc = await asyncio.create_subprocess_exec(
                *probe_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()
            codec_name = stdout.decode().strip().lower()
            
            # Force transcode for x265/HEVC sources
            if codec_name in ["hevc", "h265", "x265"]:
                log.info(f"Detected x265/HEVC source ({codec_name}), forcing H.264 transcode for compatibility")
                vcodec = "h264"
                # Update the job's vcodec to reflect the change
                job.vcodec = "h264"
            else:
                log.info(f"Source codec is {codec_name}, using copy mode")
        except Exception as e:
            log.warning(f"Could not detect video codec, proceeding with {vcodec}: {e}")

    a_map = job.a_map or _pick_audio_map_for_path(src_path)

    base = [
        ffmpeg_exe(), "-hide_banner", "-nostdin", "-y",
        "-fflags", "+genpts+discardcorrupt",  # Discard corrupt frames for faster processing
        "-i", str(src_path),
        "-map", "0:v:0", "-map", a_map, "-map", "-0:s", "-dn", "-sn",
        "-max_muxing_queue_size", "1024",  # Smaller queue for faster processing
        "-vsync", "cfr",
        "-reset_timestamps", "1",
        "-avoid_negative_ts", "make_zero",  # Handle timestamp issues
    ]

    # Use H.264 for maximum browser compatibility
    if vcodec == "h264":
        vpart = _h264_encoder_args(job.gop, job.seg_dur)
        # optional scaling
        if job.v_height and int(job.v_height) > 0:
            vpart = ["-vf", f"scale=-2:{int(job.v_height)}", *vpart]
        # optional bitrate cap
        if job.v_bitrate:
            br = str(job.v_bitrate)
            try:
                # rough bufsize ~2x maxrate
                num = int(br.rstrip('kK'))
                buf = f"{max(num*2, num+1)}k"
            except Exception:
                buf = br
            vpart = [*vpart, "-b:v", br, "-maxrate", br, "-bufsize", buf]
    else:
        # For copy mode, ensure we have compatible settings
        vpart = ["-c:v", "copy"]

    # Ensure audio is always AAC for browser compatibility
    apart = [
        "-c:a", "aac",
        "-ac", os.getenv("FFMPEG_AC", "2"),
        "-ar", os.getenv("FFMPEG_AR", "48000"),
        "-b:a", os.getenv("FFMPEG_ABR", "128k"),
        "-aac_coder", "fast",
        "-af", "aresample=async=1:first_pts=0:min_hard_comp=0.100",
    ]

    hls = [
        "-f", "hls",
        "-hls_time", f"{job.seg_dur}",
        "-hls_playlist_type", "event",
        "-sc_threshold", "0",
    ]
    if job.container == "fmp4":
        # Jellyfin-style: single-file fMP4 segments with byteranges
        hls += [
            "-hls_segment_type", "fmp4",
            "-hls_fmp4_init_filename", "init.mp4",
            # Use per-segment fMP4 (.m4s) rather than single_file for better compatibility
            "-hls_flags", "independent_segments+append_list+temp_file",
            "-hls_segment_filename", str(job.workdir / "seg_%05d.m4s"),
        ]
    else:
        # Legacy MPEG-TS multi-file segments with delete_segments
        hls += [
            "-hls_list_size", "10",
            "-hls_segment_filename", segpat,
            "-hls_flags", "independent_segments+delete_segments+temp_file",
            "-hls_start_number_source", "generic",
            "-hls_segment_type", "mpegts",
        ]
        if _needs_ts_annexb(job.container, vcodec):
            hls = ["-bsf:v", "h264_mp4toannexb", *hls]

    cmd = [*base, *vpart, *apart, *hls, m3u8_out]
    log.info("ffmpeg cwd=%s vcodec=%s cmd=%s", job.workdir, vcodec, " ".join(shlex.quote(x) for x in cmd))

    # Avoid unconsumed PIPE deadlocks: write ffmpeg output to a log file in workdir
    log_file = job.workdir / "ffmpeg.log"
    try:
        lf = open(log_file, "ab", buffering=0)
    except Exception:
        lf = None
    job.proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=lf if lf else asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.STDOUT if lf else asyncio.subprocess.DEVNULL,
        cwd=str(job.workdir),
        creationflags=_WIN_BELOW_NORMAL,
    )

    # If remux fails instantly, fall back to h264 encode
    await asyncio.sleep(0.4)
    if job.proc.returncode is not None and vcodec == "copy":
        # Attempt to surface some log context for troubleshooting
        try:
            stderr_txt = (log_file.read_text(errors="ignore") if log_file.exists() else "")
        except Exception:
            stderr_txt = ""
        log.warning("copy pipeline failed; retrying with h264 encode\n%s", stderr_txt[-2000:])
        job.vcodec = "h264"
        return await start_or_warm_job(src_path, job)

    # If h264 path fails immediately (e.g., GPU encoder session exhausted), retry once forcing CPU libx264
    if job.proc.returncode is not None and vcodec == "h264":
        log.warning("h264 encoder failed to start; retrying with CPU libx264")
        # Force CPU by hinting the env for this spawn
        env = os.environ.copy()
        env["FFMPEG_HW"] = "cpu"
        vpart_cpu = _h264_encoder_args(job.gop, job.seg_dur)
        cmd_cpu = [*base, *vpart_cpu, *apart, *hls, m3u8_out]
        job.proc = await asyncio.create_subprocess_exec(
            *cmd_cpu,
            stdout=lf if lf else asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.STDOUT if lf else asyncio.subprocess.DEVNULL,
            cwd=str(job.workdir),
            env=env,
            creationflags=_WIN_BELOW_NORMAL,
        )
        await asyncio.sleep(0.5)

    if job.proc.returncode is not None:
        try:
            stderr_txt = (log_file.read_text(errors="ignore") if log_file.exists() else "")
        except Exception:
            stderr_txt = ""
        log.error("ffmpeg exited code %s\n%s", job.proc.returncode, stderr_txt[-4000:])
        # Clear the lock so future attempts can retry
        with contextlib.suppress(Exception):
            lf_path = job.workdir / ".run.lock"
            if lf_path.exists():
                lf_path.unlink()
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
    
    # Get detailed codec info
    codec_info = {}
    try:
        probe_cmd = [
            ffprobe_exe(), "-v", "quiet", 
            "-select_streams", "v:0", 
            "-show_entries", "stream=codec_name,codec_type,width,height,bit_rate", 
            "-of", "json", str(src_path)
        ]
        proc = await asyncio.create_subprocess_exec(
            *probe_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await proc.communicate()
        import json
        codec_info = json.loads(stdout.decode())
    except Exception as e:
        codec_info = {"error": str(e)}
    
    # Check if it's x265/HEVC
    is_x265 = False
    if "streams" in codec_info and codec_info["streams"]:
        video_stream = codec_info["streams"][0]
        codec_name = video_stream.get("codec_name", "").lower()
        is_x265 = codec_name in ["hevc", "h265", "x265"]
    
    return {
        "file_id": item_id,
        "path": str(src_path),
        "size": stat.st_size,
        "suffix": suffix,
        "direct_compatible": direct_compatible,
        "is_x265": is_x265,
        "codec_info": codec_info,
        "exists": True
    }

# ──────────────────────────────────────────────────────────────────────────────
# Direct file serving for compatible formats
# ──────────────────────────────────────────────────────────────────────────────
def _ua_allows_hevc(user_agent: str) -> bool:
    ua = (user_agent or "").lower()
    is_safari = ("safari" in ua) and ("chrome" not in ua) and ("chromium" not in ua)
    is_ios = ("iphone" in ua) or ("ipad" in ua)
    return is_safari or is_ios

@router.head("/{item_id}/direct")
async def direct_file_head(item_id: str, request: Request, db: AsyncSession = Depends(get_db), user = Depends(get_current_user)):
    """HEAD request for direct file serving to check availability"""
    item, file_row = await get_item_and_file(db, item_id)
    src_path = _resolve_src_path(file_row)
    if not src_path.exists():
        raise HTTPException(404, "Source file missing")

    # Check if file is already browser-compatible
    suf = src_path.suffix.lower()
    if suf in ['.mp4', '.webm', '.ogg', '.m4v']:
        # For MP4/M4V, ensure video and audio codecs are browser-compatible
        if suf in ['.mp4', '.m4v']:
            try:
                # Prefer DB-known codecs if available
                v = (getattr(file_row, "vcodec", None) or "").lower()
                a = (getattr(file_row, "acodec", None) or "").lower()
                if not (v and a):
                    probe_cmd = [
                        ffprobe_exe(), "-v", "quiet",
                        "-show_entries", "stream=codec_name,codec_type",
                        "-select_streams", "v:0,a:0",
                        "-of", "json", str(src_path)
                    ]
                    proc = await asyncio.create_subprocess_exec(*probe_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                    out, err = await proc.communicate()
                    if proc.returncode != 0:
                        log.warning(f"Direct serving: ffprobe failed rc={proc.returncode} stderr={err.decode(errors='ignore')}")
                        raise HTTPException(404, "Direct serving not available")
                    import json
                    data = json.loads(out.decode() or "{}")
                    for s in data.get("streams", []):
                        t = (s.get("codec_type") or "").lower()
                        if t == "video":
                            v = (s.get("codec_name") or v or "").lower()
                        elif t == "audio":
                            a = (s.get("codec_name") or a or "").lower()

                allow_hevc = _ua_allows_hevc(request.headers.get("user-agent", ""))
                v_ok = (v in {"h264", "avc", "avc1"}) or (allow_hevc and v in {"hevc", "h265", "x265"})
                a_ok = a in {"aac", "mp3"}
                if v_ok and a_ok:
                    return Response(status_code=200, headers={
                        "Content-Type": "video/mp4",
                        "Content-Length": str(src_path.stat().st_size),
                        "Accept-Ranges": "bytes",
                    })
                raise HTTPException(404, "Direct serving not available for this format")
            except HTTPException:
                raise
            except Exception as e:
                log.warning(f"Direct serving: codec detection error for {src_path.name}: {e}")
                raise HTTPException(404, "Direct serving not available")

        # For WebM/Ogg, allow direct serving
        return Response(status_code=200, headers={
            "Content-Type": "video/webm" if suf == '.webm' else "video/ogg",
            "Content-Length": str(src_path.stat().st_size),
            "Accept-Ranges": "bytes",
        })
    
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
    suf = src_path.suffix.lower()
    if suf in ['.mp4', '.webm', '.ogg', '.m4v']:
        if suf in ['.mp4', '.m4v']:
            try:
                v = (getattr(file_row, "vcodec", None) or "").lower()
                a = (getattr(file_row, "acodec", None) or "").lower()
                if not (v and a):
                    probe_cmd = [
                        ffprobe_exe(), "-v", "quiet",
                        "-show_entries", "stream=codec_name,codec_type",
                        "-select_streams", "v:0,a:0",
                        "-of", "json", str(src_path)
                    ]
                    proc = await asyncio.create_subprocess_exec(*probe_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                    out, err = await proc.communicate()
                    if proc.returncode != 0:
                        log.warning(f"Direct GET: ffprobe failed rc={proc.returncode} stderr={err.decode(errors='ignore')}")
                        raise HTTPException(404, "Direct serving not available")
                    import json
                    data = json.loads(out.decode() or "{}")
                    for s in data.get("streams", []):
                        t = (s.get("codec_type") or "").lower()
                        if t == "video":
                            v = (s.get("codec_name") or v or "").lower()
                        elif t == "audio":
                            a = (s.get("codec_name") or a or "").lower()
                allow_hevc = _ua_allows_hevc(request.headers.get("user-agent", ""))
                v_ok = (v in {"h264", "avc", "avc1"}) or (allow_hevc and v in {"hevc", "h265", "x265"})
                a_ok = a in {"aac", "mp3"}
                if v_ok and a_ok:
                    return FileResponse(src_path, media_type="video/mp4", headers={
                        "Cache-Control": "public, max-age=3600",
                        "Accept-Ranges": "bytes",
                    })
                raise HTTPException(404, "Direct serving not available for this format")
            except HTTPException:
                raise
            except Exception as e:
                log.warning(f"Direct serving GET: codec detection failed for {src_path.name}: {e}")
                raise HTTPException(404, "Direct serving not available for this format")

        # WebM/Ogg
        return FileResponse(src_path, media_type=("video/webm" if suf == '.webm' else "video/ogg"), headers={
            "Cache-Control": "public, max-age=3600",
            "Accept-Ranges": "bytes",
        })
    
    # If not compatible, redirect to progressive fallback
    raise HTTPException(404, "Direct serving not available for this format")

# ──────────────────────────────────────────────────────────────────────────────
# Progressive MP4 fallback endpoint
# ──────────────────────────────────────────────────────────────────────────────
@router.get("/{item_id}/auto")
async def progressive_fallback(
    item_id: str,
    request: Request,
    token: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Progressive MP4 fallback with guaranteed browser-compatible codecs"""
    # Verify token if provided (for mobile app)
    if token:
        try:
            payload = decode_token(token)
            if not payload or payload.get("typ") != "access":
                raise HTTPException(status_code=401, detail="Invalid token")
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid token")
    else:
        # If no token provided, require user authentication
        user = await get_current_user(request, db)
    
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

    async with job.lock:
        if job.proc and job.proc.returncode is None:
            return

    output_path = str(job.workdir / "output.mp4")

    # Check if source is x265/HEVC and force transcode
    force_transcode = False
    try:
        probe_cmd = [
            ffprobe_exe(), "-v", "quiet", "-select_streams", "v:0", 
            "-show_entries", "stream=codec_name", "-of", "csv=p=0", str(src_path)
        ]
        proc = await asyncio.create_subprocess_exec(
            *probe_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await proc.communicate()
        codec_name = stdout.decode().strip().lower()
        
        # Force transcode for x265/HEVC sources
        if codec_name in ["hevc", "h265", "x265"]:
            log.info("Progressive fallback: Detected x265/HEVC source, forcing H.264 transcode")
            force_transcode = True
    except Exception as e:
        log.warning(f"Could not detect video codec for progressive fallback: {e}")
        force_transcode = True  # Default to transcode if we can't detect

    if force_transcode:
        vpart = _h264_encoder_args(72, 72 / 24.0)
        cmd = [
            ffmpeg_exe(), "-hide_banner", "-nostdin", "-y",
            "-i", str(src_path),
            "-map", "0:v:0", "-map", (job.a_map or _pick_audio_map_for_path(src_path)), "-map", "-0:s", "-dn", "-sn",
            *vpart,
            "-sc_threshold", "0",
            "-c:a", "aac",
            "-ac", "2",
            "-ar", "48000",
            "-b:a", "160k",
            "-movflags", "+faststart",
            "-f", "mp4",
            output_path
        ]
    else:
        # Try remux first for compatible sources
        cmd = [
            ffmpeg_exe(), "-hide_banner", "-nostdin", "-y",
            "-i", str(src_path),
            "-map", "0:v:0", "-map", (job.a_map or _pick_audio_map_for_path(src_path)), "-map", "-0:s", "-dn", "-sn",
            "-c:v", "copy",
            "-c:a", "aac",
            "-ac", "2",
            "-ar", "48000",
            "-b:a", "160k",
            "-movflags", "+faststart",
            "-f", "mp4",
            output_path
        ]

    log.info("ffmpeg progressive cwd=%s cmd=%s", job.workdir, " ".join(shlex.quote(x) for x in cmd))

    # Log output to file to avoid PIPE stalls and aid troubleshooting
    log_file = job.workdir / "ffmpeg_progressive.log"
    try:
        lf = open(log_file, "ab", buffering=0)
    except Exception:
        lf = None
    job.proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=lf if lf else asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.STDOUT if lf else asyncio.subprocess.DEVNULL,
        cwd=str(job.workdir),
        creationflags=_WIN_BELOW_NORMAL,
    )

    if job.proc.returncode is not None:
        try:
            tail = (log_file.read_text(errors="ignore") if log_file.exists() else "")
        except Exception:
            tail = ""
        log.error("progressive ffmpeg exited early with code %s\n%s", job.proc.returncode, tail[-2000:])
        raise HTTPException(500, "Progressive transcode failed to start")

# ──────────────────────────────────────────────────────────────────────────────
# Helpers: playlist rewrite & file wait
# ──────────────────────────────────────────────────────────────────────────────
async def _wait_for_file(p: Path, timeout_s: float = 5.0, poll: float = 0.05) -> bool:
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        try:
            if p.exists():
                try:
                    if p.stat().st_size > 0:
                        return True
                except (PermissionError, OSError):
                    # Windows may briefly deny stat while writer holds handle
                    pass
        except Exception:
            # Ignore transient FS errors during startup
            pass
        await asyncio.sleep(poll)
    try:
        return p.exists()
    except Exception:
        return False

async def _rewrite_ffmpeg_playlist(job: TranscodeJob, base_url: str, token: Optional[str]) -> str:
    m3u8_path = job.workdir / "ffmpeg.m3u8"
    if not m3u8_path.exists():
        return ""
    q = f"?t={token}" if token else ""
    out, have_type, have_header = [], False, False

    # Windows can transiently lock files that ffmpeg writes; retry reads briefly.
    # Also try to build a manifest from directory as a fallback to avoid 500s.
    text = ""
    _sleep = 0.03
    for _ in range(50):  # ~ a few seconds total with capped backoff
        try:
            # Re-check existence because ffmpeg writes with temp_file+rename
            if not m3u8_path.exists():
                await asyncio.sleep(_sleep)
                _sleep = min(_sleep * 1.6, 0.5)
                continue
            text = m3u8_path.read_text(encoding="utf-8", errors="ignore")
            if text:
                break
        except (PermissionError, OSError):
            await asyncio.sleep(_sleep)
            _sleep = min(_sleep * 1.6, 0.5)
        except Exception:
            # Unexpected read issue; small delay then retry
            await asyncio.sleep(_sleep)
            _sleep = min(_sleep * 1.6, 0.5)

    if not text:
        # Build a minimal but valid playlist from available segments as a last resort
        try:
            q = f"?t={token}" if token else ""
            ext = "m4s" if job.container == "fmp4" else "ts"
            segs = sorted(job.workdir.glob(f"seg_*.{ext}"))
            lines = ["#EXTM3U", "#EXT-X-VERSION:7", "#EXT-X-PLAYLIST-TYPE:EVENT"]
            # Target duration rounded up
            td = max(1, int(math.ceil(job.seg_dur)))
            lines.append(f"#EXT-X-TARGETDURATION:{td}")
            # Media sequence (derive from first segment index if present)
            if segs:
                try:
                    first = segs[0].stem.split("_")[-1]
                    media_seq = int(first)
                    lines.append(f"#EXT-X-MEDIA-SEQUENCE:{media_seq}")
                except Exception:
                    pass
            if job.container == "fmp4":
                lines.append(f'#EXT-X-MAP:URI="{base_url}/init.mp4{q}"')
            # Append known segments with nominal duration
            for p in segs:
                lines.append(f"#EXTINF:{job.seg_dur:.3f},")
                lines.append(f"{base_url}/{p.name}{q}")
            return "\n".join(lines) + "\n"
        except Exception:
            # Absolute last resort: minimal header so the client retries shortly
            return "#EXTM3U\n#EXT-X-PLAYLIST-TYPE:EVENT\n"

    for ln in text.splitlines():
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
    vbr: Optional[str] = None,
    vh: Optional[int] = None,
    aidx: Optional[int] = None,
    alang: Optional[str] = None,
    token: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    # Verify token if provided (for mobile app)
    if token:
        try:
            payload = decode_token(token)
            if not payload or payload.get("typ") != "access":
                raise HTTPException(status_code=401, detail="Invalid token")
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid token")
    else:
        # If no token provided, require user authentication
        user = await get_current_user(request, db)
    # Apply forced container from settings, if configured
    try:
        forced = (os.getenv("ARCTIC_HLS_CONTAINER", "") or "").lower()
        if forced in ("fmp4", "ts"):
            container = forced
    except Exception:
        pass
    if container not in ("ts", "fmp4"):
        raise HTTPException(400, "container must be 'ts' or 'fmp4'")

    item, file_row = await get_item_and_file(db, item_id)
    src_path = _resolve_src_path(file_row)
    if not src_path.exists():
        raise HTTPException(404, "Source file missing")

    # Prefer direct play when possible (serve original with Range support)
    try:
        suf = src_path.suffix.lower()
        direct_ok = False
        if suf in {".mp4", ".m4v", ".webm", ".ogg", ".ogv"}:
            if suf in {".mp4", ".m4v"}:
                # Prefer DB-known codecs; fall back to probe
                v = (getattr(file_row, "vcodec", None) or "").lower()
                a = (getattr(file_row, "acodec", None) or "").lower()
                if not (v and a):
                    probe_cmd = [
                        ffprobe_exe(), "-v", "quiet",
                        "-show_entries", "stream=codec_name,codec_type",
                        "-select_streams", "v:0,a:0",
                        "-of", "json", str(src_path)
                    ]
                    proc = await asyncio.create_subprocess_exec(
                        *probe_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                    )
                    out, _ = await proc.communicate()
                    import json
                    data = json.loads(out.decode(errors="ignore") or "{}")
                    for s in data.get("streams", []):
                        t = (s.get("codec_type") or "").lower()
                        if t == "video": v = (s.get("codec_name") or v or "").lower()
                        elif t == "audio": a = (s.get("codec_name") or a or "").lower()
                allow_hevc = _ua_allows_hevc(request.headers.get("user-agent", ""))
                v_ok = (v in {"h264", "avc", "avc1"}) or (allow_hevc and v in {"hevc", "h265", "x265"})
                a_ok = a in {"aac", "mp3"}
                direct_ok = v_ok and a_ok
            else:
                # webm/ogg handled natively by browsers
                direct_ok = True
        if direct_ok:
            # Redirect to robust Range-capable endpoint that supports Range requests
            return RedirectResponse(url=f"/stream/{file_row.id}/file", status_code=302)
    except Exception:
        # On any detection error, fall back to HLS below
        pass

    try:
        # normalize quality params
        vbitrate = (vbr or request.query_params.get("vbitrate") or None)
        try:
            _vh = int(vh) if vh is not None else (int(request.query_params.get("vh")) if request.query_params.get("vh") else None)
        except Exception:
            _vh = None
        # Compute explicit a_map if override provided
        a_map_override = None
        if aidx is not None or (alang and alang.strip()):
            a_map_override = _pick_audio_map_for_path(src_path, preferred_lang=(alang or None), forced_idx=aidx)
        job = await get_or_create_job(item.id, container, vcodec, acodec, vbitrate, _vh, a_map=a_map_override)
        await start_or_warm_job(src_path, job)

        # Ensure initial objects exist; bail to progressive if not ready in time
        if not await _wait_for_file(job.workdir / "ffmpeg.m3u8", 8.0):
            raise RuntimeError("hls manifest not ready")
        if container == "fmp4":
            if not await _wait_for_file(job.workdir / "init.mp4", 12.0):
                raise RuntimeError("init.mp4 not ready")
            # per-segment fMP4: wait for first .m4s segment
            if not await _wait_for_file(job.workdir / "seg_00000.m4s", 12.0):
                # some ffmpeg builds start at 00001
                if not await _wait_for_file(job.workdir / "seg_00001.m4s", 12.0):
                    raise RuntimeError("first m4s not ready")
        else:
            if not await _wait_for_file(job.workdir / "seg_00000.ts", 6.0):
                raise RuntimeError("first ts not ready")
            await _wait_for_file(job.workdir / "seg_00001.ts", 8.0)
    except Exception as e:
        # Graceful fallback: first try switching container to TS (more forgiving on Windows), then progressive
        try:
            if container != "ts":
                log.warning("HLS (fMP4) start failed for item %s (%s); trying TS container", item.id, e)
                return await hls_master(
                    item_id=item.id,
                    request=request,
                    container="ts",
                    vcodec=vcodec,
                    acodec=acodec,
                    db=db,
                    user=user,
                )
        except Exception as e2:
            log.warning("HLS TS fallback failed for item %s (%s); redirecting to progressive", item.id, e2)
        # Final fallback: progressive MP4 pipeline
        log.warning("HLS start failed for item %s (%s); redirecting to progressive", item.id, e)
        return RedirectResponse(url=f"/stream/{item.id}/auto", status_code=302)

    seg_token = _issue_seg_token({"aud": STREAM_AUDIENCE, "item": item.id, "job": job.job_id}, minutes=5)
    base_url = f"{request.base_url}stream/{item.id}/hls/{job.job_id}".rstrip("/")
    manifest = await _rewrite_ffmpeg_playlist(job, base_url, seg_token)
    headers = {"Cache-Control": "no-store", "Pragma": "no-cache"}
    return Response(manifest, media_type="application/vnd.apple.mpegurl", headers=headers)

@router.get("/{item_id}/hls/{job_id}/init.mp4")
async def hls_init_segment(item_id: str, job_id: str, request: Request, token: Optional[str] = Query(None)):
    # Verify token if provided (for mobile app)
    if token:
        try:
            payload = decode_token(token)
            if not payload or payload.get("typ") != "access":
                raise HTTPException(status_code=401, detail="Invalid token")
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid token")
    else:
        await ensure_segment_auth(request)
    job = _JOBS.get(job_id)
    if not job or job.item_id != item_id:
        # Reconstruct minimal job view for cross-worker access
        job = TranscodeJob(job_id=job_id, item_id=item_id, container="fmp4", vcodec="copy", acodec="aac")
        _JOBS.setdefault(job_id, job)
    job.touch()
    p = job.workdir / "init.mp4"
    if not p.exists() and not await _wait_for_file(p, 5.0):
        raise HTTPException(404)
    return FileResponse(p, media_type="video/mp4", headers={"Cache-Control": "no-store"})

@router.get("/{item_id}/hls/{job_id}/{segment}")
async def hls_segment(item_id: str, job_id: str, segment: str, request: Request, token: Optional[str] = Query(None)):
    # Verify token if provided (for mobile app)
    if token:
        try:
            payload = decode_token(token)
            if not payload or payload.get("typ") != "access":
                raise HTTPException(status_code=401, detail="Invalid token")
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid token")
    else:
        await ensure_segment_auth(request)
    job = _JOBS.get(job_id)
    if not job or job.item_id != item_id:
        # Deduce container from segment name
        cont = "ts" if segment.endswith(".ts") else "fmp4"
        job = TranscodeJob(job_id=job_id, item_id=item_id, container=cont, vcodec="copy", acodec="aac")
        _JOBS.setdefault(job_id, job)
    job.touch()

    if job.container == "ts" and not segment.endswith(".ts"):
        raise HTTPException(400)
    if job.container == "fmp4" and not (segment.endswith(".m4s") or segment == "segments.mp4"):
        raise HTTPException(400)

    p = job.workdir / segment
    if not p.exists():
        raise HTTPException(404)
    if job.container == "ts":
        media_type = "video/mp2t"
        return FileResponse(p, media_type=media_type, headers={"Cache-Control": "no-store"})
    # fMP4: support Range for segments.mp4 (byterange HLS)
    media_type = "video/mp4" if segment.endswith(".mp4") else "video/iso.segment"
    if segment == "segments.mp4":
        range_header = request.headers.get("range") or request.headers.get("Range")
        try:
            file_size = p.stat().st_size
        except Exception:
            raise HTTPException(404)
        if not range_header:
            return FileResponse(p, media_type=media_type, headers={"Cache-Control": "no-store", "Accept-Ranges": "bytes"})

        # Parse single-range header: bytes=start-end or bytes=start- or bytes=-length
        if not range_header.startswith("bytes="):
            raise HTTPException(416)
        r = range_header.replace("bytes=", "").strip()
        start_s, _, end_s = r.partition("-")
        try:
            if start_s == "":
                length = int(end_s)
                if length <= 0:
                    raise ValueError
                start = max(0, file_size - length)
                end = file_size - 1
            else:
                start = int(start_s)
                end = int(end_s) if end_s else (file_size - 1)
                if start < 0 or end < start:
                    raise ValueError
                end = min(end, file_size - 1)
        except Exception:
            raise HTTPException(416)

        length = end - start + 1
        chunk_size = 1024 * 1024

        async def _iter_file_async(path: Path, start: int, length: int, chunk: int, request: Request):
            with open(path, "rb") as f:
                f.seek(start)
                remaining = length
                while remaining > 0:
                    if await request.is_disconnected():
                        break
                    to_read = min(chunk, remaining)
                    data = await to_thread.run_sync(f.read, to_read)
                    if not data:
                        break
                    remaining -= len(data)
                    yield data

        headers = {
            "Content-Type": media_type,
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(length),
            "Cache-Control": "no-store",
        }
        return StreamingResponse(_iter_file_async(p, start, length, chunk_size, request), status_code=206, headers=headers)
    # legacy .m4s (if present)
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
        # Reconstruct minimal job for cross-worker access; assume fMP4
        job = TranscodeJob(job_id=job_id, item_id=item_id, container="fmp4", vcodec="copy", acodec="aac")
        _JOBS.setdefault(job_id, job)
    job.touch()

    await _wait_for_file(job.workdir / "ffmpeg.m3u8", 5.0)
    if job.container == "fmp4":
        await _wait_for_file(job.workdir / "init.mp4", 5.0)
        await _wait_for_file(job.workdir / "segments.mp4", 5.0)
    else:
        await _wait_for_file(job.workdir / "seg_00000.ts", 5.0)

    seg_token = _issue_seg_token({"aud": STREAM_AUDIENCE, "item": item_id, "job": job_id}, minutes=5)
    base_url = f"{request.base_url}Videos/{item_id}/hls/{job_id}".rstrip("/")
    manifest = await _rewrite_ffmpeg_playlist(job, base_url, seg_token)
    return PlainTextResponse(manifest, media_type="application/vnd.apple.mpegurl")

@jf_router.get("/{item_id}/hls/{job_id}/{seg_no}.ts")
@jf_router.get("/{item_id}/hls/{job_id}/{seg_no}.m4s")
async def jf_segment(item_id: str, job_id: str, seg_no: str, request: Request):
    await ensure_segment_auth(request)
    job = _JOBS.get(job_id)
    if not job or job.item_id != item_id:
        job = TranscodeJob(job_id=job_id, item_id=item_id, container="fmp4", vcodec="copy", acodec="aac")
        _JOBS.setdefault(job_id, job)
    job.touch()
    ext = "m4s" if job.container == "fmp4" else "ts"
    p = job.workdir / f"seg_{int(seg_no):05d}.{ext}"
    if not p.exists():
        raise HTTPException(404)
    media_type = "video/iso.segment" if ext == "m4s" else "video/MP2T"
    return FileResponse(p, media_type=media_type, headers={"Cache-Control": "no-store"})

@jf_router.get("/{item_id}/hls/{job_id}/init.mp4")
async def jf_init(item_id: str, job_id: str, request: Request):
    await ensure_segment_auth(request)
    job = _JOBS.get(job_id)
    if not job or job.item_id != item_id:
        raise HTTPException(404)
    job.touch()
    p = job.workdir / "init.mp4"
    if not p.exists() and not await _wait_for_file(p, 15.0):
        raise HTTPException(404)
    return FileResponse(p, media_type="video/mp4", headers={"Cache-Control": "no-store"})

@jf_router.get("/{item_id}/hls/{job_id}/segments.mp4")
async def jf_segments_file(item_id: str, job_id: str, request: Request):
    await ensure_segment_auth(request)
    job = _JOBS.get(job_id)
    if not job or job.item_id != item_id:
        raise HTTPException(404)
    job.touch()
    p = job.workdir / "segments.mp4"
    if not p.exists() and not await _wait_for_file(p, 5.0):
        raise HTTPException(404)
    range_header = request.headers.get("range") or request.headers.get("Range")
    try:
        file_size = p.stat().st_size
    except Exception:
        raise HTTPException(404)
    if not range_header:
        return FileResponse(p, media_type="video/mp4", headers={"Cache-Control": "no-store", "Accept-Ranges": "bytes"})

    if not range_header.startswith("bytes="):
        raise HTTPException(416)
    r = range_header.replace("bytes=", "").strip()
    start_s, _, end_s = r.partition("-")
    try:
        if start_s == "":
            length = int(end_s)
            if length <= 0:
                raise ValueError
            start = max(0, file_size - length)
            end = file_size - 1
        else:
            start = int(start_s)
            end = int(end_s) if end_s else (file_size - 1)
            if start < 0 or end < start:
                raise ValueError
            end = min(end, file_size - 1)
    except Exception:
        raise HTTPException(416)

    length = end - start + 1
    chunk_size = 1024 * 1024

    async def _iter_file_async(path: Path, start: int, length: int, chunk: int, request: Request):
        with open(path, "rb") as f:
            f.seek(start)
            remaining = length
            while remaining > 0:
                if await request.is_disconnected():
                    break
                to_read = min(chunk, remaining)
                data = await to_thread.run_sync(f.read, to_read)
                if not data:
                    break
                remaining -= len(data)
                yield data

    headers = {
        "Content-Type": "video/mp4",
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(length),
        "Cache-Control": "no-store",
    }
    return StreamingResponse(_iter_file_async(p, start, length, chunk_size, request), status_code=206, headers=headers)

# ──────────────────────────────────────────────────────────────────────────────
# Cleanup task
# ──────────────────────────────────────────────────────────────────────────────
async def _cleanup_loop():
    sweep_tick = 0
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
                        shutil.rmtree(job.workdir, ignore_errors=True)
                    to_remove.append((jid, job))
            for jid, job in to_remove:
                _JOBS.pop(jid, None)
                if _ITEM_JOB.get(job.item_id) == jid:
                    _ITEM_JOB.pop(job.item_id, None)
            # Periodically sweep the transcode root for orphaned/old dirs and enforce optional size cap
            sweep_tick = (sweep_tick + 1) % 8  # roughly every ~2 minutes with 15s sleep
            if sweep_tick == 0:
                with contextlib.suppress(Exception):
                    await _sweep_transcode_root()
        except Exception:
            pass
        try:
            await asyncio.sleep(15)
        except asyncio.CancelledError:
            # Clean shutdown when task is cancelled
            break

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
    # Also sweep any leftover directories in the transcode root
    with contextlib.suppress(Exception):
        await _sweep_transcode_root(force=True)

async def _sweep_transcode_root(force: bool = False) -> None:
    """Remove orphaned/old job folders and optionally enforce a soft disk cap.

    - Orphans: any subdir under TRANSCODE_ROOT not currently in use by _JOBS
      and older than ORPHAN_MAX_AGE_SECS (based on directory mtime) will be removed.
    - Size cap: if ARCTIC_TRANSCODE_MAX_GB > 0, trim oldest subdirs until under cap.
    """
    try:
        root = TRANSCODE_ROOT
        if not root.exists():
            return
        # Build set of active workdirs to protect
        active_dirs = {str(j.workdir.resolve()) for j in _JOBS.values()}

        # Collect candidate subdirs (skip non-dirs)
        entries: list[Path] = []
        for p in root.iterdir():
            if p.is_dir():
                entries.append(p)

        now = time.time()
        # Remove old/orphaned first (offload deletes to a thread)
        for p in entries:
            ps = str(p.resolve())
            if ps in active_dirs:
                continue
            try:
                age = now - p.stat().st_mtime
            except Exception:
                age = ORPHAN_MAX_AGE_SECS + 1
            if force or age > ORPHAN_MAX_AGE_SECS:
                with contextlib.suppress(Exception):
                    await to_thread.run_sync(shutil.rmtree, p, True)

        # Enforce size cap if configured
        if TRANSCODE_MAX_GB and TRANSCODE_MAX_GB > 0:
            # Recompute list after orphan purge
            subdirs = [p for p in root.iterdir() if p.is_dir()]

            def _dir_size(d: Path) -> int:
                total = 0
                for fp in d.rglob("*"):
                    try:
                        if fp.is_file():
                            total += fp.stat().st_size
                    except Exception:
                        pass
                return total

            sizes = []
            total_bytes = 0
            for d in subdirs:
                s = await to_thread.run_sync(_dir_size, d)
                try:
                    mtime = d.stat().st_mtime
                except Exception:
                    mtime = 0
                sizes.append((d, s, mtime))
                total_bytes += s
            cap_bytes = int(TRANSCODE_MAX_GB * (1024**3))
            if total_bytes > cap_bytes:
                # Sort by last modified (oldest first)
                sizes.sort(key=lambda x: x[2])
                for d, s, _ in sizes:
                    if str(d.resolve()) in active_dirs:
                        continue
                    with contextlib.suppress(Exception):
                        await to_thread.run_sync(shutil.rmtree, d, True)
                    total_bytes -= s
                    if total_bytes <= cap_bytes:
                        break
    except Exception:
        # best-effort
        pass

async def start_hls_cleanup_task(app):
    # One-time sweep on startup to clear orphans from previous runs
    with contextlib.suppress(Exception):
        await _sweep_transcode_root(force=False)
    app.state.hls_cleanup_task = asyncio.create_task(_cleanup_loop())

async def stop_hls_cleanup_task(app):
    task = getattr(app.state, "hls_cleanup_task", None)
    if task:
        task.cancel()
        with contextlib.suppress(Exception):
            await task
    await _emergency_cleanup()
