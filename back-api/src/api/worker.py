"""
ARHIAX Dx — Pipeline Worker
Proceso independiente que ejecuta diagnósticos desde la cola en PostgreSQL.
Correr con: python -m api.worker
"""

from __future__ import annotations

import asyncio
import logging
import signal
from datetime import datetime, timezone, timedelta

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [WORKER] %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("arhiax.worker")

POLL_INTERVAL   = 3    # seconds between queue checks
ORPHAN_TIMEOUT  = 30   # minutes — diagnostics stuck in "running" longer than this are orphans
ORPHAN_CHECK_INTERVAL = 5  # check for orphans every N poll cycles

_running = True
_poll_count = 0


def _handle_signal(sig, frame):
    global _running
    log.info("Shutdown signal received — finishing current job then stopping.")
    _running = False


signal.signal(signal.SIGINT, _handle_signal)
signal.signal(signal.SIGTERM, _handle_signal)


async def _recover_orphans(SessionLocal) -> int:
    """
    Find diagnostics stuck in 'running' for more than ORPHAN_TIMEOUT minutes
    and reset them to 'pending' so they get re-processed.
    Returns the number of orphans recovered.
    """
    from sqlalchemy import select, update
    from api.models import Diagnostic, SurveySession

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=ORPHAN_TIMEOUT)

    async with SessionLocal() as db:
        # Find running diagnostics that haven't been updated recently
        # Exclude those waiting for survey responses (awaiting_responses is intentional)
        result = await db.execute(
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
            # Don't recover if there's an open survey session — that's intentional pause
            survey_result = await db.execute(
                select(SurveySession)
                .where(SurveySession.diagnostic_id == diag.id)
                .where(SurveySession.status == "open")
            )
            has_open_survey = survey_result.scalar_one_or_none() is not None

            if has_open_survey:
                # Change status to awaiting_responses (correct state)
                diag.status = "awaiting_responses"
                log.info("Orphan %s has open survey — correcting status to awaiting_responses", diag.id)
            else:
                # Reset to pending for re-processing
                diag.status = "pending"
                log.warning(
                    "Orphan recovered: %s (%s) — stuck in 'running' since %s, resetting to pending",
                    diag.id, diag.organization_name, diag.updated_at.isoformat()
                )
                recovered += 1

        await db.commit()
        return recovered


async def main():
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from api.db import get_async_session_local, get_engine
    from api.models import Diagnostic, SurveySession
    from api.pipeline_runner import run_diagnostic, run_diagnostic_from_g10a

    get_engine()
    SessionLocal = get_async_session_local()

    log.info("ARHIAX Dx Worker started — polling every %ds, orphan timeout %dm",
             POLL_INTERVAL, ORPHAN_TIMEOUT)

    global _poll_count

    while _running:
        try:
            _poll_count += 1

            # ── Orphan recovery (every N cycles) ─────────────────────────────
            if _poll_count % ORPHAN_CHECK_INTERVAL == 0:
                recovered = await _recover_orphans(SessionLocal)
                if recovered:
                    log.info("Orphan recovery: %d diagnostic(s) reset to pending", recovered)

            async with SessionLocal() as db:
                # ── 1. Resume pipeline after survey closed ────────────────────
                resume_result = await db.execute(
                    select(Diagnostic)
                    .join(SurveySession, SurveySession.diagnostic_id == Diagnostic.id)
                    .where(Diagnostic.status == "running")
                    .where(SurveySession.status == "closed")
                    .order_by(Diagnostic.updated_at.asc())
                    .limit(1)
                    .with_for_update(skip_locked=True)
                )
                resume_diag = resume_result.scalar_one_or_none()

                if resume_diag:
                    diag_id   = resume_diag.id
                    diag_name = resume_diag.organization_name
                    await db.commit()
                    log.info("Resuming G10a+ for %s — %s", diag_id, diag_name)
                    await run_diagnostic_from_g10a(diag_id)
                    log.info("Completed G10a+ for %s", diag_id)
                    continue

                # ── 2. Pick one pending diagnostic (FIFO) ────────────────────
                result = await db.execute(
                    select(Diagnostic)
                    .where(Diagnostic.status == "pending")
                    .order_by(Diagnostic.created_at.asc())
                    .limit(1)
                    .with_for_update(skip_locked=True)
                )
                diagnostic = result.scalar_one_or_none()

                if diagnostic is None:
                    await asyncio.sleep(POLL_INTERVAL)
                    continue

                # Mark as running and capture all fields before closing session
                diagnostic.status = "running"
                await db.commit()

                diag_id    = diagnostic.id
                req_id     = diagnostic.request_id
                org_name   = diagnostic.organization_name
                legal_name = diagnostic.legal_name
                client_id  = diagnostic.client_id
                domain     = diagnostic.domain
                subprocess = diagnostic.subprocess
                size_org   = diagnostic.size_org or ""
                objective  = diagnostic.objective or ""
                autonomy   = diagnostic.autonomy_level

            # Get tool list from stages (separate session)
            async with SessionLocal() as db:
                result = await db.execute(
                    select(Diagnostic)
                    .options(selectinload(Diagnostic.stages))
                    .where(Diagnostic.id == diag_id)
                )
                d = result.scalar_one_or_none()
                tool_names = [s.tool_name for s in d.stages] if d else []

            payload = {
                "organization_name":        org_name,
                "legal_name":               legal_name,
                "client_id":                client_id,
                "domain":                   domain,
                "subprocess":               subprocess,
                "size_org":                 size_org,
                "objective":                objective,
                "requested_tools":          tool_names,
                "requested_operations":     ["modelInvoke", "toolCall", "dataAccess", "interAgentCall"],
                "requested_data_scopes":    ["organizational_context", "survey_responses", "report_outputs", "audit_log"],
                "requested_autonomy_level": autonomy,
                "processing_profile": {
                    "store_raw_respondent_data": False,
                    "publish_report":            False,
                    "issue_certificate":         True,
                    "retention_days":            30,
                },
            }

            log.info("Processing diagnostic %s — %s", diag_id, org_name)
            await run_diagnostic(diag_id, req_id, payload)
            log.info("Completed diagnostic %s", diag_id)

        except Exception as exc:
            log.error("Worker error: %s", exc, exc_info=True)
            await asyncio.sleep(POLL_INTERVAL)

    log.info("Worker stopped.")


if __name__ == "__main__":
    asyncio.run(main())
