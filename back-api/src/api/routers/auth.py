"""Auth endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import create_access_token, get_current_user, hash_password, verify_password
from api.db import get_db
from api.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterIn(BaseModel):
    email: str
    name: str
    password: str
    role: str = "operator"


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    name: str
    role: str


@router.post("/register", response_model=TokenOut, status_code=201)
async def register(body: RegisterIn, db: AsyncSession = Depends(get_db)) -> TokenOut:
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(email=body.email, name=body.name, role=body.role, hashed_password=hash_password(body.password))
    db.add(user)
    await db.flush()
    token = create_access_token(user.id, user.role)
    return TokenOut(access_token=token, user_id=user.id, name=user.name, role=user.role)


@router.post("/login", response_model=TokenOut)
async def login(form: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)) -> TokenOut:
    result = await db.execute(select(User).where(User.email == form.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token(user.id, user.role)
    return TokenOut(access_token=token, user_id=user.id, name=user.name, role=user.role)


@router.get("/me")
async def me(user: User = Depends(get_current_user)) -> dict:
    return {"id": user.id, "email": user.email, "name": user.name, "role": user.role}
