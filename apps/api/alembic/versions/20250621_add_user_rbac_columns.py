"""Add RBAC columns to users (role, permissions, is_active).

Revision ID: 20250621_user_rbac
Revises:
Create Date: 2026-06-21
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects.postgresql import JSONB

revision = "20250621_user_rbac"
down_revision = None
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    return table_name in inspect(bind).get_table_names()


def _column_names(table_name: str) -> set[str]:
    bind = op.get_bind()
    return {col["name"] for col in inspect(bind).get_columns(table_name)}


def upgrade() -> None:
    if not _table_exists("users"):
        op.create_table(
            "users",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("clerk_id", sa.String(length=64), nullable=False),
            sa.Column("email", sa.String(length=255), nullable=False, server_default=""),
            sa.Column("display_name", sa.String(length=128), nullable=False, server_default=""),
            sa.Column("role", sa.String(length=32), nullable=False, server_default="user"),
            sa.Column("permissions", JSONB, nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
        )
        op.create_index("ix_users_clerk_id", "users", ["clerk_id"], unique=True)
        return

    columns = _column_names("users")

    if "role" not in columns:
        op.add_column(
            "users",
            sa.Column("role", sa.String(length=32), nullable=False, server_default="user"),
        )

    if "permissions" not in columns:
        op.add_column("users", sa.Column("permissions", JSONB, nullable=True))

    if "is_active" not in columns:
        op.add_column(
            "users",
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        )


def downgrade() -> None:
    if not _table_exists("users"):
        return

    columns = _column_names("users")

    if "is_active" in columns:
        op.drop_column("users", "is_active")
    if "permissions" in columns:
        op.drop_column("users", "permissions")
    if "role" in columns:
        op.drop_column("users", "role")
