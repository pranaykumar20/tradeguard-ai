"""API route aggregation."""

from fastapi import APIRouter

from app.api.routes import advanced_risk, accounts, analysis, auth, automation, chat, execution, health, intelligence, journal, monitoring, observability, onboarding, portfolio, push, risk, strategies, validation

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(intelligence.router, prefix="/intelligence", tags=["intelligence"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(analysis.router, prefix="/analysis", tags=["analysis"])
api_router.include_router(risk.router, prefix="/risk", tags=["risk"])
api_router.include_router(portfolio.router, prefix="/portfolio", tags=["portfolio"])
api_router.include_router(accounts.router, prefix="/accounts", tags=["accounts"])
api_router.include_router(observability.router, prefix="/observability", tags=["observability"])
api_router.include_router(onboarding.router, prefix="/onboarding", tags=["onboarding"])
api_router.include_router(push.router, prefix="/push", tags=["push"])
api_router.include_router(journal.router, prefix="/journal", tags=["journal"])
api_router.include_router(advanced_risk.router, prefix="/risk", tags=["advanced-risk"])
api_router.include_router(execution.router, prefix="/execution", tags=["execution"])
api_router.include_router(monitoring.router, prefix="/monitoring", tags=["monitoring"])
api_router.include_router(strategies.router, prefix="/strategies", tags=["strategies"])
api_router.include_router(validation.router, prefix="/validation", tags=["validation"])
api_router.include_router(automation.router, prefix="/automation", tags=["automation"])
