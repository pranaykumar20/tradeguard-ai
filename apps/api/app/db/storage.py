"""Storage backend abstraction — Postgres when available, file-backed memory otherwise."""

from __future__ import annotations

import json
import math
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import structlog
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.auth import DEFAULT_USER_ID
from app.core.config import settings
from app.core.user_context import get_current_user_id
from app.db.models import (
    AlertEvent,
    AppState,
    ApprovalRequest,
    AutomationAuditLog,
    Base,
    BrokerAccount,
    ChatMessage,
    ChatSession,
    MarketFeatureCache,
    PaperTrade,
    RAGDocument,
    StrategyProposal,
    TaxLot,
    TradeStrategy,
    User,
)

logger = structlog.get_logger()


def _uid() -> str:
    return get_current_user_id()


def _row_user_id(row: dict) -> str:
    return row.get("user_id", DEFAULT_USER_ID)


def _state_key(key: str, user_id: str | None = None) -> str:
    return f"{user_id or _uid()}:{key}"


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(x * x for x in b)) or 1.0
    return dot / (na * nb)


def _matches_doc_types(meta: dict | None, doc_types: list[str] | None) -> bool:
    if not doc_types:
        return True
    doc_type = (meta or {}).get("type", "document")
    return doc_type in doc_types


def _rag_visible_to_user(meta: dict | None, user_id: str) -> bool:
    meta = meta or {}
    visibility = meta.get("visibility")
    if visibility == "global" or visibility is None:
        if meta.get("type") == "journal" and meta.get("user_id"):
            return meta.get("user_id") == user_id
        return True
    if visibility == "user":
        return meta.get("user_id") == user_id
    if visibility == "tenant":
        doc_tenant = meta.get("tenant_id", user_id)
        return doc_tenant == user_id
    if meta.get("type") == "journal":
        return meta.get("user_id") == user_id
    return True


def _rag_matches_ticker(meta: dict | None, ticker: str | None) -> bool:
    if not ticker:
        return True
    meta = meta or {}
    if meta.get("type") == "playbook":
        return True
    doc_ticker = meta.get("ticker")
    if doc_ticker:
        return str(doc_ticker).upper() == ticker.upper()
    return True


def _embedding_to_pgvector(embedding: list[float]) -> str:
    return "[" + ",".join(str(x) for x in embedding) + "]"


class StorageBackend(ABC):
    backend_name: str = "base"

    @abstractmethod
    async def init(self) -> None:
        pass

    @abstractmethod
    async def close(self) -> None:
        pass

    @abstractmethod
    async def save_chat_message(
        self, session_id: str, role: str, content: str, meta: dict | None = None
    ) -> None:
        pass

    @abstractmethod
    async def get_chat_messages(self, session_id: str, limit: int = 50) -> list[dict]:
        pass

    @abstractmethod
    async def create_paper_trade(self, trade: dict) -> dict:
        pass

    @abstractmethod
    async def update_paper_trade(self, trade_id: str, updates: dict) -> dict | None:
        pass

    @abstractmethod
    async def list_paper_trades(self, limit: int = 100) -> list[dict]:
        pass

    @abstractmethod
    async def get_paper_trade(self, trade_id: str) -> dict | None:
        pass

    @abstractmethod
    async def paper_trade_stats(self) -> dict:
        pass

    @abstractmethod
    async def upsert_rag_documents(self, docs: list[dict]) -> int:
        pass

    @abstractmethod
    async def search_rag(
        self,
        query_embedding: list[float],
        top_k: int = 3,
        ticker: str | None = None,
        doc_types: list[str] | None = None,
    ) -> list[dict]:
        pass

    @abstractmethod
    async def list_rag_documents(
        self,
        ticker: str | None = None,
        doc_types: list[str] | None = None,
    ) -> list[dict]:
        pass

    @abstractmethod
    async def get_rag_content_hashes(self, chunk_ids: list[str]) -> dict[str, str]:
        pass

    @abstractmethod
    async def list_rag_documents_raw(self) -> list[dict]:
        pass

    @abstractmethod
    async def cache_features(self, ticker: str, features: dict, provider: str) -> None:
        pass

    @abstractmethod
    async def get_cached_features(self, ticker: str) -> dict | None:
        pass

    @abstractmethod
    async def create_approval_request(self, request: dict) -> dict:
        pass

    @abstractmethod
    async def update_approval_request(self, request_id: str, updates: dict) -> dict | None:
        pass

    @abstractmethod
    async def get_approval_request(self, request_id: str) -> dict | None:
        pass

    @abstractmethod
    async def list_approval_requests(
        self, status: str | None = None, limit: int = 50
    ) -> list[dict]:
        pass

    @abstractmethod
    async def get_app_state(self, key: str) -> dict | None:
        pass

    @abstractmethod
    async def set_app_state(self, key: str, value: dict) -> dict:
        pass

    @abstractmethod
    async def create_alert_event(self, event: dict) -> dict:
        pass

    @abstractmethod
    async def list_alert_events(self, limit: int = 50) -> list[dict]:
        pass

    @abstractmethod
    async def create_trade_strategy(self, strategy: dict) -> dict:
        pass

    @abstractmethod
    async def update_trade_strategy(self, strategy_id: str, updates: dict) -> dict | None:
        pass

    @abstractmethod
    async def get_trade_strategy(self, strategy_id: str) -> dict | None:
        pass

    @abstractmethod
    async def list_trade_strategies(self) -> list[dict]:
        pass

    @abstractmethod
    async def delete_trade_strategy(self, strategy_id: str) -> bool:
        pass

    @abstractmethod
    async def create_strategy_proposal(self, proposal: dict) -> dict:
        pass

    @abstractmethod
    async def list_strategy_proposals(
        self, strategy_id: str | None = None, limit: int = 50
    ) -> list[dict]:
        pass

    @abstractmethod
    async def create_automation_audit(self, entry: dict) -> dict:
        pass

    @abstractmethod
    async def list_automation_audit(self, limit: int = 50) -> list[dict]:
        pass

    @abstractmethod
    async def get_or_create_user(
        self, clerk_id: str, email: str = "", display_name: str = ""
    ) -> dict:
        pass

    @abstractmethod
    async def list_users(self) -> list[dict]:
        pass

    @abstractmethod
    async def get_user_by_id(self, user_id: str) -> dict | None:
        pass

    @abstractmethod
    async def update_user(self, user_id: str, updates: dict) -> dict | None:
        pass

    @abstractmethod
    async def list_broker_accounts(self, enabled_only: bool = True) -> list[dict]:
        pass

    @abstractmethod
    async def create_broker_account(self, account: dict) -> dict:
        pass

    @abstractmethod
    async def update_broker_account(self, account_row_id: str, updates: dict) -> dict | None:
        pass

    @abstractmethod
    async def get_broker_account(
        self, broker_id: str, account_id: str | None = None
    ) -> dict | None:
        pass

    @abstractmethod
    async def list_tax_lots(
        self, ticker: str | None = None, account_id: str | None = None
    ) -> list[dict]:
        pass

    @abstractmethod
    async def create_tax_lot(self, lot: dict) -> dict:
        pass

    async def list_user_ids(self) -> list[str]:
        users = await self.list_users()
        if users:
            return [u["id"] for u in users]
        return [DEFAULT_USER_ID]


