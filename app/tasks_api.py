from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, insert, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from .auth import require_admin
from .database import get_db
from .models import ScheduledTask, ScheduledJobType

router = APIRouter(prefix="/admin/tasks", tags=["tasks"])

class TaskIn(BaseModel):
    name: str
    job_type: ScheduledJobType
    interval_minutes: int = Field(ge=1, le=24*60, default=60)
    library_id: str | None = None  # used for scan_library

class TaskOut(BaseModel):
    id: str
    name: str
    job_type: ScheduledJobType
    interval_minutes: int
    enabled: bool
    last_run_at: str | None = None
    next_run_at: str | None = None
    payload: dict | None = None
    class Config: from_attributes = True

@router.get("", response_model=list[TaskOut])
async def list_tasks(_: str = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(ScheduledTask).order_by(ScheduledTask.created_at.desc()))
    return res.scalars().all()

@router.post("", response_model=TaskOut, status_code=201)
async def create_task(body: TaskIn, _: str = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    payload = {}
    if body.job_type == ScheduledJobType.scan_library:
        if not body.library_id:
            raise HTTPException(400, "library_id required")
        payload = {"library_id": body.library_id}
    stmt = insert(ScheduledTask).values(
        name=body.name, job_type=body.job_type, interval_minutes=body.interval_minutes,
        payload=payload, enabled=True
    ).returning(ScheduledTask)
    row = (await db.execute(stmt)).scalar_one()
    await db.commit()
    return row

class TaskPatch(BaseModel):
    name: str | None = None
    interval_minutes: int | None = Field(default=None, ge=1, le=24*60)
    enabled: bool | None = None

@router.patch("/{task_id}", response_model=TaskOut)
async def update_task(task_id: str, body: TaskPatch, _: str = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    vals = {k:v for k,v in body.model_dump(exclude_none=True).items()}
    if vals:
        await db.execute(update(ScheduledTask).where(ScheduledTask.id==task_id).values(**vals))
        await db.commit()
    res = await db.execute(select(ScheduledTask).where(ScheduledTask.id==task_id))
    row = res.scalars().first()
    if not row: raise HTTPException(404, "Not found")
    return row

@router.delete("/{task_id}")
async def delete_task(task_id: str, _: str = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    await db.execute(delete(ScheduledTask).where(ScheduledTask.id==task_id))
    await db.commit()
    return {"ok": True}

@router.post("/{task_id}/run")
async def run_now(task_id: str, _: str = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    # set next_run_at=now to pick it up in the next scheduler tick
    res = await db.execute(select(ScheduledTask).where(ScheduledTask.id==task_id))
    row = res.scalars().first()
    if not row: raise HTTPException(404, "Not found")
    await db.execute(update(ScheduledTask).where(ScheduledTask.id==task_id).values(next_run_at=None))
    await db.commit()
    return {"ok": True}
