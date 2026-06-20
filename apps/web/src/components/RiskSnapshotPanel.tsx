"use client";

import { useEffect, useState } from "react";
import { compareTickers, getRiskSnapshot, type RiskSnapshot } from "@/lib/api";
import { Card, StatCard, StockTile } from "@/components/ui/Card";

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

function riskTone(score: number, label: string) {
  if (score >= 65 || label.toLowerCase().includes("elevated")) return "orange" as const;
  if (score < 40) return "green" as const;
  return "orange" as const;
}

export function RiskSnapshotPanel() {
  const [data, setData] = useState<RiskSnapshot>(DEMO);
  const [watchlist, setWatchlist] = useState<
    { ticker: string; composite_score: number; setup_label: string; risk_verdict: string }[]
  >([]);

  useEffect(() => {
    getRiskSnapshot()
      .then(setData)
      .catch(() => setData(DEMO));
    compareTickers(["NVDA", "TSLA", "META", "MSFT", "QQQ", "GBTC"])
      .then((r) => setWatchlist(r.tickers))
      .catch(() => {});
  }, []);

  return (
    <div className="space-y-[18px]">
      <div className="grid grid-cols-2 gap-3">
        <StatCard label="Account Value" value={`$${data.portfolio_value.toLocaleString()}`} />
        <StatCard
          label="Today P/L"
          value={`${data.daily_pnl >= 0 ? "+" : ""}$${data.daily_pnl.toLocaleString()}`}
          tone={data.daily_pnl >= 0 ? "green" : "red"}
        />
        <StatCard label="Cash" value={`${data.cash_pct}%`} />
        <StatCard
          label="Risk Level"
          value={data.risk_label.toUpperCase()}
          tone={riskTone(data.risk_score, data.risk_label)}
        />
      </div>

      {data.alerts.length > 0 && (
        <Card warning>
          <div className="tg-label">Risk Alerts</div>
          <ul className="mt-3 space-y-2 text-sm">
            {data.alerts.map((a, i) => (
              <li key={i}>
                {i + 1}. {a.detail}
              </li>
            ))}
          </ul>
        </Card>
      )}

      <Card>
        <div className="tg-label">Top Watchlist</div>
        <div className="mt-4 grid gap-3.5">
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
    </div>
  );
}
