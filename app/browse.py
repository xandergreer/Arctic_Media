# app/browse.py
from __future__ import annotations

import os
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .auth import get_current_user
from .database import get_db
from .models import MediaFile, MediaItem, MediaKind

router = APIRouter(tags=["browse"])

@router.get("/movies", response_class=HTMLResponse)
async def movies_grid(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user),
):
    items = (
        await db.execute(
            select(MediaItem)
            .where(MediaItem.kind == MediaKind.movie)
            .order_by(MediaItem.sort_title.asc())
            .limit(5000)
        )
    ).scalars().all()

    return request.app.state.templates.TemplateResponse(
        "movies.html",
        {
            "request": request,
            "items": items,
            "title": "Movies – Arctic",
        },
    )

@router.get("/movie/{item_id}", response_class=HTMLResponse)
async def movie_detail(
    item_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user),
):
    item = await db.get(MediaItem, item_id)
    if not item or item.kind != MediaKind.movie:
        raise HTTPException(status_code=404)

    files = (
        await db.execute(
            select(MediaFile).where(MediaFile.media_item_id == item.id)
        )
    ).scalars().all()

    # Prefer the largest local file as the default play source
    def _size(f: MediaFile) -> int:
        try:
            return os.path.getsize(f.path)
        except Exception:
            return 0

    files.sort(key=_size, reverse=True)

    return request.app.state.templates.TemplateResponse(
        "movie_detail.html",
        {
            "request": request,
            "item": item,
            "files": files,
            "title": f"{item.title or 'Movie'} – Arctic",
        },
    )

@router.get("/tv", response_class=HTMLResponse)
async def tv_spa(request: Request, user = Depends(get_current_user)):
    return request.app.state.templates.TemplateResponse(
        "tv_spa.html",
        {"request": request, "title": "TV – Arctic"},
    )
