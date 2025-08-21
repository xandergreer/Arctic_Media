# app/scanner.py
from __future__ import annotations
import os
import asyncio
import logging
from typing import Dict, List, Optional, Set, Tuple

from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .metadata import enrich_library
from .models import Library, MediaItem, MediaFile, MediaKind
from .utils import (
    is_video_file,
    parse_movie_from_path,
    parse_tv_parts,
    normalize_sort,
)

log = logging.getLogger("scanner")

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _walk_video_files(root: str) -> List[str]:
    """
    Walk a root folder and return all file paths that look like video files.
    """
    out: List[str] = []
    for dirpath, _dirs, files in os.walk(root):
        for f in files:
            p = os.path.join(dirpath, f)
            if is_video_file(p):
                out.append(p)
    return out

async def _load_existing_paths(session: AsyncSession, library_id: str) -> Set[str]:
    q = (
        select(MediaFile.path)
        .join(MediaItem, MediaItem.id == MediaFile.media_item_id)
        .where(MediaItem.library_id == library_id)
    )
    res = await session.execute(q)
    return {row[0] for row in res.all()}

async def _get_or_create_item(
    session: AsyncSession,
    library_id: str,
    kind: MediaKind,
    title: str,
    year: Optional[int],
    parent_id: Optional[str] = None,
) -> Optional[MediaItem]:
    """
    Create/find a MediaItem for the given attributes.
    Returns None if title is invalid (blank).
    """
    if not title or not title.strip():
        return None

    sort_title = normalize_sort(title)
    if not sort_title:
        return None

    stmt = (
        select(MediaItem)
        .where(MediaItem.library_id == library_id)
        .where(MediaItem.kind == kind)
        .where(MediaItem.parent_id == parent_id)
        .where(func.lower(MediaItem.sort_title) == sort_title)
    )
    if year is None:
        stmt = stmt.where(MediaItem.year.is_(None))
    else:
        stmt = stmt.where(MediaItem.year == year)

    res = await session.execute(stmt)
    item = res.scalar_one_or_none()
    if item:
        return item

    item = MediaItem(
        library_id=library_id,
        kind=kind,
        parent_id=parent_id,
        title=title,
        sort_title=sort_title,
        year=year,
    )
    session.add(item)
    await session.flush()  # populate item.id
    return item

# ---------------------------------------------------------------------------
# movie scanner
# ---------------------------------------------------------------------------

async def scan_movie_library(session: AsyncSession, library: Library) -> dict:
    """
    Scan a movie library directory for video files and create MediaItems + MediaFiles.
    Skips files that cannot be parsed into a sensible title.
    """
    added = skipped = updated = 0

    # sanity check path
    if not os.path.isdir(library.path):
        log.warning("scan aborted: library path not found: %s", library.path)
        return {"added": 0, "skipped": 0, "updated": 0, "discovered": 0, "known_paths": 0, "note": "path_missing"}

    existing_paths = await _load_existing_paths(session, library.id)
    all_paths = await asyncio.to_thread(_walk_video_files, library.path)

    discovered = len(all_paths)
    known_paths = len(existing_paths)

    for path in all_paths:
        if path in existing_paths:
            skipped += 1
            continue

        parsed: Optional[Tuple[str, Optional[int]]] = parse_movie_from_path(path)
        # If parsing failed (samples, trailers, or garbage), skip safely
        if not parsed:
            skipped += 1
            continue

        title, year = parsed
        if not title or not title.strip():
            skipped += 1
            continue

        movie = await _get_or_create_item(
            session, library.id, MediaKind.movie, title.strip(), year, parent_id=None
        )
        if not movie:
            skipped += 1
            continue

        mf = MediaFile(media_item_id=movie.id, path=path)
        session.add(mf)
        try:
            await session.flush()
            existing_paths.add(path)
            added += 1
            log.info("added movie: %s  -> %s (%s)", path, title, year)
        except IntegrityError:
            await session.rollback()
            skipped += 1

        if (added + updated) % 200 == 0:
            await session.commit()

    # final commit after file loop
    await session.commit()

    log.info(
        "scan %s [%s]: discovered=%d known=%d added=%d skipped=%d updated=%d",
        getattr(library, "name", library.id),
        library.type,
        discovered, known_paths, added, skipped, updated
    )

    # Enrich with TMDB and write poster/backdrop through to columns
    await enrich_library(session, settings.TMDB_API_KEY, library.id, limit=5000)
    await session.commit()

    return {
        "added": added,
        "skipped": skipped,
        "updated": updated,
        "discovered": discovered,
        "known_paths": known_paths,
    }

# ---------------------------------------------------------------------------
# TV scanner
# ---------------------------------------------------------------------------

async def scan_tv_library(session: AsyncSession, library: Library) -> dict:
    """
    Scan a TV library. Creates show -> season -> episode hierarchy.
    """
    added = skipped = updated = 0

    if not os.path.isdir(library.path):
        log.warning("scan aborted: library path not found: %s", library.path)
        return {"added": 0, "skipped": 0, "updated": 0, "discovered": 0, "known_paths": 0, "note": "path_missing"}

    existing_paths = await _load_existing_paths(session, library.id)
    all_paths = await asyncio.to_thread(_walk_video_files, library.path)

    discovered = len(all_paths)
    known_paths = len(existing_paths)

    for path in all_paths:
        if path in existing_paths:
            skipped += 1
            continue

        try:
            rel = os.path.relpath(path, library.path)
        except ValueError:
            rel = os.path.basename(path)

        tv_parts = parse_tv_parts(os.path.dirname(rel), os.path.basename(path))
        if not tv_parts:
            skipped += 1
            continue

        show_title, season_no, episode_no, ep_title_guess = tv_parts

        # show
        show = await _get_or_create_item(
            session, library_id=library.id, kind=MediaKind.show,
            title=show_title.strip(), year=None, parent_id=None
        )
        if not show:
            skipped += 1
            continue

        # season
        season_title = f"Season {int(season_no):02d}"
        season = await _get_or_create_item(
            session, library_id=library.id, kind=MediaKind.season,
            title=season_title, year=None, parent_id=show.id
        )
        if not season:
            skipped += 1
            continue

        # episode
        ep_title_core = ep_title_guess.strip() if ep_title_guess else ""
        ep_title = f"S{int(season_no):02d}E{int(episode_no):02d}" + (f" {ep_title_core}" if ep_title_core else "")
        episode = await _get_or_create_item(
            session, library_id=library.id, kind=MediaKind.episode,
            title=ep_title, year=None, parent_id=season.id
        )
        if not episode:
            skipped += 1
            continue

        # file
        mf = MediaFile(media_item_id=episode.id, path=path)
        session.add(mf)
        try:
            await session.flush()
            existing_paths.add(path)
            added += 1
            log.info("added episode: %s -> %s / %s / %s", path, show_title, season_title, ep_title)
        except IntegrityError:
            await session.rollback()
            skipped += 1

        if (added + updated) % 200 == 0:
            await session.commit()

    await session.commit()

    log.info(
        "scan %s [%s]: discovered=%d known=%d added=%d skipped=%d updated=%d",
        getattr(library, "name", library.id),
        library.type,
        discovered, known_paths, added, skipped, updated
    )

    # Enrich show/episode metadata and stills
    await enrich_library(session, settings.TMDB_API_KEY, library.id, limit=5000)
    await session.commit()

    return {
        "added": added,
        "skipped": skipped,
        "updated": updated,
        "discovered": discovered,
        "known_paths": known_paths,
    }
