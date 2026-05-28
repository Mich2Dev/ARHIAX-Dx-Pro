"""Diagnostic documents — optional context files uploaded by the client.

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-26
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "diagnostic_documents",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "diagnostic_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("diagnostics.id"),
            nullable=False,
        ),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("original_name", sa.String(), nullable=False),
        sa.Column("mime_type", sa.String(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("doc_type", sa.String(), nullable=False, server_default="context"),
        # doc_type: context | organigrama | financiero | proceso | otro
        sa.Column("extracted_text", sa.Text(), nullable=True),   # text extracted for LLM
        sa.Column("summary", sa.Text(), nullable=True),          # AI summary of the doc
        sa.Column("uploaded_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_diagnostic_documents_diagnostic",
        "diagnostic_documents",
        ["diagnostic_id"],
    )

    # Also add extra context fields to diagnostics
    op.add_column(
        "diagnostics",
        sa.Column("extra_context", postgresql.JSONB(), nullable=True),
        # Stores: problem_since, previous_attempts, expected_outcome, etc.
    )
    op.add_column(
        "diagnostics",
        sa.Column("contact_name", sa.String(), nullable=True),
    )
    op.add_column(
        "diagnostics",
        sa.Column("contact_email", sa.String(), nullable=True),
    )
    op.add_column(
        "diagnostics",
        sa.Column("deadline", sa.String(), nullable=True),
    )
    op.add_column(
        "diagnostics",
        sa.Column("survey_participants", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("diagnostics", "survey_participants")
    op.drop_column("diagnostics", "deadline")
    op.drop_column("diagnostics", "contact_email")
    op.drop_column("diagnostics", "contact_name")
    op.drop_column("diagnostics", "extra_context")
    op.drop_index("ix_diagnostic_documents_diagnostic")
    op.drop_table("diagnostic_documents")
