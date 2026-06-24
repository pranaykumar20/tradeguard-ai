"""Per-user Robinhood Agentic MCP OAuth connection."""

from __future__ import annotations

import base64
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
import structlog

from app.core.config import settings
from app.core.secrets import decrypt_secret, encrypt_secret
from app.core.user_context import user_scope
from app.db.storage import get_storage

logger = structlog.get_logger()

GLOBAL_USER_ID = "_global"
MCP_RESOURCE = "https://agent.robinhood.com/mcp/trading"
OAUTH_CLIENT_STATE_KEY = "robinhood_oauth_client"
OAUTH_PENDING_PREFIX = "robinhood_oauth_pending:"
# app_state.key is VARCHAR(64); prefix is 24 chars → keep generated state under 40 chars.
OAUTH_STATE_BYTES = 24

BROKER_ID = "robinhood_agentic"
ACCOUNT_ID = "agentic-main"


class RobinhoodConnectService:
    def mcp_url(self) -> str:
        return settings.effective_robinhood_mcp_url

    async def get_status(self) -> dict:
        meta = await self._connection_meta()
        connected = self._is_connected_meta(meta)
        return {
            "connected": connected,
            "connected_at": meta.get("connected_at"),
            "broker_id": BROKER_ID,
            "account_id": ACCOUNT_ID,
            "mcp_url": self.mcp_url(),
            "oauth_available": True,
        }

    async def is_user_connected(self) -> bool:
        meta = await self._connection_meta()
        return self._is_connected_meta(meta)

    async def start_connect(self, *, return_path: str = "/onboarding") -> dict:
        redirect_uri = settings.robinhood_oauth_redirect_uri
        client_id = await self._ensure_oauth_client(redirect_uri)
        code_verifier, code_challenge = _pkce_pair()
        state = secrets.token_urlsafe(OAUTH_STATE_BYTES)

        from app.core.user_context import get_current_user_id

        await self._set_global_state(
            f"{OAUTH_PENDING_PREFIX}{state}",
            {
                "user_id": get_current_user_id(),
                "code_verifier": code_verifier,
                "redirect_uri": redirect_uri,
                "return_path": return_path.strip() or "/onboarding",
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        )

        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "internal",
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "resource": MCP_RESOURCE,
        }
        authorization_url = f"https://robinhood.com/oauth?{urlencode(params)}"
        return {
            "authorization_url": authorization_url,
            "state": state,
            "redirect_uri": redirect_uri,
        }

    async def handle_callback(self, code: str, state: str) -> str:
        pending = await self._get_global_state(f"{OAUTH_PENDING_PREFIX}{state}")
        if not pending:
            return _frontend_redirect("error", "invalid_state")

        await self._delete_global_state(f"{OAUTH_PENDING_PREFIX}{state}")

        user_id = pending.get("user_id")
        if not user_id:
            return _frontend_redirect("error", "missing_user")

        redirect_uri = pending.get("redirect_uri") or settings.robinhood_oauth_redirect_uri
        return_path = pending.get("return_path") or "/onboarding"
        client = await self._get_registered_client()
        if not client:
            return _frontend_redirect("error", "client_not_registered", return_path)

        try:
            tokens = await self._exchange_code(
                code=code,
                code_verifier=pending["code_verifier"],
                redirect_uri=redirect_uri,
                client_id=client["client_id"],
            )
        except Exception as exc:
            logger.warning("robinhood_oauth_exchange_failed", error=str(exc))
            return _frontend_redirect("error", "token_exchange_failed", return_path)

        async with user_scope(user_id):
            await self._persist_tokens(tokens, client_id=client["client_id"])

        return _frontend_redirect("connected", None, return_path)

    async def disconnect(self) -> dict:
        storage = await get_storage()
        account = await storage.get_broker_account(BROKER_ID, ACCOUNT_ID)
        if account:
            await storage.update_broker_account(
                account["id"],
                {
                    "meta": {
                        "mcp": {
                            "connected": False,
                            "disconnected_at": datetime.now(timezone.utc).isoformat(),
                        }
                    }
                },
            )
        return await self.get_status()

    async def get_valid_access_token(self) -> str | None:
        meta = await self._connection_meta()
        if not self._is_connected_meta(meta):
            return None

        access_enc = meta.get("access_token_enc") or ""
        refresh_enc = meta.get("refresh_token_enc") or ""
        expires_at = meta.get("expires_at")

        if expires_at:
            try:
                expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                if expiry > datetime.now(timezone.utc) + timedelta(seconds=60):
                    return decrypt_secret(access_enc)
            except ValueError:
                pass

        if not refresh_enc:
            try:
                return decrypt_secret(access_enc)
            except ValueError:
                return None

        client = await self._get_registered_client()
        if not client:
            return None

        try:
            tokens = await self._refresh_tokens(
                refresh_token=decrypt_secret(refresh_enc),
                client_id=client["client_id"],
            )
        except Exception as exc:
            logger.warning("robinhood_token_refresh_failed", error=str(exc))
            return None

        await self._persist_tokens(tokens, client_id=client["client_id"])
        return tokens.get("access_token")

    async def _connection_meta(self) -> dict:
        storage = await get_storage()
        account = await storage.get_broker_account(BROKER_ID, ACCOUNT_ID)
        if not account:
            return {}
        return (account.get("meta") or {}).get("mcp") or {}

    @staticmethod
    def _is_connected_meta(meta: dict) -> bool:
        return bool(meta.get("connected") and meta.get("access_token_enc"))

    async def _persist_tokens(self, tokens: dict, *, client_id: str) -> None:
        storage = await get_storage()
        expires_in = tokens.get("expires_in")
        expires_at = None
        if expires_in:
            expires_at = (datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))).isoformat()

        mcp_meta = {
            "connected": True,
            "connected_at": datetime.now(timezone.utc).isoformat(),
            "client_id": client_id,
            "access_token_enc": encrypt_secret(tokens.get("access_token", "")),
            "refresh_token_enc": encrypt_secret(tokens.get("refresh_token", "")),
            "expires_at": expires_at,
            "scope": tokens.get("scope", "internal"),
        }

        account = await storage.get_broker_account(BROKER_ID, ACCOUNT_ID)
        if account:
            await storage.update_broker_account(account["id"], {"meta": {"mcp": mcp_meta}, "enabled": True})
        else:
            await storage.create_broker_account(
                {
                    "broker_id": BROKER_ID,
                    "account_id": ACCOUNT_ID,
                    "label": "Robinhood Agentic",
                    "account_type": "taxable",
                    "enabled": True,
                    "meta": {"mcp": mcp_meta},
                }
            )

    async def _ensure_oauth_client(self, redirect_uri: str) -> str:
        existing = await self._get_registered_client()
        if existing and existing.get("redirect_uri") == redirect_uri:
            return existing["client_id"]

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                "https://agent.robinhood.com/oauth/trading/register",
                json={
                    "client_name": "TradeGuard AI",
                    "redirect_uris": [redirect_uri],
                    "grant_types": ["authorization_code"],
                    "response_types": ["code"],
                    "token_endpoint_auth_method": "none",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        payload = {
            "client_id": data["client_id"],
            "redirect_uri": redirect_uri,
            "registered_at": datetime.now(timezone.utc).isoformat(),
        }
        await self._set_global_state(OAUTH_CLIENT_STATE_KEY, payload)
        return data["client_id"]

    async def _get_registered_client(self) -> dict | None:
        return await self._get_global_state(OAUTH_CLIENT_STATE_KEY)

    async def _exchange_code(
        self,
        *,
        code: str,
        code_verifier: str,
        redirect_uri: str,
        client_id: str,
    ) -> dict:
        return await self._token_request(
            {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": client_id,
                "code_verifier": code_verifier,
                "resource": MCP_RESOURCE,
            }
        )

    async def _refresh_tokens(self, *, refresh_token: str, client_id: str) -> dict:
        return await self._token_request(
            {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": client_id,
                "resource": MCP_RESOURCE,
            }
        )

    async def _token_request(self, form: dict) -> dict:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                "https://api.robinhood.com/oauth2/token/",
                data=form,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            resp.raise_for_status()
            return resp.json()

    async def _get_global_state(self, key: str) -> dict | None:
        async with user_scope(GLOBAL_USER_ID):
            storage = await get_storage()
            return await storage.get_app_state(key)

    async def _set_global_state(self, key: str, value: dict) -> None:
        async with user_scope(GLOBAL_USER_ID):
            storage = await get_storage()
            await storage.set_app_state(key, value)

    async def _delete_global_state(self, key: str) -> None:
        async with user_scope(GLOBAL_USER_ID):
            storage = await get_storage()
            current = await storage.get_app_state(key)
            if current is not None:
                await storage.set_app_state(key, {})


def _pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("utf-8")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("utf-8")
    return verifier, challenge


def _frontend_redirect(status: str, reason: str | None, return_path: str = "/onboarding") -> str:
    base = settings.frontend_onboarding_url.rsplit("/onboarding", 1)[0]
    path = return_path if return_path.startswith("/") else f"/{return_path}"
    url = f"{base}{path}"
    query = {"robinhood": status}
    if reason:
        query["reason"] = reason
    return f"{url}?{urlencode(query)}"
