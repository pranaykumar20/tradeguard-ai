"""Robinhood MCP OAuth connect — per-user broker linking."""

import secrets
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.secrets import decrypt_secret, encrypt_secret
from app.core.user_context import user_scope
from app.main import app
from app.services.robinhood_connect import (
    OAUTH_PENDING_PREFIX,
    OAUTH_STATE_BYTES,
    RobinhoodConnectService,
)


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_encrypt_decrypt_roundtrip():
    assert decrypt_secret(encrypt_secret("test-token-123")) == "test-token-123"


@pytest.mark.asyncio
async def test_robinhood_connect_status_not_connected():
    svc = RobinhoodConnectService()
    status = await svc.get_status()
    assert status["connected"] is False
    assert status["broker_id"] == "robinhood_agentic"
    assert "mcp_url" in status


@pytest.mark.asyncio
async def test_robinhood_persist_and_disconnect():
    svc = RobinhoodConnectService()
    await svc._persist_tokens(
        {
            "access_token": "access-abc",
            "refresh_token": "refresh-xyz",
            "expires_in": 3600,
            "scope": "internal",
        },
        client_id="client-test",
    )
    assert await svc.is_user_connected() is True
    status = await svc.get_status()
    assert status["connected"] is True
    assert status["connected_at"]

    token = await svc.get_valid_access_token()
    assert token == "access-abc"

    disconnected = await svc.disconnect()
    assert disconnected["connected"] is False
    assert await svc.is_user_connected() is False


def test_oauth_pending_state_key_fits_app_state_column():
    state = secrets.token_urlsafe(OAUTH_STATE_BYTES)
    key = f"{OAUTH_PENDING_PREFIX}{state}"
    assert len(key) <= 64


@pytest.mark.asyncio
async def test_start_connect_returns_authorization_url():
    svc = RobinhoodConnectService()
    with patch.object(svc, "_ensure_oauth_client", new=AsyncMock(return_value="client-test-id")):
        payload = await svc.start_connect(return_path="/onboarding")
    assert "authorization_url" in payload
    assert "robinhood.com/oauth" in payload["authorization_url"]
    assert "client-test-id" in payload["authorization_url"]
    assert payload["state"]


@pytest.mark.asyncio
async def test_oauth_callback_persists_tokens():
    svc = RobinhoodConnectService()
    state = "test-state-123"
    await svc._set_global_state(
        f"robinhood_oauth_pending:{state}",
        {
            "user_id": "default",
            "code_verifier": "verifier",
            "redirect_uri": "http://localhost:8000/api/brokers/robinhood/callback",
            "return_path": "/onboarding",
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    await svc._set_global_state(
        "robinhood_oauth_client",
        {"client_id": "client-test-id", "redirect_uri": "http://localhost:8000/api/brokers/robinhood/callback"},
    )

    with patch.object(
        svc,
        "_exchange_code",
        new=AsyncMock(
            return_value={
                "access_token": "new-access",
                "refresh_token": "new-refresh",
                "expires_in": 7200,
            }
        ),
    ):
        redirect = await svc.handle_callback(code="auth-code", state=state)

    assert "robinhood=connected" in redirect
    async with user_scope("default"):
        assert await svc.is_user_connected() is True


@pytest.mark.asyncio
async def test_robinhood_brokers_api(client):
    status = await client.get("/api/brokers/robinhood/status")
    assert status.status_code == 200
    assert status.json()["connected"] is False

    connect_service = RobinhoodConnectService()
    with patch.object(connect_service, "_ensure_oauth_client", new=AsyncMock(return_value="client-test-id")):
        with patch("app.api.routes.brokers.connect_service", connect_service):
            connect = await client.post(
                "/api/brokers/robinhood/connect",
                json={"return_path": "/onboarding"},
            )
    assert connect.status_code == 200
    data = connect.json()
    assert "authorization_url" in data


@pytest.mark.asyncio
async def test_onboarding_reflects_robinhood_connection(client):
    svc = RobinhoodConnectService()
    await svc._persist_tokens(
        {"access_token": "tok", "refresh_token": "ref", "expires_in": 3600},
        client_id="client-test",
    )

    resp = await client.get("/api/onboarding/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["mcp"]["connected"] is True
    connect_step = next(s for s in data["steps"] if s["id"] == "connect_mcp")
    assert connect_step["completed"] is True
