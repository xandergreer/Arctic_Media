# app/auth.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from .database import get_db
from .models import User
from .utils import hash_password, verify_password, create_token, decode_token, new_csrf
from .config import settings

router = APIRouter(tags=["auth"])

ACCESS_COOKIE = "am_access"
ACCESS_TOKEN_EXPIRE_SECONDS = int(getattr(settings, "ACCESS_TOKEN_EXPIRE_SECONDS", 60 * 60 * 24 * 30))

# -------- Schemas --------
class RegisterIn(BaseModel):
    email: str
    username: str
    password: str

class LoginIn(BaseModel):
    username: str  # username or email
    password: str

# -------- Helpers --------
def _wants_html(request: Request) -> bool:
    accept = (request.headers.get("accept") or "").lower()
    return "text/html" in accept or "*/*" in accept

def _set_access_cookie(resp: RedirectResponse | JSONResponse, token: str):
    resp.set_cookie(
        ACCESS_COOKIE, token,
        httponly=True, samesite="lax", path="/",
        max_age=ACCESS_TOKEN_EXPIRE_SECONDS,
    )

async def _first_user_is_admin(db: AsyncSession) -> bool:
    n = (await db.execute(select(func.count()).select_from(User))).scalar_one()
    return n == 0

# -------- Endpoints (mounted with prefix="/auth" in main.py) --------
@router.post("/register")
async def register(request: Request, db: AsyncSession = Depends(get_db)):
    ctype = (request.headers.get("content-type") or "").lower()
    if ctype.startswith("application/x-www-form-urlencoded") or ctype.startswith("multipart/form-data"):
        form = await request.form()
        data = RegisterIn(
            email=(form.get("email") or "").strip(),
            username=(form.get("username") or "").strip(),
            password=(form.get("password") or ""),
        )
    else:
        data = RegisterIn(**(await request.json()))
    if not data.email or not data.username or not data.password:
        raise HTTPException(400, "Missing fields")

    dup = (await db.execute(
        select(User).where(or_(User.email == data.email, User.username == data.username))
    )).scalars().first()
    if dup:
        raise HTTPException(400, "User exists")

    user = User(
        email=data.email,
        username=data.username,
        password_hash=hash_password(data.password),
        # do NOT pass is_admin here; some schemas don't have it
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Make first user admin only if model supports it
    if hasattr(user, "is_admin") and await _first_user_is_admin(db):
        setattr(user, "is_admin", True)
        db.add(user)
        await db.commit()
        await db.refresh(user)

    access = create_token({"sub": user.id, "typ": "access"}, expires_in=ACCESS_TOKEN_EXPIRE_SECONDS)

    if _wants_html(request):
        resp = RedirectResponse("/home", status_code=303)
        _set_access_cookie(resp, access)
        return resp
    return JSONResponse({"ok": True, "user_id": user.id, "access": access})

@router.post("/auth/login")
async def login(request: Request, db: AsyncSession = Depends(get_db)):
    # Accept either JSON or form, and either "identifier" (username/email) or "username"
    ctype = (request.headers.get("content-type") or "").lower()
    if "application/x-www-form-urlencoded" in ctype or "multipart/form-data" in ctype:
        form = await request.form()
        ident = (form.get("identifier") or form.get("username") or form.get("email") or "").strip()
        password = (form.get("password") or "").strip()
    else:
        try:
            data = await request.json()
        except Exception:
            data = {}
        ident = (data.get("identifier") or data.get("username") or data.get("email") or "").strip()
        password = (data.get("password") or "").strip()

    if not ident or not password:
        raise HTTPException(status_code=422, detail="username/email and password are required")

    # Lookup by username OR email (case-insensitive)
    q = (
        select(User)
        .where(or_(func.lower(User.username) == ident.lower(), func.lower(User.email) == ident.lower()))
        .limit(1)
    )
    user = (await db.execute(q)).scalars().first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Issue cookies / tokens (adjust names to your constants if needed)
    access = create_token({"sub": str(user.id), "scope": "access"}, expires_in=settings.ACCESS_EXPIRES)
    refresh = create_token({"sub": str(user.id), "scope": "refresh"}, expires_in=settings.REFRESH_EXPIRES)
    csrf = new_csrf()

    resp = RedirectResponse(url="/home", status_code=303)
    resp.set_cookie("am_access", access, httponly=True, samesite="lax", secure=bool(getattr(settings, "COOKIE_SECURE", False)), path="/")
    resp.set_cookie("am_refresh", refresh, httponly=True, samesite="lax", secure=bool(getattr(settings, "COOKIE_SECURE", False)), path="/")
    resp.set_cookie("am_csrf", csrf, httponly=False, samesite="lax", secure=bool(getattr(settings, "COOKIE_SECURE", False)), path="/")
    return resp

@router.post("/logout")
async def logout(request: Request):
    resp = RedirectResponse("/login", status_code=303) if _wants_html(request) else JSONResponse({"ok": True})
    resp.delete_cookie(ACCESS_COOKIE, path="/")
    return resp

@router.get("/me")
async def me(user=Depends(lambda req=...: get_current_user(req))):
    return {
        "id": user.id,
        "username": user.username,
        "email": getattr(user, "email", None),
        "is_admin": getattr(user, "is_admin", True if not hasattr(user, "is_admin") else bool(user.is_admin)),
    }

# -------- Dependencies --------
async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    token = request.cookies.get(ACCESS_COOKIE)
    if not token:
        raise HTTPException(401, "Not authenticated")
    payload = decode_token(token)
    if not payload or payload.get("typ") != "access":
        raise HTTPException(401, "Invalid token")
    uid = payload.get("sub")
    if not uid:
        raise HTTPException(401, "Invalid token payload")
    user = (await db.execute(select(User).where(User.id == uid))).scalars().first()
    if not user:
        raise HTTPException(401, "User not found")
    return user

async def require_admin(user: User = Depends(get_current_user)) -> User:
    # If the model has no is_admin flag, allow (single-user desktop default).
    if hasattr(user, "is_admin") and not getattr(user, "is_admin"):
        raise HTTPException(403, "Admin required")
    return user
