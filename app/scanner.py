# app/scanner.py
from __future__ import annotations
import os
import asyncio
import logging
import re
from typing import Dict, List, Optional, Set, Tuple, Awaitable, Callable

from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .metadata import enrich_library
from .streaming import ffprobe_streams  # reuse async ffprobe helper
from .models import Library, MediaItem, MediaFile, MediaKind
from .utils import (
    is_video_file,
    parse_movie_from_path,
    parse_tv_parts,
    normalize_sort,
    _clean_show_title_enhanced,
)

_JUNK_PATTERNS = re.compile(
    r"""(?ix)
        \b(19|20)\d{2}\b|
        \bS\d{1,2}E\d{1,3}\b|
        \bS\d{1,2}\b|
        \bE\d{1,3}\b|
        \b(2160p|1080p|720p|4k)\b|
        \b(HEVC|H\.?265|H\.?264|x265|x264)\b|
        \b(Blu-?Ray|WEB[- ]?(DL|Rip)|HDR10|HDR|DV|DoVi)\b|
        \b(DDP?\.?5\.1|AAC|FLAC|DTS[- ]?HD(?:MA)?)\b|
        \b(PROPER|REPACK|EXTENDED|INTERNAL|UNCENSORED)\b
    """
)

def _clean_segment(name: str) -> str:
    n = name.replace(".", " ").replace("_", " ").strip()
    n = _JUNK_PATTERNS.sub("", n)
    n = re.sub(r"\s{2,}", " ", n).strip(" -_.")
    if n.lower().startswith("tv "):
        n = n[3:].strip()
    if n.lower() in {"tv", "shows", "tv shows"}:
        return ""
    return n

def _clean_show_title_from_existing(title: str) -> str:
    t = _clean_segment(title)
    t = re.sub(r"^(tv|shows|tv shows)\s+", "", t, flags=re.I).strip()
    t = re.sub(r"\b(\w+)(\s+\1)+\b", r"\1", t, flags=re.I)  # collapse dupes
    return t


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
                # Normalize path for consistent comparison on Windows
                out.append(os.path.normpath(p))
    return out

async def _load_existing_paths(session: AsyncSession, library_id: str) -> Set[str]:
    q = (
        select(MediaFile.path)
        .join(MediaItem, MediaItem.id == MediaFile.media_item_id)
        .where(MediaItem.library_id == library_id)
    )
    res = await session.execute(q)
    # Normalize paths for consistent comparison on Windows
    return {os.path.normpath(row[0]) for row in res.all()}

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

async def scan_movie_library(
    session: AsyncSession,
    library: Library,
    library_name: str,
    library_type: str,
    library_id: str,
    progress_cb: Optional[Callable[[int, int], Awaitable[None]]] = None,
) -> dict:
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

    processed = 0
    for path in all_paths:
        if path in existing_paths:
            skipped += 1
            processed += 1
            if progress_cb and processed % 50 == 0:
                await progress_cb(processed, discovered)
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

        mf = MediaFile(media_item_id=movie.id, path=os.path.normpath(path))
        session.add(mf)
        try:
            await session.flush()
            existing_paths.add(os.path.normpath(path))
            added += 1
            log.info("added movie: %s  -> %s (%s)", path, title, year)
        except IntegrityError:
            await session.rollback()
            skipped += 1

        # Probe codecs/dimensions and persist into MediaFile for faster future playback decisions
        try:
            info = await ffprobe_streams(path)
            ext = os.path.splitext(path)[1].lower().lstrip('.') or None
            if info or ext:
                mf.container = ext
                mf.vcodec = info.get('vcodec') or mf.vcodec
                mf.acodec = info.get('acodec') or mf.acodec
                ch = info.get('channels'); mf.channels = int(ch) if ch else mf.channels
                w = info.get('width'); mf.width = int(w) if w else mf.width
                h = info.get('height'); mf.height = int(h) if h else mf.height
                br = info.get('bitrate'); mf.bitrate = int(br) if br else mf.bitrate
                try:
                    st = os.stat(path); mf.size_bytes = int(getattr(st, 'st_size', 0))
                except Exception:
                    pass
        except Exception:
            pass

        if (added + updated) % 200 == 0:
            await session.commit()
        processed += 1
        if progress_cb and processed % 50 == 0:
            await progress_cb(processed, discovered)

    # final commit after file loop
    await session.commit()

    log.info(
        "scan %s [%s]: discovered=%d known=%d added=%d skipped=%d updated=%d",
        library_name,
        library_type,
        discovered, known_paths, added, skipped, updated
    )

    # Enrich with TMDB and write poster/backdrop through to columns
    await enrich_library(session, settings.TMDB_API_KEY, library_id, limit=5000)
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

