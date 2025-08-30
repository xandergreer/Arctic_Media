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
from sqlalchemy import event
from .config import settings

for name in ("sqlalchemy.engine", "sqlalchemy.pool"):
    logging.getLogger(name).setLevel(logging.WARNING)

Base = declarative_base()

_engine: Optional[AsyncEngine] = None
_SessionLocal: Optional[async_sessionmaker[AsyncSession]] = None

def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        db_url = getattr(settings, "DATABASE_URL", None)
        if not db_url:
            raise RuntimeError("settings.DATABASE_URL is not set")

        _engine = create_async_engine(
            db_url,
            echo=False,
            future=True,
            pool_pre_ping=True,
            connect_args={"timeout": 30},  # reduce lock waits; seconds
        )
        # Apply SQLite pragmas on each new connection to improve concurrency
        try:
            def _set_sqlite_pragmas(dbapi_conn, _record):
                try:
                    cur = dbapi_conn.cursor()
                    cur.execute("PRAGMA journal_mode=WAL;")
                    cur.execute("PRAGMA synchronous=NORMAL;")
                    cur.execute("PRAGMA temp_store=MEMORY;")
                    cur.execute("PRAGMA busy_timeout=30000;")
                    cur.close()
                except Exception:
                    pass

            event.listen(_engine.sync_engine, "connect", _set_sqlite_pragmas)
        except Exception:
            pass
    return _engine

def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
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
    from . import models  # noqa: F401
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Ensure helpful indexes exist (idempotent for SQLite)
        try:
            await conn.exec_driver_sql(
                "CREATE INDEX IF NOT EXISTS ix_media_items_created_at ON media_items (created_at)"
            )
        except Exception:
            pass
        try:
            await conn.exec_driver_sql(
                "CREATE INDEX IF NOT EXISTS ix_media_files_item_created ON media_files (media_item_id, created_at)"
            )
        except Exception:
            pass

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    Session = get_sessionmaker()
    async with Session() as session:
        yield session
