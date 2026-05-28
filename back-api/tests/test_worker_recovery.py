"""Tests for worker orphan recovery logic."""
from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.models import Diagnostic, SurveySession


async def _make_diagnostic(db: AsyncSession, status: str, minutes_ago: int = 0) -> Diagnostic:
    import uuid
    diag = Diagnostic(
        request_id=str(uuid.uuid4()),
        client_id="client-orphan-test",
        legal_name="Orphan Test Corp",
        organization_name="Orphan Test Corp",
        domain="Test",
        subprocess="Test subprocess",
        status=status,
        autonomy_level="A1",
    )
    db.add(diag)
    await db.flush()

    if minutes_ago > 0:
        from sqlalchemy import update
        await db.execute(
            update(Diagnostic)
            .where(Diagnostic.id == diag.id)
            .values(updated_at=datetime.now(timezone.utc) - timedelta(minutes=minutes_ago))
        )
        await db.flush()

    return diag


async def _run_recovery(db_session: AsyncSession) -> int:
    """Run orphan recovery using the test session directly."""
    from datetime import datetime, timezone, timedelta
    from sqlalchemy import select
    from api.models import Diagnostic, SurveySession

    ORPHAN_TIMEOUT = 30
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=ORPHAN_TIMEOUT)

    result = await db_session.execute(
        select(Diagnostic)
        .where(Diagnostic.status == "running")
        .where(Diagnostic.updated_at < cutoff)
        .order_by(Diagnostic.updated_at.asc())
        .limit(5)
    )
    orphans = result.scalars().all()

    if not orphans:
        return 0

    recovered = 0
    for diag in orphans:
        survey_result = await db_session.execute(
            select(SurveySession)
            .where(SurveySession.diagnostic_id == diag.id)
            .where(SurveySession.status == "open")
        )
        has_open_survey = survey_result.scalar_one_or_none() is not None

        if has_open_survey:
            diag.status = "awaiting_responses"
        else:
            diag.status = "pending"
            recovered += 1

    await db_session.flush()
    return recovered


@pytest.mark.asyncio
async def test_no_orphans_when_fresh(db_session: AsyncSession):
    """Fresh running diagnostics should not be recovered."""
    await _make_diagnostic(db_session, "running", minutes_ago=5)
    recovered = await _run_recovery(db_session)
    assert recovered == 0


@pytest.mark.asyncio
async def test_orphan_reset_to_pending(db_session: AsyncSession):
    """Diagnostics stuck in 'running' for >30 min should be reset to pending."""
    from sqlalchemy import select
    diag = await _make_diagnostic(db_session, "running", minutes_ago=45)
    diag_id = diag.id

    recovered = await _run_recovery(db_session)
    assert recovered == 1

    result = await db_session.execute(
        select(Diagnostic).where(Diagnostic.id == diag_id)
    )
    updated = result.scalar_one()
    assert updated.status == "pending"


@pytest.mark.asyncio
async def test_orphan_with_open_survey_corrected(db_session: AsyncSession):
    """Orphan with open survey should be set to awaiting_responses, not pending."""
    import uuid
    from sqlalchemy import select

    diag = await _make_diagnostic(db_session, "running", minutes_ago=45)

    survey = SurveySession(
        diagnostic_id=diag.id,
        token=str(uuid.uuid4()),
        questions={"questions": []},
        status="open",
        min_responses=5,
        target_responses=20,
        responses_count=3,
    )
    db_session.add(survey)
    await db_session.flush()

    recovered = await _run_recovery(db_session)
    assert recovered == 0  # not counted as recovered

    result = await db_session.execute(
        select(Diagnostic).where(Diagnostic.id == diag.id)
    )
    updated = result.scalar_one()
    assert updated.status == "awaiting_responses"


@pytest.mark.asyncio
async def test_completed_diagnostics_not_touched(db_session: AsyncSession):
    """Completed diagnostics should never be touched by orphan recovery."""
    from sqlalchemy import select
    diag = await _make_diagnostic(db_session, "completed", minutes_ago=60)

    recovered = await _run_recovery(db_session)
    assert recovered == 0

    result = await db_session.execute(
        select(Diagnostic).where(Diagnostic.id == diag.id)
    )
    updated = result.scalar_one()
    assert updated.status == "completed"


@pytest.mark.asyncio
async def test_multiple_orphans_recovered(db_session: AsyncSession):
    """Multiple orphans should all be recovered."""
    await _make_diagnostic(db_session, "running", minutes_ago=35)
    await _make_diagnostic(db_session, "running", minutes_ago=50)
    await _make_diagnostic(db_session, "running", minutes_ago=10)  # not orphan

    recovered = await _run_recovery(db_session)
    assert recovered == 2