async def scan_tv_library(
    session: AsyncSession,
    library: Library,
    library_name: str,
    library_type: str,
    library_id: str,
    progress_cb: Optional[Callable[[int, int], Awaitable[None]]] = None,
) -> dict:
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

    # Debug logging to understand the skipping issue
    log.info("TV DEBUG: discovered=%d, known_paths=%d", discovered, known_paths)
    if existing_paths:
        log.info("TV DEBUG: Sample existing paths: %s", list(existing_paths)[:2])
    if all_paths:
        log.info("TV DEBUG: Sample all paths: %s", all_paths[:2])

    processed = 0
    for path in all_paths:
        # Debug the first few path comparisons
        if processed < 3:
            log.info("TV PATH CHECK: path='%s', in_existing=%s", path, path in existing_paths)
        
        if path in existing_paths:
            skipped += 1
            processed += 1
            if progress_cb and processed % 50 == 0:
                await progress_cb(processed, discovered)
            continue

        try:
            rel = os.path.relpath(path, library.path)
        except ValueError:
            rel = os.path.basename(path)

        tv_parts = parse_tv_parts(os.path.dirname(rel), os.path.basename(path))
        if not tv_parts:
            skipped += 1
            # Log first few parsing failures to understand the issue
            if skipped <= 5:
                log.info("TV PARSE FAIL: path=%s, rel=%s, dirname=%s, basename=%s", 
                        path, rel, os.path.dirname(rel), os.path.basename(path))
            continue

        show_title, season_no, episode_no, ep_title_guess = tv_parts

        # Apply enhanced cleaning to show title
        show_title_cleaned = _clean_show_title_enhanced(show_title)
        
        # Fallback to original if cleaning resulted in empty string
        if not show_title_cleaned or len(show_title_cleaned.strip()) < 2:
            show_title_cleaned = show_title.strip()

        # show
        show = await _get_or_create_item(
            session, library_id=library.id, kind=MediaKind.show,
            title=show_title_cleaned, year=None, parent_id=None
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
        
        # Set season and episode numbers in extra_json for metadata enrichment
        if not episode.extra_json:
            episode.extra_json = {}
        episode.extra_json["season"] = int(season_no)
        episode.extra_json["episode"] = int(episode_no)

        # file
        mf = MediaFile(media_item_id=episode.id, path=os.path.normpath(path))
        session.add(mf)
        try:
            await session.flush()
            existing_paths.add(os.path.normpath(path))
            added += 1
            log.info("added episode: %s -> %s / %s / %s", path, show_title, season_title, ep_title)
        except IntegrityError:
            await session.rollback()
            skipped += 1

        # Probe codecs/dimensions and persist into MediaFile for faster future playback decisions
        try:
            info = await ffprobe_streams(path)
            ext = os.path.splitext(path)[1].lower().lstrip('.') or None
            if info or ext:
                mf.container = ext
                mf.vcodec = info.get('vcodec') or mf.vcodec
                mf.acodec = info.get('acodec') or mf.acodec
                ch = info.get('channels'); mf.channels = int(ch) if ch else mf.channels
                w = info.get('width'); mf.width = int(w) if w else mf.width
                h = info.get('height'); mf.height = int(h) if h else mf.height
                br = info.get('bitrate'); mf.bitrate = int(br) if br else mf.bitrate
                try:
                    st = os.stat(path); mf.size_bytes = int(getattr(st, 'st_size', 0))
                except Exception:
                    pass
        except Exception:
            pass

        if (added + updated) % 200 == 0:
            await session.commit()
        processed += 1
        if progress_cb and processed % 50 == 0:
            await progress_cb(processed, discovered)

    await session.commit()

    log.info(
        "scan %s [%s]: discovered=%d known=%d added=%d skipped=%d updated=%d",
        library_name,
        library_type,
        discovered, known_paths, added, skipped, updated
    )

    # Enrich show/episode metadata and stills
    await enrich_library(session, settings.TMDB_API_KEY, library_id, limit=5000)
    await session.commit()

    return {
        "added": added,
        "skipped": skipped,
        "updated": updated,
        "discovered": discovered,
        "known_paths": known_paths,
    }

# ---------------------------------------------------------------------------
# Sync versions for background threads
# ---------------------------------------------------------------------------

def _load_existing_paths_sync(session, library_id: str) -> Set[str]:
    """Synchronous version of _load_existing_paths"""
    from sqlalchemy import select
    from .models import MediaFile, MediaItem
    
    q = (
        select(MediaFile.path)
        .join(MediaItem, MediaItem.id == MediaFile.media_item_id)
        .where(MediaItem.library_id == library_id)
    )
    res = session.execute(q)
    # Normalize paths for consistent comparison on Windows
    return {os.path.normpath(row[0]) for row in res.all()}

def _get_or_create_item_sync(
    session,
    library_id: str,
    kind: MediaKind,
    title: str,
    year: Optional[int],
    parent_id: Optional[str] = None,
) -> Optional[MediaItem]:
    """Synchronous version of _get_or_create_item"""
    from sqlalchemy import select, func
    from .models import MediaItem
    from .utils import normalize_sort
    
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

    res = session.execute(stmt)
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
    session.flush()  # populate item.id
    return item

def scan_movie_library_sync(
    session,
    library: Library,
    library_name: str,
    library_type: str,
    library_id: str,
    progress_cb: Optional[Callable[[int, int], Awaitable[None]]] = None,
) -> dict:
    """Synchronous version of scan_movie_library for background threads."""
    added = skipped = updated = 0

    if not os.path.isdir(library.path):
        log.warning("scan aborted: library path not found: %s", library.path)
        return {"added": 0, "skipped": 0, "updated": 0, "discovered": 0, "known_paths": 0, "note": "path_missing"}

    existing_paths = _load_existing_paths_sync(session, library.id)
    all_paths = _walk_video_files(library.path)

    discovered = len(all_paths)
    known_paths = len(existing_paths)

    log.info("scan_movie_library_sync: path=%s, discovered=%d, known_paths=%d", library.path, discovered, known_paths)
    if discovered == 0:
        log.warning("No video files discovered in %s. Check if path is correct and contains video files.", library.path)
        # Try to list a few files to help debug
        try:
            sample_files = []
            for root, dirs, files in os.walk(library.path):
                if len(sample_files) >= 5:
                    break
                for f in files[:5]:
                    sample_files.append(os.path.join(root, f))
            if sample_files:
                log.info("Sample files in directory: %s", sample_files[:5])
        except Exception as e:
            log.warning("Could not list sample files: %s", e)

    processed = 0
    skipped_no_parse = 0
    for path in all_paths:
        if path in existing_paths:
            skipped += 1
            processed += 1
            continue

        parsed: Optional[Tuple[str, Optional[int]]] = parse_movie_from_path(path)
        if not parsed:
            skipped_no_parse += 1
            if skipped_no_parse <= 5:  # Log first 5 unparseable files
                log.debug("Movie: Could not parse %s", path)
            skipped += 1
            continue

        title, year = parsed
        if not title or not title.strip():
            skipped += 1
            continue

        movie = _get_or_create_item_sync(
            session, library.id, MediaKind.movie, title.strip(), year, parent_id=None
        )
        if not movie:
            skipped += 1
            continue

        mf = MediaFile(media_item_id=movie.id, path=os.path.normpath(path))
        session.add(mf)
        try:
            session.flush()
            existing_paths.add(os.path.normpath(path))
            added += 1
            log.info("added movie: %s  -> %s (%s)", path, title, year)
        except IntegrityError:
            session.rollback()
            skipped += 1

        if (added + updated) % 200 == 0:
            session.commit()
        processed += 1

    session.commit()

    log.info(
        "scan %s [%s]: discovered=%d known=%d added=%d skipped=%d updated=%d",
        library_name,
        library_type,
        discovered, known_paths, added, skipped, updated
    )
    if skipped_no_parse > 0:
        log.info("Movie scan: %d files could not be parsed (skipped)", skipped_no_parse)

    return {
        "added": added,
        "skipped": skipped,
        "updated": updated,
        "discovered": discovered,
        "known_paths": known_paths,
    }

def scan_tv_library_sync(
    session,
    library: Library,
    library_name: str,
    library_type: str,
    library_id: str,
    progress_cb: Optional[Callable[[int, int], Awaitable[None]]] = None,
) -> dict:
    """Synchronous version of scan_tv_library for background threads."""
    added = skipped = updated = 0

    if not os.path.isdir(library.path):
        log.warning("scan aborted: library path not found: %s", library.path)
        return {"added": 0, "skipped": 0, "updated": 0, "discovered": 0, "known_paths": 0, "note": "path_missing"}

    existing_paths = _load_existing_paths_sync(session, library.id)
    all_paths = _walk_video_files(library.path)

    discovered = len(all_paths)
    known_paths = len(existing_paths)

    log.info("scan_tv_library_sync: path=%s, discovered=%d, known_paths=%d", library.path, discovered, known_paths)
    if discovered == 0:
        log.warning("No video files discovered in %s. Check if path is correct and contains video files.", library.path)
        # Try to list a few files to help debug
        try:
            sample_files = []
            for root, dirs, files in os.walk(library.path):
                if len(sample_files) >= 5:
                    break
                for f in files[:5]:
                    sample_files.append(os.path.join(root, f))
            if sample_files:
                log.info("Sample files in directory: %s", sample_files[:5])
        except Exception as e:
            log.warning("Could not list sample files: %s", e)

    processed = 0
    skipped_no_parse = 0
    for path in all_paths:
        if path in existing_paths:
            skipped += 1
            processed += 1
            continue

        try:
            rel = os.path.relpath(path, library.path)
        except ValueError:
            rel = os.path.basename(path)

        tv_parts = parse_tv_parts(os.path.dirname(rel), os.path.basename(path))
        if not tv_parts:
            skipped_no_parse += 1
            if skipped_no_parse <= 5:  # Log first 5 unparseable files
                log.debug("TV: Could not parse %s", path)
            skipped += 1
            continue

        show_title, season_no, episode_no, ep_title_guess = tv_parts

        # Apply enhanced cleaning to show title  
        show_title_cleaned = _clean_show_title_enhanced(show_title)
        
        # Fallback to original if cleaning resulted in empty string
        if not show_title_cleaned or len(show_title_cleaned.strip()) < 2:
            show_title_cleaned = show_title.strip()

        # show
        show = _get_or_create_item_sync(session, library_id=library.id, kind=MediaKind.show,
            title=show_title_cleaned, year=None, parent_id=None)
        if not show:
            skipped += 1
            continue

        # season
        season_title = f"Season {int(season_no):02d}"
        season = _get_or_create_item_sync(session, library_id=library.id, kind=MediaKind.season,
            title=season_title, year=None, parent_id=show.id)
        if not season:
            skipped += 1
            continue

        # episode
        ep_title_core = ep_title_guess.strip() if ep_title_guess else ""
        ep_title = f"S{int(season_no):02d}E{int(episode_no):02d}" + (f" {ep_title_core}" if ep_title_core else "")
        episode = _get_or_create_item_sync(session, library_id=library.id, kind=MediaKind.episode,
            title=ep_title, year=None, parent_id=season.id)
        if not episode:
            skipped += 1
            continue
        
        # Set season and episode numbers in extra_json for metadata enrichment
        if not episode.extra_json:
            episode.extra_json = {}
        episode.extra_json["season"] = int(season_no)
        episode.extra_json["episode"] = int(episode_no)

        # file
        mf = MediaFile(media_item_id=episode.id, path=os.path.normpath(path))
        session.add(mf)
        try:
            session.flush()
            existing_paths.add(os.path.normpath(path))
            added += 1
            log.info("added episode: %s -> %s / %s / %s", path, show_title, season_title, ep_title)
        except IntegrityError:
            session.rollback()
            skipped += 1

        if (added + updated) % 200 == 0:
            session.commit()
        processed += 1

    session.commit()

    log.info(
        "scan %s [%s]: discovered=%d known=%d added=%d skipped=%d updated=%d",
        library_name,
        library_type,
        discovered, known_paths, added, skipped, updated
    )
    if skipped_no_parse > 0:
        log.info("TV scan: %d files could not be parsed (skipped)", skipped_no_parse)

    return {
        "added": added,
        "skipped": skipped,
        "updated": updated,
        "discovered": discovered,
        "known_paths": known_paths,
    }