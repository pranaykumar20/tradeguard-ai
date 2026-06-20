"""Shared pytest fixtures."""

import pytest

import app.db.storage as storage_module
from app.core.config import settings
from app.db.storage import close_storage, init_storage
from app.services.accounts import AccountService
from app.services.strategies import StrategyService


@pytest.fixture(autouse=True)
async def memory_storage(tmp_path, monkeypatch):
    """Use isolated file-backed memory storage for every test."""
    path = tmp_path / "pytest_store.json"
    monkeypatch.setattr(settings, "storage_backend", "memory")
    monkeypatch.setattr(settings, "memory_store_path", str(path))
    monkeypatch.setattr(settings, "multi_broker_enabled", True)
    storage_module._backend = None
    await init_storage()
    await AccountService().ensure_defaults()
    await StrategyService().ensure_defaults()
    yield
    await close_storage()
    storage_module._backend = None
