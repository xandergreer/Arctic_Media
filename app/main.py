from __future__ import annotations

# ── Quiet noisy logs early ────────────────────────────────────────────────────
import logging, logging.config
logging.config.dictConfig({
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"std": {"format": "%(levelname)s  %(name)s: %(message)s"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "std"}},
    "loggers": {
        "sqlalchemy":        {"level": "WARNING", "handlers": ["console"], "propagate": False},
        "sqlalchemy.engine": {"level": "WARNING", "handlers": ["console"], "propagate": False},
        "sqlalchemy.pool":   {"level": "WARNING", "handlers": ["console"], "propagate": False},
        "scanner":           {"level": "INFO",    "handlers": ["console"], "propagate": False},
    },
})

# ── Windows event loop policy (keeps asyncio stable with subprocess + sockets)
import sys, asyncio
if sys.platform.startswith("win"):
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception:
        pass

# ── Stdlib / FastAPI / SQLA ───────────────────────────────────────────────────
import os, time, secrets, re, ipaddress
from typing import Optional
from fastapi import FastAPI, Request, Depends, HTTPException, Query
from pydantic import BaseModel
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

# ── Project imports ───────────────────────────────────────────────────────────
from .config import settings
from .database import init_db, get_db
from .auth import router as auth_router, get_current_user, ACCESS_COOKIE, require_admin
from .utils import decode_token, normalize_sort
from .libraries import router as libraries_router
# from .browse import router as browse_router  # (left disabled to avoid path clashes)
from .fsbrowse import router as fs_router
from .admin_users import router as admin_users_router
from .tasks_api import router as tasks_api_router
from .jobs_api import router as jobs_router
from .settings_api import router as settings_api_router
from .nav_api import router as nav_router
from .ui_nav import router as ui_nav_router
from .tv_api import router as tv_api_router
from .streaming import router as streaming_router                 # /stream/{id}/file, /auto, etc.
from .streaming_hls import (
    router as hls_router,                                         # /stream/{item_id}/master.m3u8 + /hls/*
    jf_router as jf_stream_router,                                   # /Videos/{itemId}/master.m3u8 + /hls/*
    start_hls_cleanup_task,
    stop_hls_cleanup_task,
)
from .models import Library, MediaItem, MediaKind, User, MediaFile
from .metadata import _movie_detail_pack, _search_movie, _tv_detail_pack, _search_tv, _episode_detail_pack
from .scheduler import start_scheduler

# ── App setup ─────────────────────────────────────────────────────────────────
app = FastAPI(title="Arctic Media", version="2.0.0")

# ── Static & templates ────────────────────────────────────────────────────────
def _resolve_resource_dirs():
    import sys
    from pathlib import Path
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS) / "app"
    else:
        base = Path(__file__).parent
    return base / "static", base / "templates"
STATIC_DIR, TPL_DIR = _resolve_resource_dirs()
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

templates = Jinja2Templates(directory=str(TPL_DIR))
BUILD_ID = os.environ.get("ASSET_V") or str(int(time.time()))

def tmdb_url(path: str | None, size: str = "w342") -> str | None:
    if not path:
        return None
    if path.startswith(("http://", "https://")):
        return path
    if path.startswith("/"):
        return f"https://image.tmdb.org/t/p/{size}{path}"
    return path

templates.env.globals.update({
    "BRAND": "Arctic Media Server",
    "LOGO_MARK": "/static/img/logo-mark.svg",
    "LOGO_WORD": "/static/img/logo-word.svg",
    "LOGO_STACKED": "/static/img/logo-stacked-icecap-cutout.svg",
    "LOGO_COMPACT": "/static/img/logo-word-icecap-cutout-compact.svg",
    "ASSET_V": BUILD_ID,
    "tmdb": tmdb_url,
})
app.state.templates = templates

