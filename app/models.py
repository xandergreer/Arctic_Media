# app/models.py
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    String, Integer, ForeignKey, Enum, Boolean, DateTime, LargeBinary,
    UniqueConstraint, JSON, BigInteger, func, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def new_id() -> str:
    # simple unique id; can be swapped for ULID later
    return str(uuid.uuid4())


# ---- Enums ----
class UserRole(str, enum.Enum):
    admin = "admin"
    user = "user"


class MediaKind(str, enum.Enum):
    movie = "movie"
    show = "show"
    season = "season"
    episode = "episode"


class TranscodeMode(str, enum.Enum):
    direct = "direct"
    remux = "remux"
    transcode = "transcode"


class PlaybackState(str, enum.Enum):
    playing = "playing"
    paused = "paused"
    buffering = "buffering"
    stopped = "stopped"


# ---- Users & Devices ----
class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(120), unique=True, index=True)  # if you’ve added username
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.user, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), default=None)

    # make target explicit and back_populates match DeviceSession.user
    devices: Mapped[List["DeviceSession"]] = relationship(
        "DeviceSession", back_populates="user", cascade="all, delete-orphan"
    )

    libraries: Mapped[List["Library"]] = relationship(back_populates="owner", cascade="all, delete-orphan")

    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.admin

class DeviceSession(Base):
    __tablename__ = "device_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    user_agent: Mapped[Optional[str]] = mapped_column(String(400))
    platform: Mapped[Optional[str]] = mapped_column(String(120))
    app_version: Mapped[Optional[str]] = mapped_column(String(60))
    last_seen_ip: Mapped[Optional[str]] = mapped_column(String(64))

    # hashed refresh token (never store raw)
    refresh_token_hash: Mapped[Optional[str]] = mapped_column(String(255))
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship("User", back_populates="devices")


class DevicePairing(Base):
    __tablename__ = "device_pairings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    device_code: Mapped[str] = mapped_column(String(64), unique=True, index=True)  # Secret, only known to device
    user_code: Mapped[str] = mapped_column(String(12), unique=True, index=True)  # Human-readable (e.g., "ABCD-1234")
    user_id: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, authorized, expired
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    activated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    user: Mapped[Optional["User"]] = relationship("User")


