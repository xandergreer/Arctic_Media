# app/nav_api.py
from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .auth import get_current_user
from .database import get_db
from .models import Library, LinkedServer, RemoteLibrary
from .config import settings

router = APIRouter(prefix="/nav", tags=["nav"])

def _server_name_default():
    # fallback if you don't have a server_settings table value yet
    return getattr(settings, "SERVER_NAME", "My Server")

@router.get("/sidebar")
async def sidebar_data(db: AsyncSession = Depends(get_db), user = Depends(get_current_user)):
    # Your libraries
    lib_rows = (await db.execute(
        select(Library.id, Library.name, Library.type)
        .where(Library.owner_user_id == user.id)
        .order_by(Library.type.asc(), Library.name.asc())
    )).all()
    my = {
        "server_name": _server_name_default(),
        "libraries": [{"id": r.id, "name": r.name, "type": r.type} for r in lib_rows]
    }

    # Friends: linked servers + their remote libraries
    rows = (await db.execute(
        select(LinkedServer.id, LinkedServer.display_name,
               RemoteLibrary.id, RemoteLibrary.name, RemoteLibrary.type)
        .join(RemoteLibrary, RemoteLibrary.linked_server_id == LinkedServer.id, isouter=True)
        .where(LinkedServer.owner_user_id == user.id)
        .order_by(LinkedServer.display_name.asc(), RemoteLibrary.name.asc())
    )).all()

    friends_map: dict[str, dict] = {}
    for sid, sname, rlib_id, rlib_name, rlib_type in rows:
        server = friends_map.setdefault(sid, {"server_id": sid, "display_name": sname, "libraries": []})
        if rlib_id:
            server["libraries"].append({"id": rlib_id, "name": rlib_name, "type": rlib_type})
    friends = list(friends_map.values())

    return {"me": my, "friends": friends}
