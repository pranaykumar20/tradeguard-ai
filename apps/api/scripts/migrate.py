#!/usr/bin/env python3
"""Run database migrations (used by Railway pre-deploy)."""

from __future__ import annotations

import sys
from pathlib import Path

# Pre-deploy runs `python scripts/migrate.py`, so sys.path[0] is /app/scripts.
# Ensure /app is importable so `from app...` works (same layout as uvicorn).
APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

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
