"""TradeGuard agent orchestrator — LLM explains, risk engine decides."""

import re
import uuid
from collections.abc import AsyncIterator

import structlog

from app.agents.intent import detect_intent
from app.agents.llm import generate_reply, stream_reply
from app.agents.llm_validator import inject_citation_markers, validate_llm_reply
from app.agents.response_builder import (
    attach_citations,
    build_citations,
    build_compare_response,
    build_portfolio_response,
    build_price_response,
    build_ticker_analysis,
    extract_llm_summary,
    structured_to_markdown,
)
from app.agents.tickers import extract_tickers, is_price_query
from app.core.config import settings
from app.ml.scoring import score_ticker
from app.rag.service import RAGService, format_chunks_for_context
from app.rag.tools import RAGTools
from app.risk.engine import RiskEngine, RiskVerdict
from app.services.features import compute_ticker_features
from app.services.market_quotes import fetch_price_context, quote_to_dict
from app.services.news import NewsService, format_news_for_context
from app.db.storage import get_storage

_news = NewsService()

logger = structlog.get_logger()

TICKER_PATTERN = re.compile(r"\b(NVDA|MSFT|META|TSLA|QQQ|GBTC|AAPL|SPY|SMH)\b", re.I)  # trade intent parsing
TRADE_SIDE_PATTERN = re.compile(r"\b(buy|sell|purchase|add)\b", re.I)
OPTION_PATTERN = re.compile(r"\b(option|call|put|options)\b", re.I)


