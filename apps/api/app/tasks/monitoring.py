"""Background monitoring checks — Celery when Redis available, in-process fallback."""

import asyncio

import structlog

from app.core.config import settings
from app.services.monitoring import MonitoringService

logger = structlog.get_logger()


async def run_monitoring_check_async() -> dict:
    if not settings.monitoring_enabled:
        return {"status": "disabled"}
    service = MonitoringService()
    result = await service.run_check()
    logger.info(
        "monitoring_check_complete",
        status=result.get("status"),
        trading_halted=result.get("trading_halted"),
    )
    return result


def run_monitoring_check() -> dict:
    return asyncio.run(run_monitoring_check_async())


try:
    from celery import Celery

    from app.tasks.market import celery_app

    if celery_app is not None:
        celery_app.conf.beat_schedule.setdefault(
            "monitoring-check",
            {
                "task": "app.tasks.monitoring.run_monitoring_check",
                "schedule": settings.monitoring_interval_minutes * 60.0,
            },
        )

        @celery_app.task(name="app.tasks.monitoring.run_monitoring_check")
        def run_monitoring_check_task() -> dict:
            return run_monitoring_check()

except Exception:
    pass
