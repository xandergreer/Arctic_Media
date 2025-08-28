# app/config.py
import os
from pydantic import Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv(override=True)

class Settings(BaseSettings):
    # branding
    BRAND_NAME: str = "Arctic Media Server"
    APP_NAME: str = "Arctic Media"

    # file browser
    FS_BROWSE_MODE: str = "allowlist"  # "allowlist" | "dev_open"
    FS_BROWSE_ALLOW: str = ""          # comma/semicolon-separated absolute paths
    # Back-compat with older code that referenced FS_BROWSE_ROOTS
    FS_BROWSE_ROOTS: str = ""          # alias of FS_BROWSE_ALLOW

    # env / debug
    ENV: str = Field(default="dev", description="dev|prod")
    DEBUG: bool = False

    # crypto and session
    SECRET_KEY: str = Field(default_factory=lambda: os.urandom(32).hex())
    COOKIE_SECURE: bool = False  # set True behind TLS

    # database
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./arctic.db",
        description="e.g. postgresql+asyncpg://user:pass@host:5432/dbname"
    )

    # Server configuration
    HOST: str = Field(default="0.0.0.0", description="Server host binding")
    PORT: int = Field(default=8000, description="Server port")

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

settings = Settings()
