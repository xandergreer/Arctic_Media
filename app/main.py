# app/main.py
from __future__ import annotations

# --- quiet SQLAlchemy logs early ---
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

import os, time, secrets
from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from .config import settings
from .database import init_db, get_db
from .auth import router as auth_router
from .auth import get_current_user, ACCESS_COOKIE
from .utils import decode_token
from .libraries import router as libraries_router
# from .browse import router as browse_router   # ❌ avoid route collisions
from .fsbrowse import router as fs_router
from .admin_users import router as admin_users_router
from .tasks_api import router as tasks_api_router
from .settings_api import router as settings_api_router
from .nav_api import router as nav_router
from .ui_nav import router as ui_nav_router
from .tv_api import router as tv_api_router
from .streaming import router as streaming_router

from .models import Library, MediaItem, MediaKind, User, MediaFile

# --- App setup ---
app = FastAPI(title="Arctic Media", version="2.0.0")

# --- Static & templates ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TPL_DIR = os.path.join(BASE_DIR, "templates")
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

templates = Jinja2Templates(directory=TPL_DIR)
BUILD_ID = os.environ.get("ASSET_V") or str(int(time.time()))
templates.env.globals.update({
    "BRAND": "Arctic Media Server",
    "LOGO_MARK": "/static/img/logo-mark.svg",
    "LOGO_WORD": "/static/img/logo-word.svg",
    "LOGO_STACKED": "/static/img/logo-stacked-icecap-cutout.svg",
    "LOGO_COMPACT": "/static/img/logo-word-icecap-cutout-compact.svg",
    "ASSET_V": BUILD_ID,
})
app.state.templates = templates

# --- Middlewares ---
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[],  # tighten later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Single security/CSP middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    nonce = secrets.token_urlsafe(16)
    request.state.csp_nonce = nonce
    resp = await call_next(request)
    resp.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    resp.headers["Content-Security-Policy"] = (
        "default-src 'self' https://cdn.plyr.io https://cdnjs.cloudflare.com https://cdn.jsdelivr.net; "
        "img-src 'self' data: https://image.tmdb.org; "
        "style-src 'self' 'unsafe-inline' https://cdn.plyr.io https://cdnjs.cloudflare.com https://cdn.jsdelivr.net; "
        f"script-src 'self' https://cdn.plyr.io https://cdnjs.cloudflare.com https://cdn.jsdelivr.net 'nonce-{nonce}'; "
        "media-src 'self' blob: https://cdn.plyr.io; "
        "worker-src 'self' blob:"
    )
    return resp

logging.getLogger("scanner").info("TMDB key present: %s", bool(settings.TMDB_API_KEY))

# --- Startup (DB) ---
@app.on_event("startup")
async def startup_event():
    await init_db()

# ------------------ PAGES ------------------

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
async def home(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user),
):
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
        {"request": request, "movies_count": movies_count, "shows_count": shows_count,
         "recent_movies": recent_movies, "recent_tv": recent_tv, "libraries": libs}
    )

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "hide_chrome": True})

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request, "hide_chrome": True})

# Friendly GET shims
@app.get("/auth/register", include_in_schema=False)
async def auth_register_get_redirect():
    return RedirectResponse("/register", status_code=307)

@app.get("/auth/login", include_in_schema=False)
async def auth_login_get_redirect():
    return RedirectResponse("/login", status_code=307)

# ------------------ MOVIES ------------------

@app.get("/movies", response_class=HTMLResponse)
async def movies_index(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user),
):
    movies = (await db.execute(
        select(MediaItem).where(MediaItem.kind == MediaKind.movie).order_by(MediaItem.created_at.desc())
    )).scalars().all()
    return templates.TemplateResponse("movies.html", {"request": request, "items": movies, "movies": movies, "count": len(movies)})

@app.get("/movie/{item_id}", response_class=HTMLResponse)
async def movie_detail(
    item_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user),
):
    movie = await db.get(MediaItem, item_id)
    if not movie or movie.kind != MediaKind.movie:
        return RedirectResponse("/movies", status_code=307)

    files = (await db.execute(
        select(MediaFile).where(MediaFile.media_item_id == movie.id).order_by(MediaFile.created_at.asc())
    )).scalars().all()

    return templates.TemplateResponse("movie_detail.html", {"request": request, "item": movie, "files": files})

# ------------------ TV ------------------

@app.get("/tv", response_class=HTMLResponse)
async def tv_grid(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user),
):
    shows = (await db.execute(
        select(MediaItem).where(MediaItem.kind == MediaKind.show).order_by(MediaItem.sort_title.asc()).limit(5000)
    )).scalars().all()
    return templates.TemplateResponse("tv.html", {"request": request, "items": shows})

@app.get("/show/{show_id}", response_class=HTMLResponse)
async def show_detail_page(
    show_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user),
):
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
async def season_detail_page(
    show_id: str,
    season_num: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user),
):
    show = await db.get(MediaItem, show_id)
    if not show or show.kind != MediaKind.show:
        return RedirectResponse("/tv", status_code=307)

    seasons = (await db.execute(
        select(MediaItem).where(MediaItem.parent_id == show.id, MediaItem.kind == MediaKind.season)
        .order_by(MediaItem.sort_title.asc())
    )).scalars().all()

    season_title = f"Season {season_num}"
    season = (await db.execute(
        select(MediaItem).where(
            MediaItem.parent_id == show.id,
            MediaItem.kind == MediaKind.season,
            MediaItem.title == season_title
        )
    )).scalars().first()
    if not season and 1 <= season_num <= len(seasons):
        season = seasons[season_num - 1]
    if not season:
        return RedirectResponse(f"/show/{show.id}", status_code=307)

    eps = (await db.execute(
        select(MediaItem).where(MediaItem.parent_id == season.id, MediaItem.kind == MediaKind.episode)
        .order_by(MediaItem.sort_title.asc())
    )).scalars().all()

    episodes = []
    for ep in eps:
        mf = (await db.execute(select(MediaFile).where(MediaFile.media_item_id == ep.id).limit(1))).scalars().first()
        episodes.append({
            "id": ep.id,
            "title": ep.title,
            "poster_url": getattr(ep, "poster_url", None),
            "extra_json": ep.extra_json,
            "first_file_id": mf.id if mf else None,
        })

    return templates.TemplateResponse(
        "show_detail.html",
        {"request": request, "item": show, "seasons": seasons, "episodes": episodes, "first_play_file_id": None}
    )

# ------------------------------ Routers ---------------------------------
app.include_router(auth_router, prefix="/auth")
app.include_router(libraries_router)
# app.include_router(browse_router)  # ❌ comment out to prevent path conflicts with /movies, /movie/{id}, etc.
app.include_router(fs_router)
app.include_router(settings_api_router)
app.include_router(admin_users_router)
app.include_router(tasks_api_router)
app.include_router(nav_router)
app.include_router(ui_nav_router)
app.include_router(tv_api_router)
app.include_router(streaming_router)   # /stream/{file_id} and /stream/{file_id}/file

# --------------------------- Settings shell -----------------------------
@app.get("/settings", response_class=HTMLResponse)
async def settings_root(request: Request, user = Depends(get_current_user)):
    return templates.TemplateResponse("settings_shell.html", {"request": request, "panel": "general"})

@app.get("/settings/{panel}", response_class=HTMLResponse)
async def settings_panel(panel: str, request: Request, user = Depends(get_current_user)):
    allowed = {"general", "libraries", "remote", "transcoder", "users", "tasks"}
    if panel not in allowed:
        panel = "general"
    return templates.TemplateResponse("settings_shell.html", {"request": request, "panel": panel})
