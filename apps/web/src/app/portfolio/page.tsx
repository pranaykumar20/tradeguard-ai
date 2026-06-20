"use client";

import { useEffect, useState } from "react";
import { Sidebar } from "@/components/Sidebar";
import { getHouseholdPortfolio, type HouseholdPortfolio } from "@/lib/api";
import { Card, PageHeader, Row, StatCard } from "@/components/ui/Card";

export default function PortfolioPage() {
  const [household, setHousehold] = useState<HouseholdPortfolio | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    getHouseholdPortfolio()
      .then(setHousehold)
      .catch(() => setError(true));
  }, []);

  const positions = household
    ? Object.entries(household.positions).sort(([, a], [, b]) => b.weight_pct - a.weight_pct)
    : [];

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="mx-auto w-full max-w-[1400px] flex-1 p-7">
        <PageHeader
          title="Household Portfolio"
          subtitle="Aggregated exposure across linked broker accounts"
        />

        {error && <p className="text-sm text-red">Could not load portfolio. Is the API running?</p>}

        {household && (
          <>
            <div className="grid grid-cols-2 gap-[18px] lg:grid-cols-4">
              <StatCard
                label="Household Value"
                value={`$${household.total_value.toLocaleString()}`}
              />
              <StatCard
                label="Today P/L"
                value={`${household.total_daily_pnl >= 0 ? "+" : ""}$${household.total_daily_pnl.toLocaleString()}`}
                tone={household.total_daily_pnl >= 0 ? "green" : "red"}
              />
              <StatCard label="Linked Accounts" value={String(household.account_count)} tone="blue" />
              <StatCard label="Source" value={(household.source ?? "demo").toUpperCase()} />
            </div>

            <div className="mt-[18px] grid gap-[18px] lg:grid-cols-3">
              {household.accounts.map((account) => (
                <Card key={`${account.broker_id}-${account.account_id}`}>
                  <h2 className="text-lg font-extrabold">
                    {account.account_label ?? account.account_id}
                  </h2>
                  <div className="mt-2">
                    <Row label="Broker" value={account.broker_id ?? "—"} />
                    <Row label="Value" value={`$${account.account_value.toLocaleString()}`} />
                    <Row
                      label="Today P/L"
                      value={`${account.daily_pnl >= 0 ? "+" : ""}$${account.daily_pnl.toLocaleString()}`}
                      tone={account.daily_pnl >= 0 ? "green" : "red"}
                    />
                  </div>
                </Card>
              ))}
            </div>

            <div className="mt-[18px] grid gap-[18px] lg:grid-cols-2">
              <Card>
                <h2 className="text-lg font-extrabold">Combined Holdings</h2>
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
                <h2 className="text-lg font-extrabold">Household Sector Exposure</h2>
                <div className="mt-2">
                  {Object.entries(household.sector_exposure).map(([sector, pct]) => (
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
