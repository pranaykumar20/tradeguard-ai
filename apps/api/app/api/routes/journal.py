"""Paper trade journal API."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.journal import JournalService

router = APIRouter()
journal = JournalService()


class TradePlanRequest(BaseModel):
    ticker: str
    side: str = Field(pattern="^(buy|sell)$")
    quantity: float = Field(gt=0)
    limit_price: float = Field(gt=0)
    reason: str = ""


class FillTradeRequest(BaseModel):
    fill_price: float | None = None


@router.get("")
async def list_trades(limit: int = 100):
    return {"trades": await journal.list_trades(limit=limit)}


@router.get("/stats")
async def trade_stats():
    return await journal.stats()


@router.post("/plan")
async def create_plan(request: TradePlanRequest):
    return await journal.create_trade_plan(
        ticker=request.ticker,
        side=request.side,
        quantity=request.quantity,
        limit_price=request.limit_price,
        reason=request.reason,
    )


@router.post("/{trade_id}/fill")
async def fill_trade(trade_id: str, request: FillTradeRequest):
    try:
        return await journal.fill_trade(trade_id, fill_price=request.fill_price)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
