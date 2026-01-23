from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from .database import get_db
from .auth import get_current_user
from .models import MediaItem, MediaKind
from .utils import _clean_show_title_enhanced

def _get_image_url(path: str | None, size: str = "w342") -> str | None:
    if not path:
        return None
    if path.startswith(("http://", "https://")):
        return path
    if path.startswith("/static/"):
        # This will be prepended by the Roku client if we don't do it here,
        # but let's be explicit if we can. Actually, Roku client expects 
        # relative paths to be prepended with server_url.
        return path
    if path.startswith("/"):
        return f"https://image.tmdb.org/t/p/{size}{path}"
    return path

router = APIRouter(prefix="/api", tags=["media-api"])

def _detail_out(it: MediaItem):
    """Format MediaItem for Roku details screen."""
    print(f"[DEBUG] _detail_out for {it.id} ({it.kind}) title='{it.title}'")
    ej = it.extra_json or {}
    # Extract cast and crew if available
    cast = ej.get("cast", [])
    crew = ej.get("crew", [])
    directors = [c["name"] for c in crew if c.get("job") == "Director"]
    if not directors and crew:
        # Fallback if job is capitalized differently or missing
        directors = [c["name"] for c in crew if str(c.get("job")).lower() in ("director", "creator")]

    title = it.title or ""
    # If we have an enriched name, use it first
    if ej.get("name"):
        title = ej["name"]
    
    # Always apply cleaning to episode titles to be sure
    if it.kind == MediaKind.episode:
        title = _clean_show_title_enhanced(title)

    return {
        "id": it.id,
        "title": title or "Unknown",
        "year": it.year,
        "poster_url": _get_image_url(it.poster_url or ej.get("poster") or ej.get("still") or ej.get("backdrop")),
        "backdrop_url": _get_image_url(it.backdrop_url or ej.get("backdrop")),
        "kind": it.kind,
        "overview": it.overview or ej.get("overview") or "",
        "description": it.overview or ej.get("overview") or "",
        "runtime_ms": it.runtime_ms,
        "cast": cast,
        "directors": directors,
        "extra_json": {"poster": it.poster_url or ej.get("poster")},
        "files": [{"id": f.id} for f in (it.files or [])],
        "still": _get_image_url(it.poster_url or ej.get("still") or ej.get("poster")),
        "episode": ej.get("episode") # Useful for SeasonDetails list
    }

@router.get("/movie/{item_id}")
async def get_movie_details(item_id: str, db: AsyncSession = Depends(get_db)):
    q = select(MediaItem).where(MediaItem.id == item_id).options(selectinload(MediaItem.files))
    item = (await db.execute(q)).scalars().first()
    if not item or item.kind != MediaKind.movie:
        raise HTTPException(404, "Movie not found")
    return _detail_out(item)

@router.get("/show/{item_id}")
async def get_show_details(item_id: str, db: AsyncSession = Depends(get_db)):
    # Eager load seasons (children where kind=season)
    q = (
        select(MediaItem)
        .where(MediaItem.id == item_id, MediaItem.kind == MediaKind.show)
        .options(
            selectinload(MediaItem.files),
            selectinload(MediaItem.children).selectinload(MediaItem.files)
        )
    )
    item = (await db.execute(q)).scalars().first()
    
    if not item:
        raise HTTPException(404, "Show not found")
        
    data = _detail_out(item)
    # Add seasons
    seasons = [c for c in item.children if c.kind == MediaKind.season]
    
    def _get_season_no(s):
        # Try year first, then parse "Season X"
        if s.year: return s.year
        try:
            return int((s.title or "").split()[-1])
        except:
            return 0
    
    seasons.sort(key=_get_season_no)
    
    data["seasons"] = []
    for s in seasons:
        s_data = _detail_out(s)
        # Ensure season title is useful
        if not s_data["title"]:
            s_data["title"] = f"Season {s.year}" if s.year else "Unknown Season"
        data["seasons"].append(s_data)
        
    return data

@router.get("/season/{item_id}")
async def get_season_details(item_id: str, db: AsyncSession = Depends(get_db)):
    q = (
        select(MediaItem)
        .where(MediaItem.id == item_id, MediaItem.kind == MediaKind.season)
        .options(
            selectinload(MediaItem.files)
        )
    )
    item = (await db.execute(q)).scalars().first()
    
    if not item:
        raise HTTPException(404, "Season not found")
        
    data = _detail_out(item)
    
    # Fetch episodes explicitly to ensure full loading of JSON fields
    q_eps = (
        select(MediaItem)
        .where(MediaItem.parent_id == item.id, MediaItem.kind == MediaKind.episode)
        .options(selectinload(MediaItem.files))
    )
    episodes = (await db.execute(q_eps)).scalars().all()
    episodes = list(episodes) # convert to list
    
    # Sort by episode number (often stored in extra_json or year)
    def _get_ep_no(e):
        ej = e.extra_json or {}
        if ej.get("episode"): return int(ej["episode"])
        if e.year: return e.year
        return 0
    episodes.sort(key=_get_ep_no)
    
    data["episodes"] = []
    for e in episodes:
        d = _detail_out(e)
        # DEBUG: Print checking specifically for still
        ej = e.extra_json or {}
        # print(f"[DEBUG] Episode {e.title} ID={e.id} Still={ej.get('still')} PosterURL={e.poster_url}")
        data["episodes"].append(d)
    
    return data

@router.get("/episode/{item_id}")
async def get_episode_details(item_id: str, db: AsyncSession = Depends(get_db)):
    q = select(MediaItem).where(MediaItem.id == item_id).options(selectinload(MediaItem.files))
    item = (await db.execute(q)).scalars().first()
    if not item or item.kind != MediaKind.episode:
        raise HTTPException(404, "Episode not found")
    return _detail_out(item)
