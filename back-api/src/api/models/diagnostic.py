"""Diagnostic models - Core diagnostic workflow."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, _now, _uuid


class Diagnostic(Base):
    """
    Main diagnostic entity.
    Represents a complete organizational diagnostic workflow.
    """
    __tablename__ = "diagnostics"

    # Identity
    id: Mapped[str]               = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    request_id: Mapped[str]       = mapped_column(String, unique=True, nullable=False)
    
    # Client information
    client_id: Mapped[str]        = mapped_column(String, nullable=False)
    legal_name: Mapped[str]       = mapped_column(String, nullable=False)
    organization_name: Mapped[str]= mapped_column(String, nullable=False)
    domain: Mapped[str]           = mapped_column(String, nullable=False)
    subprocess: Mapped[str]       = mapped_column(String, nullable=False)
    objective: Mapped[str | None] = mapped_column(Text, nullable=True)
    size_org: Mapped[str | None]  = mapped_column(String, nullable=True)
    
    # Workflow status
    status: Mapped[str]           = mapped_column(String, default="pending")
    decision: Mapped[str | None]  = mapped_column(String, nullable=True)
    autonomy_level: Mapped[str]   = mapped_column(String, default="A1")
    
    # Governance
    rule_results: Mapped[list | None]  = mapped_column(JSONB, nullable=True)
    certificate: Mapped[dict | None]   = mapped_column(JSONB, nullable=True)
    execution_plan: Mapped[dict | None]= mapped_column(JSONB, nullable=True)
    human_review_required: Mapped[bool]= mapped_column(Boolean, default=False)
    
    # Timestamps
    created_at: Mapped[datetime]  = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime]  = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Extra context (added in migration 0003)
    extra_context: Mapped[dict | None]    = mapped_column(JSONB, nullable=True)
    contact_name: Mapped[str | None]      = mapped_column(String, nullable=True)
    contact_email: Mapped[str | None]     = mapped_column(String, nullable=True)
    deadline: Mapped[str | None]          = mapped_column(String, nullable=True)
    survey_participants: Mapped[str | None] = mapped_column(String, nullable=True)

    # Relationships
    stages: Mapped[list["PipelineStage"]] = relationship(
        back_populates="diagnostic", 
        order_by="PipelineStage.created_at"
    )
    reviews: Mapped[list["HumanReview"]]  = relationship(back_populates="diagnostic")


class PipelineStage(Base):
    """
    Individual stage in the diagnostic pipeline.
    Represents execution of one of the 18 AI agents.
    """
    __tablename__ = "pipeline_stages"

    id: Mapped[str]            = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    diagnostic_id: Mapped[str] = mapped_column(ForeignKey("diagnostics.id"), nullable=False)
    
    # Stage configuration
    tool_name: Mapped[str]     = mapped_column(String, nullable=False)
    phase: Mapped[str]         = mapped_column(String, nullable=False)
    status: Mapped[str]        = mapped_column(String, default="pending")
    
    # Execution metrics
    model_used: Mapped[str | None]   = mapped_column(String, nullable=True)
    tokens_used: Mapped[int | None]  = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int | None]   = mapped_column(Integer, nullable=True)
    output: Mapped[dict | None]      = mapped_column(JSONB, nullable=True)
    
    # Timestamps
    started_at: Mapped[datetime | None]   = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    # Relationships
    diagnostic: Mapped["Diagnostic"] = relationship(back_populates="stages")


class HumanReview(Base):
    """
    Human review required for certain diagnostics.
    Triggered by governance rules or quality thresholds.
    """
    __tablename__ = "human_reviews"

    id: Mapped[str]            = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    diagnostic_id: Mapped[str] = mapped_column(ForeignKey("diagnostics.id"), nullable=False)
    
    # Review details
    review_type: Mapped[str]   = mapped_column(String, nullable=False)
    status: Mapped[str]        = mapped_column(String, default="pending")
    reviewer_id: Mapped[str | None]   = mapped_column(String, nullable=True)
    reviewer_name: Mapped[str | None] = mapped_column(String, nullable=True)
    comment: Mapped[str | None]       = mapped_column(Text, nullable=True)
    
    # Timestamps
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    # Relationships
    diagnostic: Mapped["Diagnostic"] = relationship(back_populates="reviews")


class DiagnosticDocument(Base):
    """
    Optional context documents uploaded for a diagnostic.
    Can include org charts, financial reports, process docs, etc.
    """
    __tablename__ = "diagnostic_documents"

    id: Mapped[str]            = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    diagnostic_id: Mapped[str] = mapped_column(ForeignKey("diagnostics.id"), nullable=False)
    
    # File metadata
    filename: Mapped[str]      = mapped_column(String, nullable=False)       # stored filename
    original_name: Mapped[str] = mapped_column(String, nullable=False)       # original upload name
    mime_type: Mapped[str]     = mapped_column(String, nullable=False)
    size_bytes: Mapped[int]    = mapped_column(Integer, nullable=False)
    doc_type: Mapped[str]      = mapped_column(String, default="context")    # context|organigrama|financiero|proceso|otro
    
    # AI processing
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)  # text for LLM
    summary: Mapped[str | None]        = mapped_column(Text, nullable=True)  # AI summary
    
    # Metadata
    uploaded_by: Mapped[str | None]    = mapped_column(String, nullable=True)
    created_at: Mapped[datetime]       = mapped_column(DateTime(timezone=True), default=_now)


class Report(Base):
    """
    Final diagnostic report with metrics and findings.
    Generated after all 18 agents complete.
    """
    __tablename__ = "reports"

    id: Mapped[str]            = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    diagnostic_id: Mapped[str] = mapped_column(ForeignKey("diagnostics.id"), unique=True, nullable=False)
    
    # Quality metrics
    qa_score: Mapped[float | None]    = mapped_column(Float, nullable=True)
    irr_alpha: Mapped[float | None]   = mapped_column(Float, nullable=True)
    delta_sigma: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    # Report content
    narrative: Mapped[str | None]     = mapped_column(Text, nullable=True)
    findings: Mapped[dict | None]     = mapped_column(JSONB, nullable=True)
    bpmn_xml: Mapped[str | None]      = mapped_column(Text, nullable=True)
    docx_path: Mapped[str | None]     = mapped_column(String, nullable=True)
    
    # Publication
    published: Mapped[bool]           = mapped_column(Boolean, default=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


__all__ = [
    "Diagnostic",
    "PipelineStage",
    "HumanReview",
    "DiagnosticDocument",
    "Report",
]
