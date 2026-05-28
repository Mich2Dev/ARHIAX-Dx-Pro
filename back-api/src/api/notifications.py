"""
Notification service — fires webhooks on key pipeline events.
Non-blocking: failures are logged but never raise.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

log = logging.getLogger("arhiax.notifications")

# Event types
EVT_COMPLETED       = "diagnostic.completed"
EVT_REVIEW_NEEDED   = "diagnostic.awaiting_review"
EVT_SURVEY_READY    = "diagnostic.survey_ready"
EVT_DENIED          = "diagnostic.denied"
EVT_QA_REJECTED     = "diagnostic.qa_rejected"


async def notify(event: str, payload: dict) -> None:
    """Fire webhook if configured. Never raises."""
    from api.config import settings

    url = settings.hic_webhook_url
    if not url:
        return

    import httpx
    body = {
        "event":      event,
        "timestamp":  datetime.now(timezone.utc).isoformat(),
        "app_url":    settings.app_url,
        **payload,
    }
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(url, json=body)
            log.info("Webhook %s → %s %s", event, resp.status_code, url)
    except Exception as exc:
        log.warning("Webhook failed (%s): %s", event, exc)


# ── Convenience helpers ───────────────────────────────────────────────────────

async def notify_completed(diagnostic_id: str, org_name: str, qa_score: int | None = None) -> None:
    await notify(EVT_COMPLETED, {
        "diagnostic_id":   diagnostic_id,
        "organization":    org_name,
        "qa_score":        qa_score,
        "report_url":      f"{{app_url}}/dashboard/diagnostics/{diagnostic_id}",
    })


async def notify_review_needed(diagnostic_id: str, org_name: str, review_type: str) -> None:
    await notify(EVT_REVIEW_NEEDED, {
        "diagnostic_id": diagnostic_id,
        "organization":  org_name,
        "review_type":   review_type,
        "review_url":    f"{{app_url}}/dashboard/reviews",
    })


async def notify_survey_ready(diagnostic_id: str, org_name: str, survey_token: str, app_url: str) -> None:
    await notify(EVT_SURVEY_READY, {
        "diagnostic_id": diagnostic_id,
        "organization":  org_name,
        "survey_url":    f"{app_url}/survey/{survey_token}",
    })


async def notify_denied(diagnostic_id: str, org_name: str, reasons: list[str]) -> None:
    await notify(EVT_DENIED, {
        "diagnostic_id": diagnostic_id,
        "organization":  org_name,
        "reasons":       reasons,
    })
