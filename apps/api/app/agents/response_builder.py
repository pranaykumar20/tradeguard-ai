"""Build structured chat payloads for consistent UI rendering."""

from __future__ import annotations

import re
from typing import Any


def _factor(icon: str, title: str, detail: str, severity: str = "medium") -> dict:
    return {"icon": icon, "title": title, "detail": detail, "severity": severity}


def _metric(label: str, value: str, *, highlight: bool = False) -> dict:
    return {"label": label, "value": value, "highlight": highlight}


def _score_bar(label: str, value: int, maximum: int = 100) -> dict:
    return {"label": label, "value": value, "max": maximum}


def _headline_for_verdict(ticker: str, verdict: str, composite: int) -> str:
    if verdict == "BLOCK":
        return f"I don't recommend buying more {ticker} today — the trade is blocked."
    if verdict == "CAUTION":
        return f"I don't recommend buying more {ticker} today."
    if composite >= 60:
        return f"{ticker} looks acceptable, but proceed with a limit order only."
    return f"I'd wait on adding more {ticker} until the setup improves."


def _build_factors(
    *,
    ticker: str,
    features: dict,
    scores: dict,
    verdict,
    snapshot: dict,
    tech_limit: float,
    trade_preview: dict | None,
    news_data: dict | None,
) -> list[dict]:
    factors: list[dict] = []
    tech_pct = snapshot["sector_exposure"].get("Technology", 0.0)

    if tech_pct > tech_limit:
        factors.append(
            _factor(
                "⚠️",
                "High Tech Sector Exposure",
                f"Technology is {tech_pct:.0f}% of the portfolio (limit {tech_limit:.0f}%).",
                "high",
            )
        )
    elif tech_pct > tech_limit * 0.85:
        factors.append(
            _factor(
                "⚠️",
                "Tech Exposure Near Limit",
                f"Technology is {tech_pct:.0f}% (limit {tech_limit:.0f}%).",
                "medium",
            )
        )

    qqq_trend = features.get("qqq_trend", "neutral")
    macro = scores["components"]["macro"]
    if qqq_trend == "bearish" or macro < 45:
        factors.append(
            _factor(
                "📉",
                "QQQ Showing Weakness",
                f"Macro score {macro}/100; QQQ trend is {qqq_trend}.",
                "high" if macro < 40 else "medium",
            )
        )
    elif macro >= 60:
        factors.append(
            _factor(
                "📈",
                "Macro Tailwind",
                f"QQQ trend is {qqq_trend} (macro score {macro}/100).",
                "positive",
            )
        )

    if verdict.blocks:
        factors.append(_factor("🛑", "Trade Blocked", verdict.blocks[0], "high"))
    elif verdict.warnings:
        factors.append(_factor("⚠️", "Risk Warning", verdict.warnings[0], "medium"))

    if scores["composite"] >= 65 and verdict.verdict == "ALLOW":
        factors.append(
            _factor(
                "✅",
                f"Setup Score {scores['composite']}/100",
                f"{scores['label']} technical and risk profile.",
                "positive",
            )
        )

    if news_data and news_data.get("headlines"):
        sentiment = news_data.get("sentiment_label", "mixed")
        factors.append(
            _factor(
                "📰",
                "Recent Headlines",
                f"News sentiment is {sentiment}; {len(news_data['headlines'])} headline(s) in context.",
                "low",
            )
        )

    if trade_preview or verdict.verdict == "CAUTION":
        factors.append(
            _factor(
                "👤",
                "Manual Approval Required",
                "Phase 1 is analysis-only; any order needs your explicit approval.",
                "medium",
            )
        )

    if not factors:
        factors.append(
            _factor(
                "✅",
                "Risk Within Limits",
                f"Portfolio risk score {snapshot['risk_score']}/100 ({snapshot['risk_label']}).",
                "positive",
            )
        )

    return factors[:4]


