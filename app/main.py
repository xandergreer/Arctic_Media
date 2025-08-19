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
import os, time

# --- FastAPI / Starlette ---
from fastapi import FastAPI, Request, Depends, HTTPException, APIRouter
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.cors import CORSMiddleware

# --- DB / models ---
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

# --- Project imports ---
from .config import settings
from .database import init_db, get_db
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
from .metadata import enrich_library
from .tv_api import router as tv_api_router

from .models import Library, MediaItem, MediaKind, User
from .scanner import scan_movie_library, scan_tv_library
from .scheduler import start_scheduler

# --- App constants ---
LOGIN_URL  = getattr(settings, "LOGIN_URL", "/login")
HOME_URL   = getattr(settings, "HOME_URL", "/home")

# --- App setup ---
app = FastAPI(title="Arctic Media", version="2.0.0")
router = APIRouter()

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

# dev no-cache for static assets (avoid ?v= busting)
@app.middleware("http")
async def apply_csp_header(request, call_next):
    resp = await call_next(request)
    resp.headers["Content-Security-Policy"] = (
        "default-src 'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://cdn.plyr.io;"
        "img-src 'self' data: https://image.tmdb.org;"
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdn.plyr.io https://cdnjs.cloudflare.com;"
        "font-src 'self' https://cdn.jsdelivr.net https://cdn.plyr.io https://cdnjs.cloudflare.com;"
        "script-src 'self' https://cdn.jsdelivr.net https://cdn.plyr.io https://cdnjs.cloudflare.com;"
        "media-src 'self' blob:;"
        "worker-src 'self' blob:;"
        "connect-src 'self';"
    )
    return resp

# Security headers
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    resp.headers["Content-Security-Policy"] = (
        "default-src 'self' https://cdn.plyr.io https://cdnjs.cloudflare.com https://cdn.jsdelivr.net; "
        "img-src 'self' data: https://image.tmdb.org; "
        "style-src 'self' 'unsafe-inline' https://cdn.plyr.io https://cdnjs.cloudflare.com https://cdn.jsdelivr.net; "
        "script-src 'self' https://cdn.plyr.io https://cdnjs.cloudflare.com https://cdn.jsdelivr.net; "
        "media-src 'self' blob:; worker-src 'self' blob:"
    )
    return resp

# --- Startup (DB + scheduler) ---
@app.on_event("startup")
async def startup_event():
    await init_db()
    start_scheduler(app)

# ------------------ PAGES declared BEFORE routers (wins for "/") ------------------

# Root: unauth → /register on first run, else /login; auth → /home
@app.get("/", response_class=HTMLResponse)
async def root(request: Request, db: AsyncSession = Depends(get_db)):
    token = request.cookies.get(ACCESS_COOKIE)
    payload = decode_token(token) if token else None

    if not payload or payload.get("typ") != "access":
        try:
            user_count = (await db.execute(
                select(func.count()).select_from(User)
            )).scalar_one()
        except Exception:
            user_count = 1  # fail-safe: assume existing users
        return RedirectResponse("/register" if user_count == 0 else "/login", status_code=307)

    return RedirectResponse("/home", status_code=307)

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

# Friendly GET shims so visiting API URLs in a browser won’t 405
@app.get("/auth/register", include_in_schema=False)
async def auth_register_get_redirect():
    return RedirectResponse("/register", status_code=307)

@app.get("/auth/login", include_in_schema=False)
async def auth_login_get_redirect():
    return RedirectResponse("/login", status_code=307)

# ------------------------------ Routers ---------------------------------
# (These are included AFTER the root route so "/" above has priority)
app.include_router(router)
app.include_router(auth_router, prefix="/auth")
app.include_router(libraries_router)
app.include_router(browse_router)
app.include_router(fs_router)
app.include_router(settings_api_router)
app.include_router(admin_users_router)
app.include_router(tasks_api_router)
app.include_router(nav_router)
app.include_router(ui_nav_router)
app.include_router(tv_api_router)

# --------------------------- Local endpoints -----------------------------
@app.get("/settings", response_class=HTMLResponse)
async def settings_root(request: Request, user = Depends(get_current_user)):
    return templates.TemplateResponse("settings_shell.html", {"request": request, "panel": "general"})

@app.get("/settings/{panel}", response_class=HTMLResponse)
async def settings_panel(panel: str, request: Request, user = Depends(get_current_user)):
    allowed = {"general","libraries","remote","transcoder","users","tasks"}
    if panel not in allowed:
        panel = "general"
    return templates.TemplateResponse("settings_shell.html", {"request": request, "panel": panel})

# (Optional convenience)
@app.get("/settings/libraries", include_in_schema=False)
async def settings_libraries_redirect(user = Depends(get_current_user)):
    return RedirectResponse("/libraries/manage", status_code=307)