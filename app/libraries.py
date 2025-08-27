# app/libraries.py
from __future__ import annotations

import os
import re
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from .auth import get_current_user, require_admin
from .config import settings
from .database import get_db
from .metadata import enrich_library
from .models import Library, MediaFile, MediaItem, MediaKind
from .scanner import scan_movie_library, scan_tv_library
from .schemas import LibraryOut
from .utils import guess_title_year, normalize_sort  # (no slugify import here)

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

# ───────────────────────── Slug utilities ─────────────────────────

_slug_re = re.compile(r"[^a-z0-9]+")

def slugify(s: str) -> str:
    s = (s or "").lower().strip()
    s = _slug_re.sub("-", s).strip("-")
    return s or "library"

async def generate_unique_slug(db: AsyncSession, owner_user_id: str, base: str) -> str:
    """
    Return a slug unique for (owner_user_id, slug):
      base, base-2, base-3, ...
    """
    base = slugify(base)
    slug = base
    n = 2
    while True:
        exists = (await db.execute(
            select(func.count()).select_from(Library)
            .where(Library.owner_user_id == owner_user_id, Library.slug == slug)
        )).scalar_one()
        if exists == 0:
            return slug
        slug = f"{base}-{n}"
        n += 1

# ───────────────────────── Title normalization (TV) ─────────────────────────

# Junk patterns commonly found in folder/file names that should not be part of a show title.
_JUNK_PATTERNS = re.compile(
    r"""(?ix)
        \b(19|20)\d{2}\b|          # years
        \bS\d{1,2}E\d{1,3}\b|      # SxxEyy
        \bS\d{1,2}\b|              # Sxx
        \bE\d{1,3}\b|              # Exx
        \b(2160p|1080p|720p|4k)\b|
        \b(HEVC|H\.?265|H\.?264|x265|x264)\b|
        \b(Blu-?Ray|WEB[- ]?(DL|Rip)|HDR10|HDR|DV|DoVi)\b|
        \b(DDP?\.?5\.1|AAC|FLAC|DTS[- ]?HD(?:MA)?)\b|
        \b(PROPER|REPACK|EXTENDED|INTERNAL|UNCENSORED)\b
    """
)

def _clean_segment(name: str) -> str:
    """Normalize a folder/file-ish segment to a clean human title."""
    n = name.replace(".", " ").replace("_", " ").strip()
    n = _JUNK_PATTERNS.sub("", n)
    n = re.sub(r"\s{2,}", " ", n).strip(" -_.")
    # Drop leading library labels like TV, Shows
    if n.lower().startswith("tv "):
        n = n[3:].strip()
    if n.lower() in {"tv", "shows", "tv shows"}:
        n = ""
    return n

def _collapse_dupes(s: str) -> str:
    """Collapse duplicated adjacent words: 'Yellowstone Yellowstone' -> 'Yellowstone'."""
    if not s:
        return s
    s = re.sub(r"\b(\w+)(\s+\1)+\b", r"\1", s, flags=re.I)
    s = re.sub(r"^(?P<x>.+?)\s+\1$", r"\g<x>", s, flags=re.I)
    return s.strip()

def _clean_show_title_from_existing(title: str) -> str:
    """Clean a show title that may have picked up 'TV' or release junk."""
    t = _clean_segment(title)
    t = re.sub(r"^(tv|shows|tv shows)\s+", "", t, flags=re.I).strip()
    t = _collapse_dupes(t)
    return t

async def _retitle_tv_shows(db: AsyncSession, library_id: str) -> int:
    """
    In-place cleanup for TV show titles in a library.
    - Strips 'TV ' prefixes and release junk that slipped into the stored show title.
    - Collapses duplicated words like 'Yellowstone Yellowstone'.
    Returns the number of show rows changed.
    """
    shows = (await db.execute(
        select(MediaItem).where(
            MediaItem.library_id == library_id,
            MediaItem.kind == MediaKind.show
        )
    )).scalars().all()

    changed = 0
    for show in shows:
        old = show.title or ""
        new = _clean_show_title_from_existing(old)
        if new and new != old:
            show.title = new
            show.sort_title = normalize_sort(new)
            changed += 1

    if changed:
        await db.commit()
    return changed

_EP_RE = re.compile(r"[Ss](\d{1,2})[ ._-]*[Ee](\d{1,3})")

