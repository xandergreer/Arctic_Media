# app/scanner.py
from __future__ import annotations

import os
import asyncio
import logging
from typing import Dict, List, Optional, Set

from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .metadata import enrich_library
from .models import Library, MediaItem, MediaFile, MediaKind
from .utils import (
    is_video_file,
    guess_title_year,
    parse_tv_parts,
    normalize_sort,
    ffprobe_info,
)

log = logging.getLogger("scanner")

# ───────────────────────── helpers ─────────────────────────

def _walk_video_files(root: str) -> List[str]:
    """Walk a tree and return absolute paths to video files."""
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


async def _get_or_create_media(
    session: AsyncSession,
    library_id: str,
    kind: MediaKind,
    title: str,
    year: Optional[int] = None,
    parent_id: Optional[str] = None,
) -> MediaItem:
    """Find by (library, kind, parent, sort_title, year) – else create."""
    sort_title = normalize_sort(title)

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

    existing = (await session.execute(stmt)).scalars().first()
    if existing:
        return existing

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


# ───────────────────────── public scanners (old direct API) ─────────────────────────
# These are still used by some callers. The library API below calls scan_library_job.

async def scan_movie_library(session: AsyncSession, library: Library) -> dict:
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

        title, year = guess_title_year(path)
        movie = await _get_or_create_media(session, library.id, MediaKind.movie, title, year)

        info = ffprobe_info(path)
        mf = MediaFile(
            media_item_id=movie.id,
            path=path,
            container=info.get("container"),
            vcodec=info.get("vcodec"),
            acodec=info.get("acodec"),
            width=info.get("width"),
            height=info.get("height"),
            bitrate=info.get("bitrate"),
            size_bytes=os.path.getsize(path) if os.path.exists(path) else None,
        )
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

    log.info(
        "scan %s [%s]: discovered=%d known=%d added=%d skipped=%d updated=%d",
        getattr(library, "name", library.id), library.type,
        discovered, known_paths, added, skipped, updated
    )

    # Enrich posters/metadata
    await enrich_library(session, settings.TMDB_API_KEY, library.id, limit=5000)
    await session.commit()

    return {
        "added": added,
        "skipped": skipped,
        "updated": updated,
        "discovered": discovered,
        "known_paths": known_paths,
    }


async def scan_tv_library(session: AsyncSession, library: Library) -> dict:
    """Scan a TV library and create show → season → episode hierarchy."""
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

        # rel path used as hint for show title
        try:
            rel_root = os.path.relpath(os.path.dirname(path), library.path)
        except ValueError:
            rel_root = ""

        tv_parts = parse_tv_parts(rel_root, os.path.basename(path))
        if not tv_parts:
            skipped += 1
            continue

        show_title, season_no, episode_no, ep_title_guess = tv_parts

        # show
        show = await _get_or_create_media(session, library.id, MediaKind.show, show_title, None, None)

        # season
        season_title = f"Season {season_no:02d}"
        season_item = await _get_or_create_media(session, library.id, MediaKind.season, season_title, None, show.id)

        # episode
        ep_title = f"S{season_no:02d}E{episode_no:02d} {ep_title_guess}"
        episode_item = await _get_or_create_media(session, library.id, MediaKind.episode, ep_title, None, season_item.id)

        if not episode_item.extra_json:
            episode_item.extra_json = {"season": season_no, "episode": episode_no}

        info = ffprobe_info(path)
        mf = MediaFile(
            media_item_id=episode_item.id,
            path=path,
            container=info.get("container"),
            vcodec=info.get("vcodec"),
            acodec=info.get("acodec"),
            width=info.get("width"),
            height=info.get("height"),
            bitrate=info.get("bitrate"),
            size_bytes=os.path.getsize(path) if os.path.exists(path) else None,
        )
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
        getattr(library, "name", library.id), library.type,
        discovered, known_paths, added, skipped, updated
    )

    # Enrich after TV scan
    await enrich_library(session, settings.TMDB_API_KEY, library.id, limit=5000)
    await session.commit()

    return {
        "added": added,
        "skipped": skipped,
        "updated": updated,
        "discovered": discovered,
        "known_paths": known_paths,
    }


# ───────────────────────── unified worker used by /libraries/{id}/scan ─────────────────────────

async def scan_library_job(library_id: str, return_stats: bool = False):
    """
    Scan a library and index media files. When return_stats=True, returns:
      {added, updated, skipped, seen, known}
    """
    from .database import get_sessionmaker
    Session = get_sessionmaker()

    counters = {"added": 0, "updated": 0, "skipped": 0, "seen": 0, "known": 0}

    async with Session() as db:
        lib = (await db.execute(select(Library).where(Library.id == library_id))).scalars().first()
        if not lib:
            return counters if return_stats else None

        # known before scan
        counters["known"] = (await db.execute(
            select(func.count()).select_from(MediaFile)
            .join(MediaItem, MediaItem.id == MediaFile.media_item_id)
            .where(MediaItem.library_id == library_id)
        )).scalar_one()

        if not os.path.isdir(lib.path):
            print(f"[SCAN] Library path missing or not a dir: {lib.path}")
            return counters if return_stats else None

        print(f"[SCAN] Starting scan: {lib.name} [{lib.type}] -> {lib.path}")

        for root, _dirs, files in os.walk(lib.path):
            for fname in files:
                fullpath = os.path.join(root, fname)
                if not is_video_file(fullpath):
                    continue

                counters["seen"] += 1
                try:
                    if lib.type == "movie":
                        added = await _index_movie(db, lib.id, fullpath)
                    else:
                        rel_root = os.path.relpath(root, lib.path)
                        added = await _index_tv(db, lib.id, lib.path, rel_root, fullpath)

                    if added:
                        counters["added"] += 1
                    else:
                        counters["skipped"] += 1
                except Exception as e:
                    print(f"[SCAN] error indexing {fullpath}: {e}")
                    counters["skipped"] += 1

        # Optional metadata enrichment
        try:
            if getattr(settings, "TMDB_API_KEY", ""):
                await enrich_library(db, settings.TMDB_API_KEY, library_id, limit=1000)
        except Exception as e:
            print(f"[SCAN] metadata enrichment error: {e}")

        await db.commit()
        print(f"[SCAN] Done: seen={counters['seen']} added={counters['added']} skipped={counters['skipped']} known(before)={counters['known']}")

        if return_stats:
            return counters


# ───────────────────────── low-level index helpers ─────────────────────────

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
    parsed = parse_tv_parts(rel_root, os.path.basename(path))
    if not parsed:
        return False

    show_title, season, episode, ep_title_guess = parsed
    show = await _get_or_create_media(db, library_id, MediaKind.show, show_title, None, None)
    season_item = await _get_or_create_media(db, library_id, MediaKind.season, f"Season {season:02d}", None, show.id)
    ep_title = f"S{season:02d}E{episode:02d} {ep_title_guess}"
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
