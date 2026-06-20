"""Agentic onboarding wizard API."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.onboarding import OnboardingService

router = APIRouter()
onboarding = OnboardingService()


class CompleteStepRequest(BaseModel):
    step_id: str


@router.get("/status")
async def onboarding_status():
    return await onboarding.get_status()


@router.post("/complete")
async def complete_step(request: CompleteStepRequest):
    try:
        return await onboarding.complete_step(request.step_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/reset")
async def reset_onboarding():
    return await onboarding.reset()