# ── Middleware ────────────────────────────────────────────────────────────────
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)
# Compress responses > ~1KB (helps over WAN/SSL)
app.add_middleware(GZipMiddleware, minimum_size=1024)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[],                # keep same-origin; set if you need remote UI
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Smart LAN redirect: if client IP is private and LOCAL_BASE_URL is configured, redirect HTML pages
@app.middleware("http")
async def lan_redirect(request: Request, call_next):
    try:
        lbu = (getattr(settings, "LOCAL_BASE_URL", "") or "").strip().rstrip("/")
        if lbu:
            # only for HTML page navigations
            accept = (request.headers.get("accept") or "").lower()
            if request.method in {"GET", "HEAD"} and "text/html" in accept:
                # detect private/loopback client
                chost = (request.client.host if request.client else None) or ""
                try:
                    ip = ipaddress.ip_address(chost)
                    is_lan = ip.is_private or ip.is_loopback or ip.is_link_local
                except Exception:
                    is_lan = False
                if is_lan:
                    cur_host = (request.headers.get("host") or "").strip()
                    cur_origin = f"{request.url.scheme}://{cur_host}".rstrip("/")
                    if cur_origin and cur_origin.lower() != lbu.lower():
                        # preserve path/query
                        target = f"{lbu}{request.url.path}"
                        if request.url.query:
                            target += f"?{request.url.query}"
                        return RedirectResponse(url=target, status_code=307)
    except Exception:
        # best-effort; fall through on any error
        pass
    return await call_next(request)

# Single security/CSP middleware (covers all pages)
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    nonce = secrets.token_urlsafe(16)
    request.state.csp_nonce = nonce
    resp = await call_next(request)
    resp.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    resp.headers["Content-Security-Policy"] = (
    "default-src 'self' https://cdn.plyr.io https://cdnjs.cloudflare.com https://cdn.jsdelivr.net; "
    "img-src 'self' data: https://image.tmdb.org https://cdn.plyr.io; "  # add cdn.plyr.io here
    "style-src 'self' 'unsafe-inline' https://cdn.plyr.io https://cdnjs.cloudflare.com https://cdn.jsdelivr.net; "
    f"script-src 'self' https://cdn.plyr.io https://cdnjs.cloudflare.com https://cdn.jsdelivr.net 'nonce-{nonce}'; "
    "media-src 'self' blob:; "
    "connect-src 'self' blob: data: https://cdn.plyr.io https://cdnjs.cloudflare.com https://cdn.jsdelivr.net; "
    "worker-src 'self' blob:"
)
    return resp

# Cache static assets aggressively (URLs are versioned via ASSET_V)
@app.middleware("http")
async def static_cache_control(request: Request, call_next):
    resp = await call_next(request)
    if request.url.path.startswith("/static/"):
        # Immutable static assets; allow long cache
        resp.headers.setdefault("Cache-Control", "public, max-age=31536000, immutable")
    return resp

# Lightweight perf log for slow requests (ASGI-safe to avoid BaseHTTPMiddleware edge cases)
class PerfLoggerMiddleware:
    def __init__(self, app):
        self.app = app
        self.log = logging.getLogger("perf")

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            return await self.app(scope, receive, send)

        t0 = time.perf_counter()
        status_code = 0

        async def send_wrapper(message):
            nonlocal status_code
            if message.get("type") == "http.response.start":
                status_code = message.get("status", status_code)
            return await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            dt = (time.perf_counter() - t0) * 1000
            if dt > 800:
                self.log.warning("%s %s -> %d %0.0fms", scope.get("method", ""), scope.get("path", ""), status_code, dt)

app.add_middleware(PerfLoggerMiddleware)

logging.getLogger("scanner").info("TMDB key present: %s", bool(settings.TMDB_API_KEY))

