"""RAG index refresh — Celery when Redis available, in-process fallback otherwise."""

import asyncio

import structlog

from app.core.config import settings
from app.rag.indexer import RAGIndexer

logger = structlog.get_logger()


async def refresh_rag_index_async() -> dict:
    if not settings.rag_refresh_enabled:
        return {"status": "disabled"}
    result = await RAGIndexer().refresh_all()
    logger.info("rag_refresh_complete", **result)
    return result


def refresh_rag_index() -> dict:
    return asyncio.run(refresh_rag_index_async())


try:
    from celery import Celery

    from app.tasks.market import celery_app

    if celery_app is not None:
        celery_app.conf.beat_schedule.setdefault(
            "refresh-rag-index",
            {
                "task": "app.tasks.rag.refresh_rag_index",
                "schedule": settings.rag_refresh_interval_minutes * 60.0,
            },
        )

        @celery_app.task(name="app.tasks.rag.refresh_rag_index")
        def refresh_rag_index_task() -> dict:
            return refresh_rag_index()

        celery_app.conf.beat_schedule.setdefault(
            "rag-eval-nightly",
            {
                "task": "app.tasks.rag.run_rag_eval_task",
                "schedule": settings.rag_eval_interval_hours * 3600.0,
            },
        )

        @celery_app.task(name="app.tasks.rag.run_rag_eval_task")
        def run_rag_eval_task() -> dict:
            from app.rag.eval.runner import run_rag_eval

            return asyncio.run(run_rag_eval())

except Exception:
    pass
