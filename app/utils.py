# app/utils.py
from __future__ import annotations
import os
import re
import hmac
import base64
import hashlib
import secrets
import subprocess
import shutil
import json
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple, Any, List

from slugify import slugify as _slugify
from jose import jwt, JWTError

# Bring settings for SECRET_KEY
try:
    from .config import settings  # type: ignore
except Exception:
    # Fallback for PyInstaller-relative import when package context differs
    from app.config import settings  # type: ignore

# =======================
# Password utilities
# =======================

# Prefer argon2 if available; fallback to pbkdf2_sha256
try:
    from argon2 import PasswordHasher  # type: ignore
    from argon2.exceptions import VerifyMismatchError  # type: ignore
    _PH = PasswordHasher()
    _HAS_ARGON2 = True
except Exception:
    _PH = None
    _HAS_ARGON2 = False

def hash_password(password: str) -> str:
    """
    Hash a password using argon2 if available, else PBKDF2-SHA256.
    Encodings are self-identifying so verify_password can detect algorithm.
    """
    if _HAS_ARGON2:
        return _PH.hash(password)
    # pbkdf2 fallback
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 200_000)
    digest_b64 = base64.b64encode(dk).decode("ascii")
    return f"pbkdf2_sha256${salt}${digest_b64}"

def verify_password(password: str, hashed: str) -> bool:
    if hashed.startswith("$argon2"):
        if not _HAS_ARGON2:
            return False
        try:
            return _PH.verify(hashed, password)
        except Exception:
            return False
    if hashed.startswith("pbkdf2_sha256$"):
        try:
            _algo, salt, digest_b64 = hashed.split("$", 2)
            dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 200_000)
            calc_b64 = base64.b64encode(dk).decode("ascii")
            return hmac.compare_digest(calc_b64, digest_b64)
        except Exception:
            return False
    # final fallback (legacy/dev only): constant-time compare to plain text
    return hmac.compare_digest(hashed, password)

# =======================
# JWT helpers
# =======================

ALGO = "HS256"

def create_token(payload: dict[str, Any], expires_in: int, *, token_type: str = "access") -> str:
    """
    Create a signed JWT. Adds standard 'typ', 'iat', 'exp'.
    'sub' should be present in payload for user id.
    """
    now = datetime.now(timezone.utc)
    exp = now + timedelta(seconds=int(expires_in))
    data = dict(payload)
    data.setdefault("typ", token_type)
    data["iat"] = int(now.timestamp())
    data["exp"] = int(exp.timestamp())
    return jwt.encode(data, settings.SECRET_KEY, algorithm=ALGO)

def decode_token(token: str) -> Optional[dict[str, Any]]:
    """
    Verify and decode a JWT. Returns payload dict or None on failure.
    """
    if not token:
        return None
    try:
        data = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGO])
        return data  # type: ignore[return-value]
    except JWTError:
        return None

# =======================
# General helpers
# =======================

def slugify(s: str) -> str:
    return _slugify(s)

VIDEO_EXTS = {".mkv", ".mp4", ".m4v", ".avi", ".mov", ".wmv", ".mpg", ".mpeg"}

def is_video_file(path: str) -> bool:
    return os.path.splitext(path)[1].lower() in VIDEO_EXTS

