"""TradeGuard agent orchestrator — LLM explains, risk engine decides."""

import re
import uuid

import structlog

from app.agents.llm import generate_reply
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
        reply = await self._compose_reply(
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

        suggested = self._suggested_actions(verdict, tickers, trade_preview)

        result = {
            "session_id": sid,
            "reply": reply,
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

        storage = await get_storage()
        await storage.save_chat_message(sid, "user", message)
        await storage.save_chat_message(sid, "assistant", reply, meta=result)
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
    ) -> str:
        try:
            llm_reply = await generate_reply(message, context)
            if llm_reply:
                header = f"## {ticker} — **{verdict.verdict}**\n\n"
                reply = header + llm_reply.strip()
                return self._prepend_price_fact(reply, message, quote_data)
        except Exception:
            logger.info("llm_fallback_to_template", ticker=ticker)

        body = self._format_analysis(
            ticker, features, scores, verdict, snapshot, rag_chunks, trade_preview, news_data
        )
        return self._prepend_price_fact(body, message, quote_data)

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
                f"**Portfolio Risk: {snapshot['risk_label']}** ({snapshot['risk_score']}/100)\n\n"
                f"Account value: ${snapshot['portfolio_value']:,.2f} | "
                f"Beta: {snapshot['beta']} | Tech exposure: "
                f"{snapshot['sector_exposure'].get('Technology', 0):.1f}%\n\n"
                "Ask about a specific ticker (NVDA, MSFT, META, TSLA, QQQ, GBTC) "
                "or say *'Should I buy more NVDA today?'* for a full risk analysis.\n\n"
                "Phase 1 is **analysis-only** — no trades without your approval."
                f"{llm_hint}"
            )
            if rag_chunks:
                reply += f"\n\n{format_chunks_for_context(rag_chunks)}"

        reply = self._prepend_price_fact(reply, message, quote_data)

        warnings = [a["detail"] for a in snapshot.get("alerts", [])]

        result = {
            "session_id": sid,
            "reply": reply,
            "decision": "Analyze",
            "risk_verdict": "CAUTION" if snapshot["risk_score"] >= 55 else "ALLOW",
            "warnings": warnings,
            "suggested_actions": ["Show Risk", "View Holdings"],
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

    def _format_analysis(
        self, ticker, features, scores, verdict, snapshot, rag_chunks, trade_preview=None, news_data=None
    ) -> str:
        lines = [
            f"## {ticker} — {verdict.verdict}",
            "",
            f"**Setup score:** {scores['composite']}/100 ({scores['label']})",
            "",
            "**Scores**",
            f"- Technical: {scores['components']['technical']}",
            f"- Macro (QQQ): {scores['components']['macro']} ({features['qqq_trend']})",
            f"- News: {scores['components']['news']}",
            f"- ML bullish prob: {float(features['ml_bullish_prob'])*100:.0f}%",
            f"- Risk: {scores['components']['risk']}",
            "",
            "**Portfolio context**",
            f"- Tech exposure: {snapshot['sector_exposure'].get('Technology', 0):.1f}% "
            f"(limit {self.risk.rules.max_tech_sector_pct:.0f}%)",
            f"- Account risk score: {snapshot['risk_score']}/100 ({snapshot['risk_label']})",
        ]

        if trade_preview:
            lines.extend(
                [
                    "",
                    "**Trade preview**",
                    f"- {trade_preview['side'].upper()} {trade_preview['quantity']} @ "
                    f"${trade_preview['limit_price']:.2f} = ${trade_preview['order_value']:.2f}",
                    f"- Preview verdict: **{trade_preview['verdict']}**",
                ]
            )

        if verdict.warnings:
            lines.extend(["", "**Warnings**", *[f"- {w}" for w in verdict.warnings]])
        if verdict.blocks:
            lines.extend(["", "**Blocks**", *[f"- {b}" for b in verdict.blocks]])

        if news_data and news_data.get("headlines"):
            lines.extend(["", format_news_for_context(news_data)])

        lines.extend(
            [
                "",
                "**Decision**",
                "Prepare limit order only. **Manual approval required.**"
                if verdict.verdict != "BLOCK"
                else "Trade blocked by risk engine.",
            ]
        )

        if rag_chunks:
            lines.extend(["", format_chunks_for_context(rag_chunks)])

        return "\n".join(lines)

    def _suggested_actions(self, verdict, tickers: list[str], trade_preview: dict | None) -> list[str]:
        if verdict.verdict == "BLOCK":
            return ["Show Risk", "View Holdings"]

        actions = ["Show Risk", "Trade Plan"]
        if trade_preview:
            actions.insert(0, "Preview Trade")
        if len(tickers) > 1:
            actions.append(f"Analyze {tickers[1]}")
        else:
            actions.append("View Holdings")
        return actions
