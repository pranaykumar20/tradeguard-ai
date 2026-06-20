"""Phase 4.2 semi-automated strategy tests."""

from unittest.mock import AsyncMock, patch

import pytest

from app.db.storage import MemoryStorageBackend
from app.strategies.evaluator import evaluate_trigger
from app.services.strategies import StrategyService
from tests.helpers import MOCK_FEATURES


def test_sector_exposure_trigger_above():
    portfolio = {"sector_exposure": {"Technology": 42.0}}
    config = {
        "sector": "Technology",
        "threshold_pct": 25.0,
        "comparison": "above",
        "action_ticker": "QQQ",
        "action_side": "sell",
        "quantity": 1,
    }
    intent = evaluate_trigger("sector_exposure", config, portfolio)
    assert intent is not None
    assert intent["ticker"] == "QQQ"
    assert intent["side"] == "sell"


def test_sector_exposure_not_triggered():
    portfolio = {"sector_exposure": {"Technology": 20.0}}
    config = {
        "sector": "Technology",
        "threshold_pct": 25.0,
        "comparison": "above",
        "action_ticker": "QQQ",
        "action_side": "sell",
        "quantity": 1,
    }
    assert evaluate_trigger("sector_exposure", config, portfolio) is None


@pytest.mark.asyncio
async def test_strategy_crud():
    store = MemoryStorageBackend()
    store._path = store._path.parent / "test_strategy_crud.json"
    await store.init()
    store._data["trade_strategies"] = []
    store._persist()

    with patch("app.services.strategies.get_storage", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = store
        service = StrategyService()
        created = await service.create_strategy(
            {
                "name": "Test",
                "description": "desc",
                "strategy_type": "sector_exposure",
                "config": {
                    "sector": "Technology",
                    "threshold_pct": 25,
                    "comparison": "above",
                    "action_ticker": "QQQ",
                    "action_side": "sell",
                    "quantity": 1,
                },
                "auto_approve": False,
                "enabled": True,
            }
        )
        assert created["name"] == "Test"
        listed = await service.list_strategies()
        assert len(listed) == 1

    await store.close()


@pytest.mark.asyncio
async def test_evaluate_not_triggered():
    store = MemoryStorageBackend()
    store._path = store._path.parent / "test_strategy_not_triggered.json"
    await store.init()
    store._data["trade_strategies"] = []
    store._data["strategy_proposals"] = []
    store._persist()

    with patch("app.services.strategies.get_storage", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = store
        service = StrategyService()
        strategy = await service.create_strategy(
            {
                "name": "Low tech",
                "strategy_type": "sector_exposure",
                "config": {
                    "sector": "Technology",
                    "threshold_pct": 99,
                    "comparison": "above",
                    "action_ticker": "QQQ",
                    "action_side": "sell",
                    "quantity": 1,
                },
                "enabled": True,
            }
        )
        result = await service.evaluate_strategy(strategy["id"])
        assert result["status"] == "not_triggered"

    await store.close()


@pytest.mark.asyncio
async def test_auto_execute_on_allow():
    store = MemoryStorageBackend()
    store._path = store._path.parent / "test_strategy_auto_exec.json"
    await store.init()
    store._data["trade_strategies"] = []
    store._data["strategy_proposals"] = []
    store._data["approval_requests"] = []
    store._persist()

    from app.mcp.mock_client import MockRobinhoodMCPClient

    with patch("app.services.strategies.get_storage", new_callable=AsyncMock) as mock_get, patch(
        "app.services.execution.get_storage", new_callable=AsyncMock
    ) as mock_exec_get, patch(
        "app.services.monitoring.get_storage", new_callable=AsyncMock
    ) as mock_mon_get, patch(
        "app.services.automation.get_storage", new_callable=AsyncMock
    ) as mock_auto_get, patch(
        "app.risk.engine.compute_ticker_features", new_callable=AsyncMock
    ) as mock_features, patch(
        "app.services.strategies.settings"
    ) as mock_settings:
        mock_get.return_value = store
        mock_exec_get.return_value = store
        mock_mon_get.return_value = store
        mock_auto_get.return_value = store
        mock_features.return_value = MOCK_FEATURES.copy()
        mock_settings.strategies_auto_execute = True
        mock_settings.strategies_enabled = True
        mock_settings.robinhood_mcp_enabled = False
        mock_settings.automation_feature_enabled = True
        mock_settings.automation_max_daily_trades = 5

        service = StrategyService()
        service.execution.mcp = MockRobinhoodMCPClient()
        service.automation.can_auto_execute = AsyncMock(return_value=(True, ""))
        service.automation.record_auto_trade = AsyncMock()
        service.automation.log_audit = AsyncMock()

        strategy = await service.create_strategy(
            {
                "name": "Tech trim auto",
                "strategy_type": "sector_exposure",
                "config": {
                    "sector": "Technology",
                    "threshold_pct": 25,
                    "comparison": "above",
                    "action_ticker": "QQQ",
                    "action_side": "sell",
                    "quantity": 1,
                },
                "auto_approve": True,
                "enabled": True,
            }
        )
        result = await service.evaluate_strategy(strategy["id"])
        assert result["status"] in {"auto_executed", "pending_approval", "blocked"}
        if result["status"] == "auto_executed":
            assert result["proposal"]["status"] == "auto_executed"

    await store.close()
