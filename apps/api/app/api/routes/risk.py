"""Risk engine API."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.risk.engine import RiskEngine
from app.risk.rules import RiskRules, default_rules

router = APIRouter()
risk_engine = RiskEngine()


class TradePreviewRequest(BaseModel):
    ticker: str
    side: str = Field(pattern="^(buy|sell)$")
    quantity: float = Field(gt=0)
    limit_price: float = Field(gt=0)
    order_type: str = "limit"
    asset_type: str = "equity"


class TradePreviewResponse(BaseModel):
    allowed: bool
    verdict: str
    order_value: float
    warnings: list[str]
    blocks: list[str]
    requires_approval: bool
    ticker: str | None = None
    side: str | None = None
    quantity: float | None = None
    limit_price: float | None = None
    setup_label: str | None = None
    composite_score: float | None = None


class RiskRulesResponse(BaseModel):
    rules: RiskRules


@router.get("/rules", response_model=RiskRulesResponse)
async def get_rules():
    return RiskRulesResponse(rules=default_rules())


@router.post("/preview", response_model=TradePreviewResponse)
async def preview_trade(request: TradePreviewRequest):
    result = await risk_engine.preview_trade(
        ticker=request.ticker.upper(),
        side=request.side,
        quantity=request.quantity,
        limit_price=request.limit_price,
        order_type=request.order_type,
        asset_type=request.asset_type,
    )
    return TradePreviewResponse(**result)


@router.get("/snapshot")
async def risk_snapshot():
    return await risk_engine.portfolio_snapshot()
