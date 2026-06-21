"""Robinhood MCP connect — OAuth start, callback, status, disconnect."""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from app.core.auth import CurrentUser, get_current_user, require_permission
from app.core.permissions import PERMISSION_ONBOARDING
from app.services.robinhood_connect import RobinhoodConnectService

router = APIRouter()
connect_service = RobinhoodConnectService()


class ConnectRequest(BaseModel):
    return_path: str = Field(default="/onboarding", max_length=256)


@router.get("/robinhood/status")
async def robinhood_connection_status(
    user: CurrentUser = Depends(get_current_user),
):
    return {**(await connect_service.get_status()), "user_id": user.id}


@router.post("/robinhood/connect")
async def start_robinhood_connect(
    request: ConnectRequest,
    user: CurrentUser = Depends(require_permission(PERMISSION_ONBOARDING)),
):
    payload = await connect_service.start_connect(return_path=request.return_path)
    return {**payload, "user_id": user.id}


@router.get("/robinhood/callback")
async def robinhood_oauth_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
):
    if error:
        return RedirectResponse(
            url=_frontend_redirect("error", error),
            status_code=302,
        )
    if not code or not state:
        return RedirectResponse(
            url=_frontend_redirect("error", "missing_code"),
            status_code=302,
        )

    redirect_url = await connect_service.handle_callback(code=code, state=state)
    return RedirectResponse(url=redirect_url, status_code=302)


@router.post("/robinhood/disconnect")
async def disconnect_robinhood(
    user: CurrentUser = Depends(require_permission(PERMISSION_ONBOARDING)),
):
    status = await connect_service.disconnect()
    return {**status, "user_id": user.id}


def _frontend_redirect(status: str, reason: str | None) -> str:
    from app.services.robinhood_connect import _frontend_redirect as build_url

    return build_url(status, reason)
