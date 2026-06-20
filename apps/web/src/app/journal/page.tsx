"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Sidebar } from "@/components/Sidebar";
import {
  createPaperTrade,
  getJournalStats,
  getJournalTrades,
  type JournalStats,
  type PaperTrade,
} from "@/lib/api";
import { Btn, Card, PageHeader, StatCard } from "@/components/ui/Card";

function statusClass(status: string) {
  if (status === "filled") return "text-green";
  if (status === "rejected") return "text-red";
  return "text-orange";
}

function JournalTable() {
  const [trades, setTrades] = useState<PaperTrade[]>([]);
  const [stats, setStats] = useState<JournalStats | null>(null);
  const [form, setForm] = useState({ ticker: "NVDA", side: "buy" as "buy" | "sell", quantity: 1, limit_price: 120 });
  const [loading, setLoading] = useState(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    Promise.all([getJournalTrades(), getJournalStats()])
      .then(([t, s]) => {
        if (!cancelled) {
          setTrades(t.trades);
          setStats(s);
          setReady(true);
        }
      })
      .catch(() => {
        if (!cancelled) setReady(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function reload() {
    const [t, s] = await Promise.all([getJournalTrades(), getJournalStats()]);
    setTrades(t.trades);
    setStats(s);
  }

  async function submitPlan(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      await createPaperTrade(form);
      await reload();
    } finally {
      setLoading(false);
    }
  }

  if (!ready) {
    return <p className="text-muted">Loading journal…</p>;
  }

  return (
    <>
      {stats && (
        <div className="grid grid-cols-2 gap-[18px] lg:grid-cols-4">
          <StatCard label="Total Trades" value={stats.total_trades} />
          <StatCard label="Filled" value={stats.filled_trades} tone="green" />
          <StatCard label="Win Rate" value={`${stats.win_rate}%`} tone="blue" />
          <StatCard
            label="Paper P&L"
            value={`$${stats.total_pnl}`}
            tone={stats.total_pnl >= 0 ? "green" : "red"}
          />
        </div>
      )}

      {stats && (
        <Card className="mt-[18px]">
          <div className="tg-label">100-Trade Progress</div>
          <div className="tg-bar mt-3">
            <span style={{ width: `${stats.progress_pct}%` }} />
          </div>
          <p className="tg-sub mt-2">
            {stats.total_trades} / {stats.goal} trades logged ({stats.progress_pct}%)
          </p>
        </Card>
      )}

      <div className="mt-[18px] grid gap-[18px] lg:grid-cols-[0.9fr_1.1fr]">
        <Card>
          <h2 className="text-lg font-extrabold">Log paper trade plan</h2>
          <form onSubmit={submitPlan} className="mt-4 space-y-3">
            <input
              className="tg-input w-full"
              value={form.ticker}
              onChange={(e) => setForm({ ...form, ticker: e.target.value.toUpperCase() })}
              placeholder="Ticker"
            />
            <select
              className="tg-input w-full"
              value={form.side}
              onChange={(e) => setForm({ ...form, side: e.target.value as "buy" | "sell" })}
            >
              <option value="buy">Buy</option>
              <option value="sell">Sell</option>
            </select>
            <input
              type="number"
              className="tg-input w-full"
              value={form.quantity}
              onChange={(e) => setForm({ ...form, quantity: Number(e.target.value) })}
            />
            <input
              type="number"
              className="tg-input w-full"
              value={form.limit_price}
              onChange={(e) => setForm({ ...form, limit_price: Number(e.target.value) })}
            />
            <Btn type="submit" disabled={loading} className="w-full">
              {loading ? "Saving…" : "Create plan"}
            </Btn>
          </form>
        </Card>

        <Card>
          <h2 className="text-lg font-extrabold">Journal</h2>
          <table className="mt-4 w-full text-sm">
            <thead>
              <tr className="border-b border-white/10 text-left text-muted">
                <th className="pb-3 text-[13px] font-bold">Date</th>
                <th className="pb-3 text-[13px] font-bold">Ticker</th>
                <th className="pb-3 text-[13px] font-bold">Decision</th>
                <th className="pb-3 text-[13px] font-bold">Status</th>
                <th className="pb-3 text-[13px] font-bold">Replay</th>
              </tr>
            </thead>
            <tbody>
              {trades.map((t) => (
                <tr key={t.id} className="border-b border-white/[0.08]">
                  <td className="py-3.5">{t.created_at?.slice(0, 10) ?? "—"}</td>
                  <td className="py-3.5 font-bold">{t.ticker}</td>
                  <td className="py-3.5">{t.verdict}</td>
                  <td className={`py-3.5 font-bold ${statusClass(t.status)}`}>{t.status}</td>
                  <td className="py-3.5">
                    <Link
                      href={`/observability?replay=${t.id}&type=trade`}
                      className="text-teal underline"
                    >
                      View
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      </div>
    </>
  );
}

export default function JournalPage() {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="mx-auto w-full max-w-[1400px] flex-1 p-7">
        <PageHeader title="Trade Journal" subtitle="Paper trading track record — goal 100 trades" />
        <JournalTable />
      </main>
    </div>
  );
}
