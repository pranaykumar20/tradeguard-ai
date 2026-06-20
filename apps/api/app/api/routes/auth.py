"""Auth routes — current user profile (Phase 5.2)."""

from fastapi import APIRouter, Depends

from app.core.auth import CurrentUser, get_current_user, get_optional_user
from app.core.config import settings

router = APIRouter()


@router.get("/me")
async def auth_me(user: CurrentUser = Depends(get_optional_user)):
    return {
        "auth_enabled": settings.auth_enabled,
        "user": {
            "id": user.id,
            "email": user.email,
            "clerk_id": user.clerk_id,
            "is_authenticated": user.is_authenticated,
        },
    }


@router.get("/session")
async def auth_session(user: CurrentUser = Depends(get_current_user)):
    """Requires valid Clerk JWT when auth is enabled."""
    return {
        "id": user.id,
        "email": user.email,
        "clerk_id": user.clerk_id,
        "is_authenticated": user.is_authenticated,
    }
