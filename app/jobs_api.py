from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .auth import require_admin
from .database import get_db
from .models import BackgroundJob

router = APIRouter(prefix="/jobs", tags=["jobs"])


class JobOut(BaseModel):
    id: str
    job_type: str
    library_id: str | None
    status: str
    progress: int | None
    total: int | None
    message: str | None
    result: dict | None
    class Config: from_attributes = True


@router.get("/{job_id}", response_model=JobOut)
async def get_job(job_id: str, db: AsyncSession = Depends(get_db), _: str = Depends(require_admin)):
    res = await db.execute(select(BackgroundJob).where(BackgroundJob.id == job_id))
    job = res.scalars().first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("", response_model=list[JobOut])
async def list_jobs(db: AsyncSession = Depends(get_db), _: str = Depends(require_admin)):
    res = await db.execute(select(BackgroundJob).order_by(BackgroundJob.created_at.desc()).limit(50))
    return res.scalars().all()

