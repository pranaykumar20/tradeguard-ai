"""Background strategy evaluation — Celery when Redis available."""

import asyncio

import structlog

from app.core.config import settings
from app.services.strategies import StrategyService

logger = structlog.get_logger()


async def run_strategy_eval_async() -> dict:
    if not settings.strategies_enabled:
        return {"status": "disabled"}
    service = StrategyService()
    await service.ensure_defaults()
    result = await service.run_all_enabled()
    logger.info("strategy_eval_complete", evaluated=result.get("evaluated", 0))
    return result


def run_strategy_eval() -> dict:
    return asyncio.run(run_strategy_eval_async())


try:
    from app.tasks.market import celery_app

    if celery_app is not None:
        celery_app.conf.beat_schedule.setdefault(
            "strategy-eval",
            {
                "task": "app.tasks.strategies.run_strategy_eval",
                "schedule": settings.strategy_eval_interval_minutes * 60.0,
            },
        )

        @celery_app.task(name="app.tasks.strategies.run_strategy_eval")
        def run_strategy_eval_task() -> dict:
            return run_strategy_eval()

except Exception:
    pass
