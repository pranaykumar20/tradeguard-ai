"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { Sidebar } from "@/components/Sidebar";
import { compareTickers, getTickerAnalysis, type TickerAnalysis } from "@/lib/api";
import { Btn, Card, PageHeader, Row } from "@/components/ui/Card";

const ALLOWED = ["NVDA", "MSFT", "META", "TSLA", "QQQ", "GBTC"];

function verdictTone(v: string) {
  if (v === "BLOCK") return "red" as const;
  if (v === "CAUTION") return "orange" as const;
  return "green" as const;
}

function TickerPanel({ ticker }: { ticker: string }) {
  const [analysis, setAnalysis] = useState<TickerAnalysis | null>(null);
  const [compare, setCompare] = useState<
    { ticker: string; composite_score: number; setup_label: string; risk_verdict: string }[]
  >([]);

  useEffect(() => {
    let cancelled = false;

    Promise.all([
      getTickerAnalysis(ticker),
      compareTickers(["NVDA", "MSFT", "META", "QQQ"]),
    ])
      .then(([a, c]) => {
        if (!cancelled) {
          setAnalysis(a);
          setCompare(c.tickers);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setAnalysis(null);
          setCompare([]);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [ticker]);

  if (!analysis) {
    return <p className="text-sm text-muted">Analyzing {ticker}…</p>;
  }

  const mlProb = Math.round(Number(analysis.features.ml_bullish_prob) * 100);

  return (
    <div className="grid gap-[18px] lg:grid-cols-[1.35fr_0.85fr]">
      <Card>
        <h2 className="text-xl font-extrabold">{analysis.ticker} Analysis</h2>
        <div className="tg-chart mt-4">
          <span className="absolute bottom-[18px] left-[22px] text-[13px] font-bold text-muted">
            Mock live chart area
          </span>
        </div>
        <div className="mt-[18px] grid grid-cols-3 gap-3.5">
          <div className="tg-stock">
            <div className="tg-label">Technical</div>
            <div className="tg-value text-green">{Math.round(analysis.scores.technical)}</div>
          </div>
          <div className="tg-stock">
            <div className="tg-label">News</div>
            <div className="tg-value">{Math.round(analysis.scores.news)}</div>
          </div>
          <div className="tg-stock">
            <div className="tg-label">ML Bullish</div>
            <div className={`tg-value ${mlProb > 60 ? "text-green" : mlProb < 45 ? "text-red" : "text-orange"}`}>
              {mlProb}%
            </div>
          </div>
        </div>
      </Card>

      <Card warning>
        <h2 className="text-xl font-extrabold">AI Summary</h2>
        <p className="tg-sub mt-3">
          {analysis.ticker} setup: {analysis.setup_label}. Composite score {analysis.composite_score}/100.
          {analysis.warnings.length > 0
            ? ` ${analysis.warnings[0]}`
            : " Momentum and risk factors within normal range."}
        </p>
        <div className="mt-4">
          <Row label="Decision" value={analysis.setup_label.toUpperCase()} tone="orange" />
          <Row label="Risk Verdict" value={analysis.risk_verdict} tone={verdictTone(analysis.risk_verdict)} />
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <Link href="/dashboard" className="tg-btn tg-btn-primary inline-block">
            Prepare Trade
          </Link>
          <Btn variant="secondary">Add Alert</Btn>
        </div>
      </Card>

      <Card className="lg:col-span-2">
        <h2 className="font-extrabold">Compare tickers</h2>
        <table className="mt-4 w-full text-sm">
          <thead>
            <tr className="border-b border-white/10 text-left text-muted">
              <th className="pb-3 text-[13px] font-bold">Ticker</th>
              <th className="pb-3 text-[13px] font-bold">Score</th>
              <th className="pb-3 text-[13px] font-bold">Setup</th>
              <th className="pb-3 text-[13px] font-bold">Risk</th>
            </tr>
          </thead>
          <tbody>
            {compare.map((row) => (
              <tr key={row.ticker} className="border-b border-white/[0.08]">
                <td className="py-3.5 font-bold">{row.ticker}</td>
                <td className="py-3.5">{row.composite_score}</td>
                <td className="py-3.5">{row.setup_label}</td>
                <td className={`py-3.5 font-bold ${verdictTone(row.risk_verdict) === "red" ? "text-red" : verdictTone(row.risk_verdict) === "orange" ? "text-orange" : "text-green"}`}>
                  {row.risk_verdict}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}

function AnalysisContent() {
  const searchParams = useSearchParams();
  const initial = searchParams.get("ticker")?.toUpperCase() ?? "NVDA";
  const [ticker, setTicker] = useState(initial);

  return (
    <main className="mx-auto w-full max-w-[1400px] flex-1 p-7">
      <PageHeader title="Stock Analyzer" subtitle="ML scoring, risk verdict, and comparison" />

      <div className="mb-[18px] flex flex-wrap gap-2">
        {ALLOWED.map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTicker(t)}
            className={`rounded-[14px] px-4 py-2.5 text-sm font-bold ${
              ticker === t
                ? "bg-[linear-gradient(90deg,rgba(38,228,196,0.16),rgba(85,185,255,0.08))] text-foreground"
                : "border border-card-border text-muted hover:text-foreground"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      <TickerPanel key={ticker} ticker={ticker} />
    </main>
  );
}

export default function AnalysisPage() {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <Suspense fallback={<main className="flex-1 p-7 text-muted">Loading…</main>}>
        <AnalysisContent />
      </Suspense>
    </div>
  );
}
