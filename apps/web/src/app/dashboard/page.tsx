"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Sidebar } from "@/components/Sidebar";
import {
  getAdvancedRisk,
  getRiskRules,
  getRiskSnapshot,
  previewTrade,
  compareTickers,
  type AdvancedRisk,
  type RiskRules,
  type RiskSnapshot,
  type TradePreview,
} from "@/lib/api";
import { Btn, Card, PageHeader, Row, StatCard, StockTile } from "@/components/ui/Card";

function verdictTone(v: string) {
  if (v === "BLOCK") return "red" as const;
  if (v === "CAUTION") return "orange" as const;
  return "green" as const;
}

export default function DashboardPage() {
  const [rules, setRules] = useState<RiskRules | null>(null);
  const [snapshot, setSnapshot] = useState<RiskSnapshot | null>(null);
  const [preview, setPreview] = useState<TradePreview | null>(null);
  const [watchlist, setWatchlist] = useState<
    { ticker: string; composite_score: number; setup_label: string; risk_verdict: string }[]
  >([]);
  const [advanced, setAdvanced] = useState<AdvancedRisk | null>(null);
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({
    ticker: "NVDA",
    side: "buy" as "buy" | "sell",
    quantity: 1,
    limit_price: 120,
    order_type: "limit",
  });

  useEffect(() => {
    getRiskRules().then((r) => setRules(r.rules)).catch(() => {});
    getRiskSnapshot().then(setSnapshot).catch(() => {});
    compareTickers(["NVDA", "TSLA", "META", "MSFT", "QQQ", "GBTC"])
      .then((r) => setWatchlist(r.tickers))
      .catch(() => {});
    getAdvancedRisk().then(setAdvanced).catch(() => {});
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

  const techPct = snapshot?.sector_exposure?.Technology ?? 0;

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="mx-auto w-full max-w-[1400px] flex-1 p-7">
        <PageHeader
          title="Dashboard"
          subtitle="Connected: Demo portfolio · Mock data for MVP"
        />

        {snapshot && (
          <div className="grid grid-cols-2 gap-[18px] lg:grid-cols-4">
            <StatCard label="Account Value" value={`$${snapshot.portfolio_value.toLocaleString()}`} />
            <StatCard
              label="Today P/L"
              value={`${snapshot.daily_pnl >= 0 ? "+" : ""}$${snapshot.daily_pnl.toLocaleString()}`}
              tone={snapshot.daily_pnl >= 0 ? "green" : "red"}
            />
            <StatCard label="Cash" value={`${snapshot.cash_pct}%`} />
            <StatCard label="Risk Level" value={snapshot.risk_label.toUpperCase()} tone="orange" />
          </div>
        )}

        <div className="mt-[18px] grid gap-[18px] lg:grid-cols-[1.35fr_0.85fr]">
          <Card warning>
            <div className="tg-label">AI Warning</div>
            <h2 className="mt-2 text-xl font-extrabold">
              {techPct > 30 ? "Portfolio is overexposed to mega-cap tech" : "Portfolio risk within guardrails"}
            </h2>
            <p className="tg-sub mt-2">
              {snapshot?.alerts?.[0]?.detail ??
                `Technology exposure is ${techPct.toFixed(0)}%. Use limit orders and manual approval.`}
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              <Link href="/portfolio" className="tg-btn tg-btn-primary inline-block">
                Analyze Portfolio
              </Link>
              <Link href="/analysis" className="tg-btn tg-btn-secondary inline-block">
                Find Trades
              </Link>
            </div>
          </Card>

          <Card>
            <div className="tg-label">AI Recommendation</div>
            <h2 className="mt-2 text-xl font-extrabold text-orange">
              {snapshot && snapshot.risk_score >= 55 ? "Wait / Reduce Size" : "Proceed with Caution"}
            </h2>
            <p className="tg-sub mt-2">
              Manual approval required. Avoid options automation. Use limit orders only.
            </p>
          </Card>
        </div>

        <Card className="mt-[18px]">
          <div className="tg-label">Top Watchlist</div>
          <div className="mt-4 grid gap-3.5 sm:grid-cols-2 lg:grid-cols-3">
            {watchlist.map((s) => (
              <StockTile
                key={s.ticker}
                ticker={s.ticker}
                subtitle={s.setup_label}
                score={Math.round(s.composite_score)}
              />
            ))}
          </div>
        </Card>

        <div className="mt-[18px] grid gap-[18px] lg:grid-cols-2">
          <Card>
            <h2 className="text-lg font-extrabold">Portfolio Risk Dashboard</h2>
            {snapshot && (
              <div className="mt-2">
                {Object.entries(snapshot.sector_exposure).map(([sector, pct]) => (
                  <Row
                    key={sector}
                    label={sector}
                    value={`${pct.toFixed(0)}%`}
                    tone={sector === "Technology" && pct > 30 ? "orange" : "default"}
                  />
                ))}
                <Row label="Max Drawdown" value={`${snapshot.max_drawdown_est}%`} tone="red" />
              </div>
            )}
            {rules && (
              <div className="mt-4 border-t border-white/10 pt-4">
                <div className="tg-label">Active Rules</div>
                <Row label="Max trade" value={`$${rules.max_trade_usd}`} />
                <Row label="Max daily loss" value={`$${rules.max_daily_loss_usd}`} tone="red" />
                <Row label="Options" value={rules.allow_options ? "Allowed" : "Blocked"} tone="orange" />
              </div>
            )}
          </Card>

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
                {preview.setup_label && (
                  <Row
                    label="Setup"
                    value={`${preview.setup_label} (${preview.composite_score}/100)`}
                  />
                )}
                {preview.warnings.map((w) => (
                  <p key={w} className="text-sm text-orange">
                    ⚠ {w}
                  </p>
                ))}
                {preview.blocks.map((b) => (
                  <p key={b} className="text-sm text-red">
                    ✕ {b}
                  </p>
                ))}
              </div>
            )}
          </Card>
        </div>

        {advanced && (
          <div className="mt-[18px] grid gap-[18px] lg:grid-cols-2">
            <Card>
              <h2 className="text-lg font-extrabold">Advanced Risk</h2>
              <div className="mt-2">
                <Row label="1-Day VaR (95%)" value={`$${Math.abs(advanced.var_95_1d).toLocaleString()}`} tone="red" />
                <Row label="Max Drawdown Est." value={`${advanced.max_drawdown_est}%`} tone="red" />
                <Row label="Data Provider" value={advanced.data_provider ?? "mock"} tone="blue" />
              </div>
            </Card>
            <Card warning>
              <h2 className="text-lg font-extrabold">Stress Tests</h2>
              <div className="mt-2">
                {advanced.stress_tests.map((s) => (
                  <Row
                    key={s.name}
                    label={s.name}
                    value={`$${s.impact_usd.toLocaleString()}`}
                    tone={s.severity === "high" ? "red" : "orange"}
                  />
                ))}
              </div>
            </Card>
            {Object.keys(advanced.correlation_matrix).length > 0 && (
              <Card className="lg:col-span-2">
                <h2 className="text-lg font-extrabold">Correlation Heatmap</h2>
                <div className="mt-4 overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr>
                        <th className="p-2 text-left text-muted" />
                        {Object.keys(advanced.correlation_matrix).map((t) => (
                          <th key={t} className="p-2 font-bold">
                            {t}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(advanced.correlation_matrix).map(([row, cols]) => (
                        <tr key={row}>
                          <td className="p-2 font-bold">{row}</td>
                          {Object.keys(advanced.correlation_matrix).map((col) => {
                            const val = cols[col] ?? 0;
                            const intensity = Math.abs(val);
                            return (
                              <td
                                key={col}
                                className="p-2 text-center"
                                style={{
                                  background: `rgba(38, 228, 196, ${intensity * 0.35})`,
                                }}
                              >
                                {val.toFixed(2)}
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
