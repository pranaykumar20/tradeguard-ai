"""Advanced risk analytics — VaR, correlation, stress tests."""

from fastapi import APIRouter

from app.services.advanced_risk import compute_advanced_risk

router = APIRouter()


@router.get("/advanced")
async def advanced_risk():
    return await compute_advanced_risk()
