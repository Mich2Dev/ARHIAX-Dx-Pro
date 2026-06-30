"""Add missing columns to pro tables (branching + open_answers).

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-17
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def _column_exists(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = inspector.get_columns(table_name)
    return any(column["name"] == column_name for column in columns)


def upgrade() -> None:
    # branching en pro_survey_sessions (lógica de ramificación adaptativa)
    if not _column_exists("pro_survey_sessions", "branching"):
        op.add_column(
            "pro_survey_sessions",
            sa.Column("branching", postgresql.JSONB(), nullable=True),
        )

    # open_answers en pro_survey_responses (respuestas abiertas del cuestionario)
    if not _column_exists("pro_survey_responses", "open_answers"):
        op.add_column(
            "pro_survey_responses",
            sa.Column("open_answers", postgresql.JSONB(), nullable=True),
        )


def downgrade() -> None:
    if _column_exists("pro_survey_responses", "open_answers"):
        op.drop_column("pro_survey_responses", "open_answers")
    if _column_exists("pro_survey_sessions", "branching"):
        op.drop_column("pro_survey_sessions", "branching")
