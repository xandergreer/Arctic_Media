# app/ui_nav.py
from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .database import get_db
from .auth import get_current_user
from .models import Library, LinkedServer, RemoteLibrary

router = APIRouter(prefix="/ui", tags=["ui"])

@router.get("/sidebar")
async def sidebar_data(db: AsyncSession = Depends(get_db), user = Depends(get_current_user)):
    # Local libraries (only the current user's)
    res_local = await db.execute(
        select(Library).where(Library.owner_user_id == user.id).order_by(Library.name.asc())
    )
    local = [
        {
            "id": lib.id,
            "name": lib.name,
            "type": lib.type,                     # "movie" | "tv"
            "href": f"/browse/library/{lib.id}",  # your browse route
        }
        for lib in res_local.scalars().all()
    ]

    # Linked servers + their libraries
    res_links = await db.execute(select(LinkedServer).order_by(LinkedServer.display_name.asc()))
    servers = []
    for s in res_links.scalars().all():
        res_remote = await db.execute(
            select(RemoteLibrary).where(RemoteLibrary.linked_server_id == s.id).order_by(RemoteLibrary.name.asc())
        )
        items = [
            {
                "id": rl.remote_library_id,
                "name": rl.name,
                "type": rl.type,  # "movie" | "tv"
                "href": f"/remote/{s.id}/library/{rl.remote_library_id}",
            }
            for rl in res_remote.scalars().all()
        ]
        servers.append({"serverId": s.id, "name": s.display_name, "items": items})

    return {"local": local, "servers": servers}
