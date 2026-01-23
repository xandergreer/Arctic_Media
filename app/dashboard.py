from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from .database import get_db
from .auth import get_current_user
from .models import MediaItem, MediaKind, UserProgress, MediaFile

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

def _item_out(it: MediaItem):
    ej = it.extra_json or {}
    return {
        "id": it.id,
        "title": it.title,
        "year": it.year,
        "poster_url": it.poster_url or ej.get("poster"),
        "backdrop_url": it.backdrop_url,
        "kind": it.kind,
        "description": it.overview,
        "extra_json": {"poster": it.poster_url or ej.get("poster")}
    }

@router.get("/")
async def dashboard_index(db: AsyncSession = Depends(get_db), user = Depends(get_current_user)):
    # 1) Continue Watching (UserProgress where is_finished=False and position > 30s)
    # Join MediaItem to get details.
    
    # Simple query:
    q_progress = (
        select(UserProgress, MediaItem)
        .join(MediaItem, UserProgress.media_item_id == MediaItem.id)
        .where(
            UserProgress.user_id == user.id,
            UserProgress.is_finished == False,
            UserProgress.position_ms > 30000 
        )
        .order_by(UserProgress.updated_at.desc())
        .limit(20)
    )
    res_cw = (await db.execute(q_progress)).all()
    
    continue_watching = []
    for prog, item in res_cw:
        data = _item_out(item)
        data["position_ms"] = prog.position_ms
        continue_watching.append(data)

    # 2) Recent Movies
    q_movies = (
        select(MediaItem)
        .where(MediaItem.kind == MediaKind.movie)
        .order_by(MediaItem.created_at.desc())
        .limit(15)
    )
    res_movies = (await db.execute(q_movies)).scalars().all()
    recent_movies = [_item_out(m) for m in res_movies]

    # 3) Recent TV (Shows added recently)
    q_tv = (
        select(MediaItem)
        .where(MediaItem.kind == MediaKind.show)
        .order_by(MediaItem.created_at.desc())
        .limit(15)
    )
    res_tv = (await db.execute(q_tv)).scalars().all()
    recent_tv = [_item_out(s) for s in res_tv]

    return {
        "continue_watching": continue_watching,
        "recent_movies": recent_movies,
        "recent_tv": recent_tv
    }
