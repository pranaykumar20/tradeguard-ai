"""Alembic migration environment."""

from __future__ import annotations

import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from app.core.config import settings
from app.db.models import Base

config = context.config
if config.config_file_name is not None:
    try:
        fileConfig(config.config_file_name)
    except Exception:
        # Logging config is optional; migrations must still run on Railway.
        pass


def _sync_database_url(url: str) -> str:
    """Alembic needs a synchronous driver (psycopg), not asyncpg."""
    if "+asyncpg" in url:
        url = url.replace("+asyncpg", "+psycopg")
    elif url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)
    elif url.startswith("postgresql://") and "+psycopg" not in url:
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)

    # Railway public Postgres endpoints require TLS; internal *.railway.internal does not.
    lower = url.lower()
    if (
        "sslmode=" not in lower
        and ".railway.internal" not in lower
        and ("railway.app" in lower or "rlwy.net" in lower or "railway" in lower)
    ):
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}sslmode=require"

    return url


def _migration_database_url() -> str:
    url = _sync_database_url(settings.database_url)
    if settings.app_env == "production" and (
        "localhost" in url or "127.0.0.1" in url or "@host.docker.internal" in url
    ):
        print(
            "ERROR: DATABASE_URL is not configured for production migrations.\n"
            "Set DATABASE_URL on the Railway API service (reference your Postgres plugin).",
            file=sys.stderr,
        )
        raise SystemExit(1)
    return url


migration_url = _migration_database_url()
config.set_main_option("sqlalchemy.url", migration_url)
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(url=migration_url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(migration_url, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
