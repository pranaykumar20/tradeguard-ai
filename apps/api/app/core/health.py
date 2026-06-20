"""Production health and readiness probes."""

from __future__ import annotations

import structlog
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings

logger = structlog.get_logger()


async def check_postgres() -> dict:
    try:
        engine = create_async_engine(settings.database_url, echo=False)
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        await engine.dispose()
        return {"status": "ok", "backend": settings.active_storage_backend}
    except Exception as exc:
        logger.warning("health_postgres_failed", error=str(exc))
        return {"status": "fail", "error": str(exc)}


async def check_redis() -> dict:
    try:
        client = Redis.from_url(settings.redis_url, decode_responses=True)
        pong = await client.ping()
        await client.aclose()
        if pong:
            return {"status": "ok"}
        return {"status": "fail", "error": "ping returned false"}
    except Exception as exc:
        logger.warning("health_redis_failed", error=str(exc))
        return {"status": "fail", "error": str(exc)}


async def readiness_report() -> dict:
    postgres = await check_postgres()
    redis = await check_redis()
    checks = {"postgres": postgres, "redis": redis}
    ready = all(c.get("status") == "ok" for c in checks.values())
    return {
        "status": "ready" if ready else "degraded",
        "service": settings.app_name,
        "env": settings.app_env,
        "checks": checks,
    }
