"""Phase 4.3 performance validation gate tests."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.db.storage import MemoryStorageBackend
from app.services.validation import ValidationService
from app.validation.metrics import compute_metrics, evaluate_gate


def _trade(days_ago: int, pnl: float, status: str = "filled", verdict: str = "ALLOW") -> dict:
    ts = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return {
        "ticker": "NVDA",
        "side": "buy",
        "quantity": 1,
        "limit_price": 100,
        "fill_price": 100,
        "status": status,
        "verdict": verdict,
        "reason": "test",
        "pnl": pnl if status == "filled" else None,
        "created_at": ts.isoformat(),
    }


def test_compute_metrics_from_trades():
    trades = [_trade(90 - i * 2, 10.0 + (i % 3)) for i in range(30)]
    metrics = compute_metrics(trades, starting_capital=10_000)
    assert metrics["filled_trades"] == 30
    assert metrics["total_pnl"] > 0
    assert metrics["track_record_months"] >= 1.0
    assert metrics["win_rate"] > 0


def test_evaluate_gate_fails_short_track_record():
    trades = [_trade(5, 10.0) for _ in range(5)]
    metrics = compute_metrics(trades)
    thresholds = {
        "min_months": 3.0,
        "min_sharpe": 0.5,
        "max_drawdown_pct": 15.0,
        "min_win_rate": 45.0,
        "min_total_pnl": 0.0,
        "max_rule_violations": 10,
        "min_filled_trades": 20,
    }
    passed, checks, summary = evaluate_gate(metrics, thresholds)
    assert passed is False
    assert "Track record" in summary or any(c["name"] == "track_record_months" and not c["passed"] for c in checks)


def test_evaluate_gate_passes_strong_track_record():
    trades = [_trade(120 - i * 2, 12.0 + (i % 4)) for i in range(50)]
    metrics = compute_metrics(trades)
    assert metrics["track_record_months"] >= 3.0
    thresholds = {
        "min_months": 3.0,
        "min_sharpe": 0.5,
        "max_drawdown_pct": 15.0,
        "min_win_rate": 45.0,
        "min_total_pnl": 0.0,
        "max_rule_violations": 10,
        "min_filled_trades": 20,
    }
    passed, _, summary = evaluate_gate(metrics, thresholds)
    assert passed is True
    assert "passed" in summary.lower()


@pytest.mark.asyncio
async def test_validation_report_empty_journal():
    store = MemoryStorageBackend()
    store._path = store._path.parent / "test_validation_empty.json"
    await store.init()
    store._data["paper_trades"] = []
    store._persist()

    with patch("app.services.validation.get_storage", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = store
        report = await ValidationService().build_report()
        assert report["passed"] is False
        assert report["automation_unlocked"] is False
        assert len(report["checks"]) >= 5

    await store.close()


@pytest.mark.asyncio
async def test_seed_demo_passes_gate():
    store = MemoryStorageBackend()
    store._path = store._path.parent / "test_validation_seed.json"
    await store.init()
    store._data["paper_trades"] = []
    store._persist()

    with patch("app.services.validation.get_storage", new_callable=AsyncMock) as mock_get, patch(
        "app.services.validation.settings"
    ) as mock_settings:
        mock_get.return_value = store
        mock_settings.validation_allow_demo_seed = True
        mock_settings.validation_dev_bypass = False
        mock_settings.app_env = "development"
        mock_settings.validation_gate_enabled = True
        mock_settings.validation_min_months = 3.0
        mock_settings.validation_min_sharpe = 0.5
        mock_settings.validation_max_drawdown_pct = 15.0
        mock_settings.validation_min_win_rate = 45.0
        mock_settings.validation_min_total_pnl = 0.0
        mock_settings.validation_max_rule_violations = 10
        mock_settings.validation_min_filled_trades = 20
        mock_settings.validation_starting_capital = 10_000.0

        result = await ValidationService().seed_demo_track_record()
        assert result["seeded_trades"] == 48
        assert result["report"]["passed"] is True
        assert result["report"]["automation_unlocked"] is True

    await store.close()


@pytest.mark.asyncio
async def test_automation_allowed_with_dev_bypass():
    service = ValidationService()
    with patch.object(service, "check_gate", new_callable=AsyncMock) as mock_gate:
        mock_gate.return_value = (True, {"summary": "Dev bypass active", "automation_unlocked": True})
        allowed, reason = await service.automation_allowed()
        assert allowed is True
        assert reason == ""
