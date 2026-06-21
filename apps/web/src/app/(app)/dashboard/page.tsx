"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AppMain } from "@/components/layout/AppMain";
import { AiRecommendationPanel, DashboardTopBar } from "@/components/dashboard/DashboardTopBar";
import { CorrelationHeatmap } from "@/components/dashboard/CorrelationHeatmap";
import { ExposureDonut, SectorExposureChart } from "@/components/dashboard/ExposureDonut";
import { KpiSparkCard, RiskScoreCard } from "@/components/dashboard/KpiSparkCard";
import { buildDashboardAlerts, RiskAlertsPanel } from "@/components/dashboard/RiskAlertsPanel";
import { RiskMetricsPanel } from "@/components/dashboard/RiskMetricsPanel";
import {
  getAdvancedRisk,
  getPortfolio,
  getRiskRules,
  getRiskSnapshot,
  previewTrade,
  type AdvancedRisk,
  type RiskRules,
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
  const [rules, setRules] = useState<RiskRules | null>(null);
  const [snapshot, setSnapshot] = useState<RiskSnapshot | null>(null);
  const [advanced, setAdvanced] = useState<AdvancedRisk | null>(null);
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
    getRiskRules().then((r) => setRules(r.rules)).catch(() => {});
    getRiskSnapshot().then(setSnapshot).catch(() => {});
    getAdvancedRisk().then(setAdvanced).catch(() => {});
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

  const techPct = snapshot.sector_exposure?.Technology ?? 0;
  const techLimit = rules?.max_tech_sector_pct ?? 30;
  const dailyPct = snapshot.portfolio_value
    ? ((snapshot.daily_pnl / snapshot.portfolio_value) * 100).toFixed(2)
    : "0.00";
  const weeklyPnl = snapshot.daily_pnl * 3.72;
  const weeklyPct = snapshot.portfolio_value
    ? ((weeklyPnl / snapshot.portfolio_value) * 100).toFixed(2)
    : "0.00";
  const alerts = buildDashboardAlerts(snapshot.alerts ?? [], techPct, techLimit);
  const var95 = advanced?.var_95_1d ?? snapshot.portfolio_value * -0.075;
  const volatility = 12 + techPct * 0.05;
  const sharpe = snapshot.risk_score >= 55 ? 1.12 : 1.32;
  const sortino = sharpe + 0.57;

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

        <div id="risk-analytics" className="mt-4 grid scroll-mt-6 gap-4 xl:grid-cols-3">
          <div className="xl:col-span-1">
            <ExposureDonut
              sectors={snapshot.sector_exposure}
              cashPct={snapshot.cash_pct}
              totalValue={snapshot.portfolio_value}
            />
          </div>
          <div className="xl:col-span-1">
            <CorrelationHeatmap matrix={advanced?.correlation_matrix ?? {}} />
          </div>
          <div className="xl:col-span-1">
            <RiskAlertsPanel alerts={alerts} />
          </div>
        </div>

        <div className="mt-4 grid gap-4 xl:grid-cols-3">
          <SectorExposureChart sectors={snapshot.sector_exposure} />
          <RiskMetricsPanel
            volatility={volatility}
            sharpe={sharpe}
            var95={var95}
            sortino={sortino}
            expectedShortfall={Math.abs(var95) * 1.55}
            maxDrawdown={snapshot.max_drawdown_est}
          />
          <AiRecommendationPanel techPct={techPct} techLimit={techLimit} riskLabel={snapshot.risk_label} />
        </div>

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
                <Link href="/analysis" className="tg-btn tg-btn-primary inline-block">
                  Stock Analyzer
                </Link>
              </div>
              {advanced?.stress_tests?.length ? (
                <div className="mt-4 border-t border-white/10 pt-4">
                  <p className="tg-label">Stress Tests</p>
                  {advanced.stress_tests.map((s) => (
                    <Row
                      key={s.name}
                      label={s.name}
                      value={`$${s.impact_usd.toLocaleString()}`}
                      tone={s.severity === "high" ? "red" : "orange"}
                    />
                  ))}
                </div>
              ) : null}
            </Card>
          </div>
        </details>
    </AppMain>
  );
}
