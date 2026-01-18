# app/libraries.py
from __future__ import annotations

import os
import re
from typing import List, Optional

import asyncio
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from .auth import get_current_user, require_admin
from .config import settings
from .database import get_db, get_sessionmaker
from .metadata import enrich_library
from .models import Library, MediaFile, MediaItem, MediaKind, BackgroundJob
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


# ---- fire-and-forget helpers ----
async def _bg_scan_library(library_id: str, job_id: str | None = None) -> None:
    """Run a library scan in the background using a fresh DB session."""
    # Create a new event loop context for this background task
    import asyncio
    try:
        # Get or create a session maker for this context
        Session = get_sessionmaker()
        
        async with Session() as db:
            # mark job running
            if job_id:
                job = (await db.execute(select(BackgroundJob).where(BackgroundJob.id == job_id))).scalars().first()
                if job:
                    job.status = "running"
                    job.message = "Scanning library"
                    await db.commit()
            
            lib = (await db.execute(
                select(Library).where(Library.id == library_id)
            )).scalars().first()
            if not lib:
                return
                
            # progress callback updates job
            async def _progress(processed: int, total: int):
                if not job_id:
                    return
                try:
                    j = (await db.execute(select(BackgroundJob).where(BackgroundJob.id == job_id))).scalars().first()
                    if j:
                        j.progress = processed
                        j.total = total
                        j.message = f"Scanning {processed}/{total}"
                        await db.commit()
                except Exception:
                    # Ignore progress update errors in background
                    pass

            stats = {}
            # Extract simple fields to satisfy current scanner signatures
            lib_name = lib.name
            lib_type = lib.type
            lib_id = lib.id
            
            try:
                if lib.type == "movie":
                    stats = await scan_movie_library(db, lib, lib_name, lib_type, lib_id, force=getattr(lib, "_force_scan", False), progress_cb=_progress)
                elif lib.type == "tv":
                    stats = await scan_tv_library(db, lib, lib_name, lib_type, lib_id, force=getattr(lib, "_force_scan", False), progress_cb=_progress)
                await db.commit()

                if job_id:
                    job = (await db.execute(select(BackgroundJob).where(BackgroundJob.id == job_id))).scalars().first()
                    if job:
                        job.status = "done"
                        job.message = "Scan complete"
                        job.result = stats
                        await db.commit()
                        
            except Exception as e:
                # Ensure background job is marked failed instead of leaving UI polling forever
                try:
                    await db.rollback()
                except Exception:
                    pass
                if job_id:
                    try:
                        job = (await db.execute(select(BackgroundJob).where(BackgroundJob.id == job_id))).scalars().first()
                        if job:
                            job.status = "failed"
                            job.message = f"Scan error: {e!s}"
                            await db.commit()
                    except Exception:
                        pass
                # Re-raise so it surfaces in logs
                raise
                
    except Exception as e:
        # Log any unexpected errors
        import logging
        logging.getLogger(__name__).error(f"Background scan failed: {e}")
        raise

