"""TradeGuard agent orchestrator — LLM explains, risk engine decides."""

import re
import uuid

import structlog

from app.ml.features import compute_ticker_features
from app.ml.scoring import score_ticker
from app.rag.service import RAGService
from app.risk.engine import RiskEngine

logger = structlog.get_logger()

TICKER_PATTERN = re.compile(r"\b(NVDA|MSFT|META|TSLA|QQQ|GBTC|AAPL|SPY|SMH)\b", re.I)


class TradeGuardOrchestrator:
    def __init__(self):
        self.risk = RiskEngine()
        self.rag = RAGService()

    async def handle_message(self, message: str, session_id: str | None = None) -> dict:
        sid = session_id or str(uuid.uuid4())
        tickers = list(dict.fromkeys(m.upper() for m in TICKER_PATTERN.findall(message)))

        rag_chunks = await self.rag.search(message)
        snapshot = await self.risk.portfolio_snapshot()

        if not tickers:
            return self._general_response(sid, message, snapshot, rag_chunks)

        primary = tickers[0]
        features = compute_ticker_features(primary)
        scores = score_ticker(features, primary)
        verdict = self.risk.evaluate_ticker(primary, features, scores)

        reply = self._format_analysis(primary, features, scores, verdict, snapshot, rag_chunks)
        decision = scores["label"]
        if verdict.verdict == "BLOCK":
            decision = "Avoid"
        elif verdict.verdict == "CAUTION":
            decision = "Watch — manual review required"

        suggested = []
        if verdict.verdict != "BLOCK":
            suggested = ["Show Risk", "Trade Plan"]
            if len(tickers) > 1:
                suggested.append(f"Compare {tickers[1]}")
            else:
                suggested.append("Compare META")

        return {
            "session_id": sid,
            "reply": reply,
            "decision": decision,
            "risk_verdict": verdict.verdict,
            "warnings": verdict.warnings,
            "suggested_actions": suggested,
        }

    def _general_response(self, sid: str, message: str, snapshot: dict, rag_chunks) -> dict:
        reply = (
            f"**Portfolio Risk: {snapshot['risk_label']}** ({snapshot['risk_score']}/100)\n\n"
            f"Account value: ${snapshot['portfolio_value']:,.2f} | "
            f"Beta: {snapshot['beta']} | Tech exposure: "
            f"{snapshot['sector_exposure'].get('Technology', 0):.1f}%\n\n"
            "Ask about a specific ticker (NVDA, MSFT, META, TSLA, QQQ, GBTC) "
            "or say *'Should I buy more NVDA today?'* for a full risk analysis.\n\n"
            "Phase 1 is **analysis-only** — no trades without your approval."
        )
        if rag_chunks:
            reply += f"\n\n**Relevant playbook:** {rag_chunks[0].content}"

        return {
            "session_id": sid,
            "reply": reply,
            "decision": "Analyze",
            "risk_verdict": "CAUTION" if snapshot["risk_score"] >= 55 else "ALLOW",
            "warnings": [a["detail"] for a in snapshot.get("alerts", [])],
            "suggested_actions": ["Show Risk", "View Holdings"],
        }

    def _format_analysis(self, ticker, features, scores, verdict, snapshot, rag_chunks) -> str:
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

        if verdict.warnings:
            lines.extend(["", "**Warnings**", *[f"- {w}" for w in verdict.warnings]])
        if verdict.blocks:
            lines.extend(["", "**Blocks**", *[f"- {b}" for b in verdict.blocks]])

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
            lines.extend(["", f"**Playbook:** {rag_chunks[0].content}"])

        return "\n".join(lines)
