"""Public survey endpoints — no authentication required."""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.db import get_db
from api.models import Diagnostic, SurveyResponse, SurveySession
from api.models.pro import ProCase, ProSurveySession, ProSurveyResponse

router = APIRouter(prefix="/survey", tags=["survey"])

# Roles almacenados en respuestas (español). session.roles puede traer IDs en inglés del instrumento.
SURVEY_RESPONSE_ROLES = ["Estratégico", "Táctico", "Operativo"]
ROLE_ID_TO_LABEL = {
    "executive": "Estratégico",
    "operations": "Operativo",
    "technology": "Táctico",
    "management": "Táctico",
    "estrategico": "Estratégico",
    "tactico": "Táctico",
    "operativo": "Operativo",
}


def _normalize_role_label(role: str | None) -> str | None:
    if not role:
        return None
    key = role.strip().lower()
    if role in SURVEY_RESPONSE_ROLES:
        return role
    return ROLE_ID_TO_LABEL.get(key, role)


def _roles_for_responses(session) -> list[str]:
    """Etiquetas de rol usadas en stats/auditoría — siempre alineadas con respuestas guardadas."""
    return list(SURVEY_RESPONSE_ROLES)


def _question_in_dimension(q: dict, dim: dict) -> bool:
    """Las preguntas pueden referenciar dimensión por id o por nombre."""
    qdim = q.get("dimension")
    return qdim in (dim.get("id"), dim.get("name"))


# ── Schemas ──────────────────────────────────────────────────────────────────

class SurveyInfoOut(BaseModel):
    organization_name: str
    instrument_name: str
    questions: dict
    branching: dict | None
    estimated_minutes: int
    status: str
    is_pro: bool = False
    trace_id: str | None = None
    available_roles: list[str] = ["Estratégico", "Táctico", "Operativo"]


class SurveySubmitIn(BaseModel):
    role: str  # Estratégico | Táctico | Operativo
    answers: dict[str, int | str]  # {question_id: value}
    open_answers: dict[str, str] | None = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/{token}")
async def get_survey(token: str, db: AsyncSession = Depends(get_db)) -> SurveyInfoOut:
    """
    Public endpoint — returns survey questions for a given token.
    No authentication required.
    """
    result = await db.execute(
        select(SurveySession)
        .options(selectinload(SurveySession.responses))
        .where(SurveySession.token == token)
    )
    session = result.scalar_one_or_none()
    is_pro = False

    if not session:
        # Check Pro sessions
        res_pro = await db.execute(
            select(ProSurveySession)
            .options(selectinload(ProSurveySession.responses))
            .where(ProSurveySession.token == token)
        )
        session = res_pro.scalar_one_or_none()
        is_pro = True

    if not session:
        raise HTTPException(status_code=404, detail="Survey not found")

    if session.status == "closed":
        raise HTTPException(status_code=410, detail="Survey is closed")

    org_name = "Organización"
    trace_id = None
    if is_pro:
        case = await db.get(ProCase, session.case_id)
        org_name = case.client_name if case else "Organización"
        trace_id = case.trace_id if case else None
    else:
        diagnostic = await db.get(Diagnostic, session.diagnostic_id)
        org_name = diagnostic.organization_name if diagnostic else "Organización"

    # Extract estimated minutes from branching
    estimated_minutes = 15  # default
    branch_data = session.branching if hasattr(session, "branching") else None
    if branch_data and "role_tracks" in branch_data:
        times = [
            track.get("estimated_minutes", 15)
            for track in branch_data["role_tracks"].values()
        ]
        estimated_minutes = int(sum(times) / len(times)) if times else 15

    available_roles = _roles_for_responses(session)
    if hasattr(session, "roles") and session.roles:
        # Para UI: mapear IDs del instrumento a etiquetas en español
        mapped = [_normalize_role_label(r) or r for r in session.roles]
        available_roles = list(dict.fromkeys(mapped + SURVEY_RESPONSE_ROLES))

    return SurveyInfoOut(
        organization_name=org_name,
        instrument_name=session.questions.get("instrument_name", "Encuesta Multi-Rater"),
        questions=session.questions,
        branching=branch_data,
        estimated_minutes=estimated_minutes,
        status=session.status,
        is_pro=is_pro,
        trace_id=trace_id,
        available_roles=available_roles,
    )


