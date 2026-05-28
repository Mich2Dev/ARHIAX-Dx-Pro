"""
Test fixtures for ARHIAX Dx Pipeline API.
Uses the real PostgreSQL test database — requires docker-compose to be running.
"""
from __future__ import annotations

import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.db import Base, get_db
from api.main import app
from api.auth import hash_password
from api.models import User

# Use real PostgreSQL — same as dev, but isolated test schema via unique request_ids
TEST_DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://arhiax:arhiax@postgres:5432/arhiax_dx",
)


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    # Tables already exist via alembic — just use them
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine):
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as session:
        yield session
        # Rollback after each test to keep DB clean
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession):
    """HTTP test client with DB override."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def admin_user(db_session: AsyncSession) -> User:
    import uuid
    user = User(
        id=str(uuid.uuid4()),
        email=f"admin-{uuid.uuid4().hex[:8]}@test.com",
        name="Test Admin",
        role="admin",
        hashed_password=hash_password("testpass123"),
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture(scope="function")
async def reviewer_user(db_session: AsyncSession) -> User:
    import uuid
    user = User(
        id=str(uuid.uuid4()),
        email=f"reviewer-{uuid.uuid4().hex[:8]}@test.com",
        name="Test Reviewer",
        role="reviewer",
        hashed_password=hash_password("testpass123"),
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture(scope="function")
async def auth_headers(client: AsyncClient, admin_user: User) -> dict:
    """Returns Authorization headers for admin user."""
    resp = await client.post(
        "/auth/login",
        data={"username": admin_user.email, "password": "testpass123"},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture(scope="function")
async def reviewer_headers(client: AsyncClient, reviewer_user: User) -> dict:
    resp = await client.post(
        "/auth/login",
        data={"username": reviewer_user.email, "password": "testpass123"},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
