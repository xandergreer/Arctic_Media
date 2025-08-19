# app/tv_api.py
from __future__ import annotations
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from .database import get_db
from .auth import get_current_user
from .models import MediaItem, MediaKind

router = APIRouter(prefix="/api/tv", tags=["tv"])

def _show_out(it: MediaItem):
    ej = it.extra_json or {}
    return {
        "id": it.id,
        "title": it.title,
        "year": it.year,
        "poster": ej.get("poster") or ej.get("backdrop"),
        "first_air_date": ej.get("first_air_date"),
        "seasons": ej.get("number_of_seasons"),
        "episodes": ej.get("number_of_episodes"),
    }

@router.get("/shows")
async def list_shows(db: AsyncSession = Depends(get_db), user = Depends(get_current_user)):
    shows = (await db.execute(
        select(MediaItem)
        .where(MediaItem.kind == MediaKind.show)
        .order_by(MediaItem.sort_title.asc())
    )).scalars().all()
    return [_show_out(s) for s in shows]

@router.get("/seasons")
async def list_seasons(
    show_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user),
):
    seasons = (await db.execute(
        select(MediaItem)
        .where(MediaItem.parent_id == show_id, MediaItem.kind == MediaKind.season)
        .order_by(MediaItem.sort_title.asc())
    )).scalars().all()
    out = []
    for s in seasons:
        n = None
        try:
            n = int((s.title or "").split()[-1])
        except Exception:
            pass
        out.append({"id": s.id, "title": s.title, "season": n})
    return out

@router.get("/episodes")
async def list_episodes(
    show_id: str = Query(...),
    season: int = Query(...),
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user),
):
    # find season item by title "Season NN"
    season_title = f"Season {int(season):02d}"
    season_item = (await db.execute(
        select(MediaItem)
        .where(MediaItem.parent_id == show_id, MediaItem.kind == MediaKind.season, MediaItem.title == season_title)
    )).scalar_one_or_none()
    if not season_item:
        return []

    eps = (await db.execute(
        select(MediaItem)
        .where(MediaItem.parent_id == season_item.id, MediaItem.kind == MediaKind.episode)
        .order_by(MediaItem.sort_title.asc())
    )).scalars().all()

    out = []
    for e in eps:
        ej = e.extra_json or {}
        out.append({
            "id": e.id,
            "title": e.title,
            "still": ej.get("still"),
            "air_date": ej.get("air_date"),
        })
    return out
