# app/libraries.py
from __future__ import annotations

import os
from typing import List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from .database import get_db, get_sessionmaker
from .models import Library, MediaItem, MediaFile, MediaKind
from .schemas import LibraryOut  # keep response model
from .auth import get_current_user, require_admin
from .utils import slugify, is_video_file, guess_title_year, parse_tv_parts, ffprobe_info
from .metadata import enrich_library
from .config import settings

router = APIRouter(prefix="/libraries", tags=["libraries"])


# --------------------------- HTML page ---------------------------------
@router.get("/manage", response_class=HTMLResponse)
async def libraries_page(request: Request, user=Depends(get_current_user)):
    return request.app.state.templates.TemplateResponse(
        "settings_libraries.html", {"request": request}
    )


# ---------------------------- Schemas ----------------------------------
# Make 'name' optional on create. Using a local input model avoids 422 if omitted.
class LibraryCreateIn(BaseModel):
    name: Optional[str] = None
    type: str           # "movie" | "tv" (case-insensitive)
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
    # Normalize & validate type
    lib_type = (payload.type or "").lower().strip()
    if lib_type not in {"movie", "tv"}:
        raise HTTPException(status_code=400, detail="type must be 'movie' or 'tv'")

    # Normalize path and ensure it exists
    if not payload.path:
        raise HTTPException(status_code=400, detail="Path is required")
    abs_path = os.path.abspath(payload.path).rstrip("\\/")

    if not os.path.isdir(abs_path):
        raise HTTPException(status_code=400, detail="Path does not exist or is not a directory")

    # Compute default name when omitted/blank
    name = (payload.name or "").strip()
    if not name:
        tail = os.path.basename(abs_path)
        name = tail or ("Movies" if lib_type == "movie" else "TV")

    # Optional: avoid duplicate libraries for same owner+path
    existing = (
        await db.execute(
            select(Library).where(
                Library.owner_user_id == admin.id,
                Library.path == abs_path,
            )
        )
    ).scalars().first()
    if existing:
        # Return existing instead of error (friendlier UX), or change to 409 if you prefer.
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

async def trigger_library_scan(db: AsyncSession, library_id: str):
    # Convenience if you ever want to call synchronously
    await scan_library_job(library_id)


# --------------------------- Worker task --------------------------------
async def scan_library_job(library_id: str, return_stats: bool = False):
    """
    Scan a library and index media files. When return_stats=True, returns a dict:
      {added, updated, skipped, seen, known}
    """
    from .database import get_sessionmaker
    Session = get_sessionmaker()

    counters = {"added": 0, "updated": 0, "skipped": 0, "seen": 0, "known": 0}

    async with Session() as db:
        lib = (await db.execute(select(Library).where(Library.id == library_id))).scalars().first()
        if not lib:
            if return_stats:
                return counters
            return

        # Count “known” (files already in DB before scan)
        counters["known"] = (await db.execute(
            select(func.count()).select_from(MediaFile)
            .join(MediaItem, MediaItem.id == MediaFile.media_item_id)
            .where(MediaItem.library_id == library_id)
        )).scalar_one()

        if not os.path.isdir(lib.path):
            print(f"[SCAN] Library path missing or not a dir: {lib.path}")
            if return_stats:
                return counters
            return

        print(f"[SCAN] Starting scan: {lib.name} [{lib.type}] -> {lib.path}")

        for root, dirs, files in os.walk(lib.path):
            for fname in files:
                path = os.path.join(root, fname)

                # Filter to video files
                if not is_video_file(path):
                    continue

                counters["seen"] += 1
                try:
                    if lib.type == "movie":
                        added = await _index_movie(db, lib.id, path)
                    else:
                        added = await _index_tv(db, lib.id, lib.path, os.path.relpath(root, lib.path), path)

                    if added:
                        counters["added"] += 1
                    else:
                        counters["skipped"] += 1
                except Exception as e:
                    # don’t crash scan
                    print(f"[SCAN] error indexing {path}: {e}")
                    counters["skipped"] += 1

        # Optional: metadata enrichment (can be slow). Keep it, but it doesn’t affect counts.
        try:
            from .config import settings
            from .metadata import enrich_library
            if getattr(settings, "TMDB_API_KEY", ""):
                await enrich_library(db, settings.TMDB_API_KEY, library_id, limit=1000)
        except Exception as e:
            print(f"[SCAN] metadata enrichment error: {e}")

        await db.commit()

        print(f"[SCAN] Done: seen={counters['seen']} added={counters['added']} skipped={counters['skipped']} known(before)={counters['known']}")

        if return_stats:
            return counters

