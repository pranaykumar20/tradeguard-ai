"""Scheduled ML retrain — Celery when Redis available."""

import asyncio

import structlog

from app.core.config import settings
from app.services.ml_retrain import MLRetrainService

logger = structlog.get_logger()


async def retrain_direction_model_async() -> dict:
    result = await MLRetrainService().retrain()
    logger.info("ml_scheduled_retrain", status=result.get("status"), auc=result.get("auc"))
    return result


def retrain_direction_model() -> dict:
    return asyncio.run(retrain_direction_model_async())


try:
    from celery import Celery
    from celery.schedules import crontab

    celery_app = Celery("tradeguard", broker=settings.celery_broker_url, backend=settings.celery_result_backend)
    celery_app.conf.beat_schedule = {
        "retrain-direction-model": {
            "task": "app.tasks.ml.retrain_direction_model",
            "schedule": crontab(day_of_week="0", hour=3, minute=0),
        },
    }

    @celery_app.task(name="app.tasks.ml.retrain_direction_model")
    def retrain_direction_model_task() -> dict:
        return retrain_direction_model()

except Exception:
    celery_app = None  # type: ignore
