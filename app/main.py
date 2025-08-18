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

# --- stdlib ---
import os
import string
import sys
import time

# --- FastAPI / Starlette ---
from fastapi import FastAPI, Request, Depends, HTTPException, APIRouter, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import Response

# --- Project imports ---
from .config import settings
from .database import init_db, get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from .auth import router as auth_router
from .auth import get_current_user, ACCESS_COOKIE
from .utils import decode_token

from .libraries import router as libraries_router
from .browse import router as browse_router
from .fsbrowse import router as fs_router
from .admin_users import router as admin_users_router
from .tasks_api import router as tasks_api_router
from .settings_api import router as settings_api_router
from .nav_api import router as nav_router
from .ui_nav import router as ui_nav_router

from .models import Library, MediaItem, MediaKind
from .scanner import scan_movie_library, scan_tv_library
from .scheduler import start_scheduler

# --- App constants ---
LOGIN_URL  = getattr(settings, "LOGIN_URL", "/login")
HOME_URL   = getattr(settings, "HOME_URL", "/home")

# --- App setup ---
app = FastAPI(title="Arctic Media", version="2.0.0")
router = APIRouter()

# Routers
app.include_router(router)
app.include_router(auth_router, prefix="/auth")
app.include_router(libraries_router)
app.include_router(browse_router)
app.include_router(fs_router)              # keep your existing fsbrowse if you use it elsewhere
app.include_router(settings_api_router)
app.include_router(admin_users_router)
app.include_router(tasks_api_router)
app.include_router(nav_router)
app.include_router(ui_nav_router)

# --- Root redirect if no access token ---
@app.middleware("http")
async def no_cache_static(request, call_next):
    resp = await call_next(request)
    if getattr(settings, "ENV", "dev").lower() == "dev" and request.url.path.startswith("/static/"):
        resp.headers["Cache-Control"] = "no-store, max-age=0, must-revalidate"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
    return resp

# --- Static & templates ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TPL_DIR = os.path.join(BASE_DIR, "templates")

# Ensure folders exist (doesn't create, just avoids confusing errors)
if not os.path.isdir(STATIC_DIR):
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
app.state.templates = templates  # submodules can render via app.state.templates

# --- Middlewares ---
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[],  # tighten later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Security headers (CSP, HSTS) ---
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    resp.headers["Content-Security-Policy"] = (
        "default-src 'self' https://cdn.plyr.io https://cdnjs.cloudflare.com https://cdn.jsdelivr.net; "
        "img-src 'self' data: https://image.tmdb.org; "
        "style-src 'self' 'unsafe-inline' https://cdn.plyr.io https://cdnjs.cloudflare.com https://cdn.jsdelivr.net; "
        "script-src 'self' https://cdn.plyr.io https://cdnjs.cloudflare.com https://cdn.jsdelivr.net; "
        "media-src 'self' blob:; "
        "worker-src 'self' blob:"
    )
    return resp

# --- Startup (DB + scheduler) ---
@app.on_event("startup")
async def startup_event():
    await init_db()
    start_scheduler(app)

# --- Basic pages ---
@app.get("/", response_class=HTMLResponse)
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
        select(MediaItem).where(MediaItem.kind == MediaKind.movie)
        .order_by(MediaItem.created_at.desc()).limit(30)
    )).scalars().all()

    recent_tv = (await db.execute(
        select(MediaItem).where(MediaItem.kind == MediaKind.show)
        .order_by(MediaItem.created_at.desc()).limit(30)
    )).scalars().all()

    libs = (await db.execute(
        select(Library).where(Library.owner_user_id == user.id).order_by(Library.created_at.desc())
    )).scalars().all()

    return templates.TemplateResponse(
        "home.html",
        {
            "request": request,
            "movies_count": movies_count,
            "shows_count": shows_count,
            "recent_movies": recent_movies,
            "recent_tv": recent_tv,
            "libraries": libs,
        },
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

# --- Settings shell (left nav) ---
@app.get("/settings", response_class=HTMLResponse)
async def settings_root(request: Request, user = Depends(get_current_user)):
    return templates.TemplateResponse("settings_shell.html", {"request": request, "panel": "general"})

@app.get("/settings/{panel}", response_class=HTMLResponse)
async def settings_panel(panel: str, request: Request, user = Depends(get_current_user)):
    allowed = {"general","libraries","remote","transcoder","users","tasks"}
    if panel not in allowed:
        panel = "general"
    return templates.TemplateResponse("settings_shell.html", {"request": request, "panel": panel})

# --- Trigger scans ---
@router.post("/libraries/{library_id}/scan")
async def scan_library(library_id: str, session: AsyncSession = Depends(get_db)):
    lib = await session.get(Library, library_id)
    if not lib:
        raise HTTPException(status_code=404, detail="Library not found")

    if lib.type.lower() == "movie":
        result = await scan_movie_library(session, lib)
    elif lib.type.lower() in ("tv", "show", "shows"):
        result = await scan_tv_library(session, lib)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown library type {lib.type}")

    return result
