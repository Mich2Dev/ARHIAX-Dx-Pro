"""
Alerts endpoint — informational log of pipeline quality events.
No approve/reject — diagnostics always complete automatically.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.auth import get_current_user
from api.db import get_db
from api.models import Diagnostic, User

router = APIRouter(prefix="/v2/reviews", tags=["reviews"])


@router.get("/pending/count")
async def pending_count(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    """Returns count of diagnostics with quality alerts (LOG_ONLY rule results)."""
    result = await db.execute(
        select(Diagnostic)
        .where(Diagnostic.status == "completed")
        .where(Diagnostic.rule_results.isnot(None))
    )
    diagnostics = result.scalars().all()
    count = sum(
        1 for d in diagnostics
        if any(
            r.get("outcome") == "LOG_ONLY"
            for r in (d.rule_results or [])
            if isinstance(r, dict)
        )
    )
    return {"count": count}


@router.get("/pending")
async def pending_reviews(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    """
    Returns diagnostics with quality alerts.
    These are informational — no action required.
    """
    result = await db.execute(
        select(Diagnostic)
        .options(selectinload(Diagnostic.stages))
        .where(Diagnostic.status == "completed")
        .where(Diagnostic.rule_results.isnot(None))
        .order_by(Diagnostic.completed_at.desc())
        .limit(50)
    )
    diagnostics = result.scalars().all()

    items = []
    for d in diagnostics:
        alerts = [
            r for r in (d.rule_results or [])
            if isinstance(r, dict) and r.get("outcome") == "LOG_ONLY"
        ]
        if not alerts:
            continue

        # Extract key metrics from stages
        metrics = _extract_metrics(d.stages or [])

        items.append({
            "id":                d.id,
            "diagnostic_id":     d.id,
            "organization_name": d.organization_name,
            "domain":            d.domain,
            "subprocess":        d.subprocess,
            "objective":         d.objective,
            "status":            d.status,
            "alerts":            alerts,
            "metrics":           metrics,
            "completed_at":      d.completed_at.isoformat() if d.completed_at else None,
            "created_at":        d.created_at.isoformat() if d.created_at else None,
        })

    return {"items": items}


def _extract_metrics(stages: list) -> dict:
    """Extract key quality metrics from completed pipeline stages."""
    metrics = {}
    for stage in stages:
        if not stage.output:
            continue
        output = stage.output.get("output", stage.output) if isinstance(stage.output, dict) else {}
        if not isinstance(output, dict):
            continue

        if stage.tool_name == "g14_qa_control":
            metrics["qa_score"] = output.get("qa_score")
        elif stage.tool_name == "g10a_scoring":
            summary = output.get("scoring_summary", {})
            metrics["overall_score"] = summary.get("overall_score")
            delta = output.get("delta_sigma", {})
            metrics["delta_sigma"] = delta.get("max_gap")
        elif stage.tool_name == "irr_calculator":
            metrics["irr_alpha"] = output.get("krippendorff_alpha")
        elif stage.tool_name == "g12_hallazgos":
            findings = output.get("findings_matrix", [])
            metrics["total_findings"] = len(findings)
            metrics["critical_findings"] = sum(1 for f in findings if f.get("priority") == "CRITICA")

    return metrics