def build_ticker_analysis(
    *,
    layout: str,
    ticker: str,
    features: dict,
    scores: dict,
    verdict,
    snapshot: dict,
    tech_limit: float,
    trade_preview: dict | None = None,
    news_data: dict | None = None,
    quote: dict | None = None,
    llm_summary: str | None = None,
) -> dict:
    last_price = features.get("last_price")
    tech_pct = snapshot["sector_exposure"].get("Technology", 0.0)
    summary = llm_summary or _headline_for_verdict(ticker, verdict.verdict, scores["composite"])

    structured: dict[str, Any] = {
        "layout": layout,
        "summary": summary,
        "factors": _build_factors(
            ticker=ticker,
            features=features,
            scores=scores,
            verdict=verdict,
            snapshot=snapshot,
            tech_limit=tech_limit,
            trade_preview=trade_preview,
            news_data=news_data,
        ),
        "snapshot": [
            _metric("Setup score", f"{scores['composite']}/100 ({scores['label']})", highlight=True),
            _metric("Last price", f"${last_price:.2f}" if last_price is not None else "—"),
            _metric("Portfolio risk", f"{snapshot['risk_label']} ({snapshot['risk_score']}/100)"),
            _metric("Tech exposure", f"{tech_pct:.0f}% (limit {tech_limit:.0f}%)"),
        ],
        "scores": [
            _score_bar("Technical", scores["components"]["technical"]),
            _score_bar("Macro", scores["components"]["macro"]),
            _score_bar("News", scores["components"]["news"]),
            _score_bar("ML", scores["components"]["ml"]),
            _score_bar("Risk", scores["components"]["risk"]),
        ],
        "disclaimer": "Phase 1 is analysis-only — any order requires your explicit approval.",
        "follow_up": "Would you like me to run additional analysis or show alternative ideas?",
    }

    if quote and quote.get("last_price") is not None:
        structured["quote"] = quote
    if trade_preview:
        structured["trade_preview"] = {
            "ticker": trade_preview.get("ticker", ticker),
            "side": trade_preview["side"],
            "quantity": trade_preview["quantity"],
            "limit_price": trade_preview["limit_price"],
            "order_value": trade_preview["order_value"],
            "verdict": trade_preview["verdict"],
        }
    if news_data and news_data.get("headlines"):
        structured["headlines"] = [
            {
                "title": h.get("title", ""),
                "source": h.get("source", ""),
                "summary": (h.get("summary") or "")[:180],
                "url": h.get("url", ""),
                "sentiment": h.get("sentiment"),
            }
            for h in news_data["headlines"][:4]
        ]

    return structured


def build_price_response(
    *,
    ticker: str,
    features: dict,
    scores: dict,
    verdict,
    snapshot: dict,
    quote: dict | None = None,
    news_data: dict | None = None,
) -> dict:
    last_price = features.get("last_price")
    change_hint = ""
    if quote and quote.get("change_pct") is not None:
        change_hint = f" ({quote['change_pct']:+.2f}% today)"

    structured: dict[str, Any] = {
        "layout": "price",
        "summary": f"{ticker} is trading at ${last_price:.2f}{change_hint}." if last_price else f"{ticker} price data unavailable.",
        "factors": [
            _factor("📊", "Setup Score", f"{scores['composite']}/100 ({scores['label']}).", "low"),
            _factor(
                "🛡️",
                "Risk Verdict",
                f"{verdict.verdict} — portfolio risk {snapshot['risk_label']} ({snapshot['risk_score']}/100).",
                "high" if verdict.verdict == "BLOCK" else "medium" if verdict.verdict == "CAUTION" else "positive",
            ),
        ],
        "snapshot": [
            _metric("Last price", f"${last_price:.2f}" if last_price is not None else "—", highlight=True),
            _metric("RSI (14)", f"{features.get('rsi_14', '—')}"),
            _metric("QQQ trend", str(features.get("qqq_trend", "neutral")).title()),
            _metric("Setup score", f"{scores['composite']}/100"),
        ],
        "disclaimer": "Prices are for analysis only — not a trade recommendation.",
        "follow_up": f"Would you like a full risk analysis on {ticker}?",
    }

    if quote:
        structured["quote"] = quote
    if news_data and news_data.get("headlines"):
        structured["headlines"] = [
            {
                "title": h.get("title", ""),
                "source": h.get("source", ""),
                "summary": (h.get("summary") or "")[:180],
                "url": h.get("url", ""),
            }
            for h in news_data["headlines"][:3]
        ]

    return structured


def build_portfolio_response(
    *,
    snapshot: dict,
    warnings: list[str],
    quote: dict | None = None,
    news_data: dict | None = None,
    llm_summary: str | None = None,
) -> dict:
    tech_pct = snapshot["sector_exposure"].get("Technology", 0.0)
    summary = llm_summary or (
        f"Your portfolio is in {snapshot['risk_label'].lower()} risk territory "
        f"({snapshot['risk_score']}/100)."
    )

    factors = []
    for alert in snapshot.get("alerts", [])[:2]:
        sev = "high" if alert.get("severity") == "high" else "medium"
        factors.append(_factor("⚠️", alert.get("title", "Alert"), alert.get("detail", ""), sev))
    for warning in warnings[:2]:
        factors.append(_factor("⚠️", "Risk Alert", warning, "medium"))
    if not factors:
        factors.append(
            _factor(
                "✅",
                "No Active Alerts",
                f"Account value ${snapshot['portfolio_value']:,.0f} · beta {snapshot['beta']}.",
                "positive",
            )
        )

    structured: dict[str, Any] = {
        "layout": "portfolio",
        "summary": summary,
        "factors": factors[:4],
        "snapshot": [
            _metric("Account value", f"${snapshot['portfolio_value']:,.0f}", highlight=True),
            _metric("Daily P&L", f"${snapshot.get('daily_pnl', 0):+,.0f}"),
            _metric("Risk score", f"{snapshot['risk_score']}/100 ({snapshot['risk_label']})"),
            _metric("Tech exposure", f"{tech_pct:.1f}%"),
        ],
        "disclaimer": "Phase 1 is analysis-only — no trades execute without your approval.",
        "follow_up": "Ask about a ticker (e.g. *Should I buy more NVDA today?*) for a full breakdown.",
    }

    if quote:
        structured["quote"] = quote
    if news_data and news_data.get("headlines"):
        structured["headlines"] = [
            {
                "title": h.get("title", ""),
                "source": h.get("source", ""),
                "summary": (h.get("summary") or "")[:180],
                "url": h.get("url", ""),
            }
            for h in news_data["headlines"][:3]
        ]

    return structured


