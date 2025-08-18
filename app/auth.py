from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from .database import get_db
from .models import User, UserRole
from .schemas import UserOut
from .utils import hash_password, verify_password, create_token, decode_token
from .config import settings

router = APIRouter()

# -------------------- Cookie / TTL config --------------------

# Access cookie name (main.py imports this)
ACCESS_COOKIE = "am_access"

# Dev: COOKIE_SECURE=False and COOKIE_SAMESITE="lax"
COOKIE_SECURE   = bool(getattr(settings, "COOKIE_SECURE", False))
COOKIE_SAMESITE = getattr(settings, "COOKIE_SAMESITE", "lax")

# Session lifetimes (seconds)
ACCESS_TTL    = int(getattr(settings, "ACCESS_TTL", 30 * 60))             # 30 minutes
REMEMBER_TTL  = int(getattr(settings, "REMEMBER_TTL", 14 * 24 * 3600))    # 14 days

def set_cookie(resp: Response, name: str, value: str, max_age: int, http_only: bool = True):
    resp.set_cookie(
        key=name,
        value=value,
        max_age=max_age,
        httponly=http_only,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        path="/",
    )

def clear_cookie(resp: Response, name: str):
    resp.delete_cookie(name, path="/")

# -------------------- Current user helpers --------------------

class AuthUser(UserOut):
    role: str

async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> AuthUser:
    token = request.cookies.get(ACCESS_COOKIE)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    data = decode_token(token)
    if not data or data.get("typ") != "access" or "sub" not in data:
        raise HTTPException(status_code=401, detail="Invalid token")

    res = await db.execute(select(User).where(User.id == data["sub"]))
    user = res.scalars().first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return AuthUser.model_validate(user)

def require_admin(user: AuthUser = Depends(get_current_user)) -> AuthUser:
    if user.role != UserRole.admin.value:
        raise HTTPException(status_code=403, detail="Admin required")
    return user

# -------------------- Register --------------------

@router.post("/register")
async def register_post(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Accepts HTML form or JSON:
      - email, username, password
    On form submit: redirects to /login
    On JSON: returns 201 with created user
    """
    ctype = (request.headers.get("content-type") or "").lower()
    is_json = "application/json" in ctype

    if is_json:
        body = await request.json()
        email = (body.get("email") or "").strip().lower()
        username = (body.get("username") or "").strip()
        password = body.get("password") or ""
    else:
        form = await request.form()
        email = (form.get("email") or "").strip().lower()
        username = (form.get("username") or "").strip()
        password = form.get("password") or ""

    if not email or not username or not password:
        raise HTTPException(status_code=422, detail="email, username, and password are required")

    # Uniqueness (case-insensitive)
    if (await db.execute(select(User.id).where(func.lower(User.email) == email))).scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    if (await db.execute(select(User.id).where(func.lower(User.username) == username.lower()))).scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already taken")

    # First user becomes admin
    first_exists = (await db.execute(select(User.id).limit(1))).scalar_one_or_none() is not None
    role = UserRole.user if first_exists else UserRole.admin

    user = User(
        email=email,
        username=username,
        password_hash=hash_password(password),
        role=role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    if is_json:
        return JSONResponse(UserOut.model_validate(user).model_dump(), status_code=201)

    # form submit → go sign in
    return RedirectResponse(url="/login", status_code=303)

# -------------------- Login --------------------

@router.post("/login")
async def login_post(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Accepts HTML form or JSON:
      - identifier (username or email), password
      - optional remember=[on|true|1]
    Sets am_access cookie with typ="access" and redirects to "/".
    JSON clients get 200 + minimal payload.
    """
    ctype = (request.headers.get("content-type") or "").lower()
    is_json = "application/json" in ctype

    if is_json:
        body = await request.json()
        ident = (body.get("identifier") or body.get("username") or body.get("email") or body.get("user") or "").strip()
        password = (body.get("password") or body.get("pass") or "")
        remember = str(body.get("remember", "")).lower() in {"1", "true", "on", "yes"}
    else:
        form = await request.form()
        ident = (form.get("identifier") or form.get("username") or form.get("email") or form.get("user") or "").strip()
        password = (form.get("password") or form.get("pass") or "")
        remember = str(form.get("remember", "")).lower() in {"1", "true", "on", "yes"}

    if not ident or not password:
        raise HTTPException(status_code=422, detail="Provide username/email and password")

    q = select(User).where(or_(func.lower(User.username) == ident.lower(),
                               func.lower(User.email) == ident.lower()))
    res = await db.execute(q)
    user = res.scalar_one_or_none()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    ttl = REMEMBER_TTL if remember else ACCESS_TTL
    token = create_token({"sub": str(user.id), "typ": "access"}, expires_in=ttl)

    if is_json:
        resp = JSONResponse({"ok": True})
    else:
        resp = RedirectResponse(url="/", status_code=303)

    set_cookie(resp, ACCESS_COOKIE, token, ttl, http_only=True)
    return resp

# -------------------- Logout --------------------

@router.post("/logout")
async def logout_post():
    # Always redirect to login after clearing the cookie
    resp = RedirectResponse(url="/login", status_code=303)
    clear_cookie(resp, ACCESS_COOKIE)
    return resp
