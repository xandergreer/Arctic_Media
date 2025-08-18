# app/browse.py
from __future__ import annotations
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_db
from .models import MediaItem, MediaKind
from .auth import get_current_user

router = APIRouter(tags=["browse"])

def tpl(request: Request):
    return request.app.state.templates

@router.get("/movies", response_class=HTMLResponse)
async def movies_page(request: Request, db: AsyncSession = Depends(get_db), user = Depends(get_current_user)):
    q = await db.execute(
        select(MediaItem).where(MediaItem.kind == MediaKind.movie).order_by(MediaItem.created_at.desc())
    )
    movies = q.scalars().all()
    return tpl(request).TemplateResponse("movies.html", {"request": request, "movies": movies})

@router.get("/tv", response_class=HTMLResponse)
async def tv_page(request: Request, db: AsyncSession = Depends(get_db), user = Depends(get_current_user)):
    q = await db.execute(
        select(MediaItem).where(MediaItem.kind == MediaKind.show).order_by(MediaItem.sort_title.asc())
    )
    shows = q.scalars().all()
    return tpl(request).TemplateResponse("tv.html", {"request": request, "shows": shows})