@router.post("/{token}/submit")
async def submit_response(
    token: str,
    body: SurveySubmitIn,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Public endpoint — submits an anonymous survey response.
    No authentication required.
    """
    # Get session
    result = await db.execute(
        select(SurveySession).where(SurveySession.token == token)
    )
    session = result.scalar_one_or_none()
    is_pro = False

    if not session:
        res_pro = await db.execute(
            select(ProSurveySession).where(ProSurveySession.token == token)
        )
        session = res_pro.scalar_one_or_none()
        is_pro = True

    if not session:
        raise HTTPException(status_code=404, detail="Survey not found")

    if session.status != "open":
        raise HTTPException(status_code=410, detail="Survey is closed")

    # Normalize Pro role IDs (english → spanish) for the standard validator
    _ROLE_MAP = ROLE_ID_TO_LABEL
    submitted_role = _normalize_role_label(body.role) or body.role

    # Validate role — accept spanish labels OR any role in the session's configured list
    valid_standard_roles = SURVEY_RESPONSE_ROLES
    session_roles = list(session.roles or []) if is_pro else []
    all_valid = valid_standard_roles + session_roles + list(_ROLE_MAP.keys())

    if submitted_role not in all_valid and body.role not in all_valid:
        raise HTTPException(status_code=400, detail=f"Invalid role: {body.role!r}")

    # Use the normalized role for storage
    body = body.model_copy(update={"role": submitted_role})


    # Generate anonymous hash
    respondent_hash = hashlib.sha256(
        f"{session.id}:{uuid.uuid4()}:{datetime.now(timezone.utc).isoformat()}".encode()
    ).hexdigest()

    # Create response using appropriate model
    if is_pro:
        survey_response = ProSurveyResponse(
            session_id=session.id,
            respondent_hash=respondent_hash,
            role=body.role,
            answers=body.answers,
            open_answers=body.open_answers or {},
            completed=True,
            submitted_at=datetime.now(timezone.utc),
        )
    else:
        survey_response = SurveyResponse(
            session_id=session.id,
            respondent_hash=respondent_hash,
            role=body.role,
            answers=body.answers,
            open_answers=body.open_answers or {},
            completed=True,
            submitted_at=datetime.now(timezone.utc),
        )
    db.add(survey_response)

    # Increment counter
    session.responses_count += 1
    await db.commit()

    # Set cookie to prevent spam (simple approach)
    response.set_cookie(
        key=f"survey_{token}",
        value="submitted",
        max_age=30 * 24 * 60 * 60,  # 30 days
        httponly=True,
        samesite="lax",
    )

    return {
        "success": True,
        "message": "Respuesta guardada exitosamente",
        "responses_count": session.responses_count,
        "target_responses": getattr(session, "target_responses", session.responses_count),
    }


@router.get("/{token}/status")
async def get_survey_status(token: str, db: AsyncSession = Depends(get_db)) -> dict:
    """
    Public endpoint — returns survey response count + live partial scores.
    Supports both Standard (SurveySession) and Pro (ProSurveySession).
    """
    result = await db.execute(
        select(SurveySession).where(SurveySession.token == token)
    )
    session = result.scalar_one_or_none()
    is_pro = False

    if not session:
        res_pro = await db.execute(
            select(ProSurveySession)
            .options(selectinload(ProSurveySession.responses))
            .where(ProSurveySession.token == token)
        )
        session = res_pro.scalar_one_or_none()
        is_pro = True

    if not session:
        raise HTTPException(status_code=404, detail="Survey not found")

    # For Pro sessions: return simplified status
    if is_pro:
        by_role: dict[str, int] = {}
        for r in (session.responses or []):
            by_role[r.role] = by_role.get(r.role, 0) + 1
        return {
            "status": session.status,
            "responses_count": session.responses_count,
            "min_responses": session.min_responses,
            "target_responses": session.min_responses,
            "by_role": by_role,
            "ready_to_run": session.responses_count >= session.min_responses,
            "is_pro": True,
            "created_at": session.created_at.isoformat() if session.created_at else None,
            "closed_at": session.closed_at.isoformat() if session.closed_at else None,
        }

    # Standard: full live scoring
    responses_result = await db.execute(
        select(SurveyResponse)
        .where(SurveyResponse.session_id == session.id)
    )
    responses = responses_result.scalars().all()

    by_role = {}
    for r in responses:
        by_role[r.role] = by_role.get(r.role, 0) + 1

    # ── Compute live partial scores ───────────────────────────────────────────
    live_scores = _compute_live_scores(responses, session.questions)

    return {
        "status": session.status,
        "responses_count": session.responses_count,
        "min_responses": session.min_responses,
        "target_responses": session.target_responses,
        "by_role": by_role,
        "live_scores": live_scores,
        "is_pro": False,
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "closed_at": session.closed_at.isoformat() if session.closed_at else None,
    }


def _compute_live_scores(responses: list, questions_data: dict) -> dict:
    if not responses:
        return {}

    questions = []
    if isinstance(questions_data, dict):
        questions = questions_data.get("questions", [])

    q_to_dim: dict[str, str] = {}
    q_reverse: dict[str, bool] = {}
    dim_names: dict[str, str] = {}
    for q in questions:
        qid = q.get("id", "")
        q_to_dim[qid] = q.get("dimension", "DIM-01")
        q_reverse[qid] = bool(q.get("reverse_scored", False))
    for d in (questions_data.get("dimensions", []) if isinstance(questions_data, dict) else []):
        dim_names[d.get("id", "")] = d.get("name", d.get("id", ""))

    role_dim_scores: dict[str, dict[str, list]] = {}
    for resp in responses:
        role = resp.role
        if role not in role_dim_scores:
            role_dim_scores[role] = {}
        for qid, val in (resp.answers or {}).items():
            if not isinstance(val, (int, float)):
                continue
            # Apply reverse-score correction: corrected = 6 - raw (Likert 1-5)
            corrected = (6 - int(val)) if q_reverse.get(qid, False) else int(val)
            dim = q_to_dim.get(qid, "DIM-01")
            role_dim_scores[role].setdefault(dim, []).append((corrected - 1) / 4 * 100)

    if not role_dim_scores:
        return {}

    role_scores: dict[str, float] = {}
    role_dim_avgs: dict[str, dict[str, float]] = {}
    role_n: dict[str, int] = {}

    for role, dims in role_dim_scores.items():
        dim_avgs: dict[str, float] = {}
        all_vals: list[float] = []
        for dim, vals in dims.items():
            dim_avgs[dim] = round(sum(vals) / len(vals), 1)
            all_vals.extend(vals)
        role_dim_avgs[role] = dim_avgs
        role_scores[role] = round(sum(all_vals) / len(all_vals), 1) if all_vals else 0
        role_n[role] = sum(1 for r in responses if r.role == role)

    all_dims = sorted({d for dims in role_dim_avgs.values() for d in dims})
    dimension_scores = []
    for dim in all_dims:
        vals = [role_dim_avgs[r][dim] for r in role_dim_avgs if dim in role_dim_avgs[r]]
        avg = round(sum(vals) / len(vals), 1) if vals else 0
        dimension_scores.append({
            "dimension": dim,
            "name": dim_names.get(dim, dim),
            "score": avg,
            "benchmark": 75,
            "gap": round(avg - 75, 1),
        })

    delta_sigma = 0.0
    gap_pairs = []
    role_list = list(role_scores.keys())
    for i in range(len(role_list)):
        for j in range(i + 1, len(role_list)):
            r1, r2 = role_list[i], role_list[j]
            delta = abs(role_scores[r1] - role_scores[r2]) / 20
            delta_sigma = max(delta_sigma, delta)
            gap_pairs.append({
                "roles": f"{r1} vs {r2}",
                "delta": round(delta, 2),
                "critical": delta > 2.0,
            })

    overall = round(sum(role_scores.values()) / len(role_scores), 1) if role_scores else 0

    return {
        "overall_score": overall,
        "role_scores": {
            role: {"score": score, "n_responses": role_n.get(role, 0)}
            for role, score in role_scores.items()
        },
        "dimension_scores": dimension_scores,
        "delta_sigma": {"max_gap": round(delta_sigma, 2), "gap_pairs": gap_pairs},
        "total_responses": len(responses),
        "is_partial": True,
    }


# ── Admin audit endpoint ──────────────────────────────────────────────────────

@router.get("/{token}/audit")
async def get_survey_audit(
    token: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Admin endpoint — returns full instrument audit:
    questions with rationale, all responses by role, and per-question scores.
    No authentication required (token is the access control).
    """
    # Intenta buscar en Standard (por token o por ID)
    result = await db.execute(
        select(SurveySession).where(
            (SurveySession.token == token) | (SurveySession.id == token)
        )
    )
    session = result.scalar_one_or_none()
    is_pro = False

    # Si no está en Standard, busca en Pro (por token o por ID)
    if not session:
        res_pro = await db.execute(
            select(ProSurveySession).where(
                (ProSurveySession.token == token) | (ProSurveySession.id == token)
            )
        )
        session = res_pro.scalar_one_or_none()
        is_pro = True

    if not session:
        raise HTTPException(status_code=404, detail=f"Survey session not found for token/id: {token}")

    if is_pro:
        diagnostic = await db.get(ProCase, session.case_id)
        # Get all responses
        resp_result = await db.execute(
            select(ProSurveyResponse).where(ProSurveyResponse.session_id == session.id)
        )
        responses = resp_result.scalars().all()
    else:
        diagnostic = await db.get(Diagnostic, session.diagnostic_id)
        # Get all responses
        resp_result = await db.execute(
            select(SurveyResponse).where(SurveyResponse.session_id == session.id)
        )
        responses = resp_result.scalars().all()

    questions_data = session.questions or {}
    questions = questions_data.get("questions", [])
    dimensions = questions_data.get("dimensions", [])

    # Build question lookup
    q_map = {q["id"]: q for q in questions}
    q_reverse = {q["id"]: q.get("reverse_scored", False) for q in questions}

    # Per-question stats: raw scores and corrected scores by role
    available_roles = _roles_for_responses(session)

    q_stats: dict = {}
    for q in questions:
        qid = q["id"]
        if q.get("type") != "likert_5":
            continue
        q_stats[qid] = {
            "raw_by_role":       {role: [] for role in available_roles},
            "corrected_by_role": {role: [] for role in available_roles},
        }

    open_answers_by_role: dict = {role: [] for role in available_roles}

    for resp in responses:
        role = _normalize_role_label(resp.role)
        if not role:
            continue
        for qid, val in (resp.answers or {}).items():
            if qid not in q_stats or not isinstance(val, (int, float)):
                continue
            raw = int(val)
            corrected = (6 - raw) if q_reverse.get(qid, False) else raw
            q_stats[qid]["raw_by_role"].setdefault(role, []).append(raw)
            q_stats[qid]["corrected_by_role"].setdefault(role, []).append(corrected)

        for qid, text in (resp.open_answers or {}).items():
            if text:
                open_answers_by_role.setdefault(role, []).append({"question_id": qid, "text": text})

    # Build per-question summary
    questions_audit = []
    for q in questions:
        qid = q["id"]
        is_likert = q.get("type") == "likert_5"
        entry = {
            "id":              qid,
            "dimension":       q.get("dimension"),
            "text":            q.get("text"),
            "type":            q.get("type"),
            "roles":           q.get("roles", []),
            "reverse_scored":  q.get("reverse_scored", False),
            "hypothesis_tested": q.get("hypothesis_tested"),
            "rationale":       q.get("rationale"),
            "expected_direction": q.get("expected_direction"),
        }
        if is_likert and qid in q_stats:
            stats = q_stats[qid]
            entry["response_stats"] = {}
            for role in available_roles:
                raw_vals = stats["raw_by_role"].get(role, [])
                cor_vals = stats["corrected_by_role"].get(role, [])
                if raw_vals:
                    entry["response_stats"][role] = {
                        "n":                len(raw_vals),
                        "raw_avg":          round(sum(raw_vals) / len(raw_vals), 2),
                        "corrected_avg":    round(sum(cor_vals) / len(cor_vals), 2),
                        "corrected_score":  round((sum(cor_vals) / len(cor_vals) - 1) / 4 * 100, 1),
                        "distribution":     {str(i): raw_vals.count(i) for i in range(1, 6)},
                    }
        questions_audit.append(entry)

    # Dimension summary
    dim_audit = []
    for dim in dimensions:
        dim_id = dim.get("id")
        dim_questions = [
            q for q in questions
            if _question_in_dimension(q, dim) and q.get("type") == "likert_5"
        ]
        dim_entry = {
            "id":                   dim_id,
            "name":                 dim.get("name"),
            "hypothesis_mapped":    dim.get("hypothesis_mapped"),
            "hypothesis_text":      dim.get("hypothesis_text"),
            "expected_pattern_if_true":  dim.get("expected_pattern_if_true"),
            "expected_pattern_if_false": dim.get("expected_pattern_if_false"),
            "n_questions":          len(dim_questions),
            "reverse_scored_count": sum(1 for q in dim_questions if q.get("reverse_scored")),
        }
        # Compute corrected dimension score per role
        role_scores = {}
        for role in available_roles:
            all_corrected = []
            for q in dim_questions:
                qid = q["id"]
                if qid in q_stats:
                    all_corrected.extend(q_stats[qid]["corrected_by_role"].get(role, []))
            if all_corrected:
                avg = sum(all_corrected) / len(all_corrected)
                role_scores[role] = round((avg - 1) / 4 * 100, 1)
        dim_entry["role_scores"] = role_scores
        dim_audit.append(dim_entry)

    return {
        "diagnostic_id":    str(session.case_id) if is_pro else str(session.diagnostic_id),
        "organization":     (diagnostic.client_name if is_pro else diagnostic.organization_name) if diagnostic else None,
        "subprocess":       (diagnostic.domain if is_pro else diagnostic.subprocess) if diagnostic else None,
        "instrument_name":  questions_data.get("instrument_name"),
        "methodology":      questions_data.get("methodology"),
        "survey_status":    session.status,
        "total_responses":  session.responses_count,
        "responses_by_role": {
            role: sum(1 for r in responses if _normalize_role_label(r.role) == role)
            for role in SURVEY_RESPONSE_ROLES
        },
        "reverse_scored_items": [q["id"] for q in questions if q.get("reverse_scored")],
        "correction_formula":   "corrected = 6 - raw (Likert 1-5)",
        "dimensions":           dim_audit,
        "questions":            questions_audit,
        "open_answers_by_role": open_answers_by_role,
    }
