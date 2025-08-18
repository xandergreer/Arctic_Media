from __future__ import annotations
from typing import Optional, Dict, Any, List
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from .models import MediaItem, MediaKind

TMDB_API = "https://api.themoviedb.org/3"
IMG_BASE = "https://image.tmdb.org/t/p/"

class TMDB:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=15)

    async def _get(self, path: str, params: Dict[str, Any] | None = None):
        p = {"api_key": self.api_key, "language": "en-US"}
        if params: p.update(params)
        r = await self.client.get(f"{TMDB_API}{path}", params=p)
        r.raise_for_status()
        return r.json()

    async def search_movie(self, title: str, year: Optional[int]):
        data = await self._get("/search/movie", {"query": title, "year": year, "include_adult": "false"})
        return (data.get("results") or [None])[0]

    async def search_tv(self, title: str, year: Optional[int]):
        data = await self._get("/search/tv", {"query": title, "first_air_date_year": year})
        return (data.get("results") or [None])[0]

    async def movie_details(self, tmdb_id: int):
        return await self._get(f"/movie/{tmdb_id}")

    async def tv_details(self, tmdb_id: int):
        return await self._get(f"/tv/{tmdb_id}")

    @staticmethod
    def poster_url(path: Optional[str], size: str = "w342") -> Optional[str]:
        return f"{IMG_BASE}{size}{path}" if path else None

    @staticmethod
    def backdrop_url(path: Optional[str], size: str = "w780") -> Optional[str]:
        return f"{IMG_BASE}{size}{path}" if path else None

    async def close(self):
        await self.client.aclose()

async def enrich_library(db: AsyncSession, api_key: str, library_id: str, limit: int = 500) -> int:
    """Fill in tmdb_id/poster/backdrop/overview/runtime for movies & shows."""
    if not api_key:
        return 0

    tmdb = TMDB(api_key)
    updated = 0
    try:
        res = await db.execute(
            select(MediaItem)
            .where(MediaItem.library_id == library_id)
            .where(MediaItem.kind.in_([MediaKind.movie, MediaKind.show]))
            .order_by(MediaItem.created_at.desc())
            .limit(limit)
        )
        for mi in res.scalars().all():
            if mi.tmdb_id and mi.poster_url and mi.overview:
                continue

            hit = await (tmdb.search_movie(mi.title, mi.year) if mi.kind == MediaKind.movie
                         else tmdb.search_tv(mi.title, mi.year))

            if not hit:
                continue

            vals: Dict[str, Any] = {
                "tmdb_id": hit.get("id"),
                "poster_url": TMDB.poster_url(hit.get("poster_path")),
                "backdrop_url": TMDB.backdrop_url(hit.get("backdrop_path")),
            }

            if mi.kind == MediaKind.movie:
                det = await tmdb.movie_details(hit["id"])
                vals["overview"] = det.get("overview")
                vals["runtime_ms"] = (det.get("runtime") or 0) * 60_000
                if not mi.year and det.get("release_date"):
                    vals["year"] = int(det["release_date"][:4])
            else:
                det = await tmdb.tv_details(hit["id"])
                vals["overview"] = det.get("overview")
                runtimes: List[int] = det.get("episode_run_time") or []
                vals["runtime_ms"] = (min(runtimes) if runtimes else 0) * 60_000
                if not mi.year and det.get("first_air_date"):
                    vals["year"] = int(det["first_air_date"][:4])

            await db.execute(update(MediaItem).where(MediaItem.id == mi.id).values(**vals))
            updated += 1

        await db.commit()
        return updated
    finally:
        await tmdb.close()
