"""Phase 3 execution and MCP tests."""

from unittest.mock import AsyncMock, patch

import pytest

from app.db.storage import MemoryStorageBackend
from app.mcp.mock_client import MockRobinhoodMCPClient
from app.services.execution import ExecutionService
from tests.helpers import MOCK_FEATURES


@pytest.mark.asyncio
async def test_mock_mcp_portfolio():
    client = MockRobinhoodMCPClient()
    snap = await client.get_portfolio_snapshot()
    assert snap["source"] == "robinhood_mcp_mock"
    assert "NVDA" in snap["positions"]


@pytest.mark.asyncio
async def test_mock_mcp_preview_and_place():
    client = MockRobinhoodMCPClient()
    order = {"ticker": "NVDA", "side": "buy", "quantity": 1, "limit_price": 140.0}
    preview = await client.preview_order(order)
    assert preview["status"] == "preview_ok"

    blocked = await client.place_order(order, approved=False)
    assert blocked["status"] == "rejected"

    filled = await client.place_order(order, approved=True)
    assert filled["status"] == "filled"
    assert filled["order_id"]


@pytest.mark.asyncio
async def test_memory_storage_approvals():
    store = MemoryStorageBackend()
    store._path = store._path.parent / "test_approvals_store.json"
    await store.init()
    row = await store.create_approval_request(
        {
            "ticker": "NVDA",
            "side": "buy",
            "quantity": 1,
            "limit_price": 100,
            "order_type": "limit",
            "status": "pending",
            "risk_preview": {"verdict": "ALLOW"},
            "mcp_preview": {},
            "execution_result": None,
            "order_id": None,
            "notes": "",
        }
    )
    assert row["status"] == "pending"
    pending = await store.list_approval_requests(status="pending")
    assert len(pending) >= 1
    await store.close()


@pytest.mark.asyncio
async def test_execution_submit_and_approve():
    store = MemoryStorageBackend()
    store._path = store._path.parent / "test_exec_store.json"
    await store.init()

    svc = ExecutionService()
    mock_client = MockRobinhoodMCPClient()

    with patch.object(svc, "_resolve_broker", return_value=(mock_client, "robinhood_agentic")):
        with patch("app.services.execution.get_storage", new_callable=AsyncMock) as mock_storage:
            mock_storage.return_value = store
            with patch("app.risk.engine.compute_ticker_features", new_callable=AsyncMock) as mock_risk:
                mock_risk.return_value = MOCK_FEATURES.copy()
                submitted = await svc.submit_for_approval(
                    ticker="NVDA",
                    side="buy",
                    quantity=1,
                    limit_price=100,
                )

    assert submitted["status"] == "pending"
    approval_id = submitted["approval"]["id"]

    with patch.object(svc, "_resolve_broker", return_value=(mock_client, "robinhood_agentic")):
        with patch("app.services.execution.get_storage", new_callable=AsyncMock) as mock_storage:
            mock_storage.return_value = store
            with patch("app.risk.engine.compute_ticker_features", new_callable=AsyncMock) as mock_risk:
                mock_risk.return_value = MOCK_FEATURES.copy()
                result = await svc.approve(approval_id)

    assert result["status"] == "executed"
    assert result["execution"]["status"] == "filled"
    await store.close()


@pytest.mark.asyncio
async def test_execution_blocks_oversized_order():
    store = MemoryStorageBackend()
    store._path = store._path.parent / "test_exec_block_store.json"
    await store.init()

    svc = ExecutionService()
    mock_client = MockRobinhoodMCPClient()

    with patch.object(svc, "_resolve_broker", return_value=(mock_client, "robinhood_agentic")):
        with patch("app.services.execution.get_storage", new_callable=AsyncMock):
            with patch("app.risk.engine.compute_ticker_features", new_callable=AsyncMock) as mock_risk:
                mock_risk.return_value = MOCK_FEATURES.copy()
                result = await svc.submit_for_approval(
                    ticker="NVDA",
                    side="buy",
                    quantity=10,
                    limit_price=100,
                )

    assert result["status"] == "blocked"
    await store.close()


def test_settings_mcp_auto_mock():
    from app.core.config import Settings

    s = Settings(
        mcp_provider="auto",
        robinhood_mcp_enabled=True,
        robinhood_mcp_url="",
    )
    assert s.active_mcp_provider == "mock"
    assert s.use_live_mcp is False

    s2 = Settings(
        mcp_provider="auto",
        robinhood_mcp_enabled=True,
        robinhood_mcp_url="http://localhost:9000/mcp",
    )
    assert s2.active_mcp_provider == "live"
    assert s2.use_live_mcp is True