# Redirect unauthenticated users to /login for HTML page requests
@app.middleware("http")
async def require_login_for_pages(request: Request, call_next):
    try:
        path = request.url.path or "/"
        # Skip auth, static and service endpoints
        if (
            path.startswith("/static/")
            or path.startswith("/auth/")
            or path in {"/login", "/register", "/favicon.ico"}
            or path.startswith("/docs")
            or path.startswith("/redoc")
            or path == "/openapi.json"
            or path.startswith("/stream")
            or path.startswith("/hls")
        ):
            return await call_next(request)

        if request.method in {"GET", "HEAD"}:
            accept = (request.headers.get("accept") or "").lower()
            # Only affect page navigations
            if "text/html" in accept:
                token = request.cookies.get(ACCESS_COOKIE)
                payload = decode_token(token) if token else None
                if not payload or payload.get("typ") != "access":
                    return RedirectResponse("/login", status_code=307)
    except Exception:
        pass
    return await call_next(request)

# ── Lifecycle ────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    # Suppress benign Windows Proactor "connection reset by peer" spam
    try:
        import sys
        if sys.platform.startswith("win"):
            loop = asyncio.get_running_loop()
            def _ignore_win_reset(loop, context):
                exc = context.get("exception")
                handle = context.get("handle")
                msg = context.get("message", "") or ""
                cb_qual = getattr(getattr(handle, "_callback", None), "__qualname__", "")
                # Filter the noisy callback raised when clients close sockets early
                if isinstance(exc, ConnectionResetError) and (
                    "_ProactorBasePipeTransport._call_connection_lost" in cb_qual or
                    "connection_lost" in msg.lower()
                ):
                    return  # swallow
                loop.default_exception_handler(context)
            loop.set_exception_handler(_ignore_win_reset)
    except Exception:
        pass
    await init_db()
    # Load transcoder settings and set ffmpeg overrides in env
    try:
        from sqlalchemy import select as _sa_select
        from .models import ServerSetting as _ServerSetting
        from .database import get_sessionmaker as _get_sm
        Session = _get_sm()
        async with Session() as _db:
            _row = (await _db.execute(_sa_select(_ServerSetting).where(_ServerSetting.key == "transcoder"))).scalars().first()
            _cfg = (_row.value or {}) if _row else {}
            _ff = (_cfg.get("ffmpeg_path") or "").strip() or None
            _fp = (_cfg.get("ffprobe_path") or "").strip() or None
            if _ff: os.environ.setdefault("FFMPEG_PATH", _ff)
            if _fp: os.environ.setdefault("FFPROBE_PATH", _fp)
            _hw = (_cfg.get("hwaccel") or "").lower()
            if _hw == "none":
                os.environ["FFMPEG_HW"] = "cpu"
            elif _hw in {"nvenc", "qsv", "amf"}:
                os.environ["FFMPEG_HW"] = _hw
            # else auto: leave unset to allow auto-detect
            _alang = (_cfg.get("preferred_audio_lang") or "").strip()
            if _alang:
                os.environ["ARCTIC_PREF_AUDIO_LANG"] = _alang
            _hls_cont = (_cfg.get("hls_container") or "").lower().strip()
            if _hls_cont in ("fmp4", "ts"):
                os.environ["ARCTIC_HLS_CONTAINER"] = _hls_cont
    except Exception:
        pass
    await start_hls_cleanup_task(app)
    # start background scheduler for admin tasks (scans, metadata refresh)
    try:
        start_scheduler(app)
    except Exception:
        pass

@app.on_event("shutdown")
async def shutdown_event():
    await stop_hls_cleanup_task(app)

# ── Pages ─────────────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def root(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        user_count = (await db.execute(select(func.count()).select_from(User))).scalar_one()
    except Exception:
        user_count = 0

    if user_count == 0:
        return RedirectResponse("/register", status_code=307)

    token = request.cookies.get(ACCESS_COOKIE)
    payload = decode_token(token) if token else None
    if payload and payload.get("typ") == "access":
        return RedirectResponse("/home", status_code=307)
    return RedirectResponse("/login", status_code=307)

