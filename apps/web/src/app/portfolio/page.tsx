"use client";

import { useEffect, useState } from "react";
import { Sidebar } from "@/components/Sidebar";
import { getPortfolio, type Portfolio } from "@/lib/api";
import { Card, PageHeader, Row, StatCard } from "@/components/ui/Card";

export default function PortfolioPage() {
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    getPortfolio()
      .then(setPortfolio)
      .catch(() => setError(true));
  }, []);

  const positions = portfolio
    ? Object.entries(portfolio.positions).sort(([, a], [, b]) => b.weight_pct - a.weight_pct)
    : [];

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="mx-auto w-full max-w-[1400px] flex-1 p-7">
        <PageHeader
          title="Portfolio Risk"
          subtitle="Demo portfolio · Live Robinhood MCP in Phase 3"
        />

        {error && <p className="text-sm text-red">Could not load portfolio. Is the API running?</p>}

        {portfolio && (
          <>
            <div className="grid grid-cols-2 gap-[18px] lg:grid-cols-4">
              <StatCard label="Account Value" value={`$${portfolio.account_value.toLocaleString()}`} />
              <StatCard
                label="Today P/L"
                value={`${portfolio.daily_pnl >= 0 ? "+" : ""}$${portfolio.daily_pnl.toLocaleString()}`}
                tone={portfolio.daily_pnl >= 0 ? "green" : "red"}
              />
              <StatCard label="Buying Power" value={`$${portfolio.buying_power.toLocaleString()}`} />
              <StatCard label="Source" value={(portfolio.source ?? "demo").toUpperCase()} tone="blue" />
            </div>

            <div className="mt-[18px] grid gap-[18px] lg:grid-cols-2">
              <Card>
                <h2 className="text-lg font-extrabold">Holdings</h2>
                <table className="mt-4 w-full text-sm">
                  <thead>
                    <tr className="border-b border-white/10 text-left text-muted">
                      <th className="pb-3 pr-4 text-[13px] font-bold">Ticker</th>
                      <th className="pb-3 pr-4 text-[13px] font-bold">Shares</th>
                      <th className="pb-3 pr-4 text-[13px] font-bold">Weight</th>
                      <th className="pb-3 text-[13px] font-bold">Sector</th>
                    </tr>
                  </thead>
                  <tbody>
                    {positions.map(([ticker, pos]) => (
                      <tr key={ticker} className="border-b border-white/[0.08]">
                        <td className="py-3.5 pr-4 font-bold">{ticker}</td>
                        <td className="py-3.5 pr-4">{pos.shares}</td>
                        <td className="py-3.5 pr-4">{pos.weight_pct}%</td>
                        <td className="py-3.5">{pos.sector}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Card>

              <Card warning>
                <h2 className="text-lg font-extrabold">Sector Exposure</h2>
                <div className="mt-2">
                  {Object.entries(portfolio.sector_exposure).map(([sector, pct]) => (
                    <Row
                      key={sector}
                      label={sector}
                      value={`${pct}%`}
                      tone={sector === "Technology" && pct > 30 ? "orange" : pct > 20 ? "default" : "green"}
                    />
                  ))}
                </div>
              </Card>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