class TradeGuardOrchestrator:
    def __init__(self):
        self.risk = RiskEngine()
        self.rag = RAGService()
        self.rag_tools = RAGTools()

    async def _retrieve_rag(self, message: str, ticker: str | None) -> tuple[list, list[str]]:
        try:
            return await self.rag_tools.retrieve_for_message(message, ticker=ticker)
        except Exception as exc:
            logger.warning("rag_retrieval_failed", error=str(exc), ticker=ticker)
            return [], []

    async def _fetch_web_context(self, message: str, ticker: str | None) -> dict:
        try:
            return await _news.search_for_chat(message, ticker=ticker, limit=5)
        except Exception as exc:
            logger.warning("web_search_failed", error=str(exc), ticker=ticker)
            return {"headlines": [], "live_search": False}

    async def _fetch_price_context(self, message: str, ticker: str | None) -> tuple[dict | None, str]:
        if not ticker:
            return None, ""
        try:
            include_web = is_price_query(message) or bool(settings.tavily_api_key)
            quote, block = await fetch_price_context(ticker, include_web=include_web)
            return quote, block
        except Exception as exc:
            logger.warning("price_context_failed", ticker=ticker, error=str(exc))
            return None, ""

    async def handle_message(self, message: str, session_id: str | None = None) -> dict:
        sid = session_id or str(uuid.uuid4())
        tickers = extract_tickers(message)
        primary_ticker = tickers[0] if tickers else None

        rag_chunks, rag_tools_used = await self._retrieve_rag(message, primary_ticker)
        web_data = await self._fetch_web_context(message, primary_ticker)
        quote_data, price_context = await self._fetch_price_context(message, primary_ticker)
        snapshot = await self.risk.portfolio_snapshot()

        if not tickers:
            result = await self._general_response(
                sid,
                message,
                snapshot,
                rag_chunks,
                rag_tools_used,
                web_data,
                price_context,
                quote_data,
            )
            result = self._enrich_result(result)
            storage = await get_storage()
            await storage.save_chat_message(sid, "user", message)
            await storage.save_chat_message(sid, "assistant", result["reply"], meta=result)
            return result

        intent = detect_intent(message, tickers)

        if intent == "compare" and len(tickers) >= 2:
            result = await self._compare_response(
                sid,
                message,
                tickers[:2],
                snapshot,
                rag_chunks,
                rag_tools_used,
                web_data,
                quote_data,
            )
            result = self._enrich_result(result)
            storage = await get_storage()
            await storage.save_chat_message(sid, "user", message)
            await storage.save_chat_message(sid, "assistant", result["reply"], meta=result)
            return result

        primary = tickers[0]
        features = await compute_ticker_features(primary)
        scores = score_ticker(features, primary)
        news_data = web_data
        verdict = self.risk.evaluate_ticker(primary, features, scores)

        trade_preview = None
        trade_intent = self._parse_trade_intent(message, primary, features)
        if trade_intent:
            trade_preview = await self.risk.preview_trade(**trade_intent)

        all_warnings = list(verdict.warnings)
        all_blocks = list(verdict.blocks)
        if trade_preview:
            all_warnings = list(dict.fromkeys(all_warnings + trade_preview["warnings"]))
            all_blocks = list(dict.fromkeys(all_blocks + trade_preview["blocks"]))

        if all_blocks:
            final_verdict = "BLOCK"
        elif all_warnings:
            final_verdict = "CAUTION"
        else:
            final_verdict = "ALLOW"

        verdict = RiskVerdict(verdict=final_verdict, warnings=all_warnings, blocks=all_blocks)

        context = self._build_context(
            primary,
            features,
            scores,
            verdict,
            snapshot,
            rag_chunks,
            trade_preview,
            news_data,
            price_context,
        )
        reply, llm_summary = await self._compose_reply(
            message,
            context,
            primary,
            features,
            scores,
            verdict,
            snapshot,
            rag_chunks,
            trade_preview,
            news_data,
            quote_data,
        )

        decision = scores["label"]
        if verdict.verdict == "BLOCK":
            decision = "Avoid"
        elif verdict.verdict == "CAUTION":
            decision = "Watch — manual review required"

        suggested = self._suggested_actions(verdict, tickers, trade_preview, message)
        quote_dict = quote_to_dict(quote_data) if quote_data and quote_data.get("last_price") is not None else None

        layout = intent if intent in {"trade", "price"} else "analysis"
        if intent == "price":
            structured = build_price_response(
                ticker=primary,
                features=features,
                scores=scores,
                verdict=verdict,
                snapshot=snapshot,
                quote=quote_dict,
                news_data=news_data if news_data.get("headlines") else None,
            )
        else:
            structured = build_ticker_analysis(
                layout=layout,
                ticker=primary,
                features=features,
                scores=scores,
                verdict=verdict,
                snapshot=snapshot,
                tech_limit=self.risk.rules.max_tech_sector_pct,
                trade_preview=trade_preview,
                news_data=news_data if news_data.get("headlines") else None,
                quote=quote_dict,
                llm_summary=llm_summary,
            )

        result = {
            "session_id": sid,
            "reply": reply,
            "structured": structured,
            "decision": decision,
            "risk_verdict": verdict.verdict,
            "warnings": verdict.warnings,
            "suggested_actions": suggested,
            "rag_sources": [c.to_dict() for c in rag_chunks],
            "rag_tools": rag_tools_used,
            "web_sources": news_data.get("headlines", [])[:5],
        }
        if quote_data and quote_data.get("last_price") is not None:
            result["quote"] = quote_to_dict(quote_data)
        if trade_preview:
            result["trade_preview"] = trade_preview
        if news_data.get("headlines"):
            result["news"] = {
                "sentiment_label": news_data.get("sentiment_label"),
                "headlines": news_data.get("headlines", [])[:5],
                "live_search": news_data.get("live_search", False),
            }

        result = self._enrich_result(result)
        storage = await get_storage()
        await storage.save_chat_message(sid, "user", message)
        await storage.save_chat_message(sid, "assistant", result["reply"], meta=result)
        return result

    async def handle_message_stream(
        self, message: str, session_id: str | None = None
    ) -> AsyncIterator[dict]:
        """SSE event generator: status → structured → tokens → done."""
        sid = session_id or str(uuid.uuid4())

        async def persist(result: dict) -> None:
            storage = await get_storage()
            await storage.save_chat_message(sid, "user", message)
            await storage.save_chat_message(sid, "assistant", result["reply"], meta=result)

        yield {"type": "status", "message": "Parsing your question…"}
        tickers = extract_tickers(message)
        primary_ticker = tickers[0] if tickers else None

        yield {"type": "status", "message": "Loading portfolio risk…"}
        rag_chunks, rag_tools_used = await self._retrieve_rag(message, primary_ticker)

        yield {"type": "status", "message": "Fetching market data…"}
        web_data = await self._fetch_web_context(message, primary_ticker)
        quote_data, price_context = await self._fetch_price_context(message, primary_ticker)
        snapshot = await self.risk.portfolio_snapshot()

        if not tickers:
            result = await self._general_response(
                sid, message, snapshot, rag_chunks, rag_tools_used, web_data, price_context, quote_data
            )
            enriched = self._enrich_result(result)
            yield {"type": "structured", "data": enriched.get("structured")}
            yield {"type": "done", "data": enriched}
            await persist(enriched)
            return

        intent = detect_intent(message, tickers)

        if intent == "compare" and len(tickers) >= 2:
            yield {"type": "status", "message": "Comparing tickers…"}
            result = await self._compare_response(
                sid, message, tickers[:2], snapshot, rag_chunks, rag_tools_used, web_data, quote_data
            )
            enriched = self._enrich_result(result)
            yield {"type": "structured", "data": enriched.get("structured")}
            yield {"type": "done", "data": enriched}
            await persist(enriched)
            return

        primary = tickers[0]
        yield {"type": "status", "message": "Running risk engine…"}

        features = await compute_ticker_features(primary)
        scores = score_ticker(features, primary)
        news_data = web_data
        verdict = self.risk.evaluate_ticker(primary, features, scores)

        trade_preview = None
        trade_intent = self._parse_trade_intent(message, primary, features)
        if trade_intent:
            trade_preview = await self.risk.preview_trade(**trade_intent)

        all_warnings = list(verdict.warnings)
        all_blocks = list(verdict.blocks)
        if trade_preview:
            all_warnings = list(dict.fromkeys(all_warnings + trade_preview["warnings"]))
            all_blocks = list(dict.fromkeys(all_blocks + trade_preview["blocks"]))

        if all_blocks:
            final_verdict = "BLOCK"
        elif all_warnings:
            final_verdict = "CAUTION"
        else:
            final_verdict = "ALLOW"

        verdict = RiskVerdict(verdict=final_verdict, warnings=all_warnings, blocks=all_blocks)
        context = self._build_context(
            primary, features, scores, verdict, snapshot, rag_chunks, trade_preview, news_data, price_context
        )

        decision = scores["label"]
        if verdict.verdict == "BLOCK":
            decision = "Avoid"
        elif verdict.verdict == "CAUTION":
            decision = "Watch — manual review required"

        quote_dict = quote_to_dict(quote_data) if quote_data and quote_data.get("last_price") is not None else None
        layout = intent if intent in {"trade", "price"} else "analysis"

        if intent == "price":
            structured = build_price_response(
                ticker=primary,
                features=features,
                scores=scores,
                verdict=verdict,
                snapshot=snapshot,
                quote=quote_dict,
                news_data=news_data if news_data.get("headlines") else None,
            )
        else:
            structured = build_ticker_analysis(
                layout=layout,
                ticker=primary,
                features=features,
                scores=scores,
                verdict=verdict,
                snapshot=snapshot,
                tech_limit=self.risk.rules.max_tech_sector_pct,
                trade_preview=trade_preview,
                news_data=news_data if news_data.get("headlines") else None,
                quote=quote_dict,
            )

        pre_result = {
            "session_id": sid,
            "reply": "",
            "structured": structured,
            "decision": decision,
            "risk_verdict": verdict.verdict,
            "warnings": verdict.warnings,
            "suggested_actions": self._suggested_actions(verdict, tickers, trade_preview, message),
            "rag_sources": [c.to_dict() for c in rag_chunks],
            "rag_tools": rag_tools_used,
            "web_sources": news_data.get("headlines", [])[:5],
        }
        if quote_dict:
            pre_result["quote"] = quote_dict
        if trade_preview:
            pre_result["trade_preview"] = trade_preview
        if news_data.get("headlines"):
            pre_result["news"] = {
                "sentiment_label": news_data.get("sentiment_label"),
                "headlines": news_data.get("headlines", [])[:5],
                "live_search": news_data.get("live_search", False),
            }

        pre_enriched = self._enrich_result(pre_result)
        yield {"type": "structured", "data": pre_enriched.get("structured")}

        yield {"type": "status", "message": "Composing analysis…"}
        narrative_parts: list[str] = []
        try:
            async for token in stream_reply(message, context):
                narrative_parts.append(token)
                yield {"type": "token", "content": token}
        except Exception:
            logger.info("llm_stream_fallback", ticker=primary)

        if narrative_parts:
            raw = "".join(narrative_parts).strip()
            raw = self._prepend_price_fact(raw, message, quote_data)
            pre_result["reply"] = raw
        else:
            fallback = structured_to_markdown(structured)
            pre_result["reply"] = self._prepend_price_fact(fallback, message, quote_data)
            for word in pre_result["reply"].split():
                yield {"type": "token", "content": word + " "}

        enriched = self._enrich_result(pre_result)
        yield {"type": "done", "data": enriched}
        await persist(enriched)

    def _enrich_result(self, result: dict) -> dict:
        structured = dict(result.get("structured") or {})
        headlines = []
        if result.get("news"):
            headlines = result["news"].get("headlines", [])
        elif result.get("web_sources"):
            headlines = result["web_sources"]
        elif structured.get("headlines"):
            headlines = structured["headlines"]

        citations = build_citations(
            rag_sources=result.get("rag_sources"),
            headlines=headlines,
        )
        structured = attach_citations(structured, citations)
        result["structured"] = structured

        reply = result.get("reply", "")
        is_template = "### Snapshot" in reply or "### Key factors" in reply or "### Comparison" in reply

        if reply and not is_template:
            narrative = validate_llm_reply(reply)
            narrative = inject_citation_markers(narrative, len(citations))
            summary = extract_llm_summary(narrative)
            if summary:
                structured["summary"] = summary
                result["structured"] = structured
            result["narrative"] = narrative
            result["reply"] = narrative
        else:
            result["narrative"] = ""

        result["message_id"] = result.get("message_id") or str(uuid.uuid4())
        return result

    def _parse_trade_intent(self, message: str, ticker: str, features: dict) -> dict | None:
        if not TRADE_SIDE_PATTERN.search(message):
            return None

        side_match = TRADE_SIDE_PATTERN.search(message)
        side = "buy" if side_match and side_match.group(1).lower() in {"buy", "purchase", "add"} else "sell"

        qty_match = re.search(r"\b(\d+(?:\.\d+)?)\s*shares?\b", message, re.I)
        quantity = float(qty_match.group(1)) if qty_match else 1.0

        price_match = re.search(r"(?:at|@|\$)\s*(\d+(?:\.\d+)?)", message, re.I)
        limit_price = float(price_match.group(1)) if price_match else float(features["last_price"])

        order_type = "market" if re.search(r"\bmarket\s+order\b", message, re.I) else "limit"
        asset_type = "option" if OPTION_PATTERN.search(message) else "equity"

        return {
            "ticker": ticker,
            "side": side,
            "quantity": quantity,
            "limit_price": limit_price,
            "order_type": order_type,
            "asset_type": asset_type,
        }

    def _build_context(
        self,
        ticker: str,
        features: dict,
        scores: dict,
        verdict,
        snapshot: dict,
        rag_chunks,
        trade_preview: dict | None,
        news_data: dict | None = None,
        price_context: str = "",
    ) -> str:
        lines = [
            f"Ticker: {ticker}",
            f"Last price: ${features['last_price']:.2f}",
            f"Risk verdict: {verdict.verdict} (FINAL — do not override)",
            f"Setup score: {scores['composite']}/100 ({scores['label']})",
            f"Technical: {scores['components']['technical']}, Macro: {scores['components']['macro']}, "
            f"News: {scores['components']['news']}, ML: {scores['components']['ml']}, Risk: {scores['components']['risk']}",
            f"RSI: {features['rsi_14']}, QQQ trend: {features['qqq_trend']}, VIX change: {features['vix_change']}",
            f"Portfolio risk: {snapshot['risk_label']} ({snapshot['risk_score']}/100)",
            f"Tech exposure: {snapshot['sector_exposure'].get('Technology', 0):.1f}%",
        ]
        if price_context:
            lines.append(price_context)
        if news_data and news_data.get("headlines"):
            lines.append(format_news_for_context(news_data))
        if verdict.warnings:
            lines.append("Warnings: " + "; ".join(verdict.warnings))
        if verdict.blocks:
            lines.append("Blocks: " + "; ".join(verdict.blocks))
        if rag_chunks:
            lines.append(format_chunks_for_context(rag_chunks))
        if trade_preview:
            lines.append(
                f"Trade preview: {trade_preview['side']} {trade_preview['quantity']} "
                f"{ticker} @ ${trade_preview['limit_price']:.2f} "
                f"(${trade_preview['order_value']:.2f}) — {trade_preview['verdict']}"
            )
        return "\n".join(lines)

    async def _compose_reply(
        self,
        message: str,
        context: str,
        ticker: str,
        features: dict,
        scores: dict,
        verdict,
        snapshot: dict,
        rag_chunks,
        trade_preview: dict | None,
        news_data: dict | None = None,
        quote_data: dict | None = None,
    ) -> tuple[str, str | None]:
        llm_summary = None
        try:
            llm_reply = await generate_reply(message, context)
            if llm_reply:
                llm_summary = extract_llm_summary(llm_reply)
                return self._prepend_price_fact(llm_reply.strip(), message, quote_data), llm_summary
        except Exception:
            logger.info("llm_fallback_to_template", ticker=ticker)

        structured = build_ticker_analysis(
            layout="analysis",
            ticker=ticker,
            features=features,
            scores=scores,
            verdict=verdict,
            snapshot=snapshot,
            tech_limit=self.risk.rules.max_tech_sector_pct,
            trade_preview=trade_preview,
            news_data=news_data if news_data and news_data.get("headlines") else None,
        )
        body = structured_to_markdown(structured)
        return self._prepend_price_fact(body, message, quote_data), None

    @staticmethod
    def _prepend_price_fact(reply: str, message: str, quote_data: dict | None) -> str:
        if not is_price_query(message) or not quote_data or quote_data.get("last_price") is None:
            return reply
        live = "live" if quote_data.get("live") else "latest available"
        header = (
            f"**{quote_data['ticker']}** — **${quote_data['last_price']:.2f}** "
            f"({quote_data.get('change_pct', 0):+.2f}%, {live} via {quote_data.get('provider', 'market')})\n\n"
        )
        return header + reply

    async def _general_response(
        self,
        sid: str,
        message: str,
        snapshot: dict,
        rag_chunks,
        rag_tools_used: list[str],
        web_data: dict,
        price_context: str = "",
        quote_data: dict | None = None,
    ) -> dict:
        context = (
            f"Portfolio risk: {snapshot['risk_label']} ({snapshot['risk_score']}/100)\n"
            f"Account value: ${snapshot['portfolio_value']:,.2f}\n"
            f"Tech exposure: {snapshot['sector_exposure'].get('Technology', 0):.1f}%\n"
            f"Alerts: {[a['detail'] for a in snapshot.get('alerts', [])]}"
        )
        if price_context:
            context += f"\n{price_context}"
        web_context = format_news_for_context(web_data)
        if web_context:
            context += f"\n{web_context}"
        if rag_chunks:
            context += f"\n{format_chunks_for_context(rag_chunks)}"

        reply = None
        try:
            reply = await generate_reply(message, context)
        except Exception as exc:
            logger.warning("llm_fallback_to_template", error=str(exc))

        if not reply:
            if not (
                settings.cursor_api_key
                or settings.openai_api_key
                or settings.anthropic_api_key
            ):
                logger.info("llm_not_configured", provider=settings.llm_provider)
            else:
                logger.warning("llm_empty_reply", provider=settings.llm_provider)
            llm_hint = ""
            if settings.llm_provider == "cursor" and not settings.cursor_cloud_repo_url:
                llm_hint = (
                    "\n\n*AI replies require `CURSOR_CLOUD_REPO_URL` on Railway, "
                    "or set `LLM_PROVIDER=openai` with `OPENAI_API_KEY`.*"
                )
            elif settings.llm_provider == "openai" and not settings.openai_api_key:
                llm_hint = "\n\n*Set `OPENAI_API_KEY` on Railway to enable AI replies.*"

            reply = (
                f"**Your portfolio is in {snapshot['risk_label'].lower()} risk territory "
                f"({snapshot['risk_score']}/100).**\n\n"
                "### Overview\n"
                f"- Account value: **${snapshot['portfolio_value']:,.2f}**\n"
                f"- Beta: **{snapshot['beta']}**\n"
                f"- Tech exposure: **{snapshot['sector_exposure'].get('Technology', 0):.1f}%**\n\n"
                "### What I can help with\n"
                "Ask about a specific ticker (**NVDA**, **MSFT**, **META**, **TSLA**, **QQQ**, **GBTC**) "
                "or try: *Should I buy more NVDA today?* for a full risk breakdown.\n\n"
                "> Phase 1 is **analysis-only** — no trades execute without your approval."
                f"{llm_hint}"
            )
            if rag_chunks:
                reply += f"\n\n{format_chunks_for_context(rag_chunks)}"

        reply = self._prepend_price_fact(reply, message, quote_data)

        warnings = [a["detail"] for a in snapshot.get("alerts", [])]
        risk_verdict = "CAUTION" if snapshot["risk_score"] >= 55 else "ALLOW"
        quote_dict = quote_to_dict(quote_data) if quote_data and quote_data.get("last_price") is not None else None

        structured = build_portfolio_response(
            snapshot=snapshot,
            warnings=warnings,
            quote=quote_dict,
            news_data=web_data if web_data.get("headlines") else None,
            llm_summary=extract_llm_summary(reply),
        )

        result = {
            "session_id": sid,
            "reply": reply,
            "structured": structured,
            "decision": "Analyze",
            "risk_verdict": risk_verdict,
            "warnings": warnings,
            "suggested_actions": self._suggested_actions(
                RiskVerdict(verdict=risk_verdict, warnings=warnings, blocks=[]),
                [],
                None,
                message,
            ),
            "rag_sources": [c.to_dict() for c in rag_chunks],
            "rag_tools": rag_tools_used,
            "web_sources": web_data.get("headlines", [])[:5],
        }
        if quote_data and quote_data.get("last_price") is not None:
            result["quote"] = quote_to_dict(quote_data)
        if web_data.get("headlines"):
            result["news"] = {
                "sentiment_label": web_data.get("sentiment_label"),
                "headlines": web_data.get("headlines", [])[:5],
                "live_search": web_data.get("live_search", False),
            }
        return result

    async def _compare_response(
        self,
        sid: str,
        message: str,
        tickers: list[str],
        snapshot: dict,
        rag_chunks,
        rag_tools_used: list[str],
        web_data: dict,
        quote_data: dict | None,
    ) -> dict:
        ticker_data = []
        worst_verdict = "ALLOW"
        all_warnings: list[str] = []

        for ticker in tickers:
            features = await compute_ticker_features(ticker)
            scores = score_ticker(features, ticker)
            verdict = self.risk.evaluate_ticker(ticker, features, scores)
            all_warnings.extend(verdict.warnings)
            if verdict.verdict == "BLOCK":
                worst_verdict = "BLOCK"
            elif verdict.verdict == "CAUTION" and worst_verdict != "BLOCK":
                worst_verdict = "CAUTION"
            ticker_data.append(
                {
                    "ticker": ticker,
                    "features": features,
                    "scores": scores,
                    "verdict": verdict,
                }
            )

        rows = [
            {
                "label": "Setup score",
                "values": [f"{d['scores']['composite']}/100" for d in ticker_data],
            },
            {
                "label": "Verdict",
                "values": [d["verdict"].verdict for d in ticker_data],
            },
            {
                "label": "Last price",
                "values": [
                    f"${d['features']['last_price']:.2f}" if d["features"].get("last_price") else "—"
                    for d in ticker_data
                ],
            },
            {
                "label": "RSI",
                "values": [str(d["features"].get("rsi_14", "—")) for d in ticker_data],
            },
            {
                "label": "QQQ trend",
                "values": [str(d["features"].get("qqq_trend", "neutral")).title() for d in ticker_data],
            },
        ]

        structured = build_compare_response(tickers=tickers, rows=rows, snapshot=snapshot)
        reply = structured_to_markdown(structured)

        return {
            "session_id": sid,
            "reply": reply,
            "structured": structured,
            "decision": "Compare",
            "risk_verdict": worst_verdict,
            "warnings": list(dict.fromkeys(all_warnings)),
            "suggested_actions": [
                f"Analyze {tickers[0]}",
                f"Analyze {tickers[1]}",
                "Show Risk",
            ],
            "rag_sources": [c.to_dict() for c in rag_chunks],
            "rag_tools": rag_tools_used,
            "web_sources": web_data.get("headlines", [])[:5],
            **({"quote": quote_to_dict(quote_data)} if quote_data and quote_data.get("last_price") else {}),
        }

    def _suggested_actions(
        self,
        verdict,
        tickers: list[str],
        trade_preview: dict | None,
        message: str = "",
    ) -> list[str]:
        if verdict.verdict == "BLOCK":
            return ["Show Risk", "View Holdings"]

        actions = ["Show Risk", "Trade Plan"]
        if trade_preview:
            actions.insert(0, "Preview Trade")
        peers = {"NVDA": "META", "META": "NVDA", "MSFT": "AAPL", "AAPL": "MSFT", "TSLA": "META"}
        primary = tickers[0] if tickers else None
        if primary and peers.get(primary):
            actions.append(f"Compare {peers[primary]}")
        else:
            actions.append("View Holdings")

        lower = message.lower()
        if primary and "risk" in lower and "Show Risk" not in actions:
            actions.insert(0, "Show Risk")
        return actions[:4]
