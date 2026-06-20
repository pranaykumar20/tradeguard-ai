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


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    await init_storage()
    await ensure_direction_model()
    rag = RAGService()
    await rag.ensure_index()
    await refresh_market_features_async()
    yield
    await close_storage()


app = FastAPI(
    title=settings.app_name,
    description="AI Stock Risk Manager — ML signals, RAG, risk engine, Robinhood MCP",
    version="0.2.0",
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
        "phase": 2,
        "market_provider": settings.active_market_provider,
        "embedding_provider": settings.active_embedding_provider,
    }