_ARTICLE_RE = re.compile(r"^(the|a|an)\s+", re.I)
def normalize_sort(title: str) -> str:
    if not title:
        return ""
    t = title.strip()
    t = _ARTICLE_RE.sub("", t).lower()
    t = re.sub(r"[^\w\s]+", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t

# --- CSRF helpers ---------------------------------------------------------
import base64, secrets, hmac  # (you likely already import hmac/base64 above)

def new_csrf(length: int = 32) -> str:
    """
    Generate a URL-safe, opaque CSRF token (no server-secret needed).
    """
    raw = secrets.token_bytes(length)
    # urlsafe base64, strip '=' padding for compactness
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

def verify_csrf(provided: str, expected: str) -> bool:
    """
    Constant-time compare of two CSRF tokens (both as strings).
    Works with our urlsafe tokens even if padding is lost in transit.
    """
    if not provided or not expected:
        return False
    # normalize any missing padding so tokens compare correctly
    def _pad(s: str) -> str:
        return s + "=" * ((4 - (len(s) % 4)) % 4)
    try:
        a = base64.urlsafe_b64decode(_pad(provided).encode("ascii"))
        b = base64.urlsafe_b64decode(_pad(expected).encode("ascii"))
        return hmac.compare_digest(a, b)
    except Exception:
        # if tokens weren't base64, compare raw strings safely
        return hmac.compare_digest(str(provided), str(expected))

# Backwards-compat alias some codebases use:
check_csrf = verify_csrf

# =======================
# Title parsing for movies/TV
# =======================

_GROUP_OR_SERVICE = {
    "hulu","amzn","nf","prime","amazon","tubi","pcok","ptv","pmtp","ds4k",
    "yify","rarbg","etrg","evo","joy","saon","flux","oft","ivy","lost","lama",
    "bhdstudio","refraction","pir8","okaystopcrying","hallowed","chivaman",
    "will1869","ethel","aoc","x0r","nan0","lootera","byndr","collective",
    "multi","real",
    "sample","trailer","theatrical","workprint","teaser"
}
_BREAK_TOKENS = {
    "web","webrip","webdl","web-dl","hdtv","hdrip","dvdrip","bdrip","brrip","bluray","blu-ray","remux","uhd",
    "1080p","2160p","720p","480p","4k","8k",
    "hdr","dv","dovi","dolby","vision",
    "x264","x265","h264","h.264","h265","h.265","hevc","avc","av1","vp9","vc1","vc-1",
    "10bit","8bit",
    "ac3","eac3","dd","dd5","ddp","dts","dts-hd","ma","truehd","atmos","aac","he-aac","flac","mp3",
    "proper","repack","internal",
    "telesync","ts","cam","r5","dcp",
    "remastered","unrated","extended","directors","director","cut","criterion"
}
_SAMPLE_OR_TRAILER = {"sample","trailer","workprint","teaser"}

SEP_RE = re.compile(r"[.\-_\[\](){}/\\]+")
YEAR_RE = re.compile(r"^(19\d{2}|20\d{2}|210\d)$")

def _tokenize(s: str) -> list[str]:
    s = SEP_RE.sub(" ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s.split()

def _clean_front_noise(tokens: list[str]) -> list[str]:
    i = 0
    while i < len(tokens) and tokens[i].lower() in _GROUP_OR_SERVICE:
        i += 1
    return tokens[i:]

def _title_from_tokens(tokens: list[str]) -> Tuple[str, Optional[int]]:
    if any(t.lower() in _SAMPLE_OR_TRAILER for t in tokens):
        return ("", None)
    # find first year
    year: Optional[int] = None
    year_idx: Optional[int] = None
    for idx, t in enumerate(tokens):
        m = YEAR_RE.match(t)
        if m:
            year = int(m.group(1))
            year_idx = idx
            break
    if year_idx is not None:
        core = tokens[:year_idx]
    else:
        core = []
        for t in tokens:
            lt = t.lower()
            if lt in _BREAK_TOKENS:
                break
            core.append(t)
    core = _clean_front_noise(core)
    # strip embedded channel patterns like 'DDP 5 1'
    cleaned: list[str] = []
    i = 0
    while i < len(core):
        nxt3 = " ".join(core[i:i+3]).lower()
        if any(x in nxt3 for x in ("ddp 5 1","eac3 5 1","ac3 5 1","aac 2 0","truehd 7 1","dts 5 1","dts-hd 5 1")):
            i += 3
            continue
        t = core[i]
        if t.lower() in _BREAK_TOKENS or t.lower() in _GROUP_OR_SERVICE:
            i += 1
            continue
        cleaned.append(t)
        i += 1
    title = " ".join(cleaned).strip()
    # titlecase with small-word rules
    small = {"and","or","of","the","a","an","to","in","on","at","for","by"}
    words = title.split()
    title = " ".join([w if (i and w.lower() in small) else w.capitalize() for i, w in enumerate(words)])
    return (title, year)

def _choose_best_name(file_name: str, parent_name: str) -> Tuple[str, Optional[int]]:
    stem = os.path.splitext(file_name)[0]
    t1, y1 = _title_from_tokens(_tokenize(stem))
    t2, y2 = _title_from_tokens(_tokenize(parent_name))
    def score(title: str, year: Optional[int]) -> int:
        s = 0
        if year: s += 2
        s += min(len(title.split()), 5)
        if title and title.split()[0].lower() in _GROUP_OR_SERVICE:
            s -= 3
        return s
    return (t2, y2) if score(t2, y2) > score(t1, y1) else (t1, y1)

def guess_title_year(path: str) -> Tuple[Optional[str], Optional[int]]:
    base = os.path.basename(path)
    parent = os.path.basename(os.path.dirname(path))
    low = (base + " " + parent).lower()
    if any(k in low for k in ("[trailer", " trailer", "sample", "workprint", "teaser")):
        return (None, None)
    title, year = _choose_best_name(base, parent)
    if title:
        title = " ".join([w for w in title.split() if w.lower() not in _GROUP_OR_SERVICE and w.lower() not in _BREAK_TOKENS]).strip()
    if not title or len(title) < 2:
        return (None, None)
    return (title, year)

def parse_movie_from_path(path: str) -> Optional[Tuple[str, Optional[int]]]:
    t, y = guess_title_year(path)
    if not t:
        return None
    return (t, y)

# TV
_TV_SXXEYY = re.compile(r"(?i)\bS(\d{1,2})E(\d{1,2})\b")
_TV_ALT   = re.compile(r"(?i)\b(\d{1,2})x(\d{1,2})\b")
def parse_tv_parts(rel_dir: str, filename: str) -> Optional[Tuple[str, int, int, str]]:
    pathish = SEP_RE.sub(" ", f"{rel_dir} {filename}")
    m = _TV_SXXEYY.search(pathish) or _TV_ALT.search(pathish)
    if not m:
        return None
    if m.re is _TV_SXXEYY:
        season = int(m.group(1)); episode = int(m.group(2))
    else:
        season = int(m.group(1)); episode = int(m.group(2))
    show_raw = pathish[:m.start()]
    show_tokens = _tokenize(show_raw)
    show_tokens = _clean_front_noise(show_tokens)
    show_title, _ = _title_from_tokens(show_tokens)
    if not show_title:
        return None
    tail_tokens = _tokenize(pathish[m.end():])
    guess_tokens = []
    for t in tail_tokens:
        if t.lower() in _BREAK_TOKENS or t.lower() in _GROUP_OR_SERVICE:
            break
        guess_tokens.append(t)
    ep_guess = " ".join(guess_tokens).strip()
    return (show_title, season, episode, ep_guess)

# =======================
# ffprobe (best-effort)
# =======================

def ffprobe_info(path: str) -> dict:
    """
    Attempt to run ffprobe for basic metadata. If unavailable, return minimal info.
    """
    try:
        # Resolve ffprobe path
        exe = shutil.which("ffprobe")
        if not exe:
            raise FileNotFoundError("ffprobe not found")
        cmd = [
            exe, "-v", "error",
            "-show_entries", "format=bit_rate,duration:stream=index,codec_name,codec_type,width,height",
            "-of", "json", path,
        ]
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=10)
        data = json.loads(out.decode("utf-8", "ignore"))
        info: dict[str, Any] = {
            "container": os.path.splitext(path)[1].lstrip(".").lower(),
            "vcodec": None, "acodec": None,
            "width": None, "height": None,
            "bitrate": None, "duration": None,
        }
        fmt = (data.get("format") or {})
        if "bit_rate" in fmt:
            try: info["bitrate"] = int(fmt["bit_rate"])
            except Exception: pass
        if "duration" in fmt:
            try: info["duration"] = float(fmt["duration"])
            except Exception: pass
        for s in (data.get("streams") or []):
            if s.get("codec_type") == "video":
                info["vcodec"] = s.get("codec_name")
                info["width"]  = s.get("width")
                info["height"] = s.get("height")
            elif s.get("codec_type") == "audio" and not info.get("acodec"):
                info["acodec"] = s.get("codec_name")
        return info
    except Exception:
        return {
            "container": os.path.splitext(path)[1].lstrip(".").lower(),
            "vcodec": None, "acodec": None,
            "width": None, "height": None,
            "bitrate": None, "duration": None,
        }
