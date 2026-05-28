"""Tests for authentication endpoints."""
from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_and_login(client: AsyncClient):
    # Register
    resp = await client.post("/auth/register", json={
        "email": "new@test.com",
        "name": "New User",
        "password": "password123",
        "role": "operator",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["role"] == "operator"
    assert "access_token" in data

    # Login
    resp = await client.post("/auth/login", data={
        "username": "new@test.com",
        "password": "password123",
    })
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, admin_user):
    resp = await client.post("/auth/login", data={
        "username": "admin@test.com",
        "password": "wrongpassword",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_endpoint(client: AsyncClient, auth_headers: dict, admin_user):
    resp = await client.get("/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == admin_user.email
    assert data["role"] == "admin"


@pytest.mark.asyncio
async def test_protected_endpoint_without_token(client: AsyncClient):
    resp = await client.get("/v2/diagnostics")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_duplicate_email_rejected(client: AsyncClient, admin_user):
    resp = await client.post("/auth/register", json={
        "email": admin_user.email,  # same email as existing user
        "name": "Duplicate",
        "password": "password123",
    })
    assert resp.status_code == 400