def build_compare_response(
    *,
    tickers: list[str],
    rows: list[dict],
    snapshot: dict,
) -> dict:
    a, b = tickers[0], tickers[1]
    structured: dict[str, Any] = {
        "layout": "compare",
        "summary": f"Side-by-side comparison of {a} vs {b}.",
        "comparison": {
            "tickers": [a, b],
            "rows": rows,
        },
        "snapshot": [
            _metric("Portfolio risk", f"{snapshot['risk_label']} ({snapshot['risk_score']}/100)"),
            _metric("Tech exposure", f"{snapshot['sector_exposure'].get('Technology', 0):.0f}%"),
        ],
        "disclaimer": "Comparison is for analysis only — risk engine verdict is final per ticker.",
        "follow_up": f"Would you like a trade analysis on {a} or {b}?",
    }
    return structured


def structured_to_markdown(structured: dict) -> str:
    """Markdown fallback for clients that don't render structured UI."""
    lines = [f"**{structured['summary']}**", ""]

    if structured.get("factors"):
        lines.append("### Key factors")
        for factor in structured["factors"]:
            lines.append(f"- {factor['icon']} **{factor['title']}** — {factor['detail']}")
        lines.append("")

    if structured.get("comparison"):
        comp = structured["comparison"]
        tickers = comp["tickers"]
        lines.extend(["### Comparison", f"| Metric | {tickers[0]} | {tickers[1]} |", "| --- | --- | --- |"])
        for row in comp["rows"]:
            lines.append(f"| {row['label']} | {row['values'][0]} | {row['values'][1]} |")
        lines.append("")

    if structured.get("snapshot"):
        lines.extend(["### Snapshot", "| Metric | Value |", "| --- | --- |"])
        for item in structured["snapshot"]:
            lines.append(f"| {item['label']} | {item['value']} |")
        lines.append("")

    if structured.get("disclaimer"):
        lines.extend([f"> {structured['disclaimer']}", ""])

    if structured.get("follow_up"):
        lines.append(structured["follow_up"])

    return "\n".join(lines)


def extract_llm_summary(llm_reply: str | None) -> str | None:
    """Pull the first bold sentence from an LLM reply for structured.summary."""
    if not llm_reply:
        return None
    for line in llm_reply.splitlines():
        stripped = line.strip()
        if stripped.startswith("**") and stripped.endswith("**"):
            return stripped.strip("*").strip()
        match = re.search(r"\*\*(.+?)\*\*", stripped)
        if match:
            return match.group(1).strip()
    first = llm_reply.strip().split("\n")[0].strip("# ").strip()
    return first[:240] if first else None


def build_citations(
    *,
    rag_sources: list[dict] | None = None,
    headlines: list[dict] | None = None,
) -> list[dict]:
    citations: list[dict] = []
    idx = 1

    for headline in headlines or []:
        title = headline.get("title", "").strip()
        if not title:
            continue
        citations.append(
            {
                "id": idx,
                "kind": "news",
                "label": headline.get("source") or "News",
                "title": title,
                "url": headline.get("url", ""),
                "snippet": (headline.get("summary") or "")[:160],
            }
        )
        idx += 1
        if idx > 5:
            break

    for source in rag_sources or []:
        content = (source.get("content") or "").strip()
        if not content:
            continue
        citations.append(
            {
                "id": idx,
                "kind": "rag",
                "label": source.get("source") or "Playbook",
                "title": content[:80] + ("…" if len(content) > 80 else ""),
                "url": "",
                "snippet": content[:160],
            }
        )
        idx += 1
        if idx > 8:
            break

    return citations


def attach_citations(structured: dict, citations: list[dict]) -> dict:
    if citations:
        structured = {**structured, "citations": citations}
    return structured
