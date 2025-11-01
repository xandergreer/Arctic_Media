# app/pairing.py
from __future__ import annotations

import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from .auth import get_current_user, ACCESS_TOKEN_EXPIRE_SECONDS, create_token, hash_password, new_csrf
from .config import settings
from .database import get_db
from .models import DevicePairing, DeviceSession, User

router = APIRouter(prefix="/pair", tags=["pairing"])

# User code is human-readable: 4 letters + 4 digits, e.g., "ABCD-1234"
def _generate_user_code() -> str:
    letters = "".join(secrets.choice(string.ascii_uppercase) for _ in range(4))
    digits = "".join(secrets.choice(string.digits) for _ in range(4))
    return f"{letters}-{digits}"

# Device code is a long random secret (only known to device)
def _generate_device_code() -> str:
    return secrets.token_urlsafe(32)

# Expiry: 30 minutes (gives user plenty of time to enter code)
PAIRING_EXPIRY_SECONDS = 1800


class PairRequestOut(BaseModel):
    device_code: str
    user_code: str
    expires_in: int
    interval: int  # polling interval in seconds
    server_url: str  # base URL of the server (e.g., http://192.168.1.10:8085)


class PairPollIn(BaseModel):
    device_code: str


class PairPollOut(BaseModel):
    status: str  # "pending" or "authorized"
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None


class PairActivateIn(BaseModel):
    user_code: str


@router.post("/request", response_model=PairRequestOut)
async def pair_request(request: Request, db: AsyncSession = Depends(get_db)):
    """Request a pairing code. Returns device_code (secret) and user_code (display to user)."""
    device_code = _generate_device_code()
    user_code = _generate_user_code()
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=PAIRING_EXPIRY_SECONDS)

    # Ensure user_code is unique (unlikely collision, but check)
    existing = (await db.execute(select(DevicePairing).where(DevicePairing.user_code == user_code))).scalars().first()
    if existing:
        user_code = _generate_user_code()  # Regenerate if collision

    pairing = DevicePairing(
        device_code=device_code,
        user_code=user_code,
        status="pending",
        expires_at=expires_at,
    )
    db.add(pairing)
    await db.commit()

    # Get base URL - prefer public_base_url from settings if available
    public_url = getattr(request.state, "public_base_url", None)
    if public_url:
        base_url = public_url.rstrip("/")
    else:
        # Fallback to request URL
        base_url = f"{request.url.scheme}://{request.url.netloc}".rstrip("/")

    return PairRequestOut(
        device_code=device_code,
        user_code=user_code,
        expires_in=PAIRING_EXPIRY_SECONDS,
        interval=5,  # Poll every 5 seconds
        server_url=base_url,
    )


@router.post("/poll", response_model=PairPollOut)
async def pair_poll(payload: PairPollIn, db: AsyncSession = Depends(get_db)):
    """Poll for authorization status. Device calls this repeatedly with device_code."""
    try:
        pairing = (
            await db.execute(select(DevicePairing).where(DevicePairing.device_code == payload.device_code))
        ).scalars().first()

        if not pairing:
            raise HTTPException(status_code=404, detail="Pairing not found")

        # Check expiry (pairing.expires_at should be timezone-aware from SQLAlchemy)
        now = datetime.now(timezone.utc)
        expires_at = pairing.expires_at
        # Handle potential timezone issues
        if expires_at.tzinfo is None:
            # SQLite might return naive datetime, add UTC timezone
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        elif expires_at.tzinfo != timezone.utc:
            # Convert to UTC if different timezone
            expires_at = expires_at.astimezone(timezone.utc)
        
        if expires_at < now:
            if pairing.status == "pending":
                pairing.status = "expired"
                await db.commit()
            raise HTTPException(status_code=400, detail="Pairing code expired")

        if pairing.status == "authorized":
            # Create device session and tokens
            user = (await db.execute(select(User).where(User.id == pairing.user_id))).scalars().first()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            # Generate refresh token (store hashed)
            refresh_raw = secrets.token_urlsafe(32)
            refresh_hash = hash_password(refresh_raw)  # Reuse password hashing for consistency
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=ACCESS_TOKEN_EXPIRE_SECONDS)

            device = DeviceSession(
                user_id=user.id,
                platform="roku",
                refresh_token_hash=refresh_hash,
                expires_at=expires_at,
            )
            db.add(device)
            await db.delete(pairing)  # Clean up pairing once used
            await db.commit()

            # Generate access token
            access = create_token({"sub": str(user.id), "typ": "access"}, expires_in=ACCESS_TOKEN_EXPIRE_SECONDS)

            return PairPollOut(
                status="authorized",
                access_token=access,
                refresh_token=refresh_raw,  # Return raw only once
                expires_in=ACCESS_TOKEN_EXPIRE_SECONDS,
            )

        return PairPollOut(status="pending")
    except HTTPException:
        raise
    except Exception as e:
        import logging
        import traceback
        error_msg = f"Error in pair_poll: {type(e).__name__}: {str(e)}"
        logging.error(error_msg)
        logging.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=error_msg)


@router.post("/activate")
async def pair_activate(
    payload: PairActivateIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user),
):
    """Activate a pairing by user_code. Requires web user to be logged in."""
    pairing = (
        await db.execute(select(DevicePairing).where(DevicePairing.user_code == payload.user_code))
    ).scalars().first()

    if not pairing:
        raise HTTPException(status_code=404, detail="Invalid code")

    # Check expiry with timezone handling
    now = datetime.now(timezone.utc)
    expires_at = pairing.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    elif expires_at.tzinfo != timezone.utc:
        expires_at = expires_at.astimezone(timezone.utc)
    
    if expires_at < now:
        pairing.status = "expired"
        await db.commit()
        raise HTTPException(status_code=400, detail="Code expired")

    if pairing.status != "pending":
        raise HTTPException(status_code=400, detail="Code already used or expired")

    # Authorize
    pairing.status = "authorized"
    pairing.user_id = user.id
    pairing.activated_at = datetime.now(timezone.utc)
    await db.commit()

    return JSONResponse({"ok": True, "message": "Device authorized"})


@router.get("", response_class=HTMLResponse)
async def pair_page(request: Request):
    """Simple web page to enter the user_code."""
    from .main import templates
    
    # Get base URL - prefer public_base_url from settings if available
    public_url = getattr(request.state, "public_base_url", None)
    if public_url:
        base_url = public_url.rstrip("/")
    else:
        # Fallback to request URL
        base_url = f"{request.url.scheme}://{request.url.netloc}".rstrip("/")
    
    return templates.TemplateResponse("pair.html", {
        "request": request,
        "server_url": base_url,
    })