# --------------------------- Index helpers ------------------------------
async def _get_or_create_media(
    db: AsyncSession,
    library_id: str,
    kind: MediaKind,
    title: str,
    year: Optional[int] = None,
    parent_id: Optional[str] = None,
) -> MediaItem:
    # 1) Try to find it first
    q = await db.execute(
        select(MediaItem).where(
            MediaItem.library_id == library_id,
            MediaItem.kind == kind,
            MediaItem.title == title,
            (MediaItem.year.is_(None) if year is None else MediaItem.year == year),
            (MediaItem.parent_id.is_(None) if parent_id is None else MediaItem.parent_id == parent_id),
        )
    )
    mi = q.scalars().first()
    if mi:
        return mi

    # 2) Not found -> insert
    mi = MediaItem(
        library_id=library_id,
        kind=kind,
        title=title,
        year=year,
        parent_id=parent_id,
        sort_title=title.lower(),
    )
    db.add(mi)

    # 3) Flush; if UNIQUE fails, rollback and fetch existing
    try:
        await db.flush()
        return mi
    except IntegrityError:
        # Another row with the same (library_id, kind, title, year, parent_id) exists.
        # Roll back the failed INSERT, then re-select and return it.
        await db.rollback()
        q2 = await db.execute(
            select(MediaItem).where(
                MediaItem.library_id == library_id,
                MediaItem.kind == kind,
                MediaItem.title == title,
                (MediaItem.year.is_(None) if year is None else MediaItem.year == year),
                (MediaItem.parent_id.is_(None) if parent_id is None else MediaItem.parent_id == parent_id),
            )
        )
        existing = q2.scalars().first()
        if existing:
            # Session will autobegin a new transaction on the next write.
            return existing
        # If we truly can’t find it, re-raise for visibility.
        raise


async def _index_movie(db: AsyncSession, library_id: str, path: str) -> bool:
    title, year = guess_title_year(path)
    movie = await _get_or_create_media(db, library_id, MediaKind.movie, title, year)
    info = ffprobe_info(path)

    existing = (await db.execute(
        select(MediaFile).where(MediaFile.media_item_id == movie.id, MediaFile.path == path)
    )).scalars().first()
    if existing:
        return False

    db.add(MediaFile(
        media_item_id=movie.id,
        path=path,
        container=info.get("container"),
        vcodec=info.get("vcodec"),
        acodec=info.get("acodec"),
        width=info.get("width"),
        height=info.get("height"),
        bitrate=info.get("bitrate"),
        size_bytes=os.path.getsize(path) if os.path.exists(path) else None
    ))
    return True


async def _index_tv(db: AsyncSession, library_id: str, lib_root: str, rel_root: str, path: str) -> bool:
    parsed = parse_tv_parts(rel_root, path)
    if not parsed:
        # fallback: treat as movie if we can't parse SxxEyy
        return await _index_movie(db, library_id, path)

    show_title, season, episode, ep_title_guess = parsed
    show = await _get_or_create_media(db, library_id, MediaKind.show, show_title, None, None)
    season_item = await _get_or_create_media(db, library_id, MediaKind.season, f"Season {season}", None, show.id)
    ep_title = ep_title_guess
    episode_item = await _get_or_create_media(db, library_id, MediaKind.episode, ep_title, None, season_item.id)
    if not episode_item.extra_json:
        episode_item.extra_json = {"season": season, "episode": episode}

    info = ffprobe_info(path)
    existing = (await db.execute(
        select(MediaFile).where(MediaFile.media_item_id == episode_item.id, MediaFile.path == path)
    )).scalars().first()
    if existing:
        return False

    db.add(MediaFile(
        media_item_id=episode_item.id,
        path=path,
        container=info.get("container"),
        vcodec=info.get("vcodec"),
        acodec=info.get("acodec"),
        width=info.get("width"),
        height=info.get("height"),
        bitrate=info.get("bitrate"),
        size_bytes=os.path.getsize(path) if os.path.exists(path) else None
    ))
    return True

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