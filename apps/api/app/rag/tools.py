"""Agentic RAG tools — intent-based retrieval and structured direct calls."""

from __future__ import annotations

import asyncio

import structlog

from app.core.config import settings
from app.db.storage import get_storage
from app.ml.scoring import score_ticker
from app.rag.router import QueryPlan, plan_query
from app.rag.service import RAGChunk, RAGService
from app.rag.tool_routing import infer_rag_tools
from app.risk.engine import RiskEngine
from app.services.features import compute_ticker_features
from app.services.market_quotes import fetch_price_context, quote_to_dict
from app.services.ml_retrain import MLRetrainService
from app.services.regime import RegimeService

logger = structlog.get_logger()


class RAGTools:
    def __init__(self):
        self.rag = RAGService()
        self.risk = RiskEngine()
        self.regime = RegimeService()
        self.ml = MLRetrainService()

    async def search_playbooks(
        self, query: str, *, ticker: str | None = None, top_k: int | None = None
    ) -> list[RAGChunk]:
        return await self.rag.search(
            query,
            top_k=top_k or settings.rag_top_k,
            ticker=ticker,
            doc_types=["playbook"],
        )

    async def search_filings(
        self, query: str, *, ticker: str | None = None, top_k: int | None = None
    ) -> list[RAGChunk]:
        return await self.rag.search(
            query,
            top_k=top_k or settings.rag_top_k,
            ticker=ticker,
            doc_types=["filing"],
        )

    async def search_journal(
        self, query: str, *, ticker: str | None = None, top_k: int | None = None
    ) -> list[RAGChunk]:
        return await self.rag.search(
            query,
            top_k=top_k or settings.rag_top_k,
            ticker=ticker,
            doc_types=["journal"],
        )

    async def search_analysis_history(
        self, query: str, *, ticker: str | None = None, top_k: int | None = None
    ) -> list[RAGChunk]:
        return await self.rag.search(
            query,
            top_k=top_k or settings.rag_top_k,
            ticker=ticker,
            doc_types=["analysis_snapshot"],
        )

    async def search_ml_runs(
        self, query: str, *, ticker: str | None = None, top_k: int | None = None
    ) -> list[RAGChunk]:
        return await self.rag.search(
            query,
            top_k=top_k or settings.rag_top_k,
            ticker=ticker,
            doc_types=["ml_run"],
        )

    async def search_news(
        self, query: str, *, ticker: str | None = None, top_k: int | None = None
    ) -> list[RAGChunk]:
        return await self.rag.search(
            query,
            top_k=top_k or settings.rag_top_k,
            ticker=ticker,
            doc_types=["news"],
        )

    async def search_regime(
        self, query: str, *, ticker: str | None = None, top_k: int | None = None
    ) -> list[RAGChunk]:
        return await self.rag.search(
            query,
            top_k=top_k or settings.rag_top_k,
            ticker=ticker,
            doc_types=["regime_snapshot"],
        )

    async def query_trades(self, *, ticker: str | None = None, limit: int = 10) -> dict:
        storage = await get_storage()
        trades = await storage.list_paper_trades(limit=limit)
        if ticker:
            trades = [t for t in trades if str(t.get("ticker", "")).upper() == ticker.upper()]
        return {"trades": trades, "count": len(trades)}

    async def run_ticker_analysis(self, ticker: str) -> dict:
        ticker = ticker.upper()
        regime_data = await self.regime.detect()
        features = await compute_ticker_features(ticker)
        features["ml_vol_prob"] = regime_data.get("ml_vol_prob", 0)
        features["ml_vol_confidence"] = regime_data.get("ml_vol_confidence", 0)
        scores = score_ticker(features, ticker)
        adjusted = self.regime.apply_to_score(scores["composite"], regime_data)
        verdict = self.risk.evaluate_ticker(ticker, features, scores, regime=regime_data)
        return {
            "ticker": ticker,
            "composite_score": scores["composite"],
            "composite_score_adjusted": adjusted,
            "setup_label": scores["label"],
            "risk_verdict": verdict.verdict,
            "warnings": verdict.warnings,
            "ml_bullish_prob": features.get("ml_bullish_prob"),
        }

    async def check_risk_limits(
        self,
        ticker: str,
        *,
        side: str = "buy",
        quantity: float = 1.0,
        limit_price: float | None = None,
    ) -> dict:
        features = await compute_ticker_features(ticker)
        price = limit_price or float(features.get("last_price", 0))
        return await self.risk.preview_trade(
            ticker=ticker.upper(),
            side=side,
            quantity=quantity,
            limit_price=price,
        )

    async def get_quote(self, ticker: str) -> dict | None:
        quote, _ = await fetch_price_context(ticker.upper(), include_web=False)
        if not quote or quote.get("last_price") is None:
            return None
        return quote_to_dict(quote)

    async def portfolio_snapshot(self) -> dict:
        return await self.risk.portfolio_snapshot()

    async def ml_status(self) -> dict:
        return await self.ml.status()

    def _apply_diversity_quota(self, chunks: list[RAGChunk], top_k: int) -> list[RAGChunk]:
        caps = {
            "playbook": 2,
            "filing": 2,
            "news": 1,
            "regime_snapshot": 1,
            "journal": 1,
            "analysis_snapshot": 1,
            "ml_run": 1,
        }
        sorted_chunks = sorted(chunks, key=lambda c: c.score, reverse=True)
        picked: list[RAGChunk] = []
        type_counts: dict[str, int] = {}
        for chunk in sorted_chunks:
            doc_type = chunk.doc_type or (chunk.meta or {}).get("type", "document")
            count = type_counts.get(doc_type, 0)
            if count >= caps.get(doc_type, 2):
                continue
            picked.append(chunk)
            type_counts[doc_type] = count + 1
            if len(picked) >= top_k:
                break
        if len(picked) < top_k:
            for chunk in sorted_chunks:
                if chunk in picked:
                    continue
                picked.append(chunk)
                if len(picked) >= top_k:
                    break
        return picked

    async def _run_rag_tools(
        self,
        tool_names: list[str],
        message: str,
        *,
        ticker: str | None,
        top_k: int,
    ) -> list[RAGChunk]:
        if not tool_names:
            return []

        per_tool_k = max(1, top_k // len(tool_names))
        tool_map = {
            "search_playbooks": self.search_playbooks,
            "search_filings": self.search_filings,
            "search_journal": self.search_journal,
            "search_analysis_history": self.search_analysis_history,
            "search_ml_runs": self.search_ml_runs,
            "search_news": self.search_news,
            "search_regime": self.search_regime,
        }
        tasks = [
            tool_map[name](message, ticker=ticker, top_k=per_tool_k)
            for name in tool_names
            if name in tool_map
        ]
        if not tasks:
            return []

        results = await asyncio.gather(*tasks)
        merged: dict[str, RAGChunk] = {}
        for chunks in results:
            for chunk in chunks:
                existing = merged.get(chunk.id)
                if not existing or chunk.score > existing.score:
                    merged[chunk.id] = chunk
        return self._apply_diversity_quota(
            sorted(merged.values(), key=lambda c: c.score, reverse=True),
            top_k,
        )

    async def _run_direct_call(
        self,
        name: str,
        *,
        message: str,
        ticker: str | None,
        trade_intent: dict | None,
    ) -> tuple[str, dict]:
        if name == "get_quote" and ticker:
            data = await self.get_quote(ticker)
            return name, data or {}

        if name == "portfolio_snapshot":
            return name, await self.portfolio_snapshot()

        if name == "query_trades":
            return name, await self.query_trades(ticker=ticker)

        if name == "run_ticker_analysis" and ticker:
            return name, await self.run_ticker_analysis(ticker)

        if name == "check_risk_limits" and ticker:
            intent = trade_intent or {}
            return name, await self.check_risk_limits(
                ticker,
                side=intent.get("side", "buy"),
                quantity=float(intent.get("quantity", 1.0)),
                limit_price=intent.get("limit_price"),
            )

        if name == "ml_status":
            return name, await self.ml_status()

        return name, {}

    async def execute_plan(
        self,
        plan: QueryPlan,
        message: str,
        *,
        ticker: str | None = None,
        top_k: int | None = None,
        trade_intent: dict | None = None,
    ) -> tuple[list[RAGChunk], list[str], dict[str, dict]]:
        top_k = top_k or settings.rag_top_k
        tools_used: list[str] = list(plan.direct_calls)
        direct_results: dict[str, dict] = {}

        if plan.direct_calls:
            direct_tasks = [
                self._run_direct_call(
                    name,
                    message=message,
                    ticker=ticker,
                    trade_intent=trade_intent,
                )
                for name in plan.direct_calls
            ]
            for name, payload in await asyncio.gather(*direct_tasks):
                if payload:
                    direct_results[name] = payload

        rag_chunks: list[RAGChunk] = []
        if plan.use_rag and plan.rag_tools:
            tools_used.extend(plan.rag_tools)
            rag_chunks = await self._run_rag_tools(plan.rag_tools, message, ticker=ticker, top_k=top_k)

        if "check_risk_limits" in plan.direct_calls:
            has_playbook = any(
                (c.doc_type or (c.meta or {}).get("type")) == "playbook" for c in rag_chunks
            )
            if not has_playbook:
                extra = await self.search_playbooks(message, ticker=ticker, top_k=1)
                merged = {c.id: c for c in rag_chunks}
                for chunk in extra:
                    merged[chunk.id] = chunk
                rag_chunks = sorted(merged.values(), key=lambda c: c.score, reverse=True)[:top_k]

        logger.info(
            "query_plan_executed",
            rag_tools=plan.rag_tools,
            direct_calls=plan.direct_calls,
            chunks=len(rag_chunks),
            freshness=plan.freshness,
        )
        return rag_chunks, list(dict.fromkeys(tools_used)), direct_results

    async def retrieve_for_message(
        self,
        message: str,
        *,
        ticker: str | None = None,
        top_k: int | None = None,
        trade_intent: dict | None = None,
    ) -> tuple[list[RAGChunk], list[str], dict[str, dict], QueryPlan]:
        """Route query, run RAG + direct tools, return fused results."""
        plan = plan_query(message, tickers=[ticker] if ticker else None)
        if ticker and ticker not in plan.tickers:
            plan.tickers.insert(0, ticker)

        chunks, tools, direct = await self.execute_plan(
            plan,
            message,
            ticker=ticker,
            top_k=top_k,
            trade_intent=trade_intent,
        )
        return chunks, tools, direct, plan
