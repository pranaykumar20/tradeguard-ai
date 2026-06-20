"""Market feature refresh — Celery when Redis available, in-process fallback otherwise."""

import asyncio

import structlog

from app.core.config import settings
from app.services.features import refresh_all_tickers

logger = structlog.get_logger()

REFRESH_TICKERS = ["NVDA", "MSFT", "META", "TSLA", "QQQ", "GBTC", "SPY"]


async def refresh_market_features_async() -> dict:
    results = await refresh_all_tickers(REFRESH_TICKERS)
    logger.info("market_features_refreshed", count=len(results), provider=settings.active_market_provider)
    return {"refreshed": list(results.keys()), "provider": settings.active_market_provider}


def refresh_market_features() -> dict:
    return asyncio.run(refresh_market_features_async())


try:
    from celery import Celery

    celery_app = Celery("tradeguard", broker=settings.celery_broker_url, backend=settings.celery_result_backend)
    celery_app.conf.beat_schedule = {
        "refresh-market-features": {
            "task": "app.tasks.market.refresh_market_features",
            "schedule": settings.market_refresh_interval_minutes * 60.0,
        }
    }

    @celery_app.task(name="app.tasks.market.refresh_market_features")
    def refresh_market_features_task() -> dict:
        return refresh_market_features()

except Exception:
    celery_app = None  # type: ignore
