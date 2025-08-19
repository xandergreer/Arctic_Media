# app/config.py
import os
from pydantic import Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
load_dotenv(override=True)

class Settings(BaseSettings):
    FS_BROWSE_ROOTS: str = ""  # comma-separated extra roots to expose, e.g. "D:\\Media,\\\\NAS\\Share,/mnt/media"
    BRAND_NAME: str = "Arctic Media Server"
    # Hardened file browser:
    #   - mode: "allowlist" (recommended) or "dev_open"
    FS_BROWSE_MODE: str = "allowlist"
    # Comma-separated absolute paths that are browseable roots (required in allowlist mode)
    FS_BROWSE_ALLOW: str = ""
    # Optional comma-separated absolute paths to always deny (take precedence)
    FS_BROWSE_DENY: str = ""
    APP_NAME: str = "Arctic Media"
    ENV: str = Field(default="dev", description="dev|prod")
    DEBUG: bool = False

    # crypto and session
    SECRET_KEY: str = Field(default_factory=lambda: os.urandom(32).hex())

    # database
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./arctic.db",
        description="e.g. postgresql+asyncpg://user:pass@host:5432/dbname"
    )

    # networking
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # media toolchain
    FFMPEG_PATH: str = "ffmpeg"
    FFPROBE_PATH: str = "ffprobe"

    # tmdb
    TMDB_API_KEY: str = ""

    # cors (comma-separated)
    ALLOW_ORIGINS: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"
    
    FS_BROWSE_ROOTS: str = ""  # comma-separated extra roots to expose, e.g. "D:\\Media,\\\\NAS\\Share,/mnt/media"
    BRAND_NAME: str = "Arctic Media Server"

settings = Settings()

