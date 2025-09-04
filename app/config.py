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
    PORT: int = Field(default=8085, description="Server port")
    # Port used only on first-ever startup when no server settings exist
    FIRST_RUN_PORT: int = Field(default=8085, description="First-run default port (if no settings in DB)")
    
    # SSL Configuration
    SSL_ENABLED: bool = Field(default=False, description="Enable SSL/HTTPS")
    SSL_CERT_FILE: str = Field(default="", description="Path to SSL certificate file")
    SSL_KEY_FILE: str = Field(default="", description="Path to SSL private key file")
    SSL_CERT_PASSWORD: str = Field(default="", description="SSL certificate password (if needed)")

    # networking / UX
    LOCAL_BASE_URL: str = Field(
        default="",
        description="Optional LAN origin like https://192.168.1.10:443 for in-LAN redirects",
    )

    # media toolchain
    FFMPEG_PATH: str = "ffmpeg"
    FFPROBE_PATH: str = "ffprobe"

    # metadata/enrichment
    METADATA_ALLOW_ADULT: bool = Field(default=False, description="Allow adult/NSFW results from TMDB searches")

    # tmdb
    TMDB_API_KEY: str = ""

    # cors (comma-separated)
    ALLOW_ORIGINS: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
