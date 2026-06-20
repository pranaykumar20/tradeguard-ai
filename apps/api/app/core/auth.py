"""Optional Clerk JWT authentication — disabled by default (demo user)."""

from __future__ import annotations

from dataclasses import dataclass

import jwt
import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

logger = structlog.get_logger()
_bearer = HTTPBearer(auto_error=False)

DEFAULT_USER_ID = "default"
DEFAULT_USER_EMAIL = "demo@local"

_jwks_client: jwt.PyJWKClient | None = None


@dataclass
class CurrentUser:
    id: str
    clerk_id: str | None
    email: str
    is_authenticated: bool


def _jwks_url() -> str:
    issuer = settings.clerk_jwt_issuer.rstrip("/")
    return f"{issuer}/.well-known/jwks.json"


def _get_jwks_client() -> jwt.PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = jwt.PyJWKClient(_jwks_url())
    return _jwks_client


def _decode_clerk_token(token: str) -> dict:
    client = _get_jwks_client()
    signing_key = client.get_signing_key_from_jwt(token)
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        issuer=settings.clerk_jwt_issuer,
        options={"verify_aud": False},
    )


async def _resolve_authenticated_user(credentials: HTTPAuthorizationCredentials) -> CurrentUser:
    try:
        payload = _decode_clerk_token(credentials.credentials)
    except Exception as exc:
        logger.warning("auth_token_invalid", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc

    clerk_id = payload.get("sub")
    if not clerk_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject",
        )

    email = payload.get("email") or payload.get("primary_email") or ""
    name = payload.get("name") or payload.get("username") or email.split("@")[0]
    return await sync_user_from_clerk(clerk_id, email, name)


async def sync_user_from_clerk(clerk_id: str, email: str, display_name: str) -> CurrentUser:
    from app.db.storage import get_storage

    try:
        storage = await get_storage()
        user = await storage.get_or_create_user(
            clerk_id=clerk_id,
            email=email,
            display_name=display_name,
        )
        return CurrentUser(
            id=user["id"],
            clerk_id=clerk_id,
            email=user.get("email") or email,
            is_authenticated=True,
        )
    except Exception as exc:
        logger.warning("auth_user_sync_failed", error=str(exc))
        return CurrentUser(
            id=clerk_id,
            clerk_id=clerk_id,
            email=email,
            is_authenticated=True,
        )


async def resolve_request_user_id(request) -> str:
    """Resolve storage user id from Authorization header (middleware)."""
    if not settings.auth_enabled:
        return DEFAULT_USER_ID

    auth_header = request.headers.get("authorization", "")
    if not auth_header.lower().startswith("bearer "):
        return DEFAULT_USER_ID

    token = auth_header[7:].strip()
    if not token:
        return DEFAULT_USER_ID

    try:
        from fastapi.security import HTTPAuthorizationCredentials

        user = await _resolve_authenticated_user(
            HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        )
        return user.id
    except Exception:
        return DEFAULT_USER_ID


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> CurrentUser:
    if not settings.auth_enabled:
        return CurrentUser(
            id=DEFAULT_USER_ID,
            clerk_id=None,
            email=DEFAULT_USER_EMAIL,
            is_authenticated=False,
        )

    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
        )

    return await _resolve_authenticated_user(credentials)


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> CurrentUser:
    """Like get_current_user but falls back to demo user when auth disabled or no token."""
    if not settings.auth_enabled:
        return CurrentUser(
            id=DEFAULT_USER_ID,
            clerk_id=None,
            email=DEFAULT_USER_EMAIL,
            is_authenticated=False,
        )
    if not credentials:
        return CurrentUser(
            id=DEFAULT_USER_ID,
            clerk_id=None,
            email=DEFAULT_USER_EMAIL,
            is_authenticated=False,
        )
    return await _resolve_authenticated_user(credentials)
