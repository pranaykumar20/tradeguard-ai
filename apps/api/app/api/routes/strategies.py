"""Semi-automated trade strategy API — Phase 4.2."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.strategies import StrategyService

router = APIRouter()
strategies = StrategyService()


class StrategyConfig(BaseModel):
    sector: str | None = None
    threshold_pct: float | None = None
    comparison: str = "above"
    action_ticker: str
    action_side: str = Field(pattern="^(buy|sell)$")
    quantity: float = Field(default=1, gt=0)


class CreateStrategyRequest(BaseModel):
    name: str
    description: str = ""
    strategy_type: str = "sector_exposure"
    config: StrategyConfig
    auto_approve: bool = False
    enabled: bool = False


class UpdateStrategyRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    config: StrategyConfig | None = None
    auto_approve: bool | None = None
    enabled: bool | None = None


@router.get("/templates")
async def list_templates():
    return {"templates": strategies.templates()}


@router.get("/proposals")
async def list_proposals(strategy_id: str | None = None, limit: int = 50):
    return {"proposals": await strategies.list_proposals(strategy_id=strategy_id, limit=limit)}


@router.post("/run-all")
async def run_all_strategies():
    return await strategies.run_all_enabled()


@router.get("")
async def list_strategies():
    return {"strategies": await strategies.list_strategies()}


@router.post("")
async def create_strategy(request: CreateStrategyRequest):
    strategy = await strategies.create_strategy(
        {
            "name": request.name,
            "description": request.description,
            "strategy_type": request.strategy_type,
            "config": request.config.model_dump(),
            "auto_approve": request.auto_approve,
            "enabled": request.enabled,
        }
    )
    return {"strategy": strategy}


@router.get("/{strategy_id}")
async def get_strategy(strategy_id: str):
    strategy = await strategies.get_strategy(strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return {"strategy": strategy}


@router.patch("/{strategy_id}")
async def update_strategy(strategy_id: str, request: UpdateStrategyRequest):
    updates = request.model_dump(exclude_unset=True)
    strategy = await strategies.update_strategy(strategy_id, updates)
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return {"strategy": strategy}


@router.delete("/{strategy_id}")
async def delete_strategy(strategy_id: str):
    deleted = await strategies.delete_strategy(strategy_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return {"status": "deleted"}


@router.post("/{strategy_id}/evaluate")
async def evaluate_strategy(strategy_id: str):
    try:
        return await strategies.evaluate_strategy(strategy_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
