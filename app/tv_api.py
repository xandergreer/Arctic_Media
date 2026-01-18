# app/tv_api.py
from __future__ import annotations
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
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
    # Try multiple season title formats to be more flexible
    season_titles = [
        f"Season {int(season):02d}",  # Season 01
        f"Season {int(season)}",      # Season 1
        f"S{int(season):02d}",        # S01
        f"S{int(season)}",            # S1
    ]
    
    season_item = None
    for season_title in season_titles:
        season_item = (await db.execute(
            select(MediaItem)
            .where(MediaItem.parent_id == show_id, MediaItem.kind == MediaKind.season, MediaItem.title == season_title)
        )).scalar_one_or_none()
        if season_item:
            break
    
    if not season_item:
        return []

    eps = (await db.execute(
        select(MediaItem)
        .options(selectinload(MediaItem.files))
        .where(MediaItem.parent_id == season_item.id, MediaItem.kind == MediaKind.episode)
        .order_by(MediaItem.sort_title.asc())
    )).scalars().all()

    out = []
    for e in eps:
        ej = e.extra_json or {}
        # Get the first file ID for playback
        first_file_id = None
        if e.files:
            first_file = e.files[0]
            first_file_id = first_file.id
        
        # Clean up episode title (remove file extensions)
        title = e.title or ""
        if title:
            # Remove common video file extensions
            import re
            title = re.sub(r'\.(mkv|mp4|avi|mov|wmv|flv|webm|m4v)$', '', title, flags=re.IGNORECASE)
            # Clean up common patterns like "S01E01" at the beginning
            title = re.sub(r'^S\d+E\d+\s*[-–]\s*', '', title, flags=re.IGNORECASE)
            title = re.sub(r'^\d+x\d+\s*[-–]\s*', '', title, flags=re.IGNORECASE)
            title = re.sub(r'^\d+\.\s*', '', title)  # Remove leading episode numbers like "1. "
        
        # Prefer 'name' from extra_json if it exists (it's the enriched title from TMDB)
        display_title = ej.get("name") or title or "Unknown Episode"

        out.append({
            "id": e.id,
            "title": display_title,
            "overview": ej.get("overview") or e.overview or "",
            "still": ej.get("still") or ej.get("poster") or "", # Fallback to poster if still missing
            "air_date": ej.get("air_date") or "",
            "episode": ej.get("episode") or 0,
            "first_file_id": first_file_id,
        })
    return out