@app.get("/home", response_class=HTMLResponse)
async def home(request: Request, db: AsyncSession = Depends(get_db), user = Depends(get_current_user)):
    movies_count = (await db.execute(
        select(func.count()).select_from(MediaItem).where(MediaItem.kind == MediaKind.movie)
    )).scalar_one()
    shows_count = (await db.execute(
        select(func.count()).select_from(MediaItem).where(MediaItem.kind == MediaKind.show)
    )).scalar_one()
    recent_movies = (await db.execute(
        select(MediaItem).where(MediaItem.kind == MediaKind.movie).order_by(MediaItem.updated_at.desc()).limit(30)
    )).scalars().all()
    recent_tv = (await db.execute(
        select(MediaItem).where(MediaItem.kind == MediaKind.show).order_by(MediaItem.updated_at.desc()).limit(30)
    )).scalars().all()
    libs = (await db.execute(
        select(Library).where(Library.owner_user_id == user.id).order_by(Library.created_at.desc())
    )).scalars().all()

    return templates.TemplateResponse(
        "home.html",
        {"request": request,
         "movies_count": movies_count, "shows_count": shows_count,
         "recent_movies": recent_movies, "recent_tv": recent_tv,
         "libraries": libs}
    )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "arctic-media"}

@app.post("/admin/server/restart")
async def restart_server(user = Depends(require_admin)):
    """Restart the server (admin only)"""
    import os
    import signal
    import sys
    
    # Send restart signal to current process
    os.kill(os.getpid(), signal.SIGTERM)
    
    return {"status": "restarting"}

@app.get("/settings")
async def settings_page(request: Request, user = Depends(get_current_user)):
    """Main settings page - redirects to general settings"""
    return RedirectResponse(url="/settings/general")

@app.get("/settings/{panel}")
async def settings_panel(
    panel: str, 
    request: Request, 
    user = Depends(get_current_user)
):
    """Settings panel pages"""
    valid_panels = ["general", "libraries", "remote", "transcoder", "users", "tasks"]
    if panel not in valid_panels:
        raise HTTPException(404, "Settings panel not found")
    
    # Admin-only panels
    admin_panels = ["remote", "transcoder", "users", "tasks"]
    if panel in admin_panels and not user.is_admin:
        raise HTTPException(403, "Admin access required")
    
    return request.app.state.templates.TemplateResponse(
        "settings_shell.html", 
        {"request": request, "panel": panel, "user": user}
    )

@app.get("/admin/settings", response_class=HTMLResponse)
async def admin_settings_page(
    request: Request, 
    user = Depends(require_admin)
):
    """Admin settings page"""
    return templates.TemplateResponse("admin_settings.html", {"request": request, "user": user})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "hide_chrome": True})

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request, "hide_chrome": True})

# Friendly GET shims for POST endpoints
@app.get("/auth/register", include_in_schema=False)
async def auth_register_get_redirect():
    return RedirectResponse("/register", status_code=307)

@app.get("/auth/login", include_in_schema=False)
async def auth_login_get_redirect():
    return RedirectResponse("/login", status_code=307)