def _bg_scan_library_sync(library_id: str, job_id: str | None = None, force: bool = False) -> None:
    """Run a library scan synchronously in the background using synchronous SQLAlchemy."""
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from .database import get_engine
    from .config import settings
    import os
    from pathlib import Path
    
    try:
        # Get the database URL from the async engine
        async_url = get_engine().url
        db_url = str(async_url)
        # Convert async URL to sync URL
        if db_url.startswith("sqlite+aiosqlite://"):
            db_url = db_url.replace("sqlite+aiosqlite://", "sqlite://")
        # Ensure absolute path for sqlite to avoid per-thread CWD issues
        if db_url.startswith("sqlite:///"):
            raw_path = db_url.replace("sqlite:///", "", 1)
            if raw_path.startswith("./") or not os.path.isabs(raw_path):
                abs_path = os.path.abspath(raw_path)
                db_url = f"sqlite:///{abs_path}"
        
        # Create synchronous engine
        sync_engine = create_engine(
            db_url,
            echo=False,
            pool_pre_ping=True,
            connect_args={"timeout": 30},
        )
        
        # Apply SQLite pragmas
        def _set_sqlite_pragmas(dbapi_conn, _record):
            try:
                cur = dbapi_conn.cursor()
                cur.execute("PRAGMA journal_mode=WAL;")
                cur.execute("PRAGMA synchronous=NORMAL;")
                cur.execute("PRAGMA temp_store=MEMORY;")
                cur.execute("PRAGMA busy_timeout=30000;")
                cur.close()
            except Exception:
                pass
        
        event.listen(sync_engine, "connect", _set_sqlite_pragmas)
        
        # Create synchronous session
        sync_session = sessionmaker(bind=sync_engine, expire_on_commit=False, autoflush=False)
        
        with sync_session() as db:
            # mark job running
            if job_id:
                job = db.query(BackgroundJob).filter(BackgroundJob.id == job_id).first()
                if job:
                    job.status = "running"
                    job.message = "Scanning library"
                    db.commit()
            
            lib = db.query(Library).filter(Library.id == library_id).first()
            if not lib:
                return
                
            # progress callback updates job
            def _progress(processed: int, total: int):
                if not job_id:
                    return
                try:
                    j = db.query(BackgroundJob).filter(BackgroundJob.id == job_id).first()
                    if j:
                        j.progress = processed
                        j.total = total
                        j.message = f"Scanning {processed}/{total}"
                        db.commit()
                except Exception:
                    # Ignore progress update errors in background
                    pass

            stats = {}
            # Extract simple fields to satisfy current scanner signatures
            lib_name = lib.name
            lib_type = lib.type
            lib_id = lib.id
            
            try:
                if lib.type == "movie":
                    # Import here to avoid circular imports
                    from .scanner import scan_movie_library_sync
                    stats = scan_movie_library_sync(db, lib, lib_name, lib_type, lib_id, force=force, progress_cb=_progress)
                elif lib.type == "tv":
                    from .scanner import scan_tv_library_sync
                    stats = scan_tv_library_sync(db, lib, lib_name, lib_type, lib_id, force=force, progress_cb=_progress)
                db.commit()
                # If movie scan produced no known paths, emit diagnostic summary
                if lib.type == "movie" and (stats.get("added",0) == 0):
                    try:
                        from sqlalchemy import select
                        from .models import MediaFile, MediaItem
                        cur_count = db.execute(select(MediaFile.path).join(MediaItem, MediaItem.id==MediaFile.media_item_id).where(MediaItem.library_id==lib.id)).all()
                        import logging as _logging
                        _logging.getLogger("scanner").info("diagnostic: media_files_in_db=%d", len(cur_count))
                    except Exception:
                        pass

                if job_id:
                    job = db.query(BackgroundJob).filter(BackgroundJob.id == job_id).first()
                    if job:
                        job.status = "done"
                        job.message = "Scan complete"
                        job.result = stats
                        db.commit()
                        
            except Exception as e:
                # Ensure background job is marked failed
                try:
                    db.rollback()
                except Exception:
                    pass
                if job_id:
                    try:
                        job = db.query(BackgroundJob).filter(BackgroundJob.id == job_id).first()
                        if job:
                            job.status = "failed"
                            job.message = f"Scan error: {e!s}"
                            db.commit()
                    except Exception:
                        pass
                # Re-raise so it surfaces in logs
                raise
                
    except Exception as e:
        # Log any unexpected errors
        import logging
        logging.getLogger(__name__).error(f"Background scan failed: {e}")
        raise

