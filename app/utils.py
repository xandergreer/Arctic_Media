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

def hash_token(token: str) -> str:
    """Hash a token for storage (similar to password hashing)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

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
        # Disable strict audience verification as we handle it manually in specific routes
        data = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGO], options={"verify_aud": False})
        return data  # type: ignore[return-value]
    except JWTError as e:
        # Use simple print as fallback if logging isn't fully configured in PyInstaller environment
        print(f"[JWT][DEBUG] decode_token failed. error='{e}' key_hash='{hash_token(settings.SECRET_KEY)[:12]}' token_trimmed='{token[:15]}...' ALGO='{ALGO}'")
        return None

# =======================
# General helpers
# =======================

def slugify(s: str) -> str:
    return _slugify(s)

VIDEO_EXTS = {
    ".mkv", ".mp4", ".m4v", ".avi", ".mov", ".wmv", ".mpg", ".mpeg",
    ".flv", ".webm", ".ts", ".m2ts", ".mts", ".divx", ".xvid", ".3gp", ".3g2",
    ".asf", ".rm", ".rmvb", ".vob", ".ogv", ".qt", ".f4v", ".f4p"
}

def is_video_file(path: str) -> bool:
    ext = os.path.splitext(path)[1].lower()
    return ext in VIDEO_EXTS

_ARTICLE_RE = re.compile(r"^(the|a|an)\s+", re.I)
def normalize_sort(title: str) -> str:
    if not title:
        return ""
    t = title.strip()
    t = _ARTICLE_RE.sub("", t).lower()
    t = re.sub(r"[^\w\s]+", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t

def _log_request(req: Request, msg: str):
    ua = req.headers.get("user-agent", "")
    rng = req.headers.get("range", "")
    print(f"[stream][req] {msg} ua='{ua[:60]}' range='{rng}'")
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
    "multi","real","tvsmash","dsny",
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

# TV - Enhanced cleaning patterns
_TV_SXXEYY = re.compile(r"(?i)\bS(\d{1,2})E(\d{1,2})\b")
_TV_ALT   = re.compile(r"(?i)\b(\d{1,2})x(\d{1,2})\b")

# Enhanced cleaning variables for better title extraction
_QUALITY_PATTERNS = re.compile(r"(?i)\b(2160p|1080p|720p|480p|4k|8k|uhd|hd|sd)\b")
_CODEC_PATTERNS = re.compile(r"(?i)\b(x264|x265|h\.?264|h\.?265|hevc|avc|av1|vp9|vc1)\b")
_SOURCE_PATTERNS = re.compile(r"(?i)\b(web|webrip|webdl|web-dl|hdtv|hdrip|dvdrip|bdrip|brrip|bluray|blu-ray|remux|uhd)\b")
_AUDIO_PATTERNS = re.compile(r"(?i)\b(aac[0-9\.]*|ac3|eac3|dd[p+]?[0-9\.]*|dts(-hd)?|ma|truehd|atmos|flac|mp3)\b")
_GROUP_PATTERNS = re.compile(r"(?i)\b(ethel|tvsmash|dsny|evo|joy|saon|flux|oft|ivy|lost|lama|yify|rarbg|etrg|aoc|x0r|nan0)\b")
_YEAR_IN_TITLE = re.compile(r"(?i)\b(19|20)\d{2}\b")
_SEASON_RANGE = re.compile(r"(?i)\bS\d{1,2}(-S\d{1,2})?\b")

def _clean_show_title_enhanced(title: str) -> str:
    """Enhanced show title cleaning with configurable variables"""
    if not title:
        return ""
    
    # --- Enhanced Cleaning Logic ---
    
    # 1. Normalized basic cleanup
    cleaned = title.strip()
    # Replace common separators with spaces to make regex matching easier
    cleaned = re.sub(r'[\._\-\[\](){}+]', ' ', cleaned)
    
    # 2. Remove file extensions (handling spaced extensions too)
    cleaned = re.sub(r'\s+(mkv|mp4|avi|mov|wmv|mpg|mpeg|m4v)$', '', cleaned, flags=re.I)

    # 3. Define Aggressive Wipeout Patterns
    # These matches (and everything after them if they start a junk train) should be removed.
    
    junk_patterns = [
        # Resolution
        r'\b(2160p|1080p|720p|480p|4k|8k|uhd|hd|sd)\b',
        
        # Codecs (handling spaces like H 264)
        r'\b(x\s*26[45]|h\s*\.?\s*26[45]|hevc|avc|av1|vp9|vc1)\b',
        
        # Sources
        r'\b(web\s*[-]?\s*dl|web\s*rip|web|hdtv|hd\s*rip|dvd\s*rip|bd\s*rip|br\s*rip|bluray|blu\s*ray|remux|sdr|hdr|dv|dovi|dl|rip)\b',
        
        # Audio (handling spaces like DDP 5 1)
        r'\b(aac\s*\d*\.?\d*|ac3|eac3|dd\s*[p+]?\s*\d*\s*\.?\s*\d*|dts\s*(-?hd)?|ma|truehd|atmos|flac|mp3)\b',
        
        # Bitrate / Color
        r'\b(10\s*bit|8\s*bit|hi10p)\b',
        
        # Streaming Services
        r'\b(dsnp|amzn|hulu|nf|atvp|max|pcok|hmax|sst)\b',
        
        # Release Groups (Aggressive list based on user logs)
        r'\b(successfulcrab|bae|megusta|ntb|flux|ethel|lazycunts|bioma|kings|darq|hone|phoenix|badkat|elite|dooky|playweb|epsilon|batv|syncopy|demand|sigma|qoq|mixed|spweb)\b',
        
        # Other Scene tags
        r'\b(repack|proper|internal|extended|director|cut|unrated|mult[i]?|dual)\b'
    ]
    
    # Apply regexes
    flags = re.IGNORECASE
    for pat in junk_patterns:
        cleaned = re.sub(pat, ' ', cleaned, flags=flags)

    # 4. Remove Season/Episode IDs if they remain (e.g. S01E01)
    cleaned = re.sub(r'\bS\d{1,2}E\d{1,3}\b', '', cleaned, flags=flags)
    cleaned = re.sub(r'\b\d{1,2}x\d{1,3}\b', '', cleaned, flags=flags)

    # 5. Remove 'Season X' or 'Episode X' leftovers
    cleaned = re.sub(r'\b(season|episode)\s*\d+\b', '', cleaned, flags=flags)

    # 6. Remove common prefixes/suffixes
    cleaned = re.sub(r'^(tv\s+|shows?\s+)', '', cleaned, flags=flags)
    cleaned = re.sub(r'\s+(tv|shows?)$', '', cleaned, flags=flags)

    # 7. Collapse spaces and trim
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    # 8. Aggressive trailing digit wipe (e.g. "Title 1")
    # Only if title length > 1 (keep "24" or "911" but remove "Title S01")
    # But wait, "Toy Story 3"? We assume Show Episodes don't usually end in single digits unless it's part of the name.
    # However, junk like "1" from "DL 1" is worse.
    # We will remove trailing single digits if they are standalone
    cleaned = re.sub(r'\s+\d$', '', cleaned)

    # 8. Check if result is just the show name (duplicate prevention)
    # This is hard without knowing the show name, but we can rely on metadata enrichment 
    # to handle "empty" titles by fetching from TMDB.
    # If the title is just special chars or digits, wipe it.
    if re.fullmatch(r'[^a-zA-Z]*', cleaned):
        return ""

    return cleaned.strip(' .-_')

def parse_tv_parts(rel_root: str, path: str):
    """
    Return (show_title:str, season:int, episode:int, ep_title_guess:str|None)

    Handles examples:
      Yellowstone.2018.S05E11.Three.Fifty-Three.1080p...
      The Last of Us S01E06 Kin.mkv
      Show S05E07.E08 Title.mkv
      Show S05E07-08 Title.mkv
      Show S05e11 E12 Title.mkv
    """
    fname = os.path.basename(path)
    hay = os.path.join(rel_root or "", fname)

    # normalize separators to spaces
    norm = re.sub(r"[\._\-]+", " ", hay, flags=re.IGNORECASE).strip()

    # season marker
    s = re.search(r"(?i)\bS(\d{1,2})\b", norm)
    if not s:
        return None
    season = int(s.group(1))
    tail = norm[s.end():]

    # collect episode numbers appearing after the season marker
    eps = []

    # E07, e07 … (collect all)
    for m in re.finditer(r"(?i)\bE(\d{1,3})\b", tail):
        eps.append(int(m.group(1)))

    # Ranges like E07-08 (expand both ends)
    for m in re.finditer(r"(?i)\bE(\d{1,3})\s*[-–]\s*(\d{1,3})\b", tail):
        a, b = int(m.group(1)), int(m.group(2))
        if a not in eps: eps.append(a)
        if b not in eps: eps.append(b)

    # If no explicit E-tokens, try a bare number right after the season area
    if not eps:
        m = re.search(r"\b(\d{1,3})\b", tail)
        if m:
            eps.append(int(m.group(1)))

    if not eps:
        return None

    # show title is text before the season marker
    show_title = re.sub(r"\s+", " ", norm[:s.start()]).strip(" -._")

    # episode title guess = text after last E-token
    last_e = list(re.finditer(r"(?i)\bE(\d{1,3})\b", norm[s.start():]))
    ep_title_guess = None
    if last_e:
        last_end = s.start() + last_e[-1].end()
        ep_title_guess = norm[last_end:].strip(" -._")
        # If the "title" is actually just codec/quality junk, drop it
        if re.fullmatch(
            r"(?i)(?:\d{3,4}p|x26[45]|H\.?26[45]|HEVC|AVC|WEB(?:DL|Rip)?|BluRay|DDP?\.?\d(?:\.\d)?|AAC|DTS(?:-HD)?|HDR|10bit|NF|AMZN|HULU|REMUX)\b.*",
            ep_title_guess or ""
        ):
            ep_title_guess = None

    # return only the first episode to preserve existing scanner behavior
    return (show_title, season, eps[0], ep_title_guess)

# =======================
# ffprobe (best-effort)
# =======================

# --- More tolerant TV parser (SxxEyy without separators, 1x02, Season NN + Eyy) ---
_ROBUST_SXXEYY = re.compile(r"(?i)S(\d{1,2})\s*[\._\- ]*E(\d{1,3})")
_ROBUST_ALT    = re.compile(r"(?i)\b(\d{1,2})x(\d{1,3})\b")
_JUNK_TITLE_RE = re.compile(r"(?i)(?:\d{3,4}p|x26[45]|H\.?26[45]|HEVC|AVC|VP9|AV1|WEB(?:DL|Rip)?|BluRay|BRRip|HDR|DV|DDP?\.?\d(?:\.\d)?|AAC|AC3|DTS(?:-HD)?|TrueHD|Remux|NF|AMZN|HULU|ETHEL|TVSmash|DSNY)\b.*")

def _parse_tv_parts_robust(rel_root: str, path: str):
    fname = os.path.basename(path)
    hay_raw = os.path.join(rel_root or "", fname)
    # Normalize common separators INCLUDING path separators to spaces
    norm = re.sub(r"[\._\-/\\]+", " ", hay_raw, flags=re.IGNORECASE).strip()
    # Prefer the first folder segment as canonical show name when available
    rel_first = ""
    if rel_root:
        parts = re.split(r"[\\/]+", rel_root)
        rel_first = (parts[0] or "").strip()

    # Handle multi-season ranges like S01-S03
    multi_season = re.search(r"(?i)\bS(\d{1,2})\s*[-–]\s*S?(\d{1,2})\b", hay_raw)
    if multi_season:
        season_start = int(multi_season.group(1))
        season_end = int(multi_season.group(2))
        # For multi-season packs, use the first season and mark it as a pack
        season = season_start
        token_norm = re.sub(r"[\._\-]+", " ", multi_season.group(0)).lower()
        idx = norm.lower().find(token_norm)
        pre = norm[: idx if idx >= 0 else 0]
        show_title = re.sub(r"\s+", " ", pre).strip(" -._")
        # Enhanced cleaning for show title
        show_title = _clean_show_title_enhanced(show_title)
        # If a clean folder name exists, prefer it over a long pre-path
        if rel_first and not rel_first.lower().startswith("season "):
            folder_cleaned = _clean_show_title_enhanced(rel_first)
            if folder_cleaned and len(folder_cleaned) >= 2:
                show_title = folder_cleaned
        # For multi-season packs, create a special episode indicator
        episode = 0  # Special marker for season packs
        ep_title_guess = f"Season {season_start}-{season_end} Pack"
        return (show_title, season, episode, ep_title_guess)

    m = _ROBUST_SXXEYY.search(hay_raw) or _ROBUST_SXXEYY.search(norm)
    if m:
        season = int(m.group(1)); episode = int(m.group(2))
        token_norm = re.sub(r"[\._\-]+", " ", m.group(0)).lower()
        idx = norm.lower().find(token_norm)
        pre = norm[: idx if idx >= 0 else 0]
        show_title = re.sub(r"\s+", " ", pre).strip(" -._")
        # Enhanced cleaning for show title
        show_title = _clean_show_title_enhanced(show_title)
        # If a clean folder name exists, prefer it over a long pre-path
        if rel_first and not rel_first.lower().startswith("season "):
            folder_cleaned = _clean_show_title_enhanced(rel_first)
            if folder_cleaned and len(folder_cleaned) >= 2:
                show_title = folder_cleaned
        tail = norm[(idx + len(m.group(0))) if idx >= 0 else 0 :].strip(" -._")
        ep_title_guess = tail or None
        # Enhanced episode title cleaning
        if ep_title_guess:
            ep_title_guess = _clean_show_title_enhanced(ep_title_guess)
            if not ep_title_guess or len(ep_title_guess.strip()) < 2:
                ep_title_guess = None
        if ep_title_guess and _JUNK_TITLE_RE.fullmatch(ep_title_guess):
            ep_title_guess = None
        return (show_title, season, episode, ep_title_guess)

    m = _ROBUST_ALT.search(norm)
    if m:
        season = int(m.group(1)); episode = int(m.group(2))
        show_title = re.sub(r"\s+", " ", norm[: m.start()]).strip(" -._")
        # Enhanced cleaning for show title
        show_title = _clean_show_title_enhanced(show_title)
        if rel_first and not rel_first.lower().startswith("season "):
            folder_cleaned = _clean_show_title_enhanced(rel_first)
            if folder_cleaned and len(folder_cleaned) >= 2:
                show_title = folder_cleaned
        ep_title_guess = norm[m.end():].strip(" -._") or None
        return (show_title, season, episode, ep_title_guess)

    s_season = re.search(r"(?i)\bseason\s*(\d{1,2})\b", norm)
    if s_season:
        season = int(s_season.group(1))
        tail = norm[s_season.end():]
        m_ep = re.search(r"\b(\d{1,3})\b", tail)
        if m_ep:
            episode = int(m_ep.group(1))
        else:
            # If no explicit episode number but we're in a season folder,
            # try to extract episode number from filename or assume episode 1
            filename_part = tail.split()[-2] if len(tail.split()) >= 2 else ""
            ep_match = re.search(r"(?i)e(\d{1,3})|episode\s*(\d{1,3})", filename_part)
            if ep_match:
                episode = int(ep_match.group(1) or ep_match.group(2))
            else:
                # Assume episode 1 for files in season folders without explicit episode info
                episode = 1
        
        show_title = re.sub(r"\s+", " ", norm[: s_season.start()]).strip(" -._")
        # Enhanced cleaning for show title
        show_title = _clean_show_title_enhanced(show_title)
        if rel_first and not rel_first.lower().startswith("season "):
            folder_cleaned = _clean_show_title_enhanced(rel_first)
            if folder_cleaned and len(folder_cleaned) >= 2:
                show_title = folder_cleaned
        ep_title_guess = tail[m_ep.end():].strip(" -._") or None if m_ep else None
        if ep_title_guess and _JUNK_TITLE_RE.fullmatch(ep_title_guess):
            ep_title_guess = None
        return (show_title, season, episode, ep_title_guess)

    return None

# Override with robust parser to improve detection and reduce duplicate titles
parse_tv_parts = _parse_tv_parts_robust

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
