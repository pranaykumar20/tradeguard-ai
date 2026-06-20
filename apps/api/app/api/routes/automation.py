"""Constrained automation control API — Phase 4.4."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.automation import AutomationService
from app.services.strategies import StrategyService

router = APIRouter()
automation = AutomationService()
strategies = StrategyService()


class DisableRequest(BaseModel):
    reason: str = "Disabled by user"


@router.get("/status")
async def automation_status():
    return await automation.get_status()


@router.get("/audit")
async def automation_audit(limit: int = 50):
    return {"audit": await automation.list_audit(limit=limit)}


@router.post("/enable")
async def enable_automation():
    state = await automation.enable()
    return {"status": "enabled", "state": state}


@router.post("/disable")
async def disable_automation(request: DisableRequest):
    state = await automation.disable(reason=request.reason)
    return {"status": "disabled", "state": state}


@router.post("/run")
async def run_automation():
    """Run all enabled strategies through the constrained automation pipeline."""
    status = await automation.get_status()
    if not status["master_enabled"]:
        return {"status": "disabled", "message": "Automation master switch is off", "run": None}
    result = await strategies.run_all_enabled()
    await automation.log_audit(
        "automation_run",
        f"Evaluated {result.get('evaluated', 0)} strategies",
        meta={"evaluated": result.get("evaluated", 0)},
    )
    return {"status": "ok", "automation": status, "run": result}