async def _bg_refresh_metadata(library_id: str, force: bool, only_missing: bool, job_id: str | None = None) -> None:
    Session = get_sessionmaker()
    async with Session() as db:
        if job_id:
            job = (await db.execute(select(BackgroundJob).where(BackgroundJob.id == job_id))).scalars().first()
            if job:
                job.status = "running"
                job.message = "Refreshing metadata"
                await db.commit()

        async def _progress(processed: int, total: int):
            if not job_id:
                return
            j = (await db.execute(select(BackgroundJob).where(BackgroundJob.id == job_id))).scalars().first()
            if j:
                j.progress = processed
                j.total = total
                j.message = f"Refreshing {processed}/{total}"
                await db.commit()

        stats = await enrich_library(
            db,
            settings.TMDB_API_KEY,
            library_id,
            limit=5000,
            force=force,
            only_missing=only_missing,
            progress_cb=_progress,
        )
        await db.commit()
        if job_id:
            job = (await db.execute(select(BackgroundJob).where(BackgroundJob.id == job_id))).scalars().first()
            if job:
                job.status = "done"
                job.message = "Metadata refresh complete"
                job.result = {"stats": stats}
                await db.commit()


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
    force: bool = Query(False, description="Force re-scan and metadata refresh"),
    background: bool = Query(False, description="Queue scan and return immediately"),
    db: AsyncSession = Depends(get_db),
    admin = Depends(require_admin),
):
    lib = (await db.execute(
        select(Library).where(Library.id == library_id, Library.owner_user_id == admin.id)
    )).scalars().first()
    if not lib:
        raise HTTPException(status_code=404, detail="Library not found")

    # Extract library attributes to avoid lazy loading issues later
    library_name = lib.name
    library_type = lib.type
    library_path = lib.path
    library_id = lib.id
    
    # Store force flag on the library object so bg task can see it
    lib._force_scan = force

    if background:
        # create job row and queue background task
        job = BackgroundJob(job_type="scan_library", library_id=library_id, status="queued", progress=0, total=None)
        db.add(job)
        await db.commit()
        await db.refresh(job)
        
        # Run background scan synchronously in a thread
        import threading
        
        def run_background_scan():
            """Run the scan synchronously in a background thread"""
            try:
                _bg_scan_library_sync(library_id, job_id=job.id, force=force)
            except Exception as e:
                import logging
                import traceback
                logger = logging.getLogger(__name__)
                logger.error(f"Background scan thread failed: {e}")
                logger.error(f"Full traceback: {traceback.format_exc()}")
                
                # Mark job as failed
                try:
                    from sqlalchemy import create_engine
                    from sqlalchemy.orm import sessionmaker
                    from .database import get_engine
                    async_url = get_engine().url
                    db_url = str(async_url).replace("sqlite+aiosqlite://", "sqlite://")
                    sync_engine = create_engine(db_url, echo=False)
                    Session = sessionmaker(bind=sync_engine)
                    with Session() as session:
                        failed_job = session.query(BackgroundJob).filter(BackgroundJob.id == job.id).first()
                        if failed_job:
                            failed_job.status = "failed"
                            failed_job.message = f"Scan failed: {str(e)}"
                            session.commit()
                except:
                    pass
        
        # Start background thread
        thread = threading.Thread(target=run_background_scan, daemon=True)
        thread.start()
        
        return {"ok": True, "queued": True, "job_id": job.id}

    # Fallback to direct async scan if not background
    if lib.type == "movie":
        stats = await scan_movie_library(db, lib, library_name, library_type, library_id, force=force)
        return {"ok": True, **stats}

    if lib.type == "tv":
        stats = await scan_tv_library(db, lib, library_name, library_type, library_id, force=force)
        # 1) fix mis-titled shows (you already had this)
        retitled = await _retitle_tv_shows(db, library_id)
        # 2) NEW: split files so each SxxEyy gets its own episode row
        repaired = await _repair_tv_episodes(db, library_id)
        return {"ok": True, **stats, "tv_retitled": retitled, "tv_repaired": repaired}

    raise HTTPException(status_code=400, detail="Unsupported library type")

