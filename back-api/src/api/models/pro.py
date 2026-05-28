"""
Modelos Pro — sistema de diagnóstico gobernado independiente.
No comparte datos con Dx Standard.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, _now, _uuid


class ProCase(Base):
    """
    Caso diagnóstico Pro. Unidad central del sistema gobernado.
    Ciclo completo: intake → fusión → reporte → exportación → aprobación.
    """
    __tablename__ = "pro_cases"

    id: Mapped[str]               = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    case_id: Mapped[str]          = mapped_column(String, unique=True, nullable=False)  # case-xxx legible
    engagement_id: Mapped[str]    = mapped_column(String, nullable=False)

    # Cliente
    client_name: Mapped[str]      = mapped_column(String, nullable=False)
    domain: Mapped[str]           = mapped_column(String, nullable=False)

    # Estado del ciclo
    case_status: Mapped[str]      = mapped_column(String, default="draft")
    # draft | designing | survey_open | running | review_pending | approved | published | rejected
    approval_status: Mapped[str]  = mapped_column(String, default="draft")
    # draft | pending_review | approved | rejected | published

    # Gobernanza
    trace_id: Mapped[str | None]  = mapped_column(String, nullable=True)
    pmel_outcome: Mapped[str | None] = mapped_column(String, nullable=True)  # PERMIT | DENY | SUSPEND…
    consent: Mapped[dict | None]  = mapped_column(JSONB, nullable=True)

    # Payload de entrada (lo que envió el consultor)
    input_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Resultados de cada etapa
    fusion_result: Mapped[dict | None]   = mapped_column(JSONB, nullable=True)
    report_result: Mapped[dict | None]   = mapped_column(JSONB, nullable=True)
    render_result: Mapped[dict | None]   = mapped_column(JSONB, nullable=True)
    export_result: Mapped[dict | None]   = mapped_column(JSONB, nullable=True)

    # Stages del pipeline Gemini (igual que Standard)
    pipeline_stages: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    # [{"tool_name": "g10a_scoring", "status": "completed", "model_used": "gemini-2.5-flash", "tokens_used": 1234, "latency_ms": 2100, "output": {...}}]

    # Entregables generados
    deliverables: Mapped[list | None]    = mapped_column(JSONB, nullable=True)
    # [{"target": "markdown", "content": "...", "size_bytes": 0}]

    # Revisión humana (HIL)
    reviewer_name: Mapped[str | None]    = mapped_column(String, nullable=True)
    reviewer_role: Mapped[str | None]    = mapped_column(String, nullable=True)
    review_comment: Mapped[str | None]   = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at: Mapped[datetime]  = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime]  = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relaciones
    evidence_entries: Mapped[list["ProEvidence"]] = relationship(
        back_populates="case", order_by="ProEvidence.created_at"
    )
    survey_sessions: Mapped[list["ProSurveySession"]] = relationship(
        back_populates="case"
    )


class ProEvidence(Base):
    """
    Entrada de evidencia gobernada para un caso Pro.
    Append-only — nunca se modifica, solo se agrega.
    """
    __tablename__ = "pro_evidence"

    id: Mapped[str]            = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    case_id: Mapped[str | None] = mapped_column(ForeignKey("pro_cases.id"), nullable=True)
    trace_id: Mapped[str]      = mapped_column(String, nullable=False)

    event_type: Mapped[str]    = mapped_column(String, nullable=False)
    # policy_decision | pmel_step_aggregate | diagnostic_evaluation | agent_artifact | approval_action

    outcome: Mapped[str | None]   = mapped_column(String, nullable=True)
    package: Mapped[str | None]   = mapped_column(String, nullable=True)
    agent: Mapped[str | None]     = mapped_column(String, nullable=True)
    payload: Mapped[dict | None]  = mapped_column(JSONB, nullable=True)

    # HMAC simple para integridad
    hmac_hash: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    # Relaciones
    case: Mapped["ProCase | None"] = relationship(back_populates="evidence_entries")


class ProSurveySession(Base):
    """
    Sesión de encuesta multi-rater para un caso Pro.
    Independiente del sistema Standard.
    """
    __tablename__ = "pro_survey_sessions"

    id: Mapped[str]            = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    case_id: Mapped[str]       = mapped_column(ForeignKey("pro_cases.id"), nullable=False)
    token: Mapped[str]         = mapped_column(String, unique=True, nullable=False)

    # Configuración
    roles: Mapped[list | None]       = mapped_column(JSONB, nullable=True)
    dimensions: Mapped[list | None]  = mapped_column(JSONB, nullable=True)
    questions: Mapped[dict | None]   = mapped_column(JSONB, nullable=True)
    branching: Mapped[dict | None]   = mapped_column(JSONB, nullable=True)

    # Estado: designing → open → closed
    status: Mapped[str]              = mapped_column(String, default="designing")
    responses_count: Mapped[int]     = mapped_column(Integer, default=0)
    min_responses: Mapped[int]       = mapped_column(Integer, default=3)

    created_at: Mapped[datetime]     = mapped_column(DateTime(timezone=True), default=_now)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relaciones
    case: Mapped["ProCase"] = relationship(back_populates="survey_sessions")
    responses: Mapped[list["ProSurveyResponse"]] = relationship(back_populates="session")


class ProSurveyResponse(Base):
    """
    Respuesta individual anónima a una encuesta Pro.
    """
    __tablename__ = "pro_survey_responses"

    id: Mapped[str]              = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    session_id: Mapped[str]      = mapped_column(ForeignKey("pro_survey_sessions.id"), nullable=False)

    respondent_hash: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str]            = mapped_column(String, nullable=False)
    dimension: Mapped[str | None] = mapped_column(String, nullable=True)
    answers: Mapped[dict]        = mapped_column(JSONB, nullable=False)
    open_answers: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    completed: Mapped[bool]      = mapped_column(Boolean, default=True)

    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    # Relaciones
    session: Mapped["ProSurveySession"] = relationship(back_populates="responses")


__all__ = ["ProCase", "ProEvidence", "ProSurveySession", "ProSurveyResponse"]
