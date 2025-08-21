# app/libraries.py
from __future__ import annotations

import os
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from .auth import get_current_user, require_admin
from .config import settings
from .database import get_db
from .metadata import enrich_library
from .models import Library, MediaFile, MediaItem, MediaKind
from .scanner import scan_movie_library, scan_tv_library
from .schemas import LibraryOut
from .utils import (
    guess_title_year,
    normalize_sort,
    slugify,
)

router = APIRouter(prefix="/libraries", tags=["libraries"])

# ───────────────────────── HTML page ─────────────────────────

@router.get("/manage", response_class=HTMLResponse)
async def libraries_page(request: Request, user = Depends(get_current_user)):
    return request.app.state.templates.TemplateResponse(
        "settings_libraries.html", {"request": request}
    )

# ───────────────────────── Schemas ─────────────────────────

class LibraryCreateIn(BaseModel):
    name: Optional[str] = None
    type: str              # "movie" | "tv"
    path: str

# ───────────────────────── APIs ─────────────────────────

@router.get("", response_model=List[LibraryOut])
async def list_libraries(
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user),
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
    admin = Depends(require_admin),
):
    lib_type = (payload.type or "").strip().lower()
    if lib_type not in {"movie", "tv"}:
        raise HTTPException(status_code=400, detail="type must be 'movie' or 'tv'")

    if not payload.path:
        raise HTTPException(status_code=400, detail="Path is required")

    abs_path = os.path.abspath(payload.path).rstrip("\\/")
    if not os.path.isdir(abs_path):
        raise HTTPException(status_code=400, detail="Path does not exist or is not a directory")

    # Default name from folder tail if not provided
    name = (payload.name or "").strip()
    if not name:
        tail = os.path.basename(abs_path)
        name = tail or ("Movies" if lib_type == "movie" else "TV")

    # Prevent duplicates for this owner/path pair
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
        owner_user_id = admin.id,
        name          = name,
        slug          = slugify(name),
        type          = lib_type,
        path          = abs_path,
    )
    db.add(lib)
    await db.commit()
    await db.refresh(lib)
    return lib

@router.delete("/{library_id}")
async def delete_library(
    library_id: str,
    db: AsyncSession = Depends(get_db),
    admin = Depends(require_admin),
):
    lib = (
        await db.execute(
            select(Library).where(Library.id == library_id, Library.owner_user_id == admin.id)
        )
    ).scalars().first()
    if not lib:
        raise HTTPException(status_code=404, detail="Library not found")

    await db.delete(lib)
    await db.commit()
    return {"ok": True}

@router.post("/{library_id}/scan")
async def scan_library(
    library_id: str,
    db: AsyncSession = Depends(get_db),
    admin = Depends(require_admin),
):
    lib = (
        await db.execute(
            select(Library).where(Library.id == library_id, Library.owner_user_id == admin.id)
        )
    ).scalars().first()
    if not lib:
        raise HTTPException(status_code=404, detail="Library not found")

    if lib.type == "movie":
        stats = await scan_movie_library(db, lib)
    elif lib.type == "tv":
        stats = await scan_tv_library(db, lib)
    else:
        raise HTTPException(status_code=400, detail="Unsupported library type")

    return {"ok": True, **stats}

@router.post("/{library_id}/refresh_metadata")
async def refresh_metadata_endpoint(
    library_id: str,
    force: bool = Query(False, description="Re-match everything even if tmdb_id exists"),
    only_missing: bool = Query(True, description="Touch only items missing posters/backdrops"),
    db: AsyncSession = Depends(get_db),
    admin = Depends(require_admin),
):
    lib = (
        await db.execute(
            select(Library).where(Library.id == library_id, Library.owner_user_id == admin.id)
        )
    ).scalars().first()
    if not lib:
        raise HTTPException(status_code=404, detail="Library not found")

    if not settings.TMDB_API_KEY:
        raise HTTPException(status_code=400, detail="TMDB_API_KEY not configured")

    stats = await enrich_library(
        db,
        settings.TMDB_API_KEY,
        library_id,
        limit=5000,
        force=force,
        only_missing=only_missing,
    )
    return {"ok": True, "stats": stats}

@router.post("/{library_id}/cleanup_samples")
async def cleanup_samples(
    library_id: str,
    db: AsyncSession = Depends(get_db),
    admin = Depends(require_admin),
):
    # remove items that look like "sample"
    item_ids = (await db.execute(
        select(MediaItem.id).where(
            MediaItem.library_id == library_id,
            MediaItem.title.ilike("%sample%")
        )
    )).scalars().all()

    if not item_ids:
        return {"removed": 0}

    await db.execute(delete(MediaFile).where(MediaFile.media_item_id.in_(item_ids)))
    await db.execute(delete(MediaItem).where(MediaItem.id.in_(item_ids)))
    await db.commit()
    return {"removed": len(item_ids)}

@router.post("/{library_id}/retitle")
async def retitle_movies(
    library_id: str,
    db: AsyncSession = Depends(get_db),
    admin = Depends(require_admin),
):
    # Retitle only movie items (TV is hierarchical already)
    movies = (await db.execute(
        select(MediaItem).where(
            MediaItem.library_id == library_id,
            MediaItem.kind == MediaKind.movie
        )
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
