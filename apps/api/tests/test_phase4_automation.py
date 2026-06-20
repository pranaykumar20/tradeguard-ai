"""Phase 4.4 constrained automation tests."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.db.storage import MemoryStorageBackend
from app.services.automation import AutomationService


@pytest.mark.asyncio
async def test_automation_master_switch():
    store = MemoryStorageBackend()
    store._path = store._path.parent / "test_automation_switch.json"
    await store.init()

    with patch("app.services.automation.get_storage", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = store
        service = AutomationService()

        state = await service.enable()
        assert state["enabled"] is True

        status = await service.get_status()
        assert status["master_enabled"] is True

        await service.disable(reason="Test kill switch")
        status = await service.get_status()
        assert status["master_enabled"] is False

        audit = await service.list_audit()
        assert any(a["event_type"] == "automation_disabled" for a in audit)

    await store.close()


@pytest.mark.asyncio
async def test_can_auto_execute_requires_master_switch():
    store = MemoryStorageBackend()
    store._path = store._path.parent / "test_automation_can_auto.json"
    await store.init()
    store._data["app_state"] = {}
    store._persist()

    with patch("app.services.automation.get_storage", new_callable=AsyncMock) as mock_get, patch(
        "app.services.automation.settings"
    ) as mock_settings:
        mock_get.return_value = store
        mock_settings.automation_feature_enabled = True
        mock_settings.strategies_auto_execute = True
        mock_settings.automation_max_daily_trades = 5

        service = AutomationService()
        service.monitoring.is_trading_halted = AsyncMock(return_value=(False, ""))
        service.validation.automation_allowed = AsyncMock(return_value=(True, ""))

        ok, reason = await service.can_auto_execute(strategy_auto_approve=True, verdict="ALLOW")
        assert ok is False
        assert "master switch" in reason.lower()

        await service.enable()
        ok, reason = await service.can_auto_execute(strategy_auto_approve=True, verdict="ALLOW")
        assert ok is True

        ok, reason = await service.can_auto_execute(strategy_auto_approve=True, verdict="CAUTION")
        assert ok is False
        assert "ALLOW" in reason

    await store.close()


@pytest.mark.asyncio
async def test_daily_cap_blocks_auto_execute():
    store = MemoryStorageBackend()
    store._path = store._path.parent / "test_automation_cap.json"
    await store.init()
    today = datetime.now(timezone.utc).date().isoformat()
    await store.set_app_state(
        "automation",
        {"enabled": True, "auto_trades_today": 5, "last_reset_date": today},
    )

    with patch("app.services.automation.get_storage", new_callable=AsyncMock) as mock_get, patch(
        "app.services.automation.settings"
    ) as mock_settings:
        mock_get.return_value = store
        mock_settings.automation_feature_enabled = True
        mock_settings.strategies_auto_execute = True
        mock_settings.automation_max_daily_trades = 5

        service = AutomationService()
        service.monitoring.is_trading_halted = AsyncMock(return_value=(False, ""))
        service.validation.automation_allowed = AsyncMock(return_value=(True, ""))

        ok, reason = await service.can_auto_execute(strategy_auto_approve=True, verdict="ALLOW")
        assert ok is False
        assert "cap" in reason.lower()

    await store.close()


@pytest.mark.asyncio
async def test_record_auto_trade_increments_counter():
    store = MemoryStorageBackend()
    store._path = store._path.parent / "test_automation_record.json"
    await store.init()
    await store.set_app_state("automation", {"enabled": True})

    with patch("app.services.automation.get_storage", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = store
        service = AutomationService()
        await service.record_auto_trade("NVDA", "Tech trim", "sell 1 NVDA")
        status = await service.get_status()
        assert status["auto_trades_today"] == 1
        audit = await service.list_audit()
        assert any(a["event_type"] == "auto_executed" for a in audit)

    await store.close()
