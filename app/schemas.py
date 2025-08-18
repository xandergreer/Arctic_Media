# app/schemas.py
from __future__ import annotations
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, EmailStr, Field

# pydantic v2: enable ORM mode
class ORMBase(BaseModel):
    model_config = dict(from_attributes=True)


# ---- Users ----
class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str

class UserOut(ORMBase):
    id: str
    email: EmailStr
    username: str
    role: str
    created_at: datetime

# Login
class LoginIn(BaseModel):
    identifier: str | None = None   # username or email
    email: EmailStr | None = None   # allow classic { email, password } payloads
    password: str

# ---- Libraries ----
class LibraryCreate(BaseModel):
    name: str
    type: str  # "movie" | "tv"
    path: str


class LibraryOut(ORMBase):
    id: str
    name: str
    slug: str
    type: str
    path: str
    created_at: datetime


# ---- Media ----
class MediaItemOut(ORMBase):
    id: str
    kind: str
    title: str
    year: Optional[int] = None
    poster_url: Optional[str] = None
    backdrop_url: Optional[str] = None
    overview: Optional[str] = None
    runtime_ms: Optional[int] = None


class MediaFileOut(ORMBase):
    id: str
    path: str
    container: Optional[str] = None
    vcodec: Optional[str] = None
    acodec: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    size_bytes: Optional[int] = None


# ---- Playback (Live Dashboard) ----
class PlaybackStatsOut(ORMBase):
    id: str
    position_ms: Optional[int] = None
    bitrate_kbps: Optional[int] = None
    dropped_frames: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    vcodec: Optional[str] = None
    acodec: Optional[str] = None
    created_at: datetime


class PlaybackSessionOut(ORMBase):
    id: str
    user_id: Optional[str] = None
    media_item_id: Optional[str] = None
    state: str
    is_remote: bool
    transcode_mode: str
    started_at: datetime
    last_heartbeat_at: datetime
    stats: List[PlaybackStatsOut] = []


# ---- Sharing ----
class ShareInviteCreate(BaseModel):
    allowed_library_ids: Optional[List[str]] = None
    scopes: Optional[List[str]] = None
    expires_in_hours: int = Field(default=24, ge=1, le=720)


class ShareInviteOut(ORMBase):
    id: str
    token: str
    allowed_library_ids: Optional[List[str]] = None
    scopes: Optional[List[str]] = None
    expires_at: Optional[datetime] = None
    created_at: datetime

