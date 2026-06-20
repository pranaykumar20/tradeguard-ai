"""Monitoring and alerting routes — Phase 4.1."""

from fastapi import APIRouter, HTTPException

from app.services.monitoring import MonitoringService

router = APIRouter()
monitoring = MonitoringService()


@router.get("/status")
async def monitoring_status():
    return await monitoring.get_status()


@router.post("/check")
async def run_monitoring_check():
    return await monitoring.run_check()


@router.get("/alerts")
async def list_alerts(limit: int = 50):
    from app.db.storage import get_storage

    storage = await get_storage()
    events = await storage.list_alert_events(limit=limit)
    return {"alerts": events}


@router.post("/resume-trading")
async def resume_trading():
    state = await monitoring.get_trading_state()
    if not state.get("halted"):
        raise HTTPException(status_code=400, detail="Trading is not halted")
    updated = await monitoring.resume_trading()
    return {"status": "resumed", "trading_state": updated}
