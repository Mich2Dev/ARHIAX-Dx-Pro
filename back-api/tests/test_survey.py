"""Tests for public survey endpoints."""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.models import SurveySession, SurveyResponse, Diagnostic, PipelineStage


async def _create_survey_session(db_session: AsyncSession) -> tuple[str, str]:
    """Helper: create a diagnostic + open survey session. Returns (diagnostic_id, token)."""
    import uuid

    diag = Diagnostic(
        request_id=str(uuid.uuid4()),
        client_id="client-survey-test",
        legal_name="Survey Test Corp",
        organization_name="Survey Test Corp",
        domain="Manufactura",
        subprocess="Control de calidad",
        status="awaiting_responses",
        autonomy_level="A1",
    )
    db_session.add(diag)
    await db_session.flush()

    token = str(uuid.uuid4())
    session = SurveySession(
        diagnostic_id=diag.id,
        token=token,
        questions={
            "instrument_name": "Test Instrument",
            "questions": [
                {"id": "Q01", "text": "¿El proceso funciona bien?", "type": "likert_5",
                 "dimension": "DIM-01", "roles": ["Estratégico", "Táctico", "Operativo"]},
                {"id": "Q02", "text": "¿Hay problemas frecuentes?", "type": "likert_5",
                 "dimension": "DIM-01", "roles": ["Táctico", "Operativo"]},
                {"id": "QA01", "text": "Describe un problema reciente.", "type": "open_text",
                 "dimension": "DIM-01", "roles": ["Estratégico", "Táctico", "Operativo"]},
            ],
            "dimensions": [{"id": "DIM-01", "name": "Calidad del proceso"}],
        },
        branching={
            "role_tracks": {
                "Estratégico": {"question_ids": ["Q01", "QA01"], "estimated_minutes": 5},
                "Táctico": {"question_ids": ["Q01", "Q02", "QA01"], "estimated_minutes": 7},
                "Operativo": {"question_ids": ["Q01", "Q02", "QA01"], "estimated_minutes": 7},
            }
        },
        status="open",
        min_responses=2,
        target_responses=5,
        responses_count=0,
    )
    db_session.add(session)
    await db_session.flush()
    return diag.id, token


@pytest.mark.asyncio
async def test_get_survey(client: AsyncClient, db_session: AsyncSession):
    _, token = await _create_survey_session(db_session)

    resp = await client.get(f"/survey/{token}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["organization_name"] == "Survey Test Corp"
    assert data["status"] == "open"
    assert "questions" in data
    assert data["estimated_minutes"] > 0


@pytest.mark.asyncio
async def test_get_survey_not_found(client: AsyncClient):
    resp = await client.get("/survey/nonexistent-token")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_submit_response(client: AsyncClient, db_session: AsyncSession):
    _, token = await _create_survey_session(db_session)

    resp = await client.post(f"/survey/{token}/submit", json={
        "role": "Operativo",
        "answers": {"Q01": 2, "Q02": 1},
        "open_answers": {"QA01": "El proceso falla frecuentemente en el turno de la tarde."},
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["responses_count"] == 1


@pytest.mark.asyncio
async def test_submit_invalid_role(client: AsyncClient, db_session: AsyncSession):
    _, token = await _create_survey_session(db_session)

    resp = await client.post(f"/survey/{token}/submit", json={
        "role": "Gerente",  # invalid role
        "answers": {"Q01": 3},
    })
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_survey_status(client: AsyncClient, db_session: AsyncSession):
    _, token = await _create_survey_session(db_session)

    # Submit 2 responses
    for role in ["Operativo", "Táctico"]:
        await client.post(f"/survey/{token}/submit", json={
            "role": role,
            "answers": {"Q01": 3, "Q02": 2},
            "open_answers": {"QA01": f"Respuesta de {role}"},
        })

    resp = await client.get(f"/survey/{token}/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["responses_count"] == 2
    assert data["by_role"]["Operativo"] == 1
    assert data["by_role"]["Táctico"] == 1
    assert "live_scores" in data


@pytest.mark.asyncio
async def test_closed_survey_rejects_submission(client: AsyncClient, db_session: AsyncSession):
    _, token = await _create_survey_session(db_session)

    # Close the survey
    from sqlalchemy import select
    result = await db_session.execute(
        select(SurveySession).where(SurveySession.token == token)
    )
    session = result.scalar_one()
    session.status = "closed"
    await db_session.flush()

    resp = await client.post(f"/survey/{token}/submit", json={
        "role": "Operativo",
        "answers": {"Q01": 3},
    })
    assert resp.status_code == 410


@pytest.mark.asyncio
async def test_live_scores_computed(client: AsyncClient, db_session: AsyncSession):
    _, token = await _create_survey_session(db_session)

    # Submit responses with clear pattern: Estratégico high, Operativo low
    await client.post(f"/survey/{token}/submit", json={
        "role": "Estratégico",
        "answers": {"Q01": 5},
        "open_answers": {"QA01": "Todo funciona bien."},
    })
    await client.post(f"/survey/{token}/submit", json={
        "role": "Operativo",
        "answers": {"Q01": 1, "Q02": 1},
        "open_answers": {"QA01": "Hay muchos problemas."},
    })

    resp = await client.get(f"/survey/{token}/status")
    data = resp.json()
    live = data["live_scores"]

    assert live["total_responses"] == 2
    # Estratégico should score higher than Operativo
    assert live["role_scores"]["Estratégico"]["score"] > live["role_scores"]["Operativo"]["score"]
    assert live["delta_sigma"]["max_gap"] > 0
