"""HTTP middleware."""

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.auth import resolve_request_user_id
from app.core.user_context import reset_current_user_id, set_current_user_id


class UserContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        user_id = await resolve_request_user_id(request)
        token = set_current_user_id(user_id)
        try:
            return await call_next(request)
        finally:
            reset_current_user_id(token)
