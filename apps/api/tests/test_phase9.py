"""Phase 9 — push notifications, onboarding wizard, product UX."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.onboarding import OnboardingService
from app.services.push import PushNotificationService


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_push_subscribe_and_inbox():
    push = PushNotificationService()
    await push.subscribe({"endpoint": "https://push.test/device-1", "keys": {"p256dh": "x", "auth": "y"}})
    note = await push.notify("Test alert", "Body text", "test_event", "high")
    assert note is not None
    inbox = await push.list_inbox(limit=5)
    assert any(n["title"] == "Test alert" for n in inbox)
    marked = await push.mark_read(note["id"])
    assert marked["read"] is True


@pytest.mark.asyncio
async def test_onboarding_status_and_complete():
    svc = OnboardingService()
    await svc.reset()
    status = await svc.get_status()
    assert status["total_steps"] >= 5
    assert "steps" in status
    updated = await svc.complete_step("fund_account")
    assert any(s["id"] == "fund_account" and s["completed"] for s in updated["steps"])


@pytest.mark.asyncio
async def test_push_api(client):
    resp = await client.get("/api/push/config")
    assert resp.status_code == 200
    assert resp.json()["enabled"] is True

    sub = await client.post(
        "/api/push/subscribe",
        json={"endpoint": "https://push.test/api-1", "keys": {"p256dh": "a", "auth": "b"}},
    )
    assert sub.status_code == 200

    inbox = await client.get("/api/push/inbox")
    assert inbox.status_code == 200
    assert "notifications" in inbox.json()


@pytest.mark.asyncio
async def test_onboarding_api(client):
    await client.post("/api/onboarding/reset")
    resp = await client.get("/api/onboarding/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["progress_pct"] >= 0

    complete = await client.post("/api/onboarding/complete", json={"step_id": "complete"})
    assert complete.status_code == 200
    assert complete.json()["steps"][-1]["completed"] is True


@pytest.mark.asyncio
async def test_execution_emits_push_inbox(client):
    preview = await client.post(
        "/api/execution/preview",
        json={"ticker": "NVDA", "side": "buy", "quantity": 1, "broker_id": "mock_ira"},
    )
    assert preview.status_code == 200

    submit = await client.post(
        "/api/execution/submit",
        json={"ticker": "NVDA", "side": "buy", "quantity": 1, "broker_id": "mock_ira"},
    )
    assert submit.status_code == 200

    inbox = await client.get("/api/push/inbox?limit=5")
    assert inbox.status_code == 200
    titles = [n["title"] for n in inbox.json()["notifications"]]
    assert any("Approval needed" in t for t in titles)


@pytest.mark.asyncio
async def test_health_phase_9(client):
    resp = await client.get("/api/health/ready")
    assert resp.status_code == 200
    data = resp.json()
    assert data["phase"] == 9
    assert data["push_notifications_enabled"] is True