@router.post("/{library_id}/refresh_metadata")
async def refresh_metadata_endpoint(
    library_id: str,
    force: bool = Query(False, description="Re-match everything even if tmdb_id exists"),
    only_missing: bool = Query(True, description="Touch only items missing posters/backdrops"),
    background: bool = Query(False, description="Queue metadata refresh and return immediately"),
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

    if background:
        job = BackgroundJob(job_type="refresh_metadata", library_id=library_id, status="queued", progress=0, total=None)
        db.add(job)
        await db.commit()
        await db.refresh(job)
        
        # Run background refresh in a thread to avoid SQLAlchemy async context issues
        import concurrent.futures
        import threading
        
        def run_background_refresh():
            """Run the refresh in a separate thread with its own event loop"""
            try:
                # Create new event loop for this thread
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Run the async background refresh function
                loop.run_until_complete(_bg_refresh_metadata(library_id, force=force, only_missing=only_missing, job_id=job.id))
                loop.close()
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Background refresh thread failed: {e}")
        
        # Start background thread
        thread = threading.Thread(target=run_background_refresh, daemon=True)
        thread.start()
        
        return {"ok": True, "queued": True, "job_id": job.id}

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

@router.post("/scan_all")
async def scan_all_libraries(
    background: bool = Query(True, description="Queue scan for all libraries and return immediately"),
    refresh_metadata: bool = Query(True, description="After scan, refresh metadata for each library"),
    db: AsyncSession = Depends(get_db),
    admin = Depends(require_admin),
):
    # Get all libraries owned by this admin
    libs = (await db.execute(
        select(Library).where(Library.owner_user_id == admin.id).order_by(Library.created_at.desc())
    )).scalars().all()

    if not libs:
        return {"ok": True, "queued": False, "message": "No libraries to scan."}

    if background:
        # Create a parent job to track overall progress
        parent = BackgroundJob(job_type="scan_all", status="queued", progress=0, total=len(libs))
        db.add(parent)
        await db.commit()
        await db.refresh(parent)

        import threading
        import logging
        owner_id = admin.id  # capture primitive for thread safety

        def run_scan_all():
            try:
                # Use synchronous engine/session similar to _bg_scan_library_sync
                from sqlalchemy import create_engine
                from sqlalchemy.orm import sessionmaker
                from .database import get_engine

                async_url = get_engine().url
                db_url = str(async_url)
                if db_url.startswith("sqlite+aiosqlite://"):
                    db_url = db_url.replace("sqlite+aiosqlite://", "sqlite://")

                sync_engine = create_engine(db_url, echo=False, pool_pre_ping=True, connect_args={"timeout": 30})
                Session = sessionmaker(bind=sync_engine, expire_on_commit=False, autoflush=False)

                with Session() as s:
                    pj = s.query(BackgroundJob).filter(BackgroundJob.id == parent.id).first()
                    if pj:
                        pj.status = "running"
                        pj.message = "Scanning all libraries"
                        s.commit()

                    completed = 0
                    results: list[dict] = []
                    for lib in s.query(Library).filter(Library.owner_user_id == owner_id).order_by(Library.created_at.desc()).all():
                        # Create per-library child job
                        child = BackgroundJob(job_type="scan_library", library_id=lib.id, status="queued", progress=0, total=None)
                        s.add(child)
                        s.commit()
                        s.refresh(child)

                        try:
                            # Run scan synchronously
                            if lib.type == "movie":
                                from .scanner import scan_movie_library_sync
                                stats = scan_movie_library_sync(s, lib, lib.name, lib.type, lib.id)
                            else:
                                from .scanner import scan_tv_library_sync
                                stats = scan_tv_library_sync(s, lib, lib.name, lib.type, lib.id)
                            s.commit()

                            # Optionally refresh metadata per library
                            if refresh_metadata:
                                try:
                                    from .config import settings as _settings
                                    if getattr(_settings, "TMDB_API_KEY", None):
                                        from .metadata import enrich_library as _enrich
                                        _ = _enrich.__name__  # silence linter unused import
                                        # Run async enrich via a temporary loop
                                        import asyncio as _asyncio
                                        from .database import get_sessionmaker as _get_sm
                                        SessionAsync = _get_sm()
                                        async def _do_enrich():
                                            async with SessionAsync() as adb:
                                                return await _enrich(adb, _settings.TMDB_API_KEY, lib.id, limit=5000, force=False, only_missing=True)
                                        _loop = _asyncio.new_event_loop()
                                        _asyncio.set_event_loop(_loop)
                                        try:
                                            _loop.run_until_complete(_do_enrich())
                                        finally:
                                            _loop.close()
                                except Exception:
                                    pass

                            # Mark child job done
                            cj = s.query(BackgroundJob).filter(BackgroundJob.id == child.id).first()
                            if cj:
                                cj.status = "done"
                                cj.message = "Scan complete"
                                cj.result = stats if isinstance(stats, dict) else {"stats": stats}
                                s.commit()

                            results.append({"library_id": lib.id, "result": stats})
                        except Exception as e:
                            # Mark child failed but continue
                            try:
                                s.rollback()
                            except Exception:
                                pass
                            cj = s.query(BackgroundJob).filter(BackgroundJob.id == child.id).first()
                            if cj:
                                cj.status = "failed"
                                cj.message = f"Scan error: {e!s}"
                                s.commit()

                        # Update parent progress
                        completed += 1
                        pj = s.query(BackgroundJob).filter(BackgroundJob.id == parent.id).first()
                        if pj:
                            pj.progress = completed
                            pj.total = len(libs)
                            pj.message = f"Processed {completed}/{len(libs)}"
                            pj.result = {"completed": completed}
                            s.commit()

                    # Mark parent done
                    pj = s.query(BackgroundJob).filter(BackgroundJob.id == parent.id).first()
                    if pj:
                        pj.status = "done"
                        pj.message = "All scans complete"
                        s.commit()
            except Exception as e:
                logging.getLogger(__name__).error(f"Scan-all failed: {e}")
                try:
                    from sqlalchemy import create_engine
                    from sqlalchemy.orm import sessionmaker
                    from .database import get_engine
                    async_url = get_engine().url
                    db_url = str(async_url).replace("sqlite+aiosqlite://", "sqlite://")
                    sync_engine = create_engine(db_url, echo=False)
                    Session = sessionmaker(bind=sync_engine)
                    with Session() as s:
                        pj = s.query(BackgroundJob).filter(BackgroundJob.id == parent.id).first()
                        if pj:
                            pj.status = "failed"
                            pj.message = f"Scan-all error: {e!s}"
                            s.commit()
                except Exception:
                    pass

        threading.Thread(target=run_scan_all, daemon=True).start()
        return {"ok": True, "queued": True, "job_id": parent.id, "total": len(libs)}

    # Non-background: run sequentially (may take a while)
    results = []
    for lib in libs:
        if lib.type == "movie":
            stats = await scan_movie_library(db, lib, lib.name, lib.type, lib.id)
        else:
            stats = await scan_tv_library(db, lib, lib.name, lib.type, lib.id)
        if refresh_metadata and settings.TMDB_API_KEY:
            _ = await enrich_library(db, settings.TMDB_API_KEY, lib.id, limit=5000, force=False, only_missing=True)
        results.append({"library_id": lib.id, "result": stats})
    return {"ok": True, "queued": False, "results": results}

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
