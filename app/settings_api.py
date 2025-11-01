from __future__ import annotations
from typing import Optional, Literal, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, insert, update
from sqlalchemy.ext.asyncio import AsyncSession

from .auth import require_admin
from .database import get_db
from .models import ServerSetting
from .config import settings as cfg

router = APIRouter(prefix="/admin/settings", tags=["settings"])

# Import cache invalidation function
def invalidate_public_base_url_cache():
    """Invalidate public_base_url cache when settings change."""
    try:
        from .main import invalidate_public_base_url_cache as _invalidate
        _invalidate()
    except Exception:
        pass

# Defaults shown in UI
DEFAULTS = {
    "general": {
        "language": "en",
        "time_format": "24h",          # "12h" | "24h"
        "theme": "dark",               # "dark" | "light" (future)
        "auto_sign_in": True,
        "remember_tab": True,
        "play_theme_music": False,
    },
    "remote": {
        "enable_remote_access": False,
        "public_base_url": "",
        "port": 32400,
        "upnp": True,
        "allow_insecure_fallback": "never",  # "never"|"ask"|"always"
    },
    "transcoder": {
        "ffmpeg_path": getattr(cfg, "FFMPEG_PATH", "ffmpeg"),
        "ffprobe_path": getattr(cfg, "FFPROBE_PATH", "ffprobe"),
        "hwaccel": "auto",             # "auto"|"none"|"vaapi"|"qsv"|"nvenc"
        "max_transcodes": 2,
        "prefer_remux": True,
        "preferred_audio_lang": "eng",  # IETF/ISO code; e.g., eng/en/es/spa
        "hls_container": "auto",       # "auto"|"fmp4"|"ts"
    },
    "server": {
        "server_host": getattr(cfg, "HOST", "0.0.0.0"),
        # Prefer FIRST_RUN_PORT for initial default to avoid conflicts on first startup
        "server_port": getattr(cfg, "FIRST_RUN_PORT", getattr(cfg, "PORT", 8085)),
        "external_access": getattr(cfg, "HOST", "0.0.0.0") == "0.0.0.0",
        # Reflect env-backed SSL defaults so UI shows what's configured in .env
        "ssl_enabled": bool(getattr(cfg, "SSL_ENABLED", False)),
        "ssl_cert_file": getattr(cfg, "SSL_CERT_FILE", ""),
        "ssl_key_file": getattr(cfg, "SSL_KEY_FILE", ""),
    },
}

def _merge(db_rows: Dict[str, Any]) -> Dict[str, Any]:
    out = {k: v.copy() for k, v in DEFAULTS.items()}
    for k, v in db_rows.items():
        if k in out and isinstance(v, dict):
            out[k].update(v)
    return out

async def _load_all(db: AsyncSession) -> Dict[str, Any]:
    rows = (await db.execute(select(ServerSetting))).scalars().all()
    return {r.key: (r.value or {}) for r in rows}

async def _upsert(db: AsyncSession, key: str, value: dict):
    exists = (await db.execute(select(ServerSetting).where(ServerSetting.key == key))).scalars().first()
    if exists:
        await db.execute(update(ServerSetting).where(ServerSetting.key == key).values(value=value))
    else:
        await db.execute(insert(ServerSetting).values(key=key, value=value))
    await db.commit()

# ---- Schemas ----
class GeneralSettings(BaseModel):
    language: str = Field("en")
    time_format: Literal["12h", "24h"] = Field("24h")
    theme: Literal["dark", "light"] = Field("dark")
    auto_sign_in: bool = True
    remember_tab: bool = True
    play_theme_music: bool = False

class RemoteSettings(BaseModel):
    enable_remote_access: bool = False
    public_base_url: str = ""
    port: int = 32400
    upnp: bool = True
    allow_insecure_fallback: Literal["never", "ask", "always"] = "never"

class TranscoderSettings(BaseModel):
    ffmpeg_path: str = getattr(cfg, "FFMPEG_PATH", "ffmpeg")
    ffprobe_path: str = getattr(cfg, "FFPROBE_PATH", "ffprobe")
    hwaccel: Literal["auto", "none", "vaapi", "qsv", "nvenc"] = "auto"
    max_transcodes: int = 2
    prefer_remux: bool = True
    preferred_audio_lang: str = Field("eng", description="Preferred audio language (e.g., eng, en, spa, es)")
    hls_container: Literal["auto", "fmp4", "ts"] = "auto"

class ServerSettings(BaseModel):
    server_host: str = Field(default="0.0.0.0", description="Server host binding")
    # Allow privileged ports like 443; responsibility to run with proper privileges
    server_port: int = Field(default=8000, ge=1, le=65535, description="Server port")
    external_access: bool = Field(default=True, description="Enable external access")
    ssl_enabled: bool = Field(default=False, description="Enable SSL/HTTPS")
    ssl_cert_file: str = Field(default="", description="Path to SSL certificate file (.crt/.pem)")
    ssl_key_file: str = Field(default="", description="Path to SSL private key file (.key)")

class SettingsPatch(BaseModel):
    general: Optional[GeneralSettings] = None
    remote: Optional[RemoteSettings] = None
    transcoder: Optional[TranscoderSettings] = None
    server: Optional[ServerSettings] = None

# ---- Routes ----
@router.get("")
async def get_all(_: str = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    db_rows = await _load_all(db)
    return _merge(db_rows)

@router.get("/general", response_model=GeneralSettings)
async def get_general(_: str = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    return GeneralSettings(**_merge(await _load_all(db))["general"])

@router.get("/remote", response_model=RemoteSettings)
async def get_remote(_: str = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    return RemoteSettings(**_merge(await _load_all(db))["remote"])

@router.get("/transcoder", response_model=TranscoderSettings)
async def get_transcoder(_: str = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    return TranscoderSettings(**_merge(await _load_all(db))["transcoder"])

@router.get("/server", response_model=ServerSettings)
async def get_server(_: str = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    return ServerSettings(**_merge(await _load_all(db))["server"])

@router.patch("")
async def patch_settings(body: SettingsPatch, _: str = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    if body.general is not None:
        await _upsert(db, "general", body.general.model_dump())
    if body.remote is not None:
        await _upsert(db, "remote", body.remote.model_dump())
        # Invalidate cache when remote settings (including public_base_url) change
        invalidate_public_base_url_cache()
    if body.transcoder is not None:
        await _upsert(db, "transcoder", body.transcoder.model_dump())
    if body.server is not None:
        await _upsert(db, "server", body.server.model_dump())
    return {"ok": True}
