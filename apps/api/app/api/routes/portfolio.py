"""Portfolio endpoints — single account or household aggregation."""

from fastapi import APIRouter, Query

from app.core.config import settings
from app.services.portfolio import PortfolioService

router = APIRouter()
portfolio_service = PortfolioService()


@router.get("")
async def get_portfolio(
    broker_id: str | None = None,
    account_id: str | None = None,
    view: str = Query(default="single", pattern="^(single|household)$"),
):
    if view == "household" or (settings.multi_broker_enabled and not broker_id):
        return await portfolio_service.get_household()
    if broker_id and account_id:
        return await portfolio_service.get_account_portfolio(broker_id, account_id)
    if settings.robinhood_mcp_enabled:
        return await portfolio_service.get_account_portfolio(
            settings.default_broker_id, account_id or "agentic-main"
        )
    return await portfolio_service.get_household()