# ---- Libraries & Media ----
class Library(Base):
    __tablename__ = "libraries"
    __table_args__ = (UniqueConstraint("owner_user_id", "slug", name="uq_library_owner_slug"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    owner_user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    name: Mapped[str] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(140), index=True)
    type: Mapped[str] = mapped_column(String(16))  # "movie" | "tv" (top-level classification)
    path: Mapped[str] = mapped_column(String(1024))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    owner: Mapped["User"] = relationship(back_populates="libraries")
    media_items: Mapped[List["MediaItem"]] = relationship(back_populates="library", cascade="all, delete-orphan")


class MediaItem(Base):
    __tablename__ = "media_items"
    __table_args__ = (
    UniqueConstraint("library_id", "kind", "title", "year", name="uq_media_lib_kind_title_year"),
    Index("ix_item_sort_year_parent", "sort_title", "year", "parent_id"),
    Index("ix_media_item_title", "title"),  # Index for search performance
    )   

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    library_id: Mapped[str] = mapped_column(ForeignKey("libraries.id", ondelete="CASCADE"), index=True)

    kind: Mapped[MediaKind] = mapped_column(Enum(MediaKind), index=True)
    parent_id: Mapped[Optional[str]] = mapped_column(ForeignKey("media_items.id", ondelete="CASCADE"), index=True)

    title: Mapped[str] = mapped_column(String(400))
    sort_title: Mapped[Optional[str]] = mapped_column(String(400))
    year: Mapped[Optional[int]] = mapped_column(Integer)

    tmdb_id: Mapped[Optional[int]] = mapped_column(Integer, index=True)
    poster_url: Mapped[Optional[str]] = mapped_column(String(1024))
    backdrop_url: Mapped[Optional[str]] = mapped_column(String(1024))
    overview: Mapped[Optional[str]] = mapped_column(String(4000))
    runtime_ms: Mapped[Optional[int]] = mapped_column(Integer)

    extra_json: Mapped[Optional[dict]] = mapped_column(JSON, default=None)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    library: Mapped["Library"] = relationship(back_populates="media_items")
    parent: Mapped[Optional["MediaItem"]] = relationship(remote_side="MediaItem.id")
    children: Mapped[List["MediaItem"]] = relationship(back_populates="parent", cascade="all, delete-orphan")

    files: Mapped[List["MediaFile"]] = relationship(back_populates="media_item", cascade="all, delete-orphan")
    trailers: Mapped[List["Trailer"]] = relationship(back_populates="media_item", cascade="all, delete-orphan")


class MediaFile(Base):
    __tablename__ = "media_files"
    __table_args__ = (
    UniqueConstraint("path", name="uq_mediafile_path"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    media_item_id: Mapped[str] = mapped_column(ForeignKey("media_items.id", ondelete="CASCADE"), index=True)

    path: Mapped[str] = mapped_column(String(2048))
    container: Mapped[Optional[str]] = mapped_column(String(24))
    vcodec: Mapped[Optional[str]] = mapped_column(String(24))
    acodec: Mapped[Optional[str]] = mapped_column(String(24))
    channels: Mapped[Optional[int]] = mapped_column(Integer)
    width: Mapped[Optional[int]] = mapped_column(Integer)
    height: Mapped[Optional[int]] = mapped_column(Integer)
    bitrate: Mapped[Optional[int]] = mapped_column(Integer)
    size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger)
    checksum: Mapped[Optional[str]] = mapped_column(String(64))  # e.g., sha256

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    media_item: Mapped["MediaItem"] = relationship(back_populates="files")


class Trailer(Base):
    __tablename__ = "trailers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    media_item_id: Mapped[str] = mapped_column(ForeignKey("media_items.id", ondelete="CASCADE"), index=True)

    # local trailer file OR remote url (one of these)
    path: Mapped[Optional[str]] = mapped_column(String(2048))
    remote_url: Mapped[Optional[str]] = mapped_column(String(2048))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    media_item: Mapped["MediaItem"] = relationship(back_populates="trailers")


# ---- Playback (Live Dashboard) ----
class PlaybackSession(Base):
    __tablename__ = "playback_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    media_item_id: Mapped[str] = mapped_column(ForeignKey("media_items.id", ondelete="SET NULL"), nullable=True, index=True)
    device_session_id: Mapped[Optional[str]] = mapped_column(ForeignKey("device_sessions.id", ondelete="SET NULL"), index=True)

    state: Mapped[PlaybackState] = mapped_column(Enum(PlaybackState), default=PlaybackState.playing, index=True)
    is_remote: Mapped[bool] = mapped_column(Boolean, default=False)
    transcode_mode: Mapped[TranscodeMode] = mapped_column(Enum(TranscodeMode), default=TranscodeMode.direct)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_heartbeat_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[Optional["User"]] = relationship()
    media_item: Mapped[Optional["MediaItem"]] = relationship()
    device_session: Mapped[Optional["DeviceSession"]] = relationship()
    stats: Mapped[List["PlaybackStats"]] = relationship(back_populates="session", cascade="all, delete-orphan")


class PlaybackStats(Base):
    __tablename__ = "playback_stats"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    session_id: Mapped[str] = mapped_column(ForeignKey("playback_sessions.id", ondelete="CASCADE"), index=True)

    # point-in-time metrics
    position_ms: Mapped[Optional[int]] = mapped_column(Integer)  # client-reported
    bitrate_kbps: Mapped[Optional[int]] = mapped_column(Integer)
    dropped_frames: Mapped[Optional[int]] = mapped_column(Integer)
    width: Mapped[Optional[int]] = mapped_column(Integer)
    height: Mapped[Optional[int]] = mapped_column(Integer)
    vcodec: Mapped[Optional[str]] = mapped_column(String(24))
    acodec: Mapped[Optional[str]] = mapped_column(String(24))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session: Mapped["PlaybackSession"] = relationship(back_populates="stats")


# ---- Sharing / Linked Servers ----
class ShareInvite(Base):
    __tablename__ = "share_invites"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    owner_user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    token: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    allowed_library_ids: Mapped[Optional[List[str]]] = mapped_column(JSON, default=None)
    scopes: Mapped[Optional[List[str]]] = mapped_column(JSON, default=None)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    owner: Mapped["User"] = relationship()


class LinkedServer(Base):
    __tablename__ = "linked_servers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    owner_user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    display_name: Mapped[str] = mapped_column(String(120))
    remote_base_url: Mapped[str] = mapped_column(String(1024))
    remote_pubkey_pem: Mapped[str] = mapped_column(String(4000))
    local_privkey_pem: Mapped[str] = mapped_column(String(4000))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    owner: Mapped["User"] = relationship()
    remote_libraries: Mapped[List["RemoteLibrary"]] = relationship(back_populates="linked_server", cascade="all, delete-orphan")


class RemoteLibrary(Base):
    __tablename__ = "remote_libraries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    linked_server_id: Mapped[str] = mapped_column(ForeignKey("linked_servers.id", ondelete="CASCADE"), index=True)

    remote_library_id: Mapped[str] = mapped_column(String(36), index=True)
    name: Mapped[str] = mapped_column(String(120))
    type: Mapped[str] = mapped_column(String(16))  # movie|tv
    scope: Mapped[Optional[List[str]]] = mapped_column(JSON, default=None)

    linked_server: Mapped["LinkedServer"] = relationship(back_populates="remote_libraries")


class PlaybackGrant(Base):
    __tablename__ = "playback_grants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    media_item_id: Mapped[str] = mapped_column(ForeignKey("media_items.id", ondelete="CASCADE"), index=True)
    linked_server_id: Mapped[Optional[str]] = mapped_column(ForeignKey("linked_servers.id", ondelete="SET NULL"))

    # short-lived signed ticket (opaque to clients)
    signature: Mapped[bytes] = mapped_column(LargeBinary)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship()
    media_item: Mapped["MediaItem"] = relationship()
    linked_server: Mapped[Optional["LinkedServer"]] = relationship()

class ServerSetting(Base):
    __tablename__ = "server_settings"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[Optional[dict]] = mapped_column(JSON, default=None)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

# ---- Admin / Scheduled Tasks ----
class ScheduledJobType(str, enum.Enum):
    scan_library = "scan_library"
    refresh_metadata = "refresh_metadata"

class ScheduledTask(Base):
    __tablename__ = "scheduled_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(200))
    job_type: Mapped[ScheduledJobType] = mapped_column(Enum(ScheduledJobType))
    payload: Mapped[Optional[dict]] = mapped_column(JSON, default=None)  # e.g. {"library_id": "..."}
    interval_minutes: Mapped[int] = mapped_column(Integer, default=60)   # simple interval for now
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    next_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ---- Background Jobs (ad-hoc scans/refreshes) ----
class BackgroundJob(Base):
    __tablename__ = "background_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    job_type: Mapped[str] = mapped_column(String(40), index=True)  # e.g., scan_library, refresh_metadata
    library_id: Mapped[Optional[str]] = mapped_column(String(36), index=True)

    status: Mapped[str] = mapped_column(String(24), default="queued", index=True)  # queued|running|done|failed
    progress: Mapped[Optional[int]] = mapped_column(Integer, default=0)  # 0..total
    total: Mapped[Optional[int]] = mapped_column(Integer)
    message: Mapped[Optional[str]] = mapped_column(String(400))
    result: Mapped[Optional[dict]] = mapped_column(JSON, default=None)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
