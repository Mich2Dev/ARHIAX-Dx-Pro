"""Diagnostic submission and query endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
import io
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.auth import get_current_user
from api.config import settings
from api.db import get_db
from api.models import Diagnostic, HumanReview, PipelineStage, User, SurveySession, SurveyResponse
from api.tasks import run_pipeline

router = APIRouter(prefix="/v2/diagnostics", tags=["diagnostics"])


# ── Schemas ──────────────────────────────────────────────────────────────────

class ProcessingProfileIn(BaseModel):
    store_raw_respondent_data: bool = False
    publish_report: bool = False
    issue_certificate: bool = True
    retention_days: int = 30


class SubmitIn(BaseModel):
    organization_name: str
    legal_name: str
    client_id: str
    domain: str
    subprocess: str
    size_org: str
    objective: str = ""
    extra_context: dict | None = None   # nit, city, contact_*, years_operating, etc.
    requested_tools: list[str]
    requested_operations: list[str] = ["modelInvoke", "toolCall", "dataAccess", "interAgentCall"]
    requested_data_scopes: list[str] = ["organizational_context", "survey_responses", "report_outputs", "audit_log"]
    requested_autonomy_level: str = "A1"
    processing_profile: ProcessingProfileIn = ProcessingProfileIn()


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/submit", status_code=202)
async def submit(
    body: SubmitIn,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    request_id = str(uuid.uuid4())

    diagnostic = Diagnostic(
        request_id=request_id,
        client_id=body.client_id,
        legal_name=body.legal_name,
        organization_name=body.organization_name,
        domain=body.domain,
        subprocess=body.subprocess,
        objective=body.objective,
        size_org=body.size_org,
        autonomy_level=body.requested_autonomy_level,
        extra_context=body.extra_context or {},
        status="pending",
    )
    db.add(diagnostic)
    await db.flush()

    # Create pending stages for each requested tool
    for tool_name in body.requested_tools:
        db.add(PipelineStage(diagnostic_id=diagnostic.id, tool_name=tool_name, phase="unknown"))
    await db.flush()

    # Launch pipeline (Celery if available, thread fallback otherwise)
    run_pipeline(
        diagnostic_id=diagnostic.id,
        request_id=request_id,
        payload=body.model_dump(),
    )

    return {"id": diagnostic.id, "request_id": request_id, "status": "pending"}


@router.get("")
async def list_diagnostics(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 50,
    client_id: str | None = None,
    status: str | None = None,
) -> dict:
    total_q = await db.execute(select(func.count()).select_from(Diagnostic))
    total = total_q.scalar_one()

    q = select(Diagnostic).order_by(Diagnostic.created_at.desc()).offset(skip).limit(limit)
    if client_id:
        q = q.where(Diagnostic.client_id == client_id)
    if status:
        q = q.where(Diagnostic.status == status)

    result = await db.execute(q)
    items = result.scalars().all()
    return {
        "total": total,
        "items": [_summary(d) for d in items],
    }


@router.get("/clients")
async def list_clients(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    """Returns unique clients with their diagnostic counts."""
    result = await db.execute(
        select(
            Diagnostic.client_id,
            Diagnostic.legal_name,
            Diagnostic.organization_name,
            func.count(Diagnostic.id).label("total"),
            func.max(Diagnostic.created_at).label("last_diagnostic"),
        )
        .group_by(Diagnostic.client_id, Diagnostic.legal_name, Diagnostic.organization_name)
        .order_by(func.max(Diagnostic.created_at).desc())
    )
    rows = result.all()
    return {
        "items": [
            {
                "client_id":          r.client_id,
                "legal_name":         r.legal_name,
                "organization_name":  r.organization_name,
                "total_diagnostics":  r.total,
                "last_diagnostic":    r.last_diagnostic.isoformat() if r.last_diagnostic else None,
            }
            for r in rows
        ]
    }


@router.get("/clients/{client_id}/prefill")
async def get_client_prefill(
    client_id: str,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    """
    Returns the latest diagnostic's data for a client so the wizard can pre-fill.
    Pulls organization fields + extra_context (nit, city, contact, etc.).
    """
    result = await db.execute(
        select(Diagnostic)
        .where(Diagnostic.client_id == client_id)
        .order_by(Diagnostic.created_at.desc())
        .limit(1)
    )
    d = result.scalar_one_or_none()
    if not d:
        raise HTTPException(status_code=404, detail="Client not found")

    extra = d.extra_context or {}
    return {
        "organization_name": d.organization_name,
        "legal_name":        d.legal_name,
        "client_id":         d.client_id,
        "domain":            d.domain,
        "size_org":          d.size_org or "",
        "nit":               extra.get("nit", ""),
        "sector":            extra.get("sector", d.domain),
        "city":              extra.get("city", ""),
        "country":           extra.get("country", "Colombia"),
        "years_operating":   extra.get("years_operating", ""),
        "contact_name":      extra.get("contact_name", ""),
        "contact_role":      extra.get("contact_role", ""),
        "contact_email":     extra.get("contact_email", ""),
        "contact_phone":     extra.get("contact_phone", ""),
        "confidentiality":   extra.get("confidentiality", "Confidencial - Uso Estratégico"),
    }


@router.get("/stats")
async def stats(db: AsyncSession = Depends(get_db), _user: User = Depends(get_current_user)) -> dict:
    result = await db.execute(select(Diagnostic.status, func.count()).group_by(Diagnostic.status))
    counts = {row[0]: row[1] for row in result.all()}
    return {
        "running":         counts.get("running", 0),
        "awaiting_review": counts.get("awaiting_review", 0),
        "completed":       counts.get("completed", 0),
        "denied":          counts.get("denied", 0),
        "pending":         counts.get("pending", 0),
        "failed":          counts.get("failed", 0),
    }


@router.get("/{diagnostic_id}/download-report")
async def download_report(
    diagnostic_id: str,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> StreamingResponse:
    result = await db.execute(
        select(Diagnostic)
        .options(selectinload(Diagnostic.stages))
        .where(Diagnostic.id == diagnostic_id)
    )
    d = result.scalar_one_or_none()
    if not d:
        raise HTTPException(status_code=404, detail="Diagnostic not found")
    if d.status not in ("completed", "awaiting_review"):
        raise HTTPException(status_code=400, detail="Diagnostic not completed yet")

    from api.pipeline.docx_builder import build_docx
    docx_bytes = build_docx(d, d.stages or [])
    filename = f"diagnostico_{d.organization_name.replace(' ', '_')}.docx"

    return StreamingResponse(
        io.BytesIO(docx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{diagnostic_id}/download-pdf")
async def download_pdf(
    diagnostic_id: str,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> StreamingResponse:
    result = await db.execute(
        select(Diagnostic)
        .options(selectinload(Diagnostic.stages))
        .where(Diagnostic.id == diagnostic_id)
    )
    d = result.scalar_one_or_none()
    if not d:
        raise HTTPException(status_code=404, detail="Diagnostic not found")
    if d.status not in ("completed", "awaiting_review"):
        raise HTTPException(status_code=400, detail="Diagnostic not completed yet")

    from api.pipeline.pdf_builder import build_pdf
    pdf_bytes = build_pdf(d, d.stages or [])
    filename = f"diagnostico_{d.organization_name.replace(' ', '_')}.pdf"

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/{diagnostic_id}/survey/close")
async def close_survey_and_continue(
    diagnostic_id: str,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    """
    Close the survey session and continue pipeline execution from G10a.
    Requires authentication (consultant only).
    """
    # Get survey session
    result = await db.execute(
        select(SurveySession).where(SurveySession.diagnostic_id == diagnostic_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Survey session not found")
    
    if session.status != "open":
        raise HTTPException(status_code=400, detail="Survey is not open")
    
    # Close survey
    session.status = "closed"
    session.closed_at = datetime.now(timezone.utc)
    
    # Update diagnostic status back to running
    diagnostic = await db.get(Diagnostic, diagnostic_id)
    if diagnostic:
        diagnostic.status = "running"
    
    await db.commit()
    
    # Trigger pipeline continuation (from G10a onwards)
    from api.tasks import continue_pipeline_from_g10a
    continue_pipeline_from_g10a(diagnostic_id, session.id)
    
    return {
        "success": True,
        "message": "Survey closed and pipeline resumed",
        "responses_count": session.responses_count,
    }


@router.get("/{diagnostic_id}/survey/status")
async def get_diagnostic_survey_status(
    diagnostic_id: str,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    """Get survey status for a diagnostic (authenticated endpoint)."""
    result = await db.execute(
        select(SurveySession).where(SurveySession.diagnostic_id == diagnostic_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        return {"exists": False}
    
    # Count responses by role
    responses_result = await db.execute(
        select(SurveyResponse.role, func.count())
        .where(SurveyResponse.session_id == session.id)
        .group_by(SurveyResponse.role)
    )
    by_role = {role: count for role, count in responses_result.all()}
    
    return {
        "exists": True,
        "token": session.token,
        "status": session.status,
        "responses_count": session.responses_count,
        "min_responses": session.min_responses,
        "target_responses": session.target_responses,
        "by_role": by_role,
        "url": f"{settings.app_url}/survey/{session.token}",
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "closed_at": session.closed_at.isoformat() if session.closed_at else None,
    }


@router.get("/{diagnostic_id}")
async def get_diagnostic(
    diagnostic_id: str,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    result = await db.execute(
        select(Diagnostic)
        .options(selectinload(Diagnostic.stages))
        .where(Diagnostic.id == diagnostic_id)
    )
    d = result.scalar_one_or_none()
    if not d:
        raise HTTPException(status_code=404, detail="Diagnostic not found")
    
    # Include survey token if exists
    detail = _detail(d)
    
    # Get survey session
    from api.models import SurveySession
    survey_result = await db.execute(
        select(SurveySession).where(SurveySession.diagnostic_id == diagnostic_id)
    )
    survey = survey_result.scalar_one_or_none()
    if survey:
        detail["survey"] = {
            "token": survey.token,
            "status": survey.status,
            "responses_count": survey.responses_count,
            "min_responses": survey.min_responses,
            "target_responses": survey.target_responses,
        }
    
    return detail



# ── Helpers ───────────────────────────────────────────────────────────────────

def _summary(d: Diagnostic) -> dict:
    return {
        "id": d.id,
        "request_id": d.request_id,
        "organization_name": d.organization_name,
        "domain": d.domain,
        "status": d.status,
        "decision": d.decision,
        "created_at": d.created_at.isoformat() if d.created_at else None,
    }


def _detail(d: Diagnostic) -> dict:
    return {
        **_summary(d),
        "subprocess": d.subprocess,
        "objective": d.objective,
        "size_org": d.size_org,
        "autonomy_level": d.autonomy_level,
        "rule_results": d.rule_results,
        "certificate": d.certificate,
        "execution_plan": d.execution_plan,
        "human_review_required": d.human_review_required,
        "stages": [_stage(s) for s in (d.stages or [])],
        "updated_at": d.updated_at.isoformat() if d.updated_at else None,
        "completed_at": d.completed_at.isoformat() if d.completed_at else None,
    }


def _stage(s: PipelineStage) -> dict:
    return {
        "id": s.id,
        "tool_name": s.tool_name,
        "phase": s.phase,
        "status": s.status,
        "model_used": s.model_used,
        "tokens_used": s.tokens_used,
        "latency_ms": s.latency_ms,
        "started_at": s.started_at.isoformat() if s.started_at else None,
        "completed_at": s.completed_at.isoformat() if s.completed_at else None,
    }
