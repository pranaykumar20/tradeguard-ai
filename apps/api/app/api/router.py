"""API route aggregation."""

from fastapi import APIRouter

from app.api.routes import advanced_risk, analysis, chat, execution, health, journal, portfolio, risk

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(analysis.router, prefix="/analysis", tags=["analysis"])
api_router.include_router(risk.router, prefix="/risk", tags=["risk"])
api_router.include_router(portfolio.router, prefix="/portfolio", tags=["portfolio"])
api_router.include_router(journal.router, prefix="/journal", tags=["journal"])
api_router.include_router(advanced_risk.router, prefix="/risk", tags=["advanced-risk"])
api_router.include_router(execution.router, prefix="/execution", tags=["execution"])
