"use client";

import { useEffect, useState } from "react";
import { getRiskSnapshot, type RiskSnapshot } from "@/lib/api";

const DEMO: RiskSnapshot = {
  risk_score: 48,
  risk_label: "Moderate",
  portfolio_value: 105430,
  daily_pnl: 1250,
  beta: 1.18,
  max_drawdown_est: -12.6,
  diversification: "Good",
  cash_pct: 8.7,
  sector_exposure: {
    Technology: 42,
    Communication: 17,
    "Consumer Cyclical": 15,
    Healthcare: 10,
    Other: 16,
  },
  alerts: [],
};

const COLORS = ["#22c55e", "#3b82f6", "#a855f7", "#f59e0b", "#64748b"];

export function RiskSnapshotPanel() {
  const [data, setData] = useState<RiskSnapshot>(DEMO);

  useEffect(() => {
    getRiskSnapshot()
      .then(setData)
      .catch(() => setData(DEMO));
  }, []);

  const sectors = Object.entries(data.sector_exposure);
  const scoreColor =
    data.risk_score >= 65 ? "text-danger" : data.risk_score >= 45 ? "text-warning" : "text-accent";

  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-card-border bg-card p-5">
        <h2 className="text-sm font-semibold text-muted">Risk Snapshot</h2>
        <div className="mt-4 flex items-center gap-4">
          <div
            className={`flex h-24 w-24 flex-col items-center justify-center rounded-full border-4 ${
              data.risk_score >= 65
                ? "border-danger/50"
                : data.risk_score >= 45
                  ? "border-warning/50"
                  : "border-accent/50"
            }`}
          >
            <span className={`text-2xl font-bold ${scoreColor}`}>{data.risk_score}</span>
            <span className="text-[10px] text-muted">/ 100</span>
          </div>
          <div>
            <div className={`text-xl font-semibold ${scoreColor}`}>{data.risk_label} Risk</div>
            <div className="mt-2 space-y-1 text-xs text-muted">
              <div>Portfolio Beta: {data.beta}</div>
              <div>Max Drawdown Est.: {data.max_drawdown_est}%</div>
              <div>Diversification: {data.diversification}</div>
              <div>Cash: {data.cash_pct}%</div>
            </div>
          </div>
        </div>
      </div>

      <div className="rounded-2xl border border-card-border bg-card p-5">
        <h2 className="text-sm font-semibold text-muted">Position Exposure</h2>
        <div className="mt-4 flex items-center gap-4">
          <div
            className="relative h-28 w-28 shrink-0 rounded-full"
            style={{
              background: `conic-gradient(${sectors
                .map(([name, pct], i) => {
                  const start = sectors
                    .slice(0, i)
                    .reduce((acc, [, p]) => acc + p, 0);
                  return `${COLORS[i % COLORS.length]} ${start}% ${start + pct}%`;
                })
                .join(", ")})`,
            }}
          >
            <div className="absolute inset-3 flex items-center justify-center rounded-full bg-card text-xs font-medium">
              Sectors
            </div>
          </div>
          <ul className="flex-1 space-y-1.5 text-xs">
            {sectors.map(([name, pct], i) => (
              <li key={name} className="flex items-center justify-between gap-2">
                <span className="flex items-center gap-2">
                  <span
                    className="inline-block h-2 w-2 rounded-full"
                    style={{ background: COLORS[i % COLORS.length] }}
                  />
                  {name}
                </span>
                <span className="text-muted">{pct.toFixed(0)}%</span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      {data.alerts.length > 0 && (
        <div className="rounded-2xl border border-warning/30 bg-warning/5 p-4">
          <h3 className="text-sm font-semibold text-warning">Alerts</h3>
          <ul className="mt-2 space-y-2 text-xs">
            {data.alerts.map((a, i) => (
              <li key={i}>
                <span className="font-medium">{a.title}:</span> {a.detail}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
