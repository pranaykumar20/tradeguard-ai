"""Linked broker accounts — seed defaults and list household accounts."""

from datetime import datetime, timedelta, timezone

import structlog

from app.brokers.factory import list_broker_ids
from app.core.config import settings
from app.db.storage import get_storage

logger = structlog.get_logger()

DEFAULT_ACCOUNTS = [
    {
        "broker_id": "robinhood_agentic",
        "account_id": "agentic-main",
        "label": "Robinhood Agentic",
        "account_type": "taxable",
        "enabled": True,
    },
    {
        "broker_id": "mock_ira",
        "account_id": "ira-traditional",
        "label": "Traditional IRA (mock)",
        "account_type": "ira",
        "enabled": True,
    },
]

DEFAULT_TAX_LOTS = [
    {
        "broker_id": "robinhood_agentic",
        "account_id": "agentic-main",
        "ticker": "NVDA",
        "quantity": 8,
        "cost_basis": 118.5,
        "acquired_at": datetime.now(timezone.utc) - timedelta(days=45),
        "lot_method": "fifo",
    },
    {
        "broker_id": "robinhood_agentic",
        "account_id": "agentic-main",
        "ticker": "META",
        "quantity": 5,
        "cost_basis": 495.0,
        "acquired_at": datetime.now(timezone.utc) - timedelta(days=120),
        "lot_method": "fifo",
    },
    {
        "broker_id": "mock_ira",
        "account_id": "ira-traditional",
        "ticker": "QQQ",
        "quantity": 12,
        "cost_basis": 455.0,
        "acquired_at": datetime.now(timezone.utc) - timedelta(days=200),
        "lot_method": "fifo",
    },
    {
        "broker_id": "mock_ira",
        "account_id": "ira-traditional",
        "ticker": "MSFT",
        "quantity": 8,
        "cost_basis": 390.0,
        "acquired_at": datetime.now(timezone.utc) - timedelta(days=15),
        "lot_method": "fifo",
    },
]


class AccountService:
    async def ensure_defaults(self) -> None:
        if not settings.multi_broker_enabled:
            return
        try:
            storage = await get_storage()
        except RuntimeError:
            return

        existing = await storage.list_broker_accounts(enabled_only=False)
        if not existing:
            for account in DEFAULT_ACCOUNTS:
                if account["broker_id"] in list_broker_ids():
                    await storage.create_broker_account(account)
            logger.info("default_broker_accounts_seeded", count=len(DEFAULT_ACCOUNTS))

        if settings.tax_lot_tracking_enabled:
            lots = await storage.list_tax_lots()
            if not lots:
                for lot in DEFAULT_TAX_LOTS:
                    await storage.create_tax_lot(lot)
                logger.info("default_tax_lots_seeded", count=len(DEFAULT_TAX_LOTS))

    async def list_accounts(self) -> list[dict]:
        storage = await get_storage()
        return await storage.list_broker_accounts()

    async def list_brokers(self) -> list[dict]:
        from app.brokers.factory import list_brokers

        return list_brokers()