# ── Movies ────────────────────────────────────────────────────────────────────
@app.get("/movies", response_class=HTMLResponse)
async def movies_index(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user),
    page: int = 1,
    page_size: int = 60,
):
    page = max(1, int(page or 1))
    page_size = max(12, min(120, int(page_size or 60)))
    total_count = (await db.execute(
        select(func.count()).select_from(MediaItem).where(MediaItem.kind == MediaKind.movie)
    )).scalar_one()
    items = (await db.execute(
        select(MediaItem)
        .where(MediaItem.kind == MediaKind.movie)
        .order_by(MediaItem.updated_at.desc())
        .limit(page_size)
        .offset((page - 1) * page_size)
    )).scalars().all()
    total_pages = max(1, (total_count + page_size - 1) // page_size)
    return templates.TemplateResponse(
        "movies.html",
        {
            "request": request,
            "items": items,
            "movies": items,
            "count": total_count,
            "page": page,
            "total_pages": total_pages,
            "page_size": page_size,
        },
    )

@app.get("/movie/{item_id}", response_class=HTMLResponse)
async def movie_detail(item_id: str, request: Request, db: AsyncSession = Depends(get_db), user = Depends(get_current_user)):
    movie = await db.get(MediaItem, item_id)
    if not movie or movie.kind != MediaKind.movie:
        return RedirectResponse("/movies", status_code=307)

    files = (await db.execute(
        select(MediaFile).where(MediaFile.media_item_id == movie.id).order_by(MediaFile.created_at.asc())
    )).scalars().all()

    return templates.TemplateResponse("movie_detail.html", {"request": request, "item": movie, "files": files, "user": user})

# ── TV ────────────────────────────────────────────────────────────────────────
@app.get("/tv", response_class=HTMLResponse)
async def tv_grid(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user),
    page: int = 1,
    page_size: int = 60,
):
    page = max(1, int(page or 1))
    page_size = max(12, min(120, int(page_size or 60)))
    total_count = (await db.execute(
        select(func.count()).select_from(MediaItem).where(MediaItem.kind == MediaKind.show)
    )).scalar_one()
    shows = (await db.execute(
        select(MediaItem)
        .where(MediaItem.kind == MediaKind.show)
        .order_by(MediaItem.updated_at.asc())
        .limit(page_size)
        .offset((page - 1) * page_size)
    )).scalars().all()
    total_pages = max(1, (total_count + page_size - 1) // page_size)
    return templates.TemplateResponse(
        "tv.html",
        {
            "request": request,
            "items": shows,
            "count": total_count,
            "page": page,
            "total_pages": total_pages,
            "page_size": page_size,
        },
    )

@app.get("/show/{show_id}", response_class=HTMLResponse)
async def show_detail_page(show_id: str, request: Request, db: AsyncSession = Depends(get_db), user = Depends(get_current_user)):
    show = await db.get(MediaItem, show_id)
    if not show or show.kind != MediaKind.show:
        return RedirectResponse("/tv", status_code=307)

    seasons = (await db.execute(
        select(MediaItem)
        .where(MediaItem.parent_id == show.id, MediaItem.kind == MediaKind.season)
        .order_by(MediaItem.sort_title.asc())
    )).scalars().all()

    # first playable (first ep's first file)
    first_play_file_id = None
    if seasons:
        first_ep = (await db.execute(
            select(MediaItem)
            .where(MediaItem.kind == MediaKind.episode, MediaItem.parent_id.in_([s.id for s in seasons]))
            .order_by(MediaItem.sort_title.asc())
            .limit(1)
        )).scalars().first()
        if first_ep:
            first_file = (await db.execute(
                select(MediaFile).where(MediaFile.media_item_id == first_ep.id).limit(1)
            )).scalars().first()
            first_play_file_id = first_file.id if first_file else None

    return templates.TemplateResponse(
        "show_detail.html",
        {"request": request, "item": show, "seasons": seasons, "episodes": [], "first_play_file_id": first_play_file_id, "user": user}
    )

@app.get("/show/{show_id}/season/{season_num}", response_class=HTMLResponse)
async def season_detail_page(show_id: str, season_num: int, request: Request, db: AsyncSession = Depends(get_db), user = Depends(get_current_user)):
    show = await db.get(MediaItem, show_id)
    if not show or show.kind != MediaKind.show:
        return RedirectResponse("/tv", status_code=307)

    # seasons (for the Seasons grid)
    seasons = (await db.execute(
        select(MediaItem)
        .where(MediaItem.parent_id == show.id, MediaItem.kind == MediaKind.season)
        .order_by(MediaItem.sort_title.asc())
    )).scalars().all()

    # locate requested season
    season_title = f"Season {season_num}"
    season = (await db.execute(
        select(MediaItem).where(
            MediaItem.parent_id == show.id,
            MediaItem.kind == MediaKind.season,
            MediaItem.title == season_title,
        )
    )).scalars().first()
    if not season and 1 <= season_num <= len(seasons):
        season = seasons[season_num - 1]
    if not season:
        return RedirectResponse(f"/show/{show.id}", status_code=307)

# ---- Admin: Update metadata (movie/show/episode)
class UpdateMovieIn(BaseModel):
    title: Optional[str] = None
    poster_url: Optional[str] = None
    backdrop_url: Optional[str] = None
    tmdb_id: Optional[int] = None
    refresh_from_tmdb: Optional[bool] = False

@app.patch("/admin/media/{item_id}")
async def admin_update_movie(
    item_id: str,
    body: UpdateMovieIn,
    db: AsyncSession = Depends(get_db),
    admin = Depends(require_admin),
):
    item = await db.get(MediaItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    changed = False
    if body.title is not None and body.title.strip() and body.title.strip() != item.title:
        item.title = body.title.strip()
        item.sort_title = normalize_sort(item.title)
        changed = True
    if body.poster_url is not None:
        item.poster_url = body.poster_url.strip() or None
        changed = True
    if body.backdrop_url is not None:
        item.backdrop_url = body.backdrop_url.strip() or None
        changed = True

    if body.tmdb_id is not None or body.refresh_from_tmdb:
        api_key = getattr(settings, "TMDB_API_KEY", "")
        if not api_key:
            raise HTTPException(status_code=400, detail="TMDB_API_KEY not configured")
        if item.kind == MediaKind.movie:
            tmdb_id = body.tmdb_id or await _search_movie(api_key, item.title, item.year)
            if not tmdb_id:
                raise HTTPException(status_code=404, detail="TMDB movie not found")
            data = await _movie_detail_pack(api_key, int(tmdb_id))
            if data:
                ej = dict(item.extra_json or {})
                ej.update(data)
                item.extra_json = ej
                ttl = body.title if body.title is not None else data.get("title")
                if ttl and ttl.strip():
                    item.title = ttl.strip()
                    item.sort_title = normalize_sort(item.title)
                if not body.poster_url and data.get("poster"):
                    item.poster_url = data.get("poster")
                if not body.backdrop_url and data.get("backdrop"):
                    item.backdrop_url = data.get("backdrop")
                rd = (data.get("release_date") or "")
                if rd[:4].isdigit():
                    try:
                        item.year = int(rd[:4])
                    except Exception:
                        pass
                changed = True
        elif item.kind == MediaKind.show:
            tmdb_id = body.tmdb_id or await _search_tv(api_key, item.title)
            if not tmdb_id:
                raise HTTPException(status_code=404, detail="TMDB show not found")
            data = await _tv_detail_pack(api_key, int(tmdb_id))
            if data:
                ej = dict(item.extra_json or {})
                ej.update(data)
                item.extra_json = ej
                ttl = body.title if body.title is not None else data.get("name")
                if ttl and ttl.strip():
                    item.title = ttl.strip()
                    item.sort_title = normalize_sort(item.title)
                if not body.poster_url and data.get("poster"):
                    item.poster_url = data.get("poster")
                if not body.backdrop_url and data.get("backdrop"):
                    item.backdrop_url = data.get("backdrop")
                fad = (data.get("first_air_date") or "")
                if fad[:4].isdigit():
                    try:
                        item.year = int(fad[:4])
                    except Exception:
                        pass
                changed = True
        elif item.kind == MediaKind.episode:
            # Use parent season/show metadata to refresh episode details
            season = await db.get(MediaItem, item.parent_id) if item.parent_id else None
            show = await db.get(MediaItem, season.parent_id) if season and season.parent_id else None
            show_tmdb = (show.extra_json or {}).get("tmdb_id") if show and show.extra_json else None
            se = dict(item.extra_json or {})
            season_no = se.get("season") or se.get("season_number")
            episode_no = se.get("episode") or se.get("episode_number")
            if show_tmdb and season_no and episode_no:
                data = await _episode_detail_pack(api_key, int(show_tmdb), int(season_no), int(episode_no))
                if data:
                    se.update(data)
                    item.extra_json = se
                    if not body.poster_url and data.get("still"):
                        item.poster_url = data.get("still")
                    ttl = body.title if body.title is not None else data.get("title")
                    if ttl and ttl.strip():
                        item.title = ttl.strip()
                        item.sort_title = normalize_sort(item.title)
                    changed = True

    if changed:
        await db.commit()
        await db.refresh(item)
    return {"ok": True, "id": item.id}

    # 1) episodes attached to the season (ideal case)
    eps = (await db.execute(
        select(MediaItem)
        .where(MediaItem.parent_id == season.id, MediaItem.kind == MediaKind.episode)
        .order_by(MediaItem.sort_title.asc())
    )).scalars().all()

    # 2) fallback: some scanners attach episodes directly to the show.
    if len(eps) <= 1:
        loose_eps = (await db.execute(
            select(MediaItem)
            .where(MediaItem.parent_id == show.id, MediaItem.kind == MediaKind.episode)
            .order_by(MediaItem.sort_title.asc())
        )).scalars().all()

        def is_match(e: MediaItem) -> bool:
            ej = (e.extra_json or {})
            if ej.get("season") == season_num or ej.get("season_number") == season_num:
                return True
            t = (e.title or "")
            if re.search(fr"\bS0?{season_num}E\d{{1,3}}\b", t, re.I):
                return True
            if re.search(fr"\b{season_num}x\d{{1,3}}\b", t, re.I):
                return True
            return False

        by_id = {e.id: e for e in eps}
        for e in filter(is_match, loose_eps):
            by_id.setdefault(e.id, e)
        eps = list(by_id.values())
        eps.sort(key=lambda e: e.sort_title or e.title or "")

    # map each episode to include first_file_id
    episodes = []
    for ep in eps:
        mf = (await db.execute(
            select(MediaFile).where(MediaFile.media_item_id == ep.id).limit(1)
        )).scalars().first()
        episodes.append({
            "id": ep.id,
            "title": ep.title,
            "poster_url": getattr(ep, "poster_url", None),
            "extra_json": ep.extra_json,
            "first_file_id": mf.id if mf else None,
        })

    return templates.TemplateResponse(
        "show_detail.html",
        {"request": request, "item": show, "seasons": seasons, "episodes": episodes, "first_play_file_id": None, "user": user},
    )

# ── Health check endpoint ─────────────────────────────────────────────────────
@app.get("/health")
async def health_check():
    """Health check endpoint for Docker/load balancers"""
    return {"status": "healthy", "service": "arctic-media"}

# ── Routers (order matters a bit; keep app pages first, then APIs) ────────────
app.include_router(auth_router, prefix="/auth")
app.include_router(libraries_router)
# app.include_router(browse_router)  # left disabled to prevent conflicts with /movies etc.
app.include_router(fs_router)
app.include_router(settings_api_router)
app.include_router(admin_users_router)
app.include_router(tasks_api_router)
app.include_router(jobs_router)
app.include_router(nav_router)
app.include_router(ui_nav_router)
app.include_router(tv_api_router)

# Media/streaming APIs
app.include_router(streaming_router)   # /stream/{file_id}/file, /stream/{file_id}/auto, etc.
app.include_router(hls_router)         # /stream/{item_id}/master.m3u8 and /stream/{item_id}/hls/*
app.include_router(jf_stream_router)      # /Videos/{itemId}/master.m3u8 and /Videos/{itemId}/hls/*

# Lightweight JSON feeds for infinite scroll
@app.get("/api/movies")
async def api_movies(
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user),
    page: int = 1,
    page_size: int = 60,
):
    page = max(1, int(page or 1))
    page_size = max(12, min(120, int(page_size or 60)))
    total_count = (await db.execute(
        select(func.count()).select_from(MediaItem).where(MediaItem.kind == MediaKind.movie)
    )).scalar_one()
    rows = (await db.execute(
        select(MediaItem)
        .where(MediaItem.kind == MediaKind.movie)
        .order_by(MediaItem.updated_at.desc())
        .limit(page_size)
        .offset((page - 1) * page_size)
    )).scalars().all()
    total_pages = max(1, (total_count + page_size - 1) // page_size)
    items = [
        {
            "id": it.id,
            "title": it.title,
            "year": it.year,
            "poster_url": getattr(it, "poster_url", None),
            "extra_json": getattr(it, "extra_json", None) or {},
        }
        for it in rows
    ]
    return {
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "count": total_count,
        "items": items,
    }

@app.get("/api/tv")
async def api_tv(
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user),
    page: int = 1,
    page_size: int = 60,
):
    page = max(1, int(page or 1))
    page_size = max(12, min(120, int(page_size or 60)))
    total_count = (await db.execute(
        select(func.count()).select_from(MediaItem).where(MediaItem.kind == MediaKind.show)
    )).scalar_one()
    rows = (await db.execute(
        select(MediaItem)
        .where(MediaItem.kind == MediaKind.show)
        .order_by(MediaItem.sort_title.asc())
        .limit(page_size)
        .offset((page - 1) * page_size)
    )).scalars().all()
    total_pages = max(1, (total_count + page_size - 1) // page_size)
    items = [
        {
            "id": it.id,
            "title": it.title,
            "year": it.year,
            "poster_url": getattr(it, "poster_url", None),
            "extra_json": getattr(it, "extra_json", None) or {},
        }
        for it in rows
    ]
    return {
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "count": total_count,
        "items": items,
    }

@app.get("/api/search")
async def api_search(
    q: str = Query(..., description="Search query"),
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
):
    """Search movies and TV shows"""
    if not q or len(q.strip()) < 2:
        return {"movies": [], "tv_shows": [], "total": 0}

    query_str = q.strip()

    # Try prefix search first (more efficient), then fallback to contains search
    search_terms = [
        f"{query_str.lower()}%",  # Prefix search (most efficient)
        f"%{query_str.lower()}%",  # Contains search (fallback)
    ]

    all_items = []

    for search_term in search_terms:
        if len(all_items) >= limit * 2:  # Got enough results
            break

        remaining_limit = (limit * 2) - len(all_items)

        query = (
            select(MediaItem)
            .where(
                MediaItem.kind.in_([MediaKind.movie, MediaKind.show]),
                func.lower(MediaItem.title).like(search_term)
            )
            .order_by(MediaItem.title)
            .limit(remaining_limit)
        )

        result = await db.execute(query)
        items = result.scalars().all()

        # Avoid duplicates
        existing_ids = {item.id for item in all_items}
        new_items = [item for item in items if item.id not in existing_ids]
        all_items.extend(new_items)

    # Separate results by type
    movies = [item for item in all_items if item.kind == MediaKind.movie][:limit]
    tv_shows = [item for item in all_items if item.kind == MediaKind.show][:limit]

    return {
        "movies": [
            {
                "id": movie.id,
                "title": movie.title,
                "year": movie.year,
                "poster_url": movie.poster_url,
                "overview": movie.overview,
                "type": "movie"
            }
            for movie in movies
        ],
        "tv_shows": [
            {
                "id": show.id,
                "title": show.title,
                "year": show.year,
                "poster_url": show.poster_url,
                "overview": show.overview,
                "type": "tv"
            }
            for show in tv_shows
        ],
        "total": len(movies) + len(tv_shows)
    }
