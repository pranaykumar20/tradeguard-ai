"""Guarded execution and approval queue API."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.execution import ExecutionService

router = APIRouter()
execution = ExecutionService()


class OrderPreviewRequest(BaseModel):
    ticker: str
    side: str = Field(pattern="^(buy|sell)$")
    quantity: float = Field(gt=0)
    limit_price: float | None = Field(default=None, gt=0)
    order_type: str = "limit"


class OrderSubmitRequest(OrderPreviewRequest):
    notes: str = ""


class RejectRequest(BaseModel):
    reason: str = ""


@router.get("/quote/{ticker}")
async def get_quote(ticker: str):
    return await execution.get_quote(ticker)


@router.post("/preview")
async def preview_order(request: OrderPreviewRequest):
    return await execution.preview_order(
        ticker=request.ticker,
        side=request.side,
        quantity=request.quantity,
        limit_price=request.limit_price,
        order_type=request.order_type,
    )


@router.post("/submit")
async def submit_order(request: OrderSubmitRequest):
    result = await execution.submit_for_approval(
        ticker=request.ticker,
        side=request.side,
        quantity=request.quantity,
        limit_price=request.limit_price,
        order_type=request.order_type,
        notes=request.notes,
    )
    if result["status"] == "blocked":
        raise HTTPException(status_code=422, detail=result)
    return result


@router.get("/approvals")
async def list_approvals(status: str | None = None, limit: int = 50):
    return {"approvals": await execution.list_approvals(status=status, limit=limit)}


@router.get("/approvals/{request_id}")
async def get_approval(request_id: str):
    req = await execution.get_approval(request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Approval request not found")
    return req


@router.post("/approvals/{request_id}/approve")
async def approve_order(request_id: str):
    try:
        return await execution.approve(request_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/approvals/{request_id}/reject")
async def reject_order(request_id: str, request: RejectRequest):
    try:
        return await execution.reject(request_id, reason=request.reason)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
