"""Observability & compliance API — replay, exports, platform health, backtest."""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse, Response

from app.services.audit_export import AuditExportService
from app.services.backtest import BacktestService
from app.services.platform_health import PlatformHealthService
from app.services.replay import ReplayService

router = APIRouter()
replay_service = ReplayService()
export_service = AuditExportService()
backtest_service = BacktestService()
platform_service = PlatformHealthService()


@router.get("/replay/approval/{approval_id}")
async def replay_approval(approval_id: str):
    try:
        return await replay_service.replay_approval(approval_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/replay/trade/{trade_id}")
async def replay_trade(trade_id: str):
    try:
        return await replay_service.replay_trade(trade_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/export")
async def export_audit(
    format: str = Query(default="json", pattern="^(json|csv)$"),
    days: int = Query(default=90, ge=1, le=365),
):
    if format == "csv":
        content = await export_service.export_csv(days=days)
        return PlainTextResponse(
            content,
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="tradeguard-audit-{days}d.csv"'},
        )
    content = await export_service.export_json(days=days)
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="tradeguard-audit-{days}d.json"'},
    )


@router.get("/export/summary")
async def export_summary(days: int = Query(default=90, ge=1, le=365)):
    payload = await export_service.collect(days=days)
    return {
        "generated_at": payload["generated_at"],
        "period_days": payload["period_days"],
        "counts": payload["counts"],
    }


@router.get("/platform")
async def platform_status():
    return await platform_service.latest()


@router.post("/platform/check")
async def platform_check():
    return await platform_service.check(emit_alerts=True)


@router.get("/backtest/{strategy_id}")
async def backtest_strategy(strategy_id: str, days: int = Query(default=90, ge=7, le=365)):
    try:
        return await backtest_service.run(strategy_id, days=days)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
