"""Phase 2 provider and storage tests."""

import pytest

from app.db.storage import MemoryStorageBackend
from app.providers.market.mock import MockMarketDataProvider
from app.providers.embeddings.mock import MockEmbeddingProvider


@pytest.mark.asyncio
async def test_memory_storage_paper_trades():
    store = MemoryStorageBackend()
    store._path = store._path.parent / "test_store.json"
    await store.init()
    trade = await store.create_paper_trade(
        {
            "ticker": "NVDA",
            "side": "buy",
            "quantity": 1,
            "limit_price": 100,
            "fill_price": None,
            "status": "planned",
            "verdict": "CAUTION",
            "reason": "test",
            "pnl": None,
        }
    )
    assert trade["ticker"] == "NVDA"
    stats = await store.paper_trade_stats()
    assert stats["total_trades"] >= 1
    await store.close()


@pytest.mark.asyncio
async def test_mock_market_provider_bars():
    provider = MockMarketDataProvider()
    bars = await provider.get_daily_bars("NVDA", days=30)
    assert len(bars) == 30
    assert "close" in bars.columns


@pytest.mark.asyncio
async def test_mock_embeddings_deterministic():
    from app.providers.embeddings.mock import MockEmbeddingProvider

    provider = MockEmbeddingProvider()
    a = await provider.embed_text("hello")
    b = await provider.embed_text("hello")
    assert a == b


def test_settings_auto_mock_without_keys(monkeypatch):
    monkeypatch.setenv("POLYGON_API_KEY", "")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("MARKET_DATA_PROVIDER", "auto")
    monkeypatch.setenv("EMBEDDING_PROVIDER", "mock")

    from app.core.config import Settings

    s = Settings()
    assert s.active_market_provider == "mock"
    assert s.active_embedding_provider == "mock"
