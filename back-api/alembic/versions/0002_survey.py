"""Survey tables.

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-26
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Survey sessions — one per diagnostic
    op.create_table(
        "survey_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("diagnostic_id", postgresql.UUID(as_uuid=False),
                  sa.ForeignKey("diagnostics.id"), nullable=False, unique=True),
        sa.Column("token", sa.String(), nullable=False, unique=True),
        sa.Column("status", sa.String(), nullable=False, server_default="open"),
        # open | collecting | closed
        sa.Column("questions", postgresql.JSONB(), nullable=True),
        # output of g09a_preguntas stored here
        sa.Column("min_responses", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("response_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Individual survey responses — one per respondent
    op.create_table(
        "survey_responses",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=False),
                  sa.ForeignKey("survey_sessions.id"), nullable=False),
        sa.Column("respondent_hash", sa.String(), nullable=False),
        # SHA256 of (session_id + anonymous_id) — no PII stored
        sa.Column("role", sa.String(), nullable=False),
        # Estratégico | Táctico | Operativo
        sa.Column("answers", postgresql.JSONB(), nullable=False),
        # {"Q01": 4, "Q02": 3, "QA01": "texto libre..."}
        sa.Column("completed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_index("ix_survey_sessions_token", "survey_sessions", ["token"])
    op.create_index("ix_survey_responses_session", "survey_responses", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_survey_responses_session")
    op.drop_index("ix_survey_sessions_token")
    op.drop_table("survey_responses")
    op.drop_table("survey_sessions")
