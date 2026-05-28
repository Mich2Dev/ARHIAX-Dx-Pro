"""Tests for human review endpoints."""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.models import Diagnostic, HumanReview


async def _create_review(db_session: AsyncSession, review_type: str = "publication") -> tuple[str, str]:
    """Helper: create a diagnostic + pending review. Returns (diagnostic_id, review_id)."""
    import uuid

    diag = Diagnostic(
        request_id=str(uuid.uuid4()),
        client_id="client-review-test",
        legal_name="Review Test Corp",
        organization_name="Review Test Corp",
        domain="Tecnología",
        subprocess="Desarrollo de software",
        status="awaiting_review",
        autonomy_level="A1",
        human_review_required=True,
    )
    db_session.add(diag)
    await db_session.flush()

    review = HumanReview(
        diagnostic_id=diag.id,
        review_type=review_type,
        status="pending",
    )
    db_session.add(review)
    await db_session.flush()
    return diag.id, review.id


@pytest.mark.asyncio
async def test_pending_count(client: AsyncClient, auth_headers: dict, db_session: AsyncSession):
    await _create_review(db_session)

    resp = await client.get("/v2/reviews/pending/count", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["count"] >= 1


@pytest.mark.asyncio
async def test_list_pending_reviews(client: AsyncClient, auth_headers: dict, db_session: AsyncSession):
    await _create_review(db_session, "publication")
    await _create_review(db_session, "critical_gap")

    resp = await client.get("/v2/reviews/pending", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) >= 2


@pytest.mark.asyncio
async def test_approve_review(
    client: AsyncClient, reviewer_headers: dict, db_session: AsyncSession
):
    diag_id, review_id = await _create_review(db_session)

    resp = await client.post(
        f"/v2/reviews/{review_id}/approve",
        json={"comment": "Informe revisado y aprobado."},
        headers=reviewer_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"

    # Diagnostic should be completed
    from sqlalchemy import select
    result = await db_session.execute(
        select(Diagnostic).where(Diagnostic.id == diag_id)
    )
    diag = result.scalar_one()
    assert diag.status == "completed"


@pytest.mark.asyncio
async def test_reject_review_requires_comment(
    client: AsyncClient, reviewer_headers: dict, db_session: AsyncSession
):
    _, review_id = await _create_review(db_session)

    resp = await client.post(
        f"/v2/reviews/{review_id}/reject",
        json={"comment": ""},  # empty comment
        headers=reviewer_headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_reject_review(
    client: AsyncClient, reviewer_headers: dict, db_session: AsyncSession
):
    diag_id, review_id = await _create_review(db_session)

    resp = await client.post(
        f"/v2/reviews/{review_id}/reject",
        json={"comment": "El informe necesita más evidencia en la sección de hallazgos."},
        headers=reviewer_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"

    from sqlalchemy import select
    result = await db_session.execute(
        select(Diagnostic).where(Diagnostic.id == diag_id)
    )
    diag = result.scalar_one()
    assert diag.status == "denied"


@pytest.mark.asyncio
async def test_double_decision_rejected(
    client: AsyncClient, reviewer_headers: dict, db_session: AsyncSession
):
    _, review_id = await _create_review(db_session)

    # First decision
    await client.post(
        f"/v2/reviews/{review_id}/approve",
        json={"comment": "OK"},
        headers=reviewer_headers,
    )

    # Second decision should fail
    resp = await client.post(
        f"/v2/reviews/{review_id}/approve",
        json={"comment": "OK again"},
        headers=reviewer_headers,
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_operator_cannot_approve(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    """Operators (admin in this case has admin role, but let's test with operator)."""
    _, review_id = await _create_review(db_session)

    # Create operator user and get token
    await client.post("/auth/register", json={
        "email": "operator@test.com",
        "name": "Operator",
        "password": "pass123",
        "role": "operator",
    })
    login = await client.post("/auth/login", data={
        "username": "operator@test.com",
        "password": "pass123",
    })
    op_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    resp = await client.post(
        f"/v2/reviews/{review_id}/approve",
        json={"comment": "OK"},
        headers=op_headers,
    )
    assert resp.status_code == 403
