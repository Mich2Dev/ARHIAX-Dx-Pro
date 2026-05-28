"""Add pipeline_stages column to pro_cases.

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-14
"""
from __future__ import annotations
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "pro_cases",
        sa.Column("pipeline_stages", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("pro_cases", "pipeline_stages")
