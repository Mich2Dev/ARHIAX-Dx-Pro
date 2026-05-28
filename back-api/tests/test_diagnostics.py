"""Tests for diagnostic submission and query endpoints."""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.models import Diagnostic, PipelineStage


SUBMIT_PAYLOAD = {
    "organization_name": "Acme Logistics S.A.S.",
    "legal_name": "Acme Logistics S.A.S.",
    "client_id": "client-acme-001",
    "domain": "Logística",
    "subprocess": "Gestión de entregas de última milla",
    "size_org": "50-200",
    "objective": "Las entregas llegan tarde en el 40% de los casos",
    "extra_context": {"nit": "900123456-1", "city": "Bogotá"},
    "requested_tools": ["g01_receptor", "g02_configurador", "g05_brechas"],
    "requested_autonomy_level": "A1",
    "processing_profile": {
        "store_raw_respondent_data": False,
        "publish_report": False,
        "issue_certificate": True,
        "retention_days": 30,
    },
}


@pytest.mark.asyncio
async def test_submit_diagnostic(client: AsyncClient, auth_headers: dict):
    resp = await client.post("/v2/diagnostics/submit", json=SUBMIT_PAYLOAD, headers=auth_headers)
    assert resp.status_code == 202
    data = resp.json()
    assert "id" in data
    assert "request_id" in data
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_submit_creates_stages(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    resp = await client.post("/v2/diagnostics/submit", json=SUBMIT_PAYLOAD, headers=auth_headers)
    assert resp.status_code == 202
    diag_id = resp.json()["id"]

    from sqlalchemy import select
    result = await db_session.execute(
        select(PipelineStage).where(PipelineStage.diagnostic_id == diag_id)
    )
    stages = result.scalars().all()
    assert len(stages) == 3  # g01, g02, g05
    tool_names = {s.tool_name for s in stages}
    assert "g01_receptor" in tool_names
    assert "g02_configurador" in tool_names


@pytest.mark.asyncio
async def test_get_diagnostic(client: AsyncClient, auth_headers: dict):
    # Create
    resp = await client.post("/v2/diagnostics/submit", json=SUBMIT_PAYLOAD, headers=auth_headers)
    diag_id = resp.json()["id"]

    # Get
    resp = await client.get(f"/v2/diagnostics/{diag_id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == diag_id
    assert data["organization_name"] == "Acme Logistics S.A.S."
    assert data["domain"] == "Logística"
    assert "stages" in data


@pytest.mark.asyncio
async def test_list_diagnostics(client: AsyncClient, auth_headers: dict):
    # Create two
    await client.post("/v2/diagnostics/submit", json=SUBMIT_PAYLOAD, headers=auth_headers)
    await client.post("/v2/diagnostics/submit", json={
        **SUBMIT_PAYLOAD, "client_id": "client-002", "organization_name": "Beta Corp"
    }, headers=auth_headers)

    resp = await client.get("/v2/diagnostics", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 2
    assert len(data["items"]) >= 2


@pytest.mark.asyncio
async def test_stats_endpoint(client: AsyncClient, auth_headers: dict):
    await client.post("/v2/diagnostics/submit", json=SUBMIT_PAYLOAD, headers=auth_headers)

    resp = await client.get("/v2/diagnostics/stats", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "pending" in data
    assert "running" in data
    assert "completed" in data
    assert data["pending"] >= 1


@pytest.mark.asyncio
async def test_get_nonexistent_diagnostic(client: AsyncClient, auth_headers: dict):
    import uuid
    fake_id = str(uuid.uuid4())  # valid UUID format but doesn't exist
    resp = await client.get(f"/v2/diagnostics/{fake_id}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_extra_context_stored(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    resp = await client.post("/v2/diagnostics/submit", json=SUBMIT_PAYLOAD, headers=auth_headers)
    diag_id = resp.json()["id"]

    from sqlalchemy import select
    result = await db_session.execute(
        select(Diagnostic).where(Diagnostic.id == diag_id)
    )
    diag = result.scalar_one()
    assert diag.extra_context is not None
    assert diag.extra_context.get("nit") == "900123456-1"


@pytest.mark.asyncio
async def test_clients_endpoint(client: AsyncClient, auth_headers: dict):
    await client.post("/v2/diagnostics/submit", json=SUBMIT_PAYLOAD, headers=auth_headers)

    resp = await client.get("/v2/diagnostics/clients", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) >= 1
    client_ids = [i["client_id"] for i in data["items"]]
    assert "client-acme-001" in client_ids


@pytest.mark.asyncio
async def test_download_report_requires_completed(client: AsyncClient, auth_headers: dict):
    resp = await client.post("/v2/diagnostics/submit", json=SUBMIT_PAYLOAD, headers=auth_headers)
    diag_id = resp.json()["id"]

    resp = await client.get(f"/v2/diagnostics/{diag_id}/download-report", headers=auth_headers)
    assert resp.status_code == 400  # not completed yet
