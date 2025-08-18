# app/utils.py
from __future__ import annotations
import os
import re
import json
import shutil
import secrets
import subprocess
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Tuple

from slugify import slugify as _slugify
from jose import jwt, JWTError
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from .config import settings

# =========================
# Auth helpers (Argon2 + JWT)
# =========================
_ph = PasswordHasher()  # sane defaults

def hash_password(raw: str) -> str:
    return _ph.hash(raw)

def verify_password(raw: str, hashed: str) -> bool:
    try:
        _ = _ph.verify(hashed, raw)
        return True
    except VerifyMismatchError:
        return False

ALGO = "HS256"

def create_token(data: dict[str, Any], expires_in: int) -> str:
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + timedelta(seconds=expires_in)
    to_encode.update({"exp": expire, "iat": now})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGO)

def decode_token(token: str) -> Optional[dict[str, Any]]:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGO])
    except JWTError:
        return None

def new_csrf() -> str:
    return secrets.token_urlsafe(32)

# =========================
# Media helpers
# =========================
VIDEO_EXTS = {
    ".mp4", ".m4v", ".mkv", ".mov", ".avi", ".wmv", ".flv", ".ts", ".m2ts", ".webm"
}

def slugify(s: str) -> str:
    return _slugify(s or "", lowercase=True)

def is_video_file(path: str) -> bool:
    return os.path.splitext(path)[1].lower() in VIDEO_EXTS

# Regexes: robust 4-digit year, sample/trailer detect, and junk tags
YEAR_RE = re.compile(r"\b((?:19|20)\d{2})\b")
SAMPLE_RE = re.compile(r"\b(sample|trailer|teaser|clip|extra|extras)\b", re.I)
JUNK_RE = re.compile(
    r"\b(480p|720p|1080p|2160p|4k|uhd|hdr10\+?|hdr|dv|dolby|vision|web[-_. ]?dl|web[-_. ]?rip|"
    r"bluray|b[dr]rip|brrip|hdtv|x264|x265|h\.?264|hevc|av1|"
    r"ddp?\d(\.\d)?|dts(-?hd)?|truehd|atmos|aac|mp3|flac|"
    r"proper|remux|repack|extended|unrated|dc|amzn|nf|hdtc|cam|webrip|webr|webrdl)\b",
    re.I,
)

SMALL_WORDS = {"and","or","the","a","an","of","in","on","to","for","at","by","from","but","nor"}

def smart_title(s: str) -> str:
    parts = (s or "").lower().split()
    out = []
    for i, w in enumerate(parts):
        if w in SMALL_WORDS and i not in (0, len(parts) - 1):
            out.append(w)
        else:
            out.append(w.capitalize())
    return " ".join(out)

def normalize_sort(title: str) -> str:
    # lower and strip non-alnum for consistent DB lookups
    return re.sub(r"\W+", "", title or "").lower()

def _squash_separators(s: str) -> str:
    return re.sub(r"[\._\-]+", " ", s).strip()

# ------------- Movie parsing -------------
def parse_movie_from_path(path: str) -> Optional[Tuple[str, Optional[int]]]:
    """
    Returns (nice_title, year) or None to skip (samples/trailers).
    Only removes the first 4-digit year token and strips common junk tags.
    """
    base_name = os.path.splitext(os.path.basename(path))[0]
    base = _squash_separators(base_name)

    # Skip samples/trailers
    if SAMPLE_RE.search(base):
        return None

    # Extract 4-digit year (full token)
    year: Optional[int] = None
    m = YEAR_RE.search(base)
    if m:
        year = int(m.group(1))
        base = (base[:m.start()] + " " + base[m.end():]).strip()

    # Remove junk markers (codecs, sources, qualities)
    cleaned = JUNK_RE.sub(" ", base)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    if not cleaned:
        return None

    nice_title = smart_title(cleaned)
    return (nice_title, year)

# Back-compat: some parts of the app expect this name/signature
def guess_title_year(filename: str) -> Tuple[str, Optional[int]]:
    """
    Best-effort guess of (title, year) from a filename (no directories).
    Uses 4-digit year only and robust junk stripping. Never returns 2-digit years.
    """
    parsed = parse_movie_from_path(filename)
    if parsed:
        return parsed
    # fallback: just prettify the stem
    stem = _squash_separators(os.path.splitext(os.path.basename(filename))[0])
    return (smart_title(stem), None)

# Back-compat helper used elsewhere
def clean_title(s: str) -> str:
    base = _squash_separators(s)
    base = JUNK_RE.sub(" ", base)
    base = re.sub(r"\s+", " ", base).strip()
    return smart_title(base)

# ------------- TV parsing -------------
_TV_RX = re.compile(r"(?i)\bS(\d{1,2})[ ._-]*E(\d{1,3})\b")

def parse_tv_parts(rel_path: str, filename: str) -> Optional[Tuple[str, int, int, str]]:
    """
    Returns (show_title, season, episode, ep_title_guess)

    Heuristic: show title = first folder under the library root (rel_path).
    We still clean the title and strip junk markers.
    """
    rel_parts = [p for p in rel_path.replace("\\", "/").split("/") if p]
    raw_show = rel_parts[0] if rel_parts else "Unknown Show"
    show_title = smart_title(JUNK_RE.sub(" ", _squash_separators(raw_show))).strip() or "Unknown Show"

    base = os.path.splitext(os.path.basename(filename))[0]
    pretty_base = _squash_separators(base)

    m = _TV_RX.search(pretty_base)
    if not m:
        return None

    season = int(m.group(1))
    episode = int(m.group(2))

    # Everything after the SxxEyy token as an episode title guess
    ep_guess = pretty_base[m.end():].strip()
    ep_guess = JUNK_RE.sub(" ", ep_guess)
    ep_guess = re.sub(r"\s+", " ", ep_guess).strip()
    ep_title_guess = smart_title(ep_guess) if ep_guess else f"S{season:02d}E{episode:02d}"

    return (show_title, season, episode, ep_title_guess)

# ------------- ffprobe -------------
def ffprobe_info(path: str) -> dict:
    """
    Return a dict:
      container, vcodec, acodec, width, height, bitrate, duration
    Falls back to extension-only if ffprobe fails.
    """
    cmd = [
        settings.FFPROBE_PATH,
        "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        "-show_format",
        path,
    ]
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        data = json.loads(out.decode("utf-8", errors="ignore"))

        info = {
            "container": os.path.splitext(path)[1].lstrip(".").lower(),
            "vcodec": None,
            "acodec": None,
            "width": None,
            "height": None,
            "bitrate": None,
            "duration": None,
        }

        fmt = data.get("format") or {}
        if "bit_rate" in fmt:
            try:
                info["bitrate"] = int(fmt["bit_rate"])
            except Exception:
                pass
        if "duration" in fmt:
            try:
                info["duration"] = float(fmt["duration"])
            except Exception:
                pass

        streams = data.get("streams") or []
        for s in streams:
            ctype = s.get("codec_type")
            if ctype == "video" and info["vcodec"] is None:
                info["vcodec"] = s.get("codec_name")
                info["width"] = s.get("width")
                info["height"] = s.get("height")
            elif ctype == "audio" and info["acodec"] is None:
                info["acodec"] = s.get("codec_name")

        return info
    except Exception:
        # ffprobe missing or failed; fall back to extension only
        return {
            "container": os.path.splitext(path)[1].lstrip(".").lower(),
            "vcodec": None,
            "acodec": None,
            "width": None,
            "height": None,
            "bitrate": None,
            "duration": None,
        }
