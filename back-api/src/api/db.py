"""Async SQLAlchemy engine and session — lazy initialization."""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


_engine       = None
_session_factory = None


def _async_url() -> str:
    url = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://arhiax:arhiax@localhost:5432/arhiax_dx",
    )
    if "+asyncpg" not in url:
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_async_engine(_async_url(), echo=False, pool_pre_ping=True)
    return _engine


def get_async_session_local():
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    factory = get_async_session_local()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
