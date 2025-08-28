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
import os, time, secrets, re
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

# ── Project imports ───────────────────────────────────────────────────────────
from .config import settings
from .database import init_db, get_db
from .auth import router as auth_router, get_current_user, ACCESS_COOKIE, require_admin
from .utils import decode_token
from .libraries import router as libraries_router
# from .browse import router as browse_router  # (left disabled to avoid path clashes)
from .fsbrowse import router as fs_router
from .admin_users import router as admin_users_router
from .tasks_api import router as tasks_api_router
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

# ── App setup ─────────────────────────────────────────────────────────────────
app = FastAPI(title="Arctic Media", version="2.0.0")

# ── Static & templates ────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TPL_DIR = os.path.join(BASE_DIR, "templates")
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

templates = Jinja2Templates(directory=TPL_DIR)
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=[],                # keep same-origin; set if you need remote UI
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

logging.getLogger("scanner").info("TMDB key present: %s", bool(settings.TMDB_API_KEY))

# ── Lifecycle ────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    await init_db()
    await start_hls_cleanup_task(app)

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
        select(MediaItem).where(MediaItem.kind == MediaKind.movie).order_by(MediaItem.created_at.desc()).limit(30)
    )).scalars().all()
    recent_tv = (await db.execute(
        select(MediaItem).where(MediaItem.kind == MediaKind.show).order_by(MediaItem.created_at.desc()).limit(30)
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
    
    return request.app.state.templates.TemplateResponse(
        "settings_shell.html", 
        {"request": request, "panel": panel}
    )

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
async def movies_index(request: Request, db: AsyncSession = Depends(get_db), user = Depends(get_current_user)):
    movies = (await db.execute(
        select(MediaItem).where(MediaItem.kind == MediaKind.movie).order_by(MediaItem.created_at.desc())
    )).scalars().all()
    return templates.TemplateResponse("movies.html", {"request": request, "items": movies, "movies": movies, "count": len(movies)})

@app.get("/movie/{item_id}", response_class=HTMLResponse)
async def movie_detail(item_id: str, request: Request, db: AsyncSession = Depends(get_db), user = Depends(get_current_user)):
    movie = await db.get(MediaItem, item_id)
    if not movie or movie.kind != MediaKind.movie:
        return RedirectResponse("/movies", status_code=307)

    files = (await db.execute(
        select(MediaFile).where(MediaFile.media_item_id == movie.id).order_by(MediaFile.created_at.asc())
    )).scalars().all()

    return templates.TemplateResponse("movie_detail.html", {"request": request, "item": movie, "files": files})

# ── TV ────────────────────────────────────────────────────────────────────────
@app.get("/tv", response_class=HTMLResponse)
async def tv_grid(request: Request, db: AsyncSession = Depends(get_db), user = Depends(get_current_user)):
    shows = (await db.execute(
        select(MediaItem).where(MediaItem.kind == MediaKind.show).order_by(MediaItem.sort_title.asc()).limit(5000)
    )).scalars().all()
    return templates.TemplateResponse("tv.html", {"request": request, "items": shows})

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
        {"request": request, "item": show, "seasons": seasons, "episodes": [], "first_play_file_id": first_play_file_id}
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
        {"request": request, "item": show, "seasons": seasons, "episodes": episodes, "first_play_file_id": None},
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
app.include_router(nav_router)
app.include_router(ui_nav_router)
app.include_router(tv_api_router)

# Media/streaming APIs
app.include_router(streaming_router)   # /stream/{file_id}/file, /stream/{file_id}/auto, etc.
app.include_router(hls_router)         # /stream/{item_id}/master.m3u8 and /stream/{item_id}/hls/*
app.include_router(jf_stream_router)      # /Videos/{itemId}/master.m3u8 and /Videos/{itemId}/hls/*