class MemoryStorageBackend(StorageBackend):
    backend_name = "memory"

    def __init__(self):
        self._path = Path(settings.memory_store_path)
        self._data: dict = {
            "chat_sessions": {},
            "chat_messages": [],
            "paper_trades": [],
            "approval_requests": [],
            "rag_documents": [],
            "feature_cache": {},
            "app_state": {},
            "alert_events": [],
            "trade_strategies": [],
            "strategy_proposals": [],
            "automation_audit": [],
            "users": [],
            "broker_accounts": [],
            "tax_lots": [],
        }

    async def init(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if self._path.exists():
            try:
                self._data = json.loads(self._path.read_text())
            except json.JSONDecodeError:
                logger.warning("memory_store_corrupt", path=str(self._path))
        self._migrate_memory_store()
        logger.info("storage_init", backend="memory", path=str(self._path))

    def _migrate_memory_store(self) -> None:
        app_state = self._data.get("app_state", {})
        if app_state and not any(":" in str(k) for k in app_state):
            self._data["app_state"] = {f"{DEFAULT_USER_ID}:{k}": v for k, v in app_state.items()}
            self._persist()

    async def close(self) -> None:
        self._persist()

    def _persist(self) -> None:
        self._path.write_text(json.dumps(self._data, indent=2, default=str))

    async def save_chat_message(
        self, session_id: str, role: str, content: str, meta: dict | None = None
    ) -> None:
        uid = _uid()
        sessions = self._data.setdefault("chat_sessions", {})
        session = sessions.get(session_id)
        if session and _row_user_id(session) != uid:
            return
        if not session:
            sessions[session_id] = {
                "id": session_id,
                "user_id": uid,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        self._data["chat_messages"].append(
            {
                "id": str(uuid4()),
                "session_id": session_id,
                "role": role,
                "content": content,
                "meta": meta,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        self._persist()

    async def get_chat_messages(self, session_id: str, limit: int = 50) -> list[dict]:
        uid = _uid()
        session = self._data.get("chat_sessions", {}).get(session_id)
        if session and _row_user_id(session) != uid:
            return []
        msgs = [m for m in self._data["chat_messages"] if m["session_id"] == session_id]
        return msgs[-limit:]

    async def create_paper_trade(self, trade: dict) -> dict:
        row = {
            "id": str(uuid4()),
            "user_id": trade.get("user_id", _uid()),
            "created_at": datetime.now(timezone.utc).isoformat(),
            **trade,
        }
        self._data["paper_trades"].insert(0, row)
        self._persist()
        return row

    async def update_paper_trade(self, trade_id: str, updates: dict) -> dict | None:
        uid = _uid()
        for trade in self._data["paper_trades"]:
            if trade["id"] == trade_id and _row_user_id(trade) == uid:
                trade.update(updates)
                self._persist()
                return trade
        return None

    async def list_paper_trades(self, limit: int = 100) -> list[dict]:
        uid = _uid()
        rows = [t for t in self._data["paper_trades"] if _row_user_id(t) == uid]
        return rows[:limit]

    async def get_paper_trade(self, trade_id: str) -> dict | None:
        uid = _uid()
        return next(
            (t for t in self._data["paper_trades"] if t["id"] == trade_id and _row_user_id(t) == uid),
            None,
        )

    async def paper_trade_stats(self) -> dict:
        trades = await self.list_paper_trades(limit=500)
        filled = [t for t in trades if t.get("status") == "filled"]
        wins = [t for t in filled if (t.get("pnl") or 0) > 0]
        total_pnl = sum(t.get("pnl") or 0 for t in filled)
        return {
            "total_trades": len(trades),
            "filled_trades": len(filled),
            "win_rate": round(len(wins) / len(filled) * 100, 1) if filled else 0.0,
            "total_pnl": round(total_pnl, 2),
            "goal": settings.paper_trade_goal,
            "progress_pct": round(min(100, len(trades) / settings.paper_trade_goal * 100), 1),
        }

    async def upsert_rag_documents(self, docs: list[dict]) -> int:
        existing = {d["chunk_id"]: d for d in self._data["rag_documents"]}
        for doc in docs:
            existing[doc["chunk_id"]] = doc
        self._data["rag_documents"] = list(existing.values())
        self._persist()
        return len(docs)

    async def search_rag(
        self,
        query_embedding: list[float],
        top_k: int = 3,
        ticker: str | None = None,
        doc_types: list[str] | None = None,
    ) -> list[dict]:
        fetch_k = top_k * 4 if doc_types else top_k
        scored = []
        uid = _uid()
        for doc in self._data["rag_documents"]:
            if not _rag_matches_ticker(doc.get("meta"), ticker):
                continue
            if not _matches_doc_types(doc.get("meta"), doc_types):
                continue
            if not _rag_visible_to_user(doc.get("meta"), uid):
                continue
            emb = doc.get("embedding") or []
            score = _cosine(query_embedding, emb) if emb else 0.0
            scored.append({**doc, "score": score})
        scored.sort(key=lambda d: d["score"], reverse=True)
        return scored[:fetch_k]

    async def list_rag_documents(
        self,
        ticker: str | None = None,
        doc_types: list[str] | None = None,
    ) -> list[dict]:
        rows = []
        uid = _uid()
        for doc in self._data["rag_documents"]:
            if not _rag_matches_ticker(doc.get("meta"), ticker):
                continue
            if not _matches_doc_types(doc.get("meta"), doc_types):
                continue
            if not _rag_visible_to_user(doc.get("meta"), uid):
                continue
            rows.append(dict(doc))
        return rows

    async def get_rag_content_hashes(self, chunk_ids: list[str]) -> dict[str, str]:
        if not chunk_ids:
            return {}
        wanted = set(chunk_ids)
        hashes: dict[str, str] = {}
        for doc in self._data["rag_documents"]:
            chunk_id = doc.get("chunk_id")
            if chunk_id not in wanted:
                continue
            digest = (doc.get("meta") or {}).get("content_hash")
            if digest:
                hashes[chunk_id] = digest
        return hashes

    async def list_rag_documents_raw(self) -> list[dict]:
        return [dict(doc) for doc in self._data["rag_documents"]]

    async def cache_features(self, ticker: str, features: dict, provider: str) -> None:
        self._data["feature_cache"][ticker.upper()] = {
            "features": features,
            "provider": provider,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._persist()

    async def get_cached_features(self, ticker: str) -> dict | None:
        row = self._data["feature_cache"].get(ticker.upper())
        return row["features"] if row else None

    async def create_approval_request(self, request: dict) -> dict:
        row = {
            "id": str(uuid4()),
            "user_id": request.get("user_id", _uid()),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "resolved_at": None,
            **request,
        }
        self._data.setdefault("approval_requests", []).insert(0, row)
        self._persist()
        return row

    async def update_approval_request(self, request_id: str, updates: dict) -> dict | None:
        uid = _uid()
        for req in self._data.get("approval_requests", []):
            if req["id"] == request_id and _row_user_id(req) == uid:
                req.update(updates)
                self._persist()
                return req
        return None

    async def get_approval_request(self, request_id: str) -> dict | None:
        uid = _uid()
        return next(
            (
                r
                for r in self._data.get("approval_requests", [])
                if r["id"] == request_id and _row_user_id(r) == uid
            ),
            None,
        )

    async def list_approval_requests(
        self, status: str | None = None, limit: int = 50
    ) -> list[dict]:
        uid = _uid()
        rows = [r for r in self._data.get("approval_requests", []) if _row_user_id(r) == uid]
        if status:
            rows = [r for r in rows if r.get("status") == status]
        return rows[:limit]

    async def get_app_state(self, key: str) -> dict | None:
        return self._data.get("app_state", {}).get(_state_key(key))

    async def set_app_state(self, key: str, value: dict) -> dict:
        self._data.setdefault("app_state", {})[_state_key(key)] = value
        self._persist()
        return value

    async def create_alert_event(self, event: dict) -> dict:
        row = {
            "id": str(uuid4()),
            "user_id": event.get("user_id", _uid()),
            "created_at": datetime.now(timezone.utc).isoformat(),
            **event,
        }
        self._data.setdefault("alert_events", []).insert(0, row)
        self._persist()
        return row

    async def list_alert_events(self, limit: int = 50) -> list[dict]:
        uid = _uid()
        rows = [e for e in self._data.get("alert_events", []) if _row_user_id(e) == uid]
        return rows[:limit]

    async def create_trade_strategy(self, strategy: dict) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        row = {
            "id": str(uuid4()),
            "user_id": strategy.get("user_id", _uid()),
            "created_at": now,
            "updated_at": now,
            "auto_approve": False,
            "enabled": False,
            **strategy,
        }
        self._data.setdefault("trade_strategies", []).append(row)
        self._persist()
        return row

    async def update_trade_strategy(self, strategy_id: str, updates: dict) -> dict | None:
        uid = _uid()
        for strategy in self._data.get("trade_strategies", []):
            if strategy["id"] == strategy_id and _row_user_id(strategy) == uid:
                strategy.update(updates)
                strategy["updated_at"] = datetime.now(timezone.utc).isoformat()
                self._persist()
                return strategy
        return None

    async def get_trade_strategy(self, strategy_id: str) -> dict | None:
        uid = _uid()
        return next(
            (
                s
                for s in self._data.get("trade_strategies", [])
                if s["id"] == strategy_id and _row_user_id(s) == uid
            ),
            None,
        )

    async def list_trade_strategies(self) -> list[dict]:
        uid = _uid()
        return [s for s in self._data.get("trade_strategies", []) if _row_user_id(s) == uid]

    async def delete_trade_strategy(self, strategy_id: str) -> bool:
        uid = _uid()
        strategies = self._data.get("trade_strategies", [])
        before = len(strategies)
        self._data["trade_strategies"] = [
            s for s in strategies if not (s["id"] == strategy_id and _row_user_id(s) == uid)
        ]
        if len(self._data["trade_strategies"]) < before:
            self._persist()
            return True
        return False

    async def create_strategy_proposal(self, proposal: dict) -> dict:
        row = {
            "id": str(uuid4()),
            "user_id": proposal.get("user_id", _uid()),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "resolved_at": None,
            **proposal,
        }
        self._data.setdefault("strategy_proposals", []).insert(0, row)
        self._persist()
        return row

    async def list_strategy_proposals(
        self, strategy_id: str | None = None, limit: int = 50
    ) -> list[dict]:
        uid = _uid()
        rows = [r for r in self._data.get("strategy_proposals", []) if _row_user_id(r) == uid]
        if strategy_id:
            rows = [r for r in rows if r.get("strategy_id") == strategy_id]
        return rows[:limit]

    async def create_automation_audit(self, entry: dict) -> dict:
        row = {
            "id": str(uuid4()),
            "user_id": entry.get("user_id", _uid()),
            "created_at": datetime.now(timezone.utc).isoformat(),
            **entry,
        }
        self._data.setdefault("automation_audit", []).insert(0, row)
        self._persist()
        return row

    async def list_automation_audit(self, limit: int = 50) -> list[dict]:
        uid = _uid()
        rows = [e for e in self._data.get("automation_audit", []) if _row_user_id(e) == uid]
        return rows[:limit]

    async def list_users(self) -> list[dict]:
        return list(self._data.get("users", []))

    async def get_or_create_user(
        self, clerk_id: str, email: str = "", display_name: str = ""
    ) -> dict:
        from app.core.permissions import resolve_initial_role

        users = self._data.setdefault("users", [])
        admin_emails = settings.platform_admin_email_set
        for user in users:
            if user.get("clerk_id") == clerk_id:
                if email and user.get("email") != email:
                    user["email"] = email
                if display_name and user.get("display_name") != display_name:
                    user["display_name"] = display_name
                if email and email.lower() in admin_emails:
                    user["role"] = "platform_admin"
                user.setdefault("role", "user")
                user.setdefault("permissions", None)
                user.setdefault("is_active", True)
                user["updated_at"] = datetime.now(timezone.utc).isoformat()
                self._persist()
                return user
        row = {
            "id": str(uuid4()),
            "clerk_id": clerk_id,
            "email": email,
            "display_name": display_name or email.split("@")[0] if email else "",
            "role": resolve_initial_role(email, admin_emails),
            "permissions": None,
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        users.append(row)
        self._persist()
        return row

    async def get_user_by_id(self, user_id: str) -> dict | None:
        for user in self._data.get("users", []):
            if user.get("id") == user_id:
                return user
        return None

    async def update_user(self, user_id: str, updates: dict) -> dict | None:
        from app.core.permissions import ALL_PERMISSIONS, normalize_role

        user = await self.get_user_by_id(user_id)
        if not user:
            return None
        allowed = {"role", "permissions", "is_active", "display_name"}
        for key, value in updates.items():
            if key not in allowed:
                continue
            if key == "role":
                user["role"] = normalize_role(str(value))
            elif key == "permissions":
                if value is None:
                    user["permissions"] = None
                else:
                    user["permissions"] = [p for p in value if p in ALL_PERMISSIONS]
            else:
                user[key] = value
        user["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._persist()
        return user

    async def list_broker_accounts(self, enabled_only: bool = True) -> list[dict]:
        uid = _uid()
        rows = [
            a
            for a in self._data.get("broker_accounts", [])
            if _row_user_id(a) == uid and (not enabled_only or a.get("enabled", True))
        ]
        return rows

    async def create_broker_account(self, account: dict) -> dict:
        row = {
            "id": str(uuid4()),
            "user_id": account.get("user_id", _uid()),
            "created_at": datetime.now(timezone.utc).isoformat(),
            **account,
        }
        self._data.setdefault("broker_accounts", []).append(row)
        self._persist()
        return row

    async def update_broker_account(self, account_row_id: str, updates: dict) -> dict | None:
        uid = _uid()
        for account in self._data.get("broker_accounts", []):
            if account.get("id") == account_row_id and _row_user_id(account) == uid:
                for key, value in updates.items():
                    if key == "meta" and isinstance(account.get("meta"), dict) and isinstance(value, dict):
                        account["meta"] = {**account["meta"], **value}
                    else:
                        account[key] = value
                self._persist()
                return account
        return None

    async def get_broker_account(
        self, broker_id: str, account_id: str | None = None
    ) -> dict | None:
        uid = _uid()
        for account in self._data.get("broker_accounts", []):
            if _row_user_id(account) != uid:
                continue
            if account.get("broker_id") != broker_id:
                continue
            if account_id and account.get("account_id") != account_id:
                continue
            return account
        return None

    async def list_tax_lots(
        self, ticker: str | None = None, account_id: str | None = None
    ) -> list[dict]:
        uid = _uid()
        rows = [lot for lot in self._data.get("tax_lots", []) if _row_user_id(lot) == uid]
        if ticker:
            rows = [lot for lot in rows if lot.get("ticker") == ticker.upper()]
        if account_id:
            rows = [lot for lot in rows if lot.get("account_id") == account_id]
        return rows

    async def create_tax_lot(self, lot: dict) -> dict:
        row = {
            "id": str(uuid4()),
            "user_id": lot.get("user_id", _uid()),
            "created_at": datetime.now(timezone.utc).isoformat(),
            **lot,
        }
        if isinstance(row.get("acquired_at"), datetime):
            row["acquired_at"] = row["acquired_at"].isoformat()
        self._data.setdefault("tax_lots", []).append(row)
        self._persist()
        return row


class PostgresStorageBackend(StorageBackend):
    backend_name = "postgres"

    def __init__(self):
        self._engine = create_async_engine(settings.database_url, echo=False)
        self._session_factory = async_sessionmaker(self._engine, expire_on_commit=False)

    async def init(self) -> None:
        async with self._engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
            await conn.run_sync(Base.metadata.create_all)
            try:
                await conn.execute(
                    text(
                        """
                        CREATE INDEX IF NOT EXISTS rag_documents_embedding_hnsw_idx
                        ON rag_documents USING hnsw (embedding vector_cosine_ops)
                        """
                    )
                )
            except Exception as exc:
                logger.warning("rag_hnsw_index_skipped", error=str(exc))
            try:
                await conn.execute(
                    text(
                        """
                        CREATE INDEX IF NOT EXISTS rag_documents_content_trgm_idx
                        ON rag_documents USING gin (content gin_trgm_ops)
                        """
                    )
                )
            except Exception as exc:
                logger.warning("rag_trgm_index_skipped", error=str(exc))
            for index_sql in (
                "CREATE INDEX IF NOT EXISTS rag_documents_meta_type_idx ON rag_documents ((meta->>'type'))",
                "CREATE INDEX IF NOT EXISTS rag_documents_meta_ticker_idx ON rag_documents ((meta->>'ticker'))",
                "CREATE INDEX IF NOT EXISTS rag_documents_meta_user_idx ON rag_documents ((meta->>'user_id'))",
            ):
                try:
                    await conn.execute(text(index_sql))
                except Exception as exc:
                    logger.warning("rag_meta_index_skipped", sql=index_sql, error=str(exc))
        logger.info("storage_init", backend="postgres")

    async def close(self) -> None:
        await self._engine.dispose()

    def _session(self) -> AsyncSession:
        return self._session_factory()

    async def save_chat_message(
        self, session_id: str, role: str, content: str, meta: dict | None = None
    ) -> None:
        uid = _uid()
        async with self._session() as session:
            exists = await session.get(ChatSession, session_id)
            if exists and exists.user_id != uid:
                return
            if not exists:
                session.add(ChatSession(id=session_id, user_id=uid))
            session.add(
                ChatMessage(session_id=session_id, role=role, content=content, meta=meta)
            )
            await session.commit()

    async def get_chat_messages(self, session_id: str, limit: int = 50) -> list[dict]:
        uid = _uid()
        async with self._session() as session:
            chat_session = await session.get(ChatSession, session_id)
            if chat_session and chat_session.user_id != uid:
                return []
            result = await session.execute(
                select(ChatMessage)
                .where(ChatMessage.session_id == session_id)
                .order_by(ChatMessage.created_at.desc())
                .limit(limit)
            )
            rows = list(reversed(result.scalars().all()))
            return [
                {
                    "id": r.id,
                    "session_id": r.session_id,
                    "role": r.role,
                    "content": r.content,
                    "meta": r.meta,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in rows
            ]

    async def create_paper_trade(self, trade: dict) -> dict:
        async with self._session() as session:
            payload = dict(trade)
            payload.setdefault("user_id", _uid())
            if isinstance(payload.get("created_at"), str):
                payload["created_at"] = datetime.fromisoformat(
                    payload["created_at"].replace("Z", "+00:00")
                )
            row = PaperTrade(**payload)
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return self._paper_trade_to_dict(row)

    async def update_paper_trade(self, trade_id: str, updates: dict) -> dict | None:
        async with self._session() as session:
            row = await session.get(PaperTrade, trade_id)
            if not row or row.user_id != _uid():
                return None
            for key, val in updates.items():
                setattr(row, key, val)
            await session.commit()
            await session.refresh(row)
            return self._paper_trade_to_dict(row)

    async def list_paper_trades(self, limit: int = 100) -> list[dict]:
        async with self._session() as session:
            result = await session.execute(
                select(PaperTrade)
                .where(PaperTrade.user_id == _uid())
                .order_by(PaperTrade.created_at.desc())
                .limit(limit)
            )
            return [self._paper_trade_to_dict(r) for r in result.scalars().all()]

    async def get_paper_trade(self, trade_id: str) -> dict | None:
        async with self._session() as session:
            row = await session.get(PaperTrade, trade_id)
            if not row or row.user_id != _uid():
                return None
            return self._paper_trade_to_dict(row)

    async def paper_trade_stats(self) -> dict:
        trades = await self.list_paper_trades(limit=500)
        filled = [t for t in trades if t.get("status") == "filled"]
        wins = [t for t in filled if (t.get("pnl") or 0) > 0]
        total_pnl = sum(t.get("pnl") or 0 for t in filled)
        return {
            "total_trades": len(trades),
            "filled_trades": len(filled),
            "win_rate": round(len(wins) / len(filled) * 100, 1) if filled else 0.0,
            "total_pnl": round(total_pnl, 2),
            "goal": settings.paper_trade_goal,
            "progress_pct": round(min(100, len(trades) / settings.paper_trade_goal * 100), 1),
        }

    async def upsert_rag_documents(self, docs: list[dict]) -> int:
        async with self._session() as session:
            for doc in docs:
                existing = await session.execute(
                    select(RAGDocument).where(RAGDocument.chunk_id == doc["chunk_id"])
                )
                row = existing.scalar_one_or_none()
                if row:
                    row.content = doc["content"]
                    row.source = doc["source"]
                    row.embedding = doc["embedding"]
                    row.meta = doc.get("meta")
                else:
                    session.add(
                        RAGDocument(
                            source=doc["source"],
                            chunk_id=doc["chunk_id"],
                            content=doc["content"],
                            embedding=doc["embedding"],
                            meta=doc.get("meta"),
                        )
                    )
            await session.commit()
        return len(docs)

    async def search_rag(
        self,
        query_embedding: list[float],
        top_k: int = 3,
        ticker: str | None = None,
        doc_types: list[str] | None = None,
    ) -> list[dict]:
        fetch_k = top_k * 4 if doc_types else top_k
        vec = _embedding_to_pgvector(query_embedding)
        ticker_filter = ticker.upper() if ticker else None
        sql = text(
            """
            SELECT id, chunk_id, source, content, meta,
                   1 - (embedding <=> CAST(:vec AS vector)) AS score
            FROM rag_documents
            WHERE (
                :ticker IS NULL
                OR meta->>'type' = 'playbook'
                OR meta->>'ticker' = :ticker
                OR meta->>'ticker' IS NULL
            )
            ORDER BY embedding <=> CAST(:vec AS vector)
            LIMIT :top_k
            """
        )
        async with self._session() as session:
            result = await session.execute(
                sql, {"vec": vec, "ticker": ticker_filter, "top_k": fetch_k}
            )
            rows = result.mappings().all()
            filtered = [
                {
                    "id": r["id"],
                    "chunk_id": r["chunk_id"],
                    "source": r["source"],
                    "content": r["content"],
                    "meta": r["meta"],
                    "score": float(r["score"] or 0),
                }
                for r in rows
                if _matches_doc_types(r["meta"], doc_types)
                and _rag_visible_to_user(r["meta"], _uid())
            ]
            return filtered[:top_k]

    async def list_rag_documents(
        self,
        ticker: str | None = None,
        doc_types: list[str] | None = None,
    ) -> list[dict]:
        async with self._session() as session:
            result = await session.execute(select(RAGDocument))
            docs = result.scalars().all()
            rows = []
            uid = _uid()
            for doc in docs:
                meta = doc.meta or {}
                if not _rag_matches_ticker(meta, ticker):
                    continue
                if not _matches_doc_types(meta, doc_types):
                    continue
                if not _rag_visible_to_user(meta, uid):
                    continue
                rows.append(
                    {
                        "id": doc.id,
                        "chunk_id": doc.chunk_id,
                        "source": doc.source,
                        "content": doc.content,
                        "meta": meta,
                    }
                )
            return rows

    async def get_rag_content_hashes(self, chunk_ids: list[str]) -> dict[str, str]:
        if not chunk_ids:
            return {}
        async with self._session() as session:
            result = await session.execute(
                select(RAGDocument.chunk_id, RAGDocument.meta).where(
                    RAGDocument.chunk_id.in_(chunk_ids)
                )
            )
            hashes: dict[str, str] = {}
            for chunk_id, meta in result.all():
                digest = (meta or {}).get("content_hash")
                if digest:
                    hashes[chunk_id] = digest
            return hashes

    async def list_rag_documents_raw(self) -> list[dict]:
        async with self._session() as session:
            result = await session.execute(select(RAGDocument))
            docs = result.scalars().all()
            return [
                {
                    "id": doc.id,
                    "chunk_id": doc.chunk_id,
                    "source": doc.source,
                    "content": doc.content,
                    "meta": doc.meta or {},
                }
                for doc in docs
            ]

    async def cache_features(self, ticker: str, features: dict, provider: str) -> None:
        async with self._session() as session:
            row = await session.get(MarketFeatureCache, ticker.upper())
            if row:
                row.features = features
                row.provider = provider
            else:
                session.add(
                    MarketFeatureCache(
                        ticker=ticker.upper(), features=features, provider=provider
                    )
                )
            await session.commit()

    async def get_cached_features(self, ticker: str) -> dict | None:
        async with self._session() as session:
            row = await session.get(MarketFeatureCache, ticker.upper())
            return row.features if row else None

    async def create_approval_request(self, request: dict) -> dict:
        async with self._session() as session:
            payload = dict(request)
            payload.setdefault("user_id", _uid())
            row = ApprovalRequest(**payload)
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return self._approval_to_dict(row)

    async def update_approval_request(self, request_id: str, updates: dict) -> dict | None:
        async with self._session() as session:
            row = await session.get(ApprovalRequest, request_id)
            if not row or row.user_id != _uid():
                return None
            for key, val in updates.items():
                setattr(row, key, val)
            await session.commit()
            await session.refresh(row)
            return self._approval_to_dict(row)

    async def get_approval_request(self, request_id: str) -> dict | None:
        async with self._session() as session:
            row = await session.get(ApprovalRequest, request_id)
            if not row or row.user_id != _uid():
                return None
            return self._approval_to_dict(row)

    async def list_approval_requests(
        self, status: str | None = None, limit: int = 50
    ) -> list[dict]:
        async with self._session() as session:
            query = (
                select(ApprovalRequest)
                .where(ApprovalRequest.user_id == _uid())
                .order_by(ApprovalRequest.created_at.desc())
                .limit(limit)
            )
            if status:
                query = query.where(ApprovalRequest.status == status)
            result = await session.execute(query)
            return [self._approval_to_dict(r) for r in result.scalars().all()]

    async def get_app_state(self, key: str) -> dict | None:
        async with self._session() as session:
            row = await session.get(AppState, (_uid(), key))
            return dict(row.value) if row and row.value else None

    async def set_app_state(self, key: str, value: dict) -> dict:
        async with self._session() as session:
            state_id = (_uid(), key)
            row = await session.get(AppState, state_id)
            if row:
                row.value = value
            else:
                session.add(AppState(user_id=_uid(), key=key, value=value))
            await session.commit()
            return value

    async def create_alert_event(self, event: dict) -> dict:
        async with self._session() as session:
            payload = dict(event)
            payload.setdefault("user_id", _uid())
            row = AlertEvent(**payload)
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return self._alert_to_dict(row)

    async def list_alert_events(self, limit: int = 50) -> list[dict]:
        async with self._session() as session:
            result = await session.execute(
                select(AlertEvent)
                .where(AlertEvent.user_id == _uid())
                .order_by(AlertEvent.created_at.desc())
                .limit(limit)
            )
            return [self._alert_to_dict(r) for r in result.scalars().all()]

    async def create_trade_strategy(self, strategy: dict) -> dict:
        async with self._session() as session:
            payload = dict(strategy)
            payload.setdefault("user_id", _uid())
            row = TradeStrategy(**payload)
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return self._strategy_to_dict(row)

    async def update_trade_strategy(self, strategy_id: str, updates: dict) -> dict | None:
        async with self._session() as session:
            row = await session.get(TradeStrategy, strategy_id)
            if not row or row.user_id != _uid():
                return None
            for key, val in updates.items():
                setattr(row, key, val)
            await session.commit()
            await session.refresh(row)
            return self._strategy_to_dict(row)

    async def get_trade_strategy(self, strategy_id: str) -> dict | None:
        async with self._session() as session:
            row = await session.get(TradeStrategy, strategy_id)
            if not row or row.user_id != _uid():
                return None
            return self._strategy_to_dict(row)

    async def list_trade_strategies(self) -> list[dict]:
        async with self._session() as session:
            result = await session.execute(
                select(TradeStrategy)
                .where(TradeStrategy.user_id == _uid())
                .order_by(TradeStrategy.created_at.asc())
            )
            return [self._strategy_to_dict(r) for r in result.scalars().all()]

    async def delete_trade_strategy(self, strategy_id: str) -> bool:
        async with self._session() as session:
            row = await session.get(TradeStrategy, strategy_id)
            if not row or row.user_id != _uid():
                return False
            await session.delete(row)
            await session.commit()
            return True

    async def create_strategy_proposal(self, proposal: dict) -> dict:
        async with self._session() as session:
            payload = dict(proposal)
            payload.setdefault("user_id", _uid())
            row = StrategyProposal(**payload)
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return self._proposal_to_dict(row)

    async def list_strategy_proposals(
        self, strategy_id: str | None = None, limit: int = 50
    ) -> list[dict]:
        async with self._session() as session:
            query = (
                select(StrategyProposal)
                .where(StrategyProposal.user_id == _uid())
                .order_by(StrategyProposal.created_at.desc())
                .limit(limit)
            )
            if strategy_id:
                query = query.where(StrategyProposal.strategy_id == strategy_id)
            result = await session.execute(query)
            return [self._proposal_to_dict(r) for r in result.scalars().all()]

    async def create_automation_audit(self, entry: dict) -> dict:
        async with self._session() as session:
            payload = dict(entry)
            payload.setdefault("user_id", _uid())
            row = AutomationAuditLog(**payload)
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return self._automation_audit_to_dict(row)

    async def list_automation_audit(self, limit: int = 50) -> list[dict]:
        async with self._session() as session:
            result = await session.execute(
                select(AutomationAuditLog)
                .where(AutomationAuditLog.user_id == _uid())
                .order_by(AutomationAuditLog.created_at.desc())
                .limit(limit)
            )
            return [self._automation_audit_to_dict(r) for r in result.scalars().all()]

    async def list_users(self) -> list[dict]:
        async with self._session() as session:
            result = await session.execute(select(User).order_by(User.created_at.asc()))
            return [self._user_to_dict(r) for r in result.scalars().all()]

    async def get_or_create_user(
        self, clerk_id: str, email: str = "", display_name: str = ""
    ) -> dict:
        from app.core.permissions import resolve_initial_role

        admin_emails = settings.platform_admin_email_set
        async with self._session() as session:
            result = await session.execute(select(User).where(User.clerk_id == clerk_id))
            row = result.scalar_one_or_none()
            if row:
                if email and row.email != email:
                    row.email = email
                if display_name and row.display_name != display_name:
                    row.display_name = display_name
                if email and email.lower() in admin_emails:
                    row.role = "platform_admin"
                await session.commit()
                return self._user_to_dict(row)
            row = User(
                clerk_id=clerk_id,
                email=email,
                display_name=display_name or (email.split("@")[0] if email else ""),
                role=resolve_initial_role(email, admin_emails),
                permissions=None,
                is_active=True,
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return self._user_to_dict(row)

    async def get_user_by_id(self, user_id: str) -> dict | None:
        async with self._session() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            row = result.scalar_one_or_none()
            return self._user_to_dict(row) if row else None

    async def update_user(self, user_id: str, updates: dict) -> dict | None:
        from app.core.permissions import ALL_PERMISSIONS, normalize_role

        async with self._session() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            row = result.scalar_one_or_none()
            if not row:
                return None
            if "role" in updates:
                row.role = normalize_role(str(updates["role"]))
            if "permissions" in updates:
                perms = updates["permissions"]
                row.permissions = None if perms is None else [p for p in perms if p in ALL_PERMISSIONS]
            if "is_active" in updates:
                row.is_active = bool(updates["is_active"])
            if "display_name" in updates:
                row.display_name = str(updates["display_name"])
            await session.commit()
            await session.refresh(row)
            return self._user_to_dict(row)

    async def list_broker_accounts(self, enabled_only: bool = True) -> list[dict]:
        async with self._session() as session:
            query = select(BrokerAccount).where(BrokerAccount.user_id == _uid())
            if enabled_only:
                query = query.where(BrokerAccount.enabled.is_(True))
            result = await session.execute(query.order_by(BrokerAccount.created_at.asc()))
            return [self._broker_account_to_dict(r) for r in result.scalars().all()]

    async def create_broker_account(self, account: dict) -> dict:
        async with self._session() as session:
            payload = dict(account)
            payload.setdefault("user_id", _uid())
            row = BrokerAccount(**payload)
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return self._broker_account_to_dict(row)

    async def update_broker_account(self, account_row_id: str, updates: dict) -> dict | None:
        async with self._session() as session:
            result = await session.execute(
                select(BrokerAccount).where(
                    BrokerAccount.id == account_row_id,
                    BrokerAccount.user_id == _uid(),
                )
            )
            row = result.scalar_one_or_none()
            if not row:
                return None
            for key, value in updates.items():
                if key == "meta" and isinstance(value, dict):
                    row.meta = {**(row.meta or {}), **value}
                elif hasattr(row, key):
                    setattr(row, key, value)
            await session.commit()
            await session.refresh(row)
            return self._broker_account_to_dict(row)

    async def get_broker_account(
        self, broker_id: str, account_id: str | None = None
    ) -> dict | None:
        async with self._session() as session:
            query = select(BrokerAccount).where(
                BrokerAccount.user_id == _uid(),
                BrokerAccount.broker_id == broker_id,
            )
            if account_id:
                query = query.where(BrokerAccount.account_id == account_id)
            result = await session.execute(query.limit(1))
            row = result.scalar_one_or_none()
            return self._broker_account_to_dict(row) if row else None

    async def list_tax_lots(
        self, ticker: str | None = None, account_id: str | None = None
    ) -> list[dict]:
        async with self._session() as session:
            query = select(TaxLot).where(TaxLot.user_id == _uid())
            if ticker:
                query = query.where(TaxLot.ticker == ticker.upper())
            if account_id:
                query = query.where(TaxLot.account_id == account_id)
            result = await session.execute(query.order_by(TaxLot.acquired_at.asc()))
            return [self._tax_lot_to_dict(r) for r in result.scalars().all()]

    async def create_tax_lot(self, lot: dict) -> dict:
        async with self._session() as session:
            payload = dict(lot)
            payload.setdefault("user_id", _uid())
            row = TaxLot(**payload)
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return self._tax_lot_to_dict(row)

    @staticmethod
    def _paper_trade_to_dict(row: PaperTrade) -> dict:
        return {
            "id": row.id,
            "user_id": row.user_id,
            "ticker": row.ticker,
            "side": row.side,
            "quantity": row.quantity,
            "limit_price": row.limit_price,
            "fill_price": row.fill_price,
            "status": row.status,
            "verdict": row.verdict,
            "reason": row.reason,
            "pnl": row.pnl,
            "approval_id": row.approval_id,
            "source": row.source,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }

    @staticmethod
    def _user_to_dict(row: User) -> dict:
        return {
            "id": row.id,
            "clerk_id": row.clerk_id,
            "email": row.email,
            "display_name": row.display_name,
            "role": getattr(row, "role", "user") or "user",
            "permissions": getattr(row, "permissions", None),
            "is_active": getattr(row, "is_active", True),
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }

    @staticmethod
    def _automation_audit_to_dict(row: AutomationAuditLog) -> dict:
        return {
            "id": row.id,
            "event_type": row.event_type,
            "detail": row.detail,
            "ticker": row.ticker,
            "strategy_id": row.strategy_id,
            "strategy_name": row.strategy_name,
            "verdict": row.verdict,
            "meta": row.meta or {},
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }

    @staticmethod
    def _strategy_to_dict(row: TradeStrategy) -> dict:
        return {
            "id": row.id,
            "name": row.name,
            "description": row.description,
            "strategy_type": row.strategy_type,
            "config": row.config or {},
            "auto_approve": row.auto_approve,
            "enabled": row.enabled,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }

    @staticmethod
    def _proposal_to_dict(row: StrategyProposal) -> dict:
        return {
            "id": row.id,
            "strategy_id": row.strategy_id,
            "strategy_name": row.strategy_name,
            "ticker": row.ticker,
            "side": row.side,
            "quantity": row.quantity,
            "limit_price": row.limit_price,
            "trigger_context": row.trigger_context,
            "trigger_reason": row.trigger_reason,
            "risk_preview": row.risk_preview,
            "status": row.status,
            "approval_id": row.approval_id,
            "execution_result": row.execution_result,
            "notes": row.notes,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "resolved_at": row.resolved_at.isoformat() if row.resolved_at else None,
        }

    @staticmethod
    def _alert_to_dict(row: AlertEvent) -> dict:
        return {
            "id": row.id,
            "event_type": row.event_type,
            "severity": row.severity,
            "title": row.title,
            "detail": row.detail,
            "channels_sent": row.channels_sent or [],
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }

    @staticmethod
    def _broker_account_to_dict(row: BrokerAccount) -> dict:
        return {
            "id": row.id,
            "user_id": row.user_id,
            "broker_id": row.broker_id,
            "account_id": row.account_id,
            "label": row.label,
            "account_type": row.account_type,
            "enabled": row.enabled,
            "meta": row.meta or {},
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }

    @staticmethod
    def _tax_lot_to_dict(row: TaxLot) -> dict:
        return {
            "id": row.id,
            "user_id": row.user_id,
            "broker_id": row.broker_id,
            "account_id": row.account_id,
            "ticker": row.ticker,
            "quantity": row.quantity,
            "cost_basis": row.cost_basis,
            "acquired_at": row.acquired_at.isoformat() if row.acquired_at else None,
            "lot_method": row.lot_method,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }

    @staticmethod
    def _approval_to_dict(row: ApprovalRequest) -> dict:
        return {
            "id": row.id,
            "user_id": row.user_id,
            "ticker": row.ticker,
            "side": row.side,
            "quantity": row.quantity,
            "limit_price": row.limit_price,
            "order_type": row.order_type,
            "asset_type": row.asset_type,
            "broker_id": row.broker_id,
            "account_id": row.account_id,
            "option_contract": row.option_contract,
            "status": row.status,
            "risk_preview": row.risk_preview,
            "mcp_preview": row.mcp_preview,
            "execution_result": row.execution_result,
            "order_id": row.order_id,
            "notes": row.notes,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "resolved_at": row.resolved_at.isoformat() if row.resolved_at else None,
        }


_backend: StorageBackend | None = None


async def get_storage() -> StorageBackend:
    global _backend
    if _backend is None:
        raise RuntimeError("Storage not initialized — call init_storage() on startup")
    return _backend


async def init_storage() -> StorageBackend:
    global _backend
    if settings.storage_backend == "memory":
        _backend = MemoryStorageBackend()
        await _backend.init()
        return _backend

    if settings.storage_backend == "postgres":
        _backend = PostgresStorageBackend()
        await _backend.init()
        return _backend

    # auto: try postgres, fall back to memory
    try:
        pg = PostgresStorageBackend()
        await pg.init()
        _backend = pg
        logger.info("storage_selected", backend="postgres")
    except Exception as exc:
        logger.warning("storage_postgres_unavailable", error=str(exc))
        mem = MemoryStorageBackend()
        await mem.init()
        _backend = mem
        logger.info("storage_selected", backend="memory")
    return _backend


async def close_storage() -> None:
    global _backend
    if _backend:
        await _backend.close()
        _backend = None
