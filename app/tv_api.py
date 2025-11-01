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

    # Get show item for poster fallback
    show_item = (await db.execute(
        select(MediaItem)
        .where(MediaItem.id == show_id, MediaItem.kind == MediaKind.show)
    )).scalar_one_or_none()
    
    # Get show and season posters for fallback
    show_poster = None
    if show_item:
        show_ej = show_item.extra_json or {}
        show_poster = show_ej.get("poster") or show_item.poster_url
    
    season_ej = season_item.extra_json or {}
    season_poster = season_ej.get("poster") or season_item.poster_url
    # If season poster is not available, use show poster as fallback
    if not season_poster:
        season_poster = show_poster

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
        
        # Get episode title - prefer metadata name, then cleaned title
        title = ej.get("name")  # TMDB episode name from metadata
        if not title:
            # Fallback to cleaning the stored title (filename-based)
            title = e.title or ""
            if title:
                # Remove common video file extensions
                import re
                title = re.sub(r'\.(mkv|mp4|avi|mov|wmv|flv|webm|m4v)$', '', title, flags=re.IGNORECASE)
                # Clean up common patterns like "S01E01" at the beginning
                title = re.sub(r'^S\d+E\d+\s*[-–]\s*', '', title, flags=re.IGNORECASE)
                title = re.sub(r'^\d+x\d+\s*[-–]\s*', '', title, flags=re.IGNORECASE)
                title = re.sub(r'^\d+\.\s*', '', title)  # Remove leading episode numbers like "1. "
        
        # Get episode still with fallback to season poster, then show poster
        episode_still = ej.get("still")
        # Check if still is missing, None, or empty string
        if not episode_still or (isinstance(episode_still, str) and not episode_still.strip()):
            # Use fallback: try season poster first, then show poster
            episode_still = season_poster if season_poster else show_poster
        
        # Debug logging (can be removed later)
        if not episode_still:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Episode {e.id} has no still, season_poster={bool(season_poster)}, show_poster={bool(show_poster)}")
        
        out.append({
            "id": e.id,
            "title": title,
            "still": episode_still,  # Can be None if no fallback available
            "air_date": ej.get("air_date"),
            "episode": ej.get("episode"),
            "first_file_id": first_file_id,
        })
    return out
