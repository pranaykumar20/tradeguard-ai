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

from app.core.config import settings
from app.db.models import (
    ApprovalRequest,
    Base,
    ChatMessage,
    ChatSession,
    MarketFeatureCache,
    PaperTrade,
    RAGDocument,
)

logger = structlog.get_logger()


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(x * x for x in b)) or 1.0
    return dot / (na * nb)


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
    async def paper_trade_stats(self) -> dict:
        pass

    @abstractmethod
    async def upsert_rag_documents(self, docs: list[dict]) -> int:
        pass

    @abstractmethod
    async def search_rag(self, query_embedding: list[float], top_k: int = 3) -> list[dict]:
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


class MemoryStorageBackend(StorageBackend):
    backend_name = "memory"

    def __init__(self):
        self._path = Path(settings.memory_store_path)
        self._data: dict = {
            "chat_messages": [],
            "paper_trades": [],
            "approval_requests": [],
            "rag_documents": [],
            "feature_cache": {},
        }

    async def init(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if self._path.exists():
            try:
                self._data = json.loads(self._path.read_text())
            except json.JSONDecodeError:
                logger.warning("memory_store_corrupt", path=str(self._path))
        logger.info("storage_init", backend="memory", path=str(self._path))

    async def close(self) -> None:
        self._persist()

    def _persist(self) -> None:
        self._path.write_text(json.dumps(self._data, indent=2, default=str))

    async def save_chat_message(
        self, session_id: str, role: str, content: str, meta: dict | None = None
    ) -> None:
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
        msgs = [m for m in self._data["chat_messages"] if m["session_id"] == session_id]
        return msgs[-limit:]

    async def create_paper_trade(self, trade: dict) -> dict:
        row = {
            "id": str(uuid4()),
            "created_at": datetime.now(timezone.utc).isoformat(),
            **trade,
        }
        self._data["paper_trades"].insert(0, row)
        self._persist()
        return row

    async def update_paper_trade(self, trade_id: str, updates: dict) -> dict | None:
        for trade in self._data["paper_trades"]:
            if trade["id"] == trade_id:
                trade.update(updates)
                self._persist()
                return trade
        return None

    async def list_paper_trades(self, limit: int = 100) -> list[dict]:
        return self._data["paper_trades"][:limit]

    async def paper_trade_stats(self) -> dict:
        trades = self._data["paper_trades"]
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

    async def search_rag(self, query_embedding: list[float], top_k: int = 3) -> list[dict]:
        scored = []
        for doc in self._data["rag_documents"]:
            emb = doc.get("embedding") or []
            score = _cosine(query_embedding, emb) if emb else 0.0
            scored.append({**doc, "score": score})
        scored.sort(key=lambda d: d["score"], reverse=True)
        return scored[:top_k]

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
            "created_at": datetime.now(timezone.utc).isoformat(),
            "resolved_at": None,
            **request,
        }
        self._data.setdefault("approval_requests", []).insert(0, row)
        self._persist()
        return row

    async def update_approval_request(self, request_id: str, updates: dict) -> dict | None:
        for req in self._data.get("approval_requests", []):
            if req["id"] == request_id:
                req.update(updates)
                self._persist()
                return req
        return None

    async def get_approval_request(self, request_id: str) -> dict | None:
        return next(
            (r for r in self._data.get("approval_requests", []) if r["id"] == request_id),
            None,
        )

    async def list_approval_requests(
        self, status: str | None = None, limit: int = 50
    ) -> list[dict]:
        rows = self._data.get("approval_requests", [])
        if status:
            rows = [r for r in rows if r.get("status") == status]
        return rows[:limit]


