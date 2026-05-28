"""Pro tables — sistema diagnóstico gobernado independiente.

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-02
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── pro_cases ─────────────────────────────────────────────────────────────
    op.create_table(
        "pro_cases",
        sa.Column("id",              postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("case_id",         sa.String(),  nullable=False, unique=True),
        sa.Column("engagement_id",   sa.String(),  nullable=False),
        sa.Column("client_name",     sa.String(),  nullable=False),
        sa.Column("domain",          sa.String(),  nullable=False),
        sa.Column("case_status",     sa.String(),  nullable=False, server_default="draft"),
        sa.Column("approval_status", sa.String(),  nullable=False, server_default="draft"),
        sa.Column("trace_id",        sa.String(),  nullable=True),
        sa.Column("pmel_outcome",    sa.String(),  nullable=True),
        sa.Column("consent",         postgresql.JSONB(), nullable=True),
        sa.Column("input_payload",   postgresql.JSONB(), nullable=True),
        sa.Column("fusion_result",   postgresql.JSONB(), nullable=True),
        sa.Column("report_result",   postgresql.JSONB(), nullable=True),
        sa.Column("render_result",   postgresql.JSONB(), nullable=True),
        sa.Column("export_result",   postgresql.JSONB(), nullable=True),
        sa.Column("deliverables",    postgresql.JSONB(), nullable=True),
        sa.Column("reviewer_name",   sa.String(),  nullable=True),
        sa.Column("reviewer_role",   sa.String(),  nullable=True),
        sa.Column("review_comment",  sa.Text(),    nullable=True),
        sa.Column("reviewed_at",     sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at",      sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at",      sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at",    sa.DateTime(timezone=True), nullable=True),
    )

    # ── pro_evidence ──────────────────────────────────────────────────────────
    op.create_table(
        "pro_evidence",
        sa.Column("id",         postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("case_id",    postgresql.UUID(as_uuid=False), sa.ForeignKey("pro_cases.id"), nullable=True),
        sa.Column("trace_id",   sa.String(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("outcome",    sa.String(), nullable=True),
        sa.Column("package",    sa.String(), nullable=True),
        sa.Column("agent",      sa.String(), nullable=True),
        sa.Column("payload",    postgresql.JSONB(), nullable=True),
        sa.Column("hmac_hash",  sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_pro_evidence_trace_id", "pro_evidence", ["trace_id"])
    op.create_index("ix_pro_evidence_case_id",  "pro_evidence", ["case_id"])

    # ── pro_survey_sessions ───────────────────────────────────────────────────
    op.create_table(
        "pro_survey_sessions",
        sa.Column("id",              postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("case_id",         postgresql.UUID(as_uuid=False), sa.ForeignKey("pro_cases.id"), nullable=False),
        sa.Column("token",           sa.String(), nullable=False, unique=True),
        sa.Column("roles",           postgresql.JSONB(), nullable=True),
        sa.Column("dimensions",      postgresql.JSONB(), nullable=True),
        sa.Column("questions",       postgresql.JSONB(), nullable=True),
        sa.Column("status",          sa.String(), nullable=False, server_default="open"),
        sa.Column("responses_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("min_responses",   sa.Integer(), nullable=False, server_default="3"),
        sa.Column("created_at",      sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at",       sa.DateTime(timezone=True), nullable=True),
    )

    # ── pro_survey_responses ──────────────────────────────────────────────────
    op.create_table(
        "pro_survey_responses",
        sa.Column("id",               postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("session_id",       postgresql.UUID(as_uuid=False), sa.ForeignKey("pro_survey_sessions.id"), nullable=False),
        sa.Column("respondent_hash",  sa.String(), nullable=False),
        sa.Column("role",             sa.String(), nullable=False),
        sa.Column("dimension",        sa.String(), nullable=True),
        sa.Column("answers",          postgresql.JSONB(), nullable=False),
        sa.Column("completed",        sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("submitted_at",     sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("pro_survey_responses")
    op.drop_table("pro_survey_sessions")
    op.drop_index("ix_pro_evidence_case_id",  "pro_evidence")
    op.drop_index("ix_pro_evidence_trace_id", "pro_evidence")
    op.drop_table("pro_evidence")
    op.drop_table("pro_cases")