async def _repair_tv_episodes(db: AsyncSession, library_id: str) -> dict:
    """
    For each season in the library:
      - Look at all MediaFiles currently attached to any episode under that season.
      - Parse SxxEyy from each file path.
      - Ensure there's a distinct MediaItem(episode) for each Eyy and move the file to it.
    Returns counters of created episode items and moved files.
    """
    # seasons in this library
    seasons = (await db.execute(
        select(MediaItem).where(
            MediaItem.library_id == library_id,
            MediaItem.kind == MediaKind.season
        )
    )).scalars().all()

    created_eps = 0
    moved_files = 0

    for season in seasons:
        # try to extract season number from "Season 01"
        m_season = re.search(r"(\d+)", season.title or "")
        season_num = int(m_season.group(1)) if m_season else None

        # all current episode rows under this season
        eps = (await db.execute(
            select(MediaItem).where(
                MediaItem.parent_id == season.id,
                MediaItem.kind == MediaKind.episode
            )
        )).scalars().all()
        ep_by_num = {}

        # index existing episodes by episode number when possible
        for ep in eps:
            m_ep = re.search(r"[Ee](\d{1,3})", ep.title or "")
            if m_ep:
                ep_by_num[int(m_ep.group(1))] = ep

        # all files attached to any of those episodes
        if not eps:
            continue
        ep_ids = [e.id for e in eps]
        files = (await db.execute(
            select(MediaFile).where(MediaFile.media_item_id.in_(ep_ids))
        )).scalars().all()

        changed = False
        for mf in files:
            m = _EP_RE.search(mf.path or "")
            if not m:
                continue
            s_num = int(m.group(1))
            e_num = int(m.group(2))

            # if we could read the season number, ensure file belongs to this season
            if season_num and s_num != season_num:
                continue

            target = ep_by_num.get(e_num)
            if not target:
                # create the missing episode row
                title = f"S{(season_num or 0):02d}E{e_num:02d}"
                target = MediaItem(
                    library_id=season.library_id,
                    kind=MediaKind.episode,
                    parent_id=season.id,
                    title=title,
                    sort_title=normalize_sort(title),
                )
                db.add(target)
                await db.flush()  # get target.id
                ep_by_num[e_num] = target
                created_eps += 1
                changed = True

            if mf.media_item_id != target.id:
                mf.media_item_id = target.id
                moved_files += 1
                changed = True

        if changed:
            await db.commit()

    return {"created_episodes": created_eps, "moved_files": moved_files}


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
    existing = (await db.execute(
        select(Library).where(
            Library.owner_user_id == admin.id,
            Library.path == abs_path,
        )
    )).scalars().first()
    if existing:
        return existing

    # Unique slug for this owner
    base_for_slug = name or lib_type
    slug = await generate_unique_slug(db, admin.id, base_for_slug)

    lib = Library(
        owner_user_id = admin.id,
        name          = name,
        slug          = slug,     # e.g., tv, tv-2, tv-3
        type          = lib_type,
        path          = abs_path,
    )

    try:
        db.add(lib)
        await db.commit()
    except IntegrityError:
        # Extremely rare race: regenerate and try once more
        await db.rollback()
        lib.slug = await generate_unique_slug(db, admin.id, base_for_slug)
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
    lib = (await db.execute(
        select(Library).where(Library.id == library_id, Library.owner_user_id == admin.id)
    )).scalars().first()
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
    lib = (await db.execute(
        select(Library).where(Library.id == library_id, Library.owner_user_id == admin.id)
    )).scalars().first()
    if not lib:
        raise HTTPException(status_code=404, detail="Library not found")

    if lib.type == "movie":
        stats = await scan_movie_library(db, lib)
        return {"ok": True, **stats}

    if lib.type == "tv":
        stats = await scan_tv_library(db, lib)
        # 1) fix mis-titled shows (you already had this)
        retitled = await _retitle_tv_shows(db, lib.id)
        # 2) NEW: split files so each SxxEyy gets its own episode row
        repaired = await _repair_tv_episodes(db, lib.id)
        return {"ok": True, **stats, "tv_retitled": retitled, "tv_repaired": repaired}

    raise HTTPException(status_code=400, detail="Unsupported library type")

@router.post("/{library_id}/refresh_metadata")
async def refresh_metadata_endpoint(
    library_id: str,
    force: bool = Query(False, description="Re-match everything even if tmdb_id exists"),
    only_missing: bool = Query(True, description="Touch only items missing posters/backdrops"),
    db: AsyncSession = Depends(get_db),
    admin = Depends(require_admin),
):
    lib = (await db.execute(
        select(Library).where(Library.id == library_id, Library.owner_user_id == admin.id)
    )).scalars().first()
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

@router.post("/{library_id}/retitle_tv")
async def retitle_tv(
    library_id: str,
    db: AsyncSession = Depends(get_db),
    admin = Depends(require_admin),
):
    lib = (await db.execute(
        select(Library).where(Library.id == library_id, Library.owner_user_id == admin.id)
    )).scalars().first()
    if not lib:
        raise HTTPException(status_code=404, detail="Library not found")
    if lib.type != "tv":
        raise HTTPException(status_code=400, detail="This endpoint is only for TV libraries")

    changed = await _retitle_tv_shows(db, library_id)
    return {"tv_retitled": changed}
