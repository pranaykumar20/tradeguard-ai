"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AppMain } from "@/components/layout/AppMain";
import { DashboardTopBar } from "@/components/dashboard/DashboardTopBar";
import { KpiSparkCard, RiskScoreCard } from "@/components/dashboard/KpiSparkCard";
import {
  getPortfolio,
  getRiskSnapshot,
  previewTrade,
  type RiskSnapshot,
  type TradePreview,
} from "@/lib/api";
import { Btn, Card, Row } from "@/components/ui/Card";

function verdictTone(v: string) {
  if (v === "BLOCK") return "red" as const;
  if (v === "CAUTION") return "orange" as const;
  return "green" as const;
}

export default function DashboardPage() {
  const [snapshot, setSnapshot] = useState<RiskSnapshot | null>(null);
  const [holdingsCount, setHoldingsCount] = useState(0);
  const [preview, setPreview] = useState<TradePreview | null>(null);
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({
    ticker: "NVDA",
    side: "buy" as "buy" | "sell",
    quantity: 1,
    limit_price: 120,
  });

  useEffect(() => {
    getRiskSnapshot().then(setSnapshot).catch(() => {});
    getPortfolio()
      .then((p) => setHoldingsCount(Object.keys(p.positions ?? {}).length))
      .catch(() => setHoldingsCount(0));
  }, []);

  async function runPreview(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      setPreview(await previewTrade(form));
    } catch {
      setPreview(null);
    } finally {
      setLoading(false);
    }
  }

  if (!snapshot) {
    return (
      <AppMain showMenuButton={false}>
        <div className="flex min-h-[50vh] items-center justify-center text-muted">Loading dashboard…</div>
      </AppMain>
    );
  }

  const dailyPct = snapshot.portfolio_value
    ? ((snapshot.daily_pnl / snapshot.portfolio_value) * 100).toFixed(2)
    : "0.00";
  const weeklyPnl = snapshot.daily_pnl * 3.72;
  const weeklyPct = snapshot.portfolio_value
    ? ((weeklyPnl / snapshot.portfolio_value) * 100).toFixed(2)
    : "0.00";

  return (
    <AppMain showMenuButton={false}>
        <DashboardTopBar />

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <KpiSparkCard
            label="Daily P&L"
            value={`${snapshot.daily_pnl >= 0 ? "+" : ""}$${Math.abs(snapshot.daily_pnl).toLocaleString()}`}
            subValue={`${snapshot.daily_pnl >= 0 ? "+" : ""}${dailyPct}%`}
            tone={snapshot.daily_pnl >= 0 ? "green" : "red"}
            sparkPositive={snapshot.daily_pnl >= 0}
          />
          <KpiSparkCard
            label="Weekly P&L"
            value={`${weeklyPnl >= 0 ? "+" : ""}$${Math.abs(weeklyPnl).toLocaleString(undefined, { maximumFractionDigits: 0 })}`}
            subValue={`${weeklyPnl >= 0 ? "+" : ""}${weeklyPct}%`}
            tone={weeklyPnl >= 0 ? "green" : "red"}
            sparkPositive={weeklyPnl >= 0}
          />
          <KpiSparkCard
            label="Portfolio Value"
            value={`$${snapshot.portfolio_value.toLocaleString()}`}
            subValue={`Total Holdings: ${holdingsCount || "—"}`}
          />
          <RiskScoreCard score={snapshot.risk_score} label={snapshot.risk_label} />
        </div>

        <Card className="mt-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-lg font-extrabold">Risk Analytics</h2>
              <p className="tg-sub mt-1">
                Exposure breakdown, correlation matrix, VaR, and concentration alerts
              </p>
            </div>
            <Link href="/risk-analytics" className="tg-btn tg-btn-primary shrink-0">
              Open Risk Analytics
            </Link>
          </div>
        </Card>

        <details className="mt-4">
          <summary className="cursor-pointer text-sm font-semibold text-muted hover:text-white">
            Trade preview & advanced tools
          </summary>
          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            <Card>
              <h2 className="text-lg font-extrabold">Trade Preview</h2>
              <p className="tg-sub mt-1">Simulate an order — no execution in Phase 1.</p>
              <form onSubmit={runPreview} className="mt-4 space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <input
                    value={form.ticker}
                    onChange={(e) => setForm({ ...form, ticker: e.target.value.toUpperCase() })}
                    className="tg-input"
                    placeholder="Ticker"
                  />
                  <select
                    value={form.side}
                    onChange={(e) => setForm({ ...form, side: e.target.value as "buy" | "sell" })}
                    className="tg-input"
                  >
                    <option value="buy">Buy</option>
                    <option value="sell">Sell</option>
                  </select>
                  <input
                    type="number"
                    min={0.01}
                    step={0.01}
                    value={form.quantity}
                    onChange={(e) => setForm({ ...form, quantity: Number(e.target.value) })}
                    className="tg-input"
                    placeholder="Qty"
                  />
                  <input
                    type="number"
                    min={0.01}
                    step={0.01}
                    value={form.limit_price}
                    onChange={(e) => setForm({ ...form, limit_price: Number(e.target.value) })}
                    className="tg-input"
                    placeholder="Limit price"
                  />
                </div>
                <Btn type="submit" disabled={loading} className="w-full">
                  {loading ? "Checking…" : "Preview trade"}
                </Btn>
              </form>
              {preview && (
                <div className="mt-4">
                  <Row label="Verdict" value={preview.verdict} tone={verdictTone(preview.verdict)} />
                  <Row label="Order value" value={`$${preview.order_value.toFixed(2)}`} />
                </div>
              )}
            </Card>
            <Card>
              <h2 className="text-lg font-extrabold">Quick Links</h2>
              <div className="mt-4 flex flex-wrap gap-2">
                <Link href="/chat" className="tg-btn tg-btn-secondary inline-block">
                  Ask AI
                </Link>
                <Link href="/portfolio" className="tg-btn tg-btn-secondary inline-block">
                  Portfolio
                </Link>
                <Link href="/risk-analytics" className="tg-btn tg-btn-secondary inline-block">
                  Risk Analytics
                </Link>
                <Link href="/analysis" className="tg-btn tg-btn-primary inline-block">
                  Stock Analyzer
                </Link>
              </div>
            </Card>
          </div>
        </details>
    </AppMain>
  );
}
