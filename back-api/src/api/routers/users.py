"""User management endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user, hash_password
from api.db import get_db
from api.models import User

router = APIRouter(prefix="/v2/users", tags=["users"])


class CreateUserIn(BaseModel):
    email: str
    name: str
    password: str
    role: str = "operator"  # operator | reviewer | admin


class UpdateUserIn(BaseModel):
    name: str | None = None
    role: str | None = None
    password: str | None = None


def _require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return user


@router.get("")
async def list_users(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(_require_admin),
) -> dict:
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()
    return {"items": [_out(u) for u in users]}


@router.post("", status_code=201)
async def create_user(
    body: CreateUserIn,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(_require_admin),
) -> dict:
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        email=body.email,
        name=body.name,
        role=body.role,
        hashed_password=hash_password(body.password),
    )
    db.add(user)
    await db.flush()
    return _out(user)


@router.patch("/{user_id}")
async def update_user(
    user_id: str,
    body: UpdateUserIn,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(_require_admin),
) -> dict:
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if body.name:
        user.name = body.name
    if body.role:
        user.role = body.role
    if body.password:
        user.hashed_password = hash_password(body.password)
    return _out(user)


@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(_require_admin),
) -> None:
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await db.delete(user)


def _out(u: User) -> dict:
    return {
        "id":         u.id,
        "email":      u.email,
        "name":       u.name,
        "role":       u.role,
        "created_at": u.created_at.isoformat() if u.created_at else None,
    }
