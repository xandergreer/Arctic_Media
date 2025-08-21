# app/streaming.py
from __future__ import annotations

import os
import mimetypes
import hashlib
from typing import Optional, Tuple

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from fastapi.responses import StreamingResponse, HTMLResponse, FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from .auth import get_current_user
from .database import get_db
from .models import MediaFile, MediaItem

router = APIRouter(prefix="/stream", tags=["stream"])

# ---------- helpers ----------

def _parse_range(range_header: Optional[str], file_size: int) -> Tuple[int, int]:
    """
    Parse a HTTP Range header like "bytes=START-END".
    Returns (start, end) as inclusive byte offsets. If header is invalid, raise.
    """
    if not range_header or not range_header.startswith("bytes="):
        return (0, file_size - 1)

    ranges = range_header.replace("bytes=", "").strip()
    if "," in ranges:  # single range only
        raise HTTPException(status_code=416, detail="Multiple ranges not supported")

    start_s, _, end_s = ranges.partition("-")
    if start_s == "" and end_s == "":
        return (0, file_size - 1)

    if start_s == "":
        # suffix range: last N bytes
        length = int(end_s)
        if length <= 0:
            raise HTTPException(status_code=416, detail="Invalid range")
        start = max(0, file_size - length)
        end = file_size - 1
    else:
        start = int(start_s)
        end = file_size - 1 if end_s == "" else int(end_s)
        if start > end or start >= file_size:
            raise HTTPException(status_code=416, detail="Invalid range")

    return (max(0, start), min(end, file_size - 1))


async def _get_file_and_item(
    db: AsyncSession, file_id: str
) -> Tuple[MediaFile, Optional[MediaItem]]:
    mf = await db.get(MediaFile, file_id)
    if not mf:
        raise HTTPException(status_code=404, detail="File not found")
    # parent item (for title/poster)
    item = await db.get(MediaItem, mf.media_item_id) if mf.media_item_id else None
    return mf, item


# ---------- pages ----------

@router.get("/{file_id}", response_class=HTMLResponse)
async def player_page(
    file_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user),
):
    mf, item = await _get_file_and_item(db, file_id)
    path = mf.path
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Missing media file on disk")

    poster = (item.extra_json or {}).get("poster") if item and item.extra_json else None

    return request.app.state.templates.TemplateResponse(
        "player.html",
        {
            "request": request,
            "file": mf,
            "item": item,
            "poster": poster or "/static/img/placeholder.png",
            "play_url": f"/stream/{file_id}/file",
        },
    )


# ---------- streaming (HTTP Range) ----------

@router.get("/{file_id}/file")
async def stream_file(
    file_id: str,
    request: Request,
    range: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user),
):
    mf, _item = await _get_file_and_item(db, file_id)
    path = mf.path
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Missing media file on disk")

    file_stat = os.stat(path)
    file_size = file_stat.st_size
    content_type, _ = mimetypes.guess_type(path)
    content_type = content_type or "application/octet-stream"

    # lightweight ETag/Last-Modified
    last_mod = datetime.utcfromtimestamp(int(file_stat.st_mtime)).strftime("%a, %d %b %Y %H:%M:%S GMT")
    etag = f'W/"{hashlib.md5(str(file_stat.st_mtime_ns).encode()).hexdigest()}"'

    # HEAD fast-path
    if request.method == "HEAD":
        return Response(
            status_code=200,
            headers={
                "Content-Type": content_type,
                "Content-Length": str(file_size),
                "Accept-Ranges": "bytes",
                "ETag": etag,
                "Last-Modified": last_mod,
                "Cache-Control": "private, max-age=0, must-revalidate",
            },
        )

    if not range:
        # full file via sendfile
        return FileResponse(
            path,
            media_type=content_type,
            filename=os.path.basename(path),
            headers={
                "Accept-Ranges": "bytes",
                "Content-Disposition": f'inline; filename="{os.path.basename(path)}"',
                "ETag": etag,
                "Last-Modified": last_mod,
                "Cache-Control": "private, max-age=0, must-revalidate",
                # "Access-Control-Expose-Headers": "Content-Range, Accept-Ranges, Content-Length, ETag, Last-Modified",
            },
        )

    # Partial content
    try:
        start, end = _parse_range(range, file_size)
    except HTTPException as e:
        # RFC 9110: send bytes */size when 416
        if e.status_code == 416:
            return Response(
                status_code=416,
                headers={
                    "Content-Range": f"bytes */{file_size}",
                    "Accept-Ranges": "bytes",
                },
            )
        raise

    chunk_size = 1024 * 1024  # 1 MiB
    length = end - start + 1

    def iter_file():
        with open(path, "rb") as f:
            f.seek(start)
            remaining = length
            while remaining > 0:
                data = f.read(min(chunk_size, remaining))
                if not data:
                    break
                remaining -= len(data)
                yield data

    headers = {
        "Content-Type": content_type,
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(length),
        "Content-Disposition": f'inline; filename="{os.path.basename(path)}"',
        "ETag": etag,
        "Last-Modified": last_mod,
        "Cache-Control": "private, max-age=0, must-revalidate",
        # "Access-Control-Expose-Headers": "Content-Range, Accept-Ranges, Content-Length, ETag, Last-Modified",
    }
    return StreamingResponse(iter_file(), status_code=206, headers=headers)