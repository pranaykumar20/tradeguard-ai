"""Partial indexes on rag_documents meta type for common doc types.

Revision ID: 20250625_rag_partial_idx
Revises: 20250624_rag_tsv
Create Date: 2026-06-25
"""

from __future__ import annotations

from alembic import op

revision = "20250625_rag_partial_idx"
down_revision = "20250624_rag_tsv"
branch_labels = None
depends_on = None

_DOC_TYPES = ("playbook", "filing", "news", "journal", "regime_snapshot")


def upgrade() -> None:
    for doc_type in _DOC_TYPES:
        op.execute(
            f"""
            CREATE INDEX IF NOT EXISTS rag_documents_type_{doc_type}_idx
            ON rag_documents ((meta->>'type'))
            WHERE meta->>'type' = '{doc_type}'
            """
        )


def downgrade() -> None:
    for doc_type in _DOC_TYPES:
        op.execute(f"DROP INDEX IF EXISTS rag_documents_type_{doc_type}_idx")
