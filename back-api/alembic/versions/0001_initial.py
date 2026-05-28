"""Initial schema.

Revision ID: 0001
Revises:
Create Date: 2026-04-24
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("email", sa.String(), nullable=False, unique=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False, server_default="operator"),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "diagnostics",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("request_id", sa.String(), nullable=False, unique=True),
        sa.Column("client_id", sa.String(), nullable=False),
        sa.Column("legal_name", sa.String(), nullable=False),
        sa.Column("organization_name", sa.String(), nullable=False),
        sa.Column("domain", sa.String(), nullable=False),
        sa.Column("subprocess", sa.String(), nullable=False),
        sa.Column("objective", sa.Text(), nullable=True),
        sa.Column("size_org", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("decision", sa.String(), nullable=True),
        sa.Column("autonomy_level", sa.String(), nullable=False, server_default="A1"),
        sa.Column("rule_results", postgresql.JSONB(), nullable=True),
        sa.Column("certificate", postgresql.JSONB(), nullable=True),
        sa.Column("execution_plan", postgresql.JSONB(), nullable=True),
        sa.Column("human_review_required", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "pipeline_stages",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("diagnostic_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("diagnostics.id"), nullable=False),
        sa.Column("tool_name", sa.String(), nullable=False),
        sa.Column("phase", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("model_used", sa.String(), nullable=True),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("output", postgresql.JSONB(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "human_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("diagnostic_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("diagnostics.id"), nullable=False),
        sa.Column("review_type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("reviewer_id", sa.String(), nullable=True),
        sa.Column("reviewer_name", sa.String(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "reports",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("diagnostic_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("diagnostics.id"), unique=True, nullable=False),
        sa.Column("qa_score", sa.Float(), nullable=True),
        sa.Column("irr_alpha", sa.Float(), nullable=True),
        sa.Column("delta_sigma", sa.Float(), nullable=True),
        sa.Column("narrative", sa.Text(), nullable=True),
        sa.Column("findings", postgresql.JSONB(), nullable=True),
        sa.Column("bpmn_xml", sa.Text(), nullable=True),
        sa.Column("docx_path", sa.String(), nullable=True),
        sa.Column("published", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("reports")
    op.drop_table("human_reviews")
    op.drop_table("pipeline_stages")
    op.drop_table("diagnostics")
    op.drop_table("users")
