"""Phase 8 — observability, audit exports, platform health, backtest."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.storage import get_storage
from app.main import app
from app.services.audit_export import AuditExportService
from app.services.backtest import BacktestService
from app.services.platform_health import PlatformHealthService
from app.services.replay import ReplayService


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_replay_approval_timeline():
    storage = await get_storage()
    approval = await storage.create_approval_request(
        {
            "ticker": "NVDA",
            "side": "buy",
            "quantity": 1,
            "limit_price": 100,
            "order_type": "limit",
            "status": "executed",
            "risk_preview": {"verdict": "ALLOW", "allowed": True, "blocks": [], "warnings": []},
            "mcp_preview": {"status": "preview_ok"},
            "execution_result": {"status": "filled", "order_id": "t1"},
            "order_id": "t1",
            "notes": "test",
            "resolved_at": "2026-06-20T12:00:00+00:00",
        }
    )
    await storage.create_paper_trade(
        {
            "ticker": "NVDA",
            "side": "buy",
            "quantity": 1,
            "limit_price": 100,
            "fill_price": 100,
            "status": "filled",
            "verdict": "ALLOW",
            "reason": "test",
            "pnl": 1.2,
            "approval_id": approval["id"],
            "source": "execution",
        }
    )

    replay = await ReplayService().replay_approval(approval["id"])
    assert replay["event_count"] >= 3
    steps = [e["step"] for e in replay["events"]]
    assert "submitted" in steps
    assert "risk_evaluated" in steps
    assert "journal_logged" in steps


@pytest.mark.asyncio
async def test_audit_export_json():
    storage = await get_storage()
    await storage.create_paper_trade(
        {
            "ticker": "MSFT",
            "side": "buy",
            "quantity": 2,
            "limit_price": 400,
            "status": "filled",
            "verdict": "ALLOW",
            "reason": "export test",
            "pnl": 5.0,
            "source": "manual",
        }
    )
    payload = await AuditExportService().collect(days=90)
    assert payload["counts"]["journal_trades"] >= 1
    assert "journal_trades" in payload


@pytest.mark.asyncio
async def test_audit_export_csv():
    csv_data = await AuditExportService().export_csv(days=90)
    assert "section,id,created_at" in csv_data.splitlines()[0]


@pytest.mark.asyncio
async def test_platform_health_check():
    result = await PlatformHealthService().check(emit_alerts=False)
    assert "readiness" in result
    assert "mcp" in result
    assert "model" in result


@pytest.mark.asyncio
async def test_backtest_strategy():
    storage = await get_storage()
    strategies = await storage.list_trade_strategies()
    assert strategies
    report = await BacktestService().run(strategies[0]["id"], days=90)
    assert report["strategy"]["id"] == strategies[0]["id"]
    assert "metrics_all_trades" in report


@pytest.mark.asyncio
async def test_observability_export_api(client):
    resp = await client.get("/api/observability/export/summary?days=90")
    assert resp.status_code == 200
    assert "counts" in resp.json()


@pytest.mark.asyncio
async def test_observability_platform_api(client):
    resp = await client.get("/api/observability/platform")
    assert resp.status_code == 200
    assert "readiness" in resp.json()


@pytest.mark.asyncio
async def test_health_phase_8(client):
    resp = await client.get("/api/health/ready")
    assert resp.status_code == 200
    assert resp.json()["phase"] == 9
