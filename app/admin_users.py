from __future__ import annotations
from typing import Optional
from datetime import datetime
from .schemas import ORMBase 

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from .auth import require_admin
from .database import get_db
from .models import User, UserRole
from .utils import hash_password

router = APIRouter(prefix="/admin/users", tags=["users"])

class UserAdminOut(ORMBase):
    id: str
    email: EmailStr
    username: str
    role: str
    created_at: datetime
    last_login_at: Optional[datetime] = None

class UserAdminCreate(BaseModel):
    email: EmailStr
    username: str
    password: str
    role: UserRole = UserRole.user

class UserAdminUpdate(BaseModel):
    role: Optional[UserRole] = None
    password: Optional[str] = None

@router.get("", response_model=list[UserAdminOut])
async def list_users(_: str = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(User).order_by(User.created_at.desc()))
    return res.scalars().all()

@router.post("", response_model=UserAdminOut, status_code=201)
async def create_user(body: UserAdminCreate, _: str = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    # unique checks
    if (await db.execute(select(User).where(func.lower(User.email)==body.email.lower()))).scalars().first():
        raise HTTPException(400, "Email already exists")
    if (await db.execute(select(User).where(func.lower(User.username)==body.username.lower()))).scalars().first():
        raise HTTPException(400, "Username taken")

    u = User(email=body.email.lower(), username=body.username, password_hash=hash_password(body.password), role=body.role)
    db.add(u); await db.commit(); await db.refresh(u)
    return u

@router.patch("/{user_id}", response_model=UserAdminOut)
async def update_user(user_id: str, body: UserAdminUpdate, _: str = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(User).where(User.id==user_id))
    u = res.scalars().first()
    if not u: raise HTTPException(404, "User not found")
    vals = {}
    if body.role is not None: vals["role"] = body.role
    if body.password: vals["password_hash"] = hash_password(body.password)
    if vals:
        await db.execute(update(User).where(User.id==user_id).values(**vals))
        await db.commit()
    await db.refresh(u)
    return u

@router.delete("/{user_id}")
async def delete_user(user_id: str, _: str = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    await db.execute(delete(User).where(User.id==user_id))
    await db.commit()
    return {"ok": True}
