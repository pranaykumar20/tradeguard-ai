"""Phase 5.2 — per-user data isolation tests."""

import pytest

from app.core.auth import DEFAULT_USER_ID
from app.core.user_context import user_scope
from app.db.storage import MemoryStorageBackend


@pytest.fixture
async def memory_store(tmp_path, monkeypatch):
    from app.core import config

    path = tmp_path / "scoped_store.json"
    monkeypatch.setattr(config.settings, "memory_store_path", str(path))
    backend = MemoryStorageBackend()
    await backend.init()
    yield backend
    await backend.close()


@pytest.mark.asyncio
async def test_paper_trades_isolated_by_user(memory_store):
    async with user_scope("user-a"):
        await memory_store.create_paper_trade(
            {
                "ticker": "NVDA",
                "side": "buy",
                "quantity": 1,
                "limit_price": 100,
                "status": "planned",
                "verdict": "ALLOW",
                "reason": "test",
            }
        )
    async with user_scope("user-b"):
        await memory_store.create_paper_trade(
            {
                "ticker": "MSFT",
                "side": "buy",
                "quantity": 1,
                "limit_price": 200,
                "status": "planned",
                "verdict": "ALLOW",
                "reason": "test",
            }
        )

    async with user_scope("user-a"):
        trades = await memory_store.list_paper_trades()
        assert len(trades) == 1
        assert trades[0]["ticker"] == "NVDA"

    async with user_scope("user-b"):
        trades = await memory_store.list_paper_trades()
        assert len(trades) == 1
        assert trades[0]["ticker"] == "MSFT"


@pytest.mark.asyncio
async def test_cannot_update_other_users_trade(memory_store):
    async with user_scope("owner"):
        trade = await memory_store.create_paper_trade(
            {
                "ticker": "QQQ",
                "side": "buy",
                "quantity": 1,
                "limit_price": 400,
                "status": "planned",
                "verdict": "ALLOW",
                "reason": "",
            }
        )
    async with user_scope("intruder"):
        result = await memory_store.update_paper_trade(trade["id"], {"status": "filled"})
        assert result is None


@pytest.mark.asyncio
async def test_app_state_scoped_per_user(memory_store):
    async with user_scope("user-a"):
        await memory_store.set_app_state("trading", {"halted": True})
    async with user_scope("user-b"):
        await memory_store.set_app_state("trading", {"halted": False})

    async with user_scope("user-a"):
        state = await memory_store.get_app_state("trading")
        assert state == {"halted": True}
    async with user_scope("user-b"):
        state = await memory_store.get_app_state("trading")
        assert state == {"halted": False}


@pytest.mark.asyncio
async def test_approval_requests_scoped(memory_store):
    async with user_scope("user-a"):
        req = await memory_store.create_approval_request(
            {
                "ticker": "NVDA",
                "side": "buy",
                "quantity": 1,
                "limit_price": 100,
                "status": "pending",
            }
        )
    async with user_scope("user-b"):
        assert await memory_store.get_approval_request(req["id"]) is None
        rows = await memory_store.list_approval_requests()
        assert rows == []


@pytest.mark.asyncio
async def test_list_user_ids_falls_back_to_default(memory_store):
    ids = await memory_store.list_user_ids()
    assert ids == [DEFAULT_USER_ID]


@pytest.mark.asyncio
async def test_list_user_ids_returns_registered_users(memory_store):
    await memory_store.get_or_create_user("clerk_1", "a@test.com", "A")
    await memory_store.get_or_create_user("clerk_2", "b@test.com", "B")
    ids = await memory_store.list_user_ids()
    assert len(ids) == 2


@pytest.mark.asyncio
async def test_chat_session_isolation(memory_store):
    async with user_scope("user-a"):
        await memory_store.save_chat_message("sess-1", "user", "hello")
    async with user_scope("user-b"):
        msgs = await memory_store.get_chat_messages("sess-1")
        assert msgs == []
