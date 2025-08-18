# app/database.py
import logging
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.orm import declarative_base
from .config import settings

# Quiet SQLAlchemy's chatty logs
for name in ("sqlalchemy.engine", "sqlalchemy.pool"):
    logging.getLogger(name).setLevel(logging.WARNING)

Base = declarative_base()

_engine: Optional[AsyncEngine] = None
_SessionLocal: Optional[async_sessionmaker[AsyncSession]] = None

def get_engine() -> AsyncEngine:
    """Create a singleton AsyncEngine."""
    global _engine
    if _engine is None:
        db_url = getattr(settings, "DATABASE_URL", None)
        if not db_url:
            raise RuntimeError("settings.DATABASE_URL is not set")

        # Echo off by default; can enable with settings.SQL_ECHO=True (or fallback to settings.DEBUG)
        echo = bool(getattr(settings, "SQL_ECHO", getattr(settings, "DEBUG", False)))

        _engine = create_async_engine(
            db_url,
            echo=False,
            future=True,
            pool_pre_ping=True,
        )
    return _engine

def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """Create a singleton async sessionmaker."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return _SessionLocal

async def init_db() -> None:
    """Dev convenience: create tables (use Alembic in prod)."""
    from . import models  # noqa: F401
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# FastAPI dependency
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    Session = get_sessionmaker()
    async with Session() as session:
        yield session
