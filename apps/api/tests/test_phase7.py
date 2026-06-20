"""Phase 7 — multi-broker, tax lots, options workflow, household."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.brokers.factory import list_brokers
from app.brokers.mock_ira import MockIRABroker
from app.main import app
from app.services.accounts import AccountService
from app.services.execution import ExecutionService
from app.services.portfolio import PortfolioService
from app.services.tax import TaxService
from tests.helpers import MOCK_FEATURES


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_multi_broker_registry():
    brokers = list_brokers()
    ids = {b["broker_id"] for b in brokers}
    assert "mock_ira" in ids


@pytest.mark.asyncio
async def test_mock_ira_portfolio():
    broker = MockIRABroker()
    snap = await broker.get_portfolio_snapshot()
    assert snap["broker_id"] == "mock_ira"
    assert "QQQ" in snap["positions"]


@pytest.mark.asyncio
async def test_household_aggregation():
    await AccountService().ensure_defaults()
    household = await PortfolioService().get_household()
    assert household["account_count"] >= 1
    assert household["total_value"] > 0
    assert household["positions"]


@pytest.mark.asyncio
async def test_tax_lot_wash_sale_warning():
    await AccountService().ensure_defaults()
    analysis = await TaxService().analyze_sell("MSFT", 2, 400, account_id="ira-traditional")
    assert analysis["enabled"] is True
    assert analysis["lots_selected"]


@pytest.mark.asyncio
async def test_options_preview_allowed_with_approval():
    svc = ExecutionService()
    with patch("app.risk.engine.compute_ticker_features", new_callable=AsyncMock) as mock_features:
        mock_features.return_value = MOCK_FEATURES.copy()
        preview = await svc.preview_order(
            ticker="NVDA",
            side="buy",
            quantity=1,
            limit_price=50,
            asset_type="option",
            broker_id="mock_ira",
            option_contract={"option_type": "call", "strike": 140, "expiry": "2026-07-18"},
        )
    assert preview["risk"]["allowed"] is True
    assert preview["risk"]["requires_approval"] is True


@pytest.mark.asyncio
async def test_accounts_api(client):
    resp = await client.get("/api/accounts")
    assert resp.status_code == 200
    data = resp.json()
    assert "accounts" in data
    assert len(data["accounts"]) >= 1


@pytest.mark.asyncio
async def test_household_api(client):
    resp = await client.get("/api/accounts/household")
    assert resp.status_code == 200
    data = resp.json()
    assert data["account_count"] >= 1
    assert "sector_exposure" in data


@pytest.mark.asyncio
async def test_health_phase_7(client):
    resp = await client.get("/api/health/ready")
    assert resp.status_code == 200
    assert resp.json()["phase"] == 9
