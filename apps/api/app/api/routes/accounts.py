"""Linked accounts and household portfolio API."""

from fastapi import APIRouter, Depends

from app.core.auth import CurrentUser, get_optional_user
from app.services.accounts import AccountService
from app.services.portfolio import PortfolioService
from app.services.tax import TaxService

router = APIRouter()
accounts = AccountService()
portfolio_service = PortfolioService()
tax_service = TaxService()


@router.get("/brokers")
async def list_brokers():
    return {"brokers": await accounts.list_brokers()}


@router.get("")
async def list_accounts(user: CurrentUser = Depends(get_optional_user)):
    return {"accounts": await accounts.list_accounts(), "user_id": user.id}


@router.get("/household")
async def household_view(user: CurrentUser = Depends(get_optional_user)):
    household = await portfolio_service.get_household()
    return {**household, "user_id": user.id}


@router.get("/tax-lots")
async def list_tax_lots(ticker: str | None = None, account_id: str | None = None):
    lots = await tax_service.list_lots(ticker=ticker, account_id=account_id)
    return {"lots": lots, "count": len(lots)}


@router.get("/tax-lots/analyze")
async def analyze_tax_sell(
    ticker: str,
    quantity: float,
    limit_price: float,
    account_id: str | None = None,
):
    return await tax_service.analyze_sell(ticker, quantity, limit_price, account_id=account_id)
