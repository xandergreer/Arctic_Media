# app/metadata.py
from __future__ import annotations
import re
import time
import logging
from typing import Any, Dict, List, Optional

import requests
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Library, MediaItem, MediaKind
from .utils import normalize_sort

log = logging.getLogger("scanner")

TMDB_API = "https://api.themoviedb.org/3"
IMG_BASE = "https://image.tmdb.org/t/p"   # /w342, /w500, /original, etc.

# -------- helpers: images & http --------

def _img(url_part: Optional[str], size: str = "w500") -> Optional[str]:
    if not url_part:
        return None
    return f"{IMG_BASE}/{size}{url_part}"

def _headers(api_key: str) -> Dict[str, str]:
    # TMDB v4 tokens look like JWTs; v3 is a plain hex string.
    return {"Authorization": f"Bearer {api_key}"} if api_key.count(".") >= 2 else {}

def _params(api_key: str) -> Dict[str, str]:
    # support both v4 bearer and v3 ?api_key=
    return {} if api_key.count(".") >= 2 else {"api_key": api_key}

def _get(api_key: str, path: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    time.sleep(0.11)  # small cushion
    try:
        q = {**_params(api_key), **params}
        r = requests.get(f"{TMDB_API}/{path}", headers=_headers(api_key), params=q, timeout=15)
        if r.status_code == 429:
            time.sleep(0.6)
            r = requests.get(f"{TMDB_API}/{path}", headers=_headers(api_key), params=q, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        log.warning("TMDB GET %s failed: %s", path, e)
        return None

# -------- helpers: title cleaning & matching --------

# tokens we strip out of scene/release names
_STOPWORDS = {
    "1080p","2160p","720p","480p","4k","hdr","dv","dolby","vision",
    "webrip","web-dl","web","bluray","brrip","dvdrip","hdtv","cam","ts","hdrip","remux","proper","repack",
    "x264","x265","h264","h.264","h265","h.265","hevc","avc","xvid","divx","10bit","8bit",
    "ac3","eac3","dd5","ddp","dd","dts","dts-hd","ma","truehd","atmos","aac","mp3","flac",
    "subs","multi","dual","dl","enc","rip","sample","yify","rarbg","etrg","evo","joy","saon","flux","oft","ivy","lost","lama","bhdstudio","refraction","pir8","okaystopcrying","hallowed","chivaman","will1869","ethel","aoc","x0r","nan0","lootera","ptv","pmtp","ds4k","web","webdl","real","multi",
    "1","2ch","5.1","7.1"
}

_token_re = re.compile(r"[.\-_\[\](){},]+|\s+")

def _clean_title(title: str) -> str:
    if not title:
        return title
    # replace separators with space
    s = _token_re.sub(" ", title).lower()
    parts: List[str] = []
    for p in s.split():
        # keep 4-digit years
        if re.fullmatch(r"\d{4}", p):
            parts.append(p)
            continue
        # drop stopwords and codec/source noise
        if p in _STOPWORDS:
            continue
        # drop stray single letters/tokens
        if len(p) == 1 and not p.isdigit():
            continue
        parts.append(p)
    # collapse runs like "the 13th warrior hd ma5 1 avc" -> "the 13th warrior"
    out = " ".join(parts).strip()
    # dedupe spaces
    out = re.sub(r"\s{2,}", " ", out)
    return out

def _norm_key(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())

def _best_movie_match(results: List[Dict[str, Any]], q_title: str, year: Optional[int]) -> Optional[int]:
    if not results:
        return None
    qk = _norm_key(q_title)
    # prefer year match + strong title match
    ranked: List[tuple[int, int]] = []  # (idx, score)
    for i, r in enumerate(results):
        t = r.get("title") or r.get("original_title") or ""
        rk = _norm_key(t)
        score = 0
        if year and (r.get("release_date") or "").startswith(str(year)):
            score += 3
        if rk == qk:
            score += 3
        elif rk.startswith(qk) or qk.startswith(rk):
            score += 2
        # light boost for popularity to break ties
        try:
            score += int(float(r.get("popularity") or 0) > 20)
        except Exception:
            pass
        ranked.append((i, score))
    ranked.sort(key=lambda x: x[1], reverse=True)
    return results[ranked[0][0]].get("id")

# -------- packers --------

def _pack_common(d: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "tmdb_id": d.get("id"),
        "imdb_id": d.get("imdb_id"),  # movie only (None for tv)
        "overview": (d.get("overview") or "").strip() or None,
        "genres": [g.get("name") for g in (d.get("genres") or []) if g.get("name")],
        "rating_vote_average": d.get("vote_average"),
        "rating_vote_count": d.get("vote_count"),
        "popularity": d.get("popularity"),
        "poster": _img(d.get("poster_path"), "w500"),
        "poster_original": _img(d.get("poster_path"), "original"),
        "backdrop": _img(d.get("backdrop_path"), "w780"),
        "backdrop_original": _img(d.get("backdrop_path"), "original"),
        "homepage": d.get("homepage"),
        "status": d.get("status"),
        "tagline": d.get("tagline") or None,
        "spoken_languages": [sl.get("english_name") or sl.get("name") for sl in (d.get("spoken_languages") or [])],
        "production_countries": [pc.get("iso_3166_1") for pc in (d.get("production_countries") or []) if pc.get("iso_3166_1")],
        "production_companies": [pc.get("name") for pc in (d.get("production_companies") or []) if pc.get("name")],
    }

def _pack_cast(credits: Dict[str, Any], limit: int = 12) -> Dict[str, Any]:
    cast = []
    for c in (credits or {}).get("cast", [])[:limit]:
        cast.append({
            "name": c.get("name"),
            "character": c.get("character"),
            "profile": _img(c.get("profile_path"), "w185"),
            "tmdb_id": c.get("id"),
        })
    crew = []
    for c in (credits or {}).get("crew", []):
        if c.get("job") in {"Director", "Writer", "Screenplay", "Creator"}:
            crew.append({
                "name": c.get("name"),
                "job": c.get("job"),
                "profile": _img(c.get("profile_path"), "w185"),
                "tmdb_id": c.get("id"),
            })
    # dedupe by name+job
    seen = set()
    deduped = []
    for c in crew:
        k = (c["name"], c["job"])
        if k not in seen:
            seen.add(k)
            deduped.append(c)
    return {"cast": cast, "crew": deduped}

# -------- TMDB lookups --------

async def _search_movie(api_key: str, title: str, year: Optional[int]) -> Optional[int]:
    # try a few strategies
    q1 = title
    q2 = _clean_title(title)
    payloads: List[Optional[Dict[str, Any]]] = []

    for q, y in [(q1, year), (q2, year), (q2, None)]:
        params = {"query": q, "include_adult": True}
        if y:
            params["year"] = y  # TMDB supports 'year' for simple filtering
        payloads.append(_get(api_key, "search/movie", params))

        if payloads[-1] and payloads[-1].get("results"):
            mid = _best_movie_match(payloads[-1]["results"], q, y)
            if mid:
                return mid

    # last-ditch: search multi and filter to movie
    multi = _get(api_key, "search/multi", {"query": q2 or q1, "include_adult": True})
    if multi:
        movies = [r for r in (multi.get("results") or []) if r.get("media_type") == "movie"]
        mid = _best_movie_match(movies, q2 or q1, year)
        if mid:
            return mid

    log.info("TMDB miss for title='%s' year=%s (q2='%s')", title, year, q2)
    return None

async def _search_tv(api_key: str, title: str) -> Optional[int]:
    q1 = title
    q2 = _clean_title(title)
    for q in (q1, q2):
        payload = _get(api_key, "search/tv", {"query": q, "include_adult": True})
        if payload and payload.get("results"):
            return payload["results"][0]["id"]
    return None

async def _movie_detail_pack(api_key: str, tmdb_id: int) -> Dict[str, Any]:
    d = _get(api_key, f"movie/{tmdb_id}", {"append_to_response": "credits,releases"})
    if not d:
        return {}
    out = _pack_common(d)
    out.update({
        "media_type": "movie",
        "title": d.get("title") or d.get("original_title"),
        "original_title": d.get("original_title"),
        "release_date": d.get("release_date"),
        "runtime": d.get("runtime"),
    })
    out.update(_pack_cast(d.get("credits") or {}))
    return out

async def _tv_detail_pack(api_key: str, tmdb_id: int) -> Dict[str, Any]:
    d = _get(api_key, f"tv/{tmdb_id}", {"append_to_response": "aggregate_credits"})
    if not d:
        return {}
    out = _pack_common(d)
    out.update({
        "media_type": "tv",
        "name": d.get("name") or d.get("original_name"),
        "original_name": d.get("original_name"),
        "first_air_date": d.get("first_air_date"),
        "last_air_date": d.get("last_air_date"),
        "in_production": d.get("in_production"),
        "number_of_seasons": d.get("number_of_seasons"),
        "number_of_episodes": d.get("number_of_episodes"),
        "episode_run_time": d.get("episode_run_time"),
    })
    out.update(_pack_cast({"cast": (d.get("aggregate_credits") or {}).get("cast", [])}))
    return out

async def _episode_detail_pack(api_key: str, show_id: int, season: int, episode: int) -> Dict[str, Any]:
    d = _get(api_key, f"tv/{show_id}/season/{season}/episode/{episode}", {})
    if not d:
        return {}
    return {
        "media_type": "episode",
        "name": d.get("name"),
        "overview": (d.get("overview") or "").strip() or None,
        "air_date": d.get("air_date"),
        "still": _img(d.get("still_path"), "w300"),
        "still_original": _img(d.get("still_path"), "original"),
        "vote_average": d.get("vote_average"),
        "vote_count": d.get("vote_count"),
        "guest_stars": [
            {"name": gs.get("name"), "character": gs.get("character"), "profile": _img(gs.get("profile_path"), "w185")}
            for gs in (d.get("guest_stars") or [])[:10]
        ],
    }

# -------- public: enrich --------

async def enrich_library(
    session: AsyncSession,
    api_key: str,
    library_id: str,
    limit: int = 2000,
    force: bool = False,
    only_missing: bool = False,
) -> Dict[str, int]:
    """
    Populate MediaItem.extra_json with TMDB data.
    - force=True: ignore existing tmdb_id and re-match
    - only_missing=True: process items that lack poster/backdrop even if tmdb_id is present
    """
    if not api_key:
        log.info("TMDB_API_KEY not set; skipping enrichment")
        return {"matched": 0, "skipped": 0, "episodes": 0}

    lib = (await session.execute(select(Library).where(Library.id == library_id))).scalars().first()
    if not lib:
        return {"matched": 0, "skipped": 0, "episodes": 0}

    items = (await session.execute(
        select(MediaItem).where(MediaItem.library_id == library_id).order_by(MediaItem.created_at.desc())
    )).scalars().all()

    matched = skipped = ep_filled = 0

    tv_id_cache: Dict[str, int] = {}

    for it in items[:limit]:
        data = dict(it.extra_json or {})
        already = bool(data.get("tmdb_id"))

        # movies
        if it.kind == MediaKind.movie:
            needs_poster = not (data.get("poster") or it.poster_url)
            should_enrich = force or (not already) or (only_missing and needs_poster)

            if should_enrich:
                tmdb_id = await _search_movie(api_key, it.title, it.year)
                if not tmdb_id:
                    skipped += 1
                    continue
                data.update(await _movie_detail_pack(api_key, tmdb_id))
                # canonicalize title/year
                if data.get("title"):
                    it.title = data["title"]
                    it.sort_title = normalize_sort(it.title)
                if data.get("release_date") and not it.year:
                    y = data["release_date"][:4]
                    if y.isdigit():
                        it.year = int(y)
                it.extra_json = data
                matched += 1

            # write-through to columns if present
            if data.get("poster") and not it.poster_url:
                it.poster_url = data.get("poster")
            if data.get("backdrop") and not it.backdrop_url:
                it.backdrop_url = data.get("backdrop")

        # tv show / season / episode
        elif it.kind == MediaKind.show:
            needs_poster = not (data.get("poster") or it.poster_url)
            tmdb_id = data.get("tmdb_id") if already else None
            if force or (not tmdb_id) or (only_missing and needs_poster):
                tmdb_id = await _search_tv(api_key, it.title)
                if not tmdb_id:
                    skipped += 1
                    continue
                data.update(await _tv_detail_pack(api_key, tmdb_id))
                it.extra_json = data
                matched += 1
            tv_id_cache[it.id] = tmdb_id or data.get("tmdb_id")
            if data.get("poster") and not it.poster_url:
                it.poster_url = data.get("poster")
            if data.get("backdrop") and not it.backdrop_url:
                it.backdrop_url = data.get("backdrop")

        elif it.kind == MediaKind.season:
            if "season_number" not in data and (it.title or "").lower().startswith("season"):
                try:
                    data["season_number"] = int((it.title or "").split()[-1])
                except Exception:
                    pass
            it.extra_json = data

        elif it.kind == MediaKind.episode:
            se = dict(it.extra_json or {})
            season_no = se.get("season")
            episode_no = se.get("episode")
            if not (season_no and episode_no):
                skipped += 1
                continue

            if not tv_id_cache:
                for show in items:
                    if show.kind == MediaKind.show and (show.extra_json or {}).get("tmdb_id"):
                        tv_id_cache[show.id] = show.extra_json["tmdb_id"]

            show_tmdb_id = None
            for show_id, s_tmdb in tv_id_cache.items():
                show = next((x for x in items if x.id == show_id), None)
                if show and show.title and it.title and normalize_sort(show.title) in normalize_sort(it.title):
                    show_tmdb_id = s_tmdb
                    break
            if not show_tmdb_id:
                show_tmdb_id = await _search_tv(api_key, it.title.split("S")[0].strip())
            if not show_tmdb_id:
                skipped += 1
                continue

            ep_data = await _episode_detail_pack(api_key, show_tmdb_id, int(season_no), int(episode_no))
            if ep_data:
                se.update(ep_data)
                it.extra_json = se
                ep_filled += 1

        if (matched + ep_filled) % 50 == 0:
            await session.commit()

    await session.commit()
    log.info("enrich done: matched=%d skipped=%d episodes=%d", matched, skipped, ep_filled)
    return {"matched": matched, "skipped": skipped, "episodes": ep_filled}
