"""Fix survey_sessions columns to match ORM model.

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-26
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── survey_sessions: add missing columns ─────────────────────────────────
    # Add branching column (output of G09b)
    op.add_column("survey_sessions",
        sa.Column("branching", postgresql.JSONB(), nullable=True))

    # Add target_responses column
    op.add_column("survey_sessions",
        sa.Column("target_responses", sa.Integer(), nullable=False, server_default="20"))

    # Rename response_count → responses_count to match ORM
    op.alter_column("survey_sessions", "response_count",
                    new_column_name="responses_count")

    # ── survey_responses: add missing columns ─────────────────────────────────
    # Add open_answers column (text answers for NLP)
    op.add_column("survey_responses",
        sa.Column("open_answers", postgresql.JSONB(), nullable=True))

    # submitted_at already exists but make sure it has a default
    # (no change needed, already nullable)


def downgrade() -> None:
    op.drop_column("survey_responses", "open_answers")
    op.alter_column("survey_sessions", "responses_count",
                    new_column_name="response_count")
    op.drop_column("survey_sessions", "target_responses")
    op.drop_column("survey_sessions", "branching")
