"""Performance validation gate API — Phase 4.3."""

from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.services.validation import ValidationService

router = APIRouter()
validation = ValidationService()


@router.get("/report")
async def validation_report():
    return await validation.build_report()


@router.get("/gate")
async def validation_gate():
    allowed, report = await validation.check_gate()
    return {"automation_unlocked": allowed, "report": report}


@router.post("/seed-demo")
async def seed_demo_track_record():
    if settings.app_env != "development":
        raise HTTPException(status_code=403, detail="Demo seed only available in development")
    try:
        return await validation.seed_demo_track_record()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
