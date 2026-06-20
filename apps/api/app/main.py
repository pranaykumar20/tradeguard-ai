"""TradeGuard AI — FastAPI application entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.logging import setup_logging
from app.db.storage import close_storage, init_storage
from app.rag.service import RAGService
from app.services.ml_bootstrap import ensure_direction_model
from app.tasks.market import refresh_market_features_async
from app.tasks.monitoring import run_monitoring_check_async
from app.tasks.strategies import run_strategy_eval_async
from app.services.strategies import StrategyService
from app.services.validation import ValidationService


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    await init_storage()
    await ensure_direction_model()
    rag = RAGService()
    await rag.ensure_index()
    await refresh_market_features_async()
    await run_monitoring_check_async()
    strategy_service = StrategyService()
    await strategy_service.ensure_defaults()
    await ValidationService().build_report()
    await run_strategy_eval_async()
    yield
    await close_storage()


app = FastAPI(
    title=settings.app_name,
    description="AI Stock Risk Manager — ML signals, RAG, risk engine, Robinhood MCP",
    version="0.3.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": settings.app_name,
        "env": settings.app_env,
        "phase": 4,
        "market_provider": settings.active_market_provider,
        "embedding_provider": settings.active_embedding_provider,
        "alert_provider": settings.active_alert_provider,
        "monitoring_enabled": settings.monitoring_enabled,
        "strategies_enabled": settings.strategies_enabled,
        "validation_gate_enabled": settings.validation_gate_enabled,
        "automation_feature_enabled": settings.automation_feature_enabled,
    }
