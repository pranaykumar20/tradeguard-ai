"""Phase 4 monitoring, alerting, and trading halt tests."""

from unittest.mock import AsyncMock, patch

import pytest

from app.core.config import settings
from app.db.storage import MemoryStorageBackend
from app.providers.alerts.mock import MockAlertProvider
from app.services.execution import ExecutionService
from app.services.monitoring import MonitoringService
from tests.helpers import MOCK_FEATURES


@pytest.mark.asyncio
async def test_mock_alert_provider():
    provider = MockAlertProvider()
    result = await provider.send("Test", "Detail", "high", "test_event")
    assert result["status"] == "sent"
    assert result["provider"] == "mock"


@pytest.mark.asyncio
async def test_trading_halt_and_resume():
    store = MemoryStorageBackend()
    store._path = store._path.parent / "test_monitoring_store.json"
    await store.init()

    with patch("app.services.monitoring.get_storage", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = store
        service = MonitoringService()

        halted, _ = await service.is_trading_halted()
        assert halted is False

        await service.halt_trading("Daily loss limit hit", daily_pnl=-75.0)
        halted, reason = await service.is_trading_halted()
        assert halted is True
        assert "Daily loss" in reason

        await service.resume_trading()
        halted, _ = await service.is_trading_halted()
        assert halted is False

    await store.close()


@pytest.mark.asyncio
async def test_emit_alert_dedupes():
    store = MemoryStorageBackend()
    store._path = store._path.parent / "test_alert_dedupe_store.json"
    await store.init()
    store._data["alert_events"] = []
    store._persist()

    with patch("app.services.monitoring.get_storage", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = store
        service = MonitoringService()
        service.alerts = MockAlertProvider()

        first = await service.emit_alert("dedupe_test", "high", "Blocked", "NVDA too large")
        second = await service.emit_alert("dedupe_test", "high", "Blocked", "NVDA too large")
        assert first is not None
        assert second is None

        events = await store.list_alert_events()
        assert len(events) == 1

    await store.close()


@pytest.mark.asyncio
async def test_monitoring_halts_on_daily_loss():
    store = MemoryStorageBackend()
    store._path = store._path.parent / "test_monitoring_halt_store.json"
    await store.init()

    with patch("app.services.monitoring.get_storage", new_callable=AsyncMock) as mock_get, patch(
        "app.services.monitoring.demo_portfolio"
    ) as mock_portfolio, patch(
        "app.services.monitoring.RiskEngine.portfolio_snapshot", new_callable=AsyncMock
    ) as mock_snapshot:
        mock_get.return_value = store
        mock_portfolio.return_value = {
            "account_value": 10000,
            "daily_pnl": -60.0,
            "max_drawdown_est": 3.0,
            "sector_exposure": {},
            "positions": {},
            "beta": 1.0,
        }
        mock_snapshot.return_value = {"alerts": []}

        service = MonitoringService()
        service.alerts = MockAlertProvider()
        result = await service.run_check()

        assert result["trading_halted"] is True
        halted, _ = await service.is_trading_halted()
        assert halted is True

    await store.close()


@pytest.mark.asyncio
async def test_execution_blocked_when_halted():
    store = MemoryStorageBackend()
    store._path = store._path.parent / "test_execution_halt_store.json"
    await store.init()
    await store.set_app_state(
        "trading",
        {"halted": True, "reason": "Daily loss limit hit"},
    )

    with patch("app.services.execution.get_storage", new_callable=AsyncMock) as mock_get, patch(
        "app.services.monitoring.get_storage", new_callable=AsyncMock
    ) as mock_mon_get, patch(
        "app.services.execution.demo_portfolio"
    ) as mock_portfolio, patch(
        "app.risk.engine.compute_ticker_features", new_callable=AsyncMock
    ) as mock_features:
        mock_get.return_value = store
        mock_mon_get.return_value = store
        mock_portfolio.return_value = {
            "daily_pnl": 0,
            "sector_exposure": {"Technology": 10},
            "positions": {},
            "beta": 1.0,
        }
        mock_features.return_value = MOCK_FEATURES.copy()

        service = ExecutionService()
        preview = await service.preview_order("MSFT", "buy", 1, limit_price=100)
        assert preview["risk"]["allowed"] is False
        assert any("Trading halted" in b for b in preview["risk"]["blocks"])

    await store.close()


@pytest.mark.asyncio
async def test_memory_storage_alert_events():
    store = MemoryStorageBackend()
    store._path = store._path.parent / "test_alert_events_store.json"
    await store.init()
    store._data["alert_events"] = []
    store._persist()
    event = await store.create_alert_event(
        {
            "event_type": "block_event",
            "severity": "high",
            "title": "Blocked",
            "detail": "test",
            "channels_sent": ["mock"],
        }
    )
    assert event["event_type"] == "block_event"
    events = await store.list_alert_events()
    assert len(events) == 1
    await store.close()
