"""Phase 5 — production hardening tests."""

from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.main import app
from app.providers.alerts.composite import CompositeAlertProvider
from app.providers.alerts.email import EmailAlertProvider
from app.providers.alerts.factory import get_alert_provider, reset_alert_provider
from app.providers.alerts.mock import MockAlertProvider


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_liveness(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["phase"] == 9


@pytest.mark.asyncio
async def test_health_ready_endpoint(client):
    resp = await client.get("/health/ready")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "checks" in data
    assert data["phase"] == 9


@pytest.mark.asyncio
async def test_api_health_ready(client):
    resp = await client.get("/api/health/ready")
    assert resp.status_code == 200
    assert resp.json()["phase"] == 9


@pytest.mark.asyncio
async def test_auth_me_demo_user(client):
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 200
    data = resp.json()
    assert data["auth_enabled"] is False
    assert data["user"]["id"] == "default"
    assert data["user"]["is_authenticated"] is False
    assert data["user"]["role"] == "platform_admin"
    assert "admin:manage" in data["user"]["permissions"]


def test_database_url_normalization():
    from app.core.config import _normalize_database_url

    assert (
        _normalize_database_url("postgres://u:p@host/db")
        == "postgresql+asyncpg://u:p@host/db"
    )
    assert (
        _normalize_database_url("postgresql://u:p@host/db")
        == "postgresql+asyncpg://u:p@host/db"
    )
    assert (
        _normalize_database_url("postgresql+asyncpg://u:p@host/db")
        == "postgresql+asyncpg://u:p@host/db"
    )


@pytest.mark.asyncio
async def test_email_alert_falls_back_to_mock():
    provider = EmailAlertProvider()
    result = await provider.send("Test", "Detail", "high", "test_event")
    assert result["status"] == "sent"
    assert result["provider"] == "mock"


@pytest.mark.asyncio
async def test_email_alert_sends_when_configured():
    provider = EmailAlertProvider()
    with patch.object(settings, "smtp_host", "smtp.example.com"), patch.object(
        settings, "alert_email_to", "ops@example.com"
    ), patch.object(settings, "smtp_user", ""), patch.object(
        settings, "smtp_password", ""
    ), patch.object(
        provider, "_send_sync", MagicMock()
    ) as mock_send:
        result = await provider.send("Test", "Detail", "high", "test_event")
        assert result["provider"] == "email"
        mock_send.assert_called_once()


@pytest.mark.asyncio
async def test_composite_alert_provider():
    mock_a = MockAlertProvider()
    mock_b = MockAlertProvider()
    composite = CompositeAlertProvider([mock_a, mock_b])
    result = await composite.send("Title", "Detail", "medium", "composite_test")
    assert result["provider"] == "composite"
    assert result["channels"] == ["mock", "mock"]


@pytest.mark.asyncio
async def test_alert_factory_composite_when_both_channels():
    reset_alert_provider()
    with patch.object(settings, "alert_provider", "auto"), patch.object(
        settings, "slack_webhook_url", "https://hooks.slack.com/test"
    ), patch.object(settings, "smtp_host", "smtp.example.com"), patch.object(
        settings, "alert_email_to", "ops@example.com"
    ):
        provider = get_alert_provider()
        assert provider.provider_name == "composite"
    reset_alert_provider()


@pytest.mark.asyncio
async def test_get_or_create_user_memory():
    from app.db.storage import MemoryStorageBackend

    backend = MemoryStorageBackend()
    await backend.init()
    user = await backend.get_or_create_user("clerk_123", "a@b.com", "Alice")
    assert user["clerk_id"] == "clerk_123"
    assert user["email"] == "a@b.com"
    again = await backend.get_or_create_user("clerk_123", "a@b.com", "Alice")
    assert again["id"] == user["id"]
    await backend.close()
