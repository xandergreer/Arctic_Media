# app/libraries.py
from __future__ import annotations

import os
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_db
from .models import Library, MediaItem, MediaFile, MediaKind
from .schemas import LibraryOut
from .auth import get_current_user, require_admin
from .utils import slugify, guess_title_year, normalize_sort, is_video_file, parse_tv_parts, ffprobe_info
from .metadata import enrich_library
from .config import settings
from .scanner import scan_library_job

router = APIRouter(prefix="/libraries", tags=["libraries"])

# --------------------------- HTML page ---------------------------------
@router.get("/manage", response_class=HTMLResponse)
async def libraries_page(request: Request, user=Depends(get_current_user)):
    return request.app.state.templates.TemplateResponse(
        "settings_libraries.html", {"request": request}
    )

# ---------------------------- Schemas ----------------------------------
class LibraryCreateIn(BaseModel):
    name: Optional[str] = None
    type: str           # "movie" | "tv"
    path: str

# ----------------------------- APIs ------------------------------------
@router.get("", response_model=List[LibraryOut])
async def list_libraries(
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    q = await db.execute(
        select(Library)
        .where(Library.owner_user_id == user.id)
        .order_by(Library.created_at.desc())
    )
    return q.scalars().all()

@router.post("", response_model=LibraryOut)
async def create_library(
    payload: LibraryCreateIn,
    db: AsyncSession = Depends(get_db),
    admin=Depends(require_admin),
):
    lib_type = (payload.type or "").lower().strip()
    if lib_type not in {"movie", "tv"}:
        raise HTTPException(status_code=400, detail="type must be 'movie' or 'tv'")

    if not payload.path:
        raise HTTPException(status_code=400, detail="Path is required")
    abs_path = os.path.abspath(payload.path).rstrip("\\/")
    if not os.path.isdir(abs_path):
        raise HTTPException(status_code=400, detail="Path does not exist or is not a directory")

    name = (payload.name or "").strip()
    if not name:
        tail = os.path.basename(abs_path)
        name = tail or ("Movies" if lib_type == "movie" else "TV")

    existing = (
        await db.execute(
            select(Library).where(
                Library.owner_user_id == admin.id,
                Library.path == abs_path,
            )
        )
    ).scalars().first()
    if existing:
        return existing

    lib = Library(
        owner_user_id=admin.id,
        name=name,
        slug=slugify(name),
        type=lib_type,
        path=abs_path,
    )
    db.add(lib)
    await db.commit()
    await db.refresh(lib)
    return lib

@router.delete("/{library_id}")
async def delete_library(
    library_id: str,
    db: AsyncSession = Depends(get_db),
    admin=Depends(require_admin),
):
    res = await db.execute(
        select(Library).where(Library.id == library_id, Library.owner_user_id == admin.id)
    )
    lib = res.scalars().first()
    if not lib:
        raise HTTPException(status_code=404, detail="Library not found")
    await db.delete(lib)
    await db.commit()
    return {"ok": True}

@router.post("/{library_id}/scan")
async def scan_library_endpoint(
    library_id: str,
    db: AsyncSession = Depends(get_db),
    admin = Depends(require_admin),
):
    # Ensure library exists and belongs to current admin
    res = await db.execute(
        select(Library).where(Library.id == library_id, Library.owner_user_id == admin.id)
    )
    lib = res.scalars().first()
    if not lib:
        raise HTTPException(status_code=404, detail="Library not found")

    # Run scan inline and return stats
    stats = await scan_library_job(library_id, return_stats=True)
    return {"ok": True, **stats}

@router.post("/{library_id}/refresh_metadata")
async def refresh_metadata(library_id: str, db: AsyncSession = Depends(get_db), admin = Depends(require_admin)):
    lib = await db.get(Library, library_id)
    if not lib:
        raise HTTPException(404, "Library not found")
    if not settings.TMDB_API_KEY:
        raise HTTPException(400, "TMDB_API_KEY not configured")
    stats = await enrich_library(db, settings.TMDB_API_KEY, library_id, limit=5000)
    return {"ok": True, "stats": stats}

@router.post("/{library_id}/cleanup_samples")
async def cleanup_samples(library_id: str, db: AsyncSession = Depends(get_db), admin = Depends(require_admin)):
    items = (await db.execute(
        select(MediaItem.id).where(
            MediaItem.library_id == library_id,
            MediaItem.title.ilike("%sample%")
        )
    )).scalars().all()
    if not items:
        return {"removed": 0}
    await db.execute(delete(MediaFile).where(MediaFile.media_item_id.in_(items)))
    await db.execute(delete(MediaItem).where(MediaItem.id.in_(items)))
    await db.commit()
    return {"removed": len(items)}

@router.post("/{library_id}/retitle")
async def retitle_movies(library_id: str, db: AsyncSession = Depends(get_db), admin = Depends(require_admin)):
    # only movies; TV already has structured show/season/episode
    movies = (await db.execute(
        select(MediaItem).where(MediaItem.library_id == library_id, MediaItem.kind == MediaKind.movie)
    )).scalars().all()
    changed = 0
    for m in movies:
        f = (await db.execute(
            select(MediaFile).where(MediaFile.media_item_id == m.id).limit(1)
        )).scalars().first()
        if not f:
            continue
        new_title, new_year = guess_title_year(f.path)
        if new_title and new_title != m.title:
            m.title = new_title
            m.sort_title = normalize_sort(new_title)
            if new_year and not m.year:
                m.year = new_year
            changed += 1
    await db.commit()
    return {"retitled": changed}
