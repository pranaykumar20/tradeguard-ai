#!/usr/bin/env python3
"""Run database migrations (used by Railway pre-deploy)."""

from __future__ import annotations

import sys

from alembic.config import Config
from alembic import command

from app.core.config import settings


def main() -> int:
    print(f"Running Alembic migrations (APP_ENV={settings.app_env})…", flush=True)
    cfg = Config("alembic.ini")
    try:
        command.upgrade(cfg, "head")
    except Exception as exc:
        print(f"Migration failed: {exc}", file=sys.stderr, flush=True)
        return 1
    print("Migrations applied successfully.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