class PostgresStorageBackend(StorageBackend):
    backend_name = "postgres"

    def __init__(self):
        self._engine = create_async_engine(settings.database_url, echo=False)
        self._session_factory = async_sessionmaker(self._engine, expire_on_commit=False)

    async def init(self) -> None:
        async with self._engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.run_sync(Base.metadata.create_all)
        logger.info("storage_init", backend="postgres")

    async def close(self) -> None:
        await self._engine.dispose()

    def _session(self) -> AsyncSession:
        return self._session_factory()

    async def save_chat_message(
        self, session_id: str, role: str, content: str, meta: dict | None = None
    ) -> None:
        async with self._session() as session:
            exists = await session.get(ChatSession, session_id)
            if not exists:
                session.add(ChatSession(id=session_id))
            session.add(
                ChatMessage(session_id=session_id, role=role, content=content, meta=meta)
            )
            await session.commit()

    async def get_chat_messages(self, session_id: str, limit: int = 50) -> list[dict]:
        async with self._session() as session:
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
            row = PaperTrade(**trade)
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return {
                "id": row.id,
                "ticker": row.ticker,
                "side": row.side,
                "quantity": row.quantity,
                "limit_price": row.limit_price,
                "fill_price": row.fill_price,
                "status": row.status,
                "verdict": row.verdict,
                "reason": row.reason,
                "pnl": row.pnl,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }

    async def update_paper_trade(self, trade_id: str, updates: dict) -> dict | None:
        async with self._session() as session:
            row = await session.get(PaperTrade, trade_id)
            if not row:
                return None
            for key, val in updates.items():
                setattr(row, key, val)
            await session.commit()
            await session.refresh(row)
            return {
                "id": row.id,
                "ticker": row.ticker,
                "side": row.side,
                "quantity": row.quantity,
                "limit_price": row.limit_price,
                "fill_price": row.fill_price,
                "status": row.status,
                "verdict": row.verdict,
                "reason": row.reason,
                "pnl": row.pnl,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }

    async def list_paper_trades(self, limit: int = 100) -> list[dict]:
        async with self._session() as session:
            result = await session.execute(
                select(PaperTrade).order_by(PaperTrade.created_at.desc()).limit(limit)
            )
            return [
                {
                    "id": r.id,
                    "ticker": r.ticker,
                    "side": r.side,
                    "quantity": r.quantity,
                    "limit_price": r.limit_price,
                    "fill_price": r.fill_price,
                    "status": r.status,
                    "verdict": r.verdict,
                    "reason": r.reason,
                    "pnl": r.pnl,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in result.scalars().all()
            ]

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

    async def search_rag(self, query_embedding: list[float], top_k: int = 3) -> list[dict]:
        async with self._session() as session:
            result = await session.execute(select(RAGDocument))
            docs = result.scalars().all()
            scored = []
            for doc in docs:
                emb = list(doc.embedding) if doc.embedding is not None else []
                score = _cosine(query_embedding, emb) if emb else 0.0
                scored.append(
                    {
                        "id": doc.id,
                        "chunk_id": doc.chunk_id,
                        "source": doc.source,
                        "content": doc.content,
                        "meta": doc.meta,
                        "score": score,
                    }
                )
            scored.sort(key=lambda d: d["score"], reverse=True)
            return scored[:top_k]

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
            row = ApprovalRequest(**request)
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return self._approval_to_dict(row)

    async def update_approval_request(self, request_id: str, updates: dict) -> dict | None:
        async with self._session() as session:
            row = await session.get(ApprovalRequest, request_id)
            if not row:
                return None
            for key, val in updates.items():
                setattr(row, key, val)
            await session.commit()
            await session.refresh(row)
            return self._approval_to_dict(row)

    async def get_approval_request(self, request_id: str) -> dict | None:
        async with self._session() as session:
            row = await session.get(ApprovalRequest, request_id)
            return self._approval_to_dict(row) if row else None

    async def list_approval_requests(
        self, status: str | None = None, limit: int = 50
    ) -> list[dict]:
        async with self._session() as session:
            query = select(ApprovalRequest).order_by(ApprovalRequest.created_at.desc()).limit(limit)
            if status:
                query = query.where(ApprovalRequest.status == status)
            result = await session.execute(query)
            return [self._approval_to_dict(r) for r in result.scalars().all()]

    @staticmethod
    def _approval_to_dict(row: ApprovalRequest) -> dict:
        return {
            "id": row.id,
            "ticker": row.ticker,
            "side": row.side,
            "quantity": row.quantity,
            "limit_price": row.limit_price,
            "order_type": row.order_type,
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
