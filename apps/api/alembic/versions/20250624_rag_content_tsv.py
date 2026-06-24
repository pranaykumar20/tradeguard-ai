"""Add tsvector column for Postgres keyword RAG search.

Revision ID: 20250624_rag_tsv
Revises: 20250621_user_rbac
Create Date: 2026-06-24
"""

from __future__ import annotations

from alembic import op

revision = "20250624_rag_tsv"
down_revision = "20250621_user_rbac"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE rag_documents ADD COLUMN IF NOT EXISTS content_tsv tsvector")
    op.execute(
        """
        UPDATE rag_documents
        SET content_tsv = to_tsvector('english', coalesce(content, ''))
        WHERE content_tsv IS NULL
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS rag_documents_content_tsv_idx
        ON rag_documents USING gin (content_tsv)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS rag_documents_content_tsv_idx")
    op.execute("ALTER TABLE rag_documents DROP COLUMN IF EXISTS content_tsv")
