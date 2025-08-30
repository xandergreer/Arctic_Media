from __future__ import annotations
import asyncio
from datetime import datetime, timedelta, timezone

import logging
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_sessionmaker
from .models import ScheduledTask, ScheduledJobType, Library
from .scanner import scan_movie_library, scan_tv_library
from .metadata import enrich_library
from .config import settings

POLL_SECONDS = 30

async def _run_job(db: AsyncSession, task: ScheduledTask):
    now = datetime.now(timezone.utc)
    try:
        if task.job_type == ScheduledJobType.scan_library:
            lib_id = (task.payload or {}).get("library_id")
            if lib_id:
                lib = (await db.execute(select(Library).where(Library.id == lib_id))).scalars().first()
                if lib:
                    if lib.type == "movie":
                        await scan_movie_library(db, lib)
                    elif lib.type == "tv":
                        await scan_tv_library(db, lib)
        elif task.job_type == ScheduledJobType.refresh_metadata:
            lib_id = (task.payload or {}).get("library_id")
            if lib_id:
                await enrich_library(db, settings.TMDB_API_KEY, lib_id, limit=5000)
    finally:
        next_time = now + timedelta(minutes=task.interval_minutes or 60)
        await db.execute(
            update(ScheduledTask)
            .where(ScheduledTask.id == task.id)
            .values(last_run_at=now, next_run_at=next_time)
        )
        await db.commit()

async def scheduler_loop():
    Session = get_sessionmaker()
    while True:
        try:
            async with Session() as db:  # db is an AsyncSession
                now = datetime.now(timezone.utc)
                result = await db.execute(
                    select(ScheduledTask)
                    .where(ScheduledTask.enabled.is_(True))
                    .where(
                        (ScheduledTask.next_run_at.is_(None)) |
                        (ScheduledTask.next_run_at <= now)
                    ).order_by(ScheduledTask.next_run_at.nullsfirst()).limit(5)
                )
                for task in result.scalars().all():
                    await _run_job(db, task)
        except Exception as e:
            logging.getLogger("scheduler").warning("scheduler loop error: %s", e)
        await asyncio.sleep(POLL_SECONDS)

def start_scheduler(app):
    app.state.scheduler_task = asyncio.create_task(scheduler_loop())
