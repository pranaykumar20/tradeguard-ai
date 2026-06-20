"use client";

import { useCallback, useEffect, useState } from "react";
import { Sidebar } from "@/components/Sidebar";
import {
  evaluateStrategy,
  getStrategies,
  getStrategyProposals,
  runAllStrategies,
  updateStrategy,
  type StrategyProposal,
  type TradeStrategy,
} from "@/lib/api";
import { Btn, Card, PageHeader } from "@/components/ui/Card";

function statusClass(status: string) {
  if (status === "auto_executed") return "text-green";
  if (status === "pending_approval") return "text-orange";
  if (status === "blocked") return "text-red";
  if (status === "not_triggered") return "text-muted";
  return "text-yellow";
}

export default function StrategiesPage() {
  const [strategies, setStrategies] = useState<TradeStrategy[]>([]);
  const [proposals, setProposals] = useState<StrategyProposal[]>([]);
  const [loading, setLoading] = useState(false);
  const [ready, setReady] = useState(false);
  const [lastRun, setLastRun] = useState<string | null>(null);

  const reload = useCallback(async () => {
    const [s, p] = await Promise.all([getStrategies(), getStrategyProposals()]);
    setStrategies(s.strategies);
    setProposals(p.proposals);
  }, []);

  useEffect(() => {
    reload()
      .catch(() => {})
      .finally(() => setReady(true));
  }, [reload]);

  async function toggleEnabled(strategy: TradeStrategy) {
    setLoading(true);
    try {
      await updateStrategy(strategy.id, { enabled: !strategy.enabled });
      await reload();
    } finally {
      setLoading(false);
    }
  }

  async function toggleAutoApprove(strategy: TradeStrategy) {
    setLoading(true);
    try {
      await updateStrategy(strategy.id, { auto_approve: !strategy.auto_approve });
      await reload();
    } finally {
      setLoading(false);
    }
  }

  async function handleEvaluate(strategyId: string) {
    setLoading(true);
    try {
      await evaluateStrategy(strategyId);
      await reload();
    } finally {
      setLoading(false);
    }
  }

  async function handleRunAll() {
    setLoading(true);
    try {
      const result = await runAllStrategies();
      setLastRun(new Date().toLocaleTimeString());
      if (result.results?.length) await reload();
    } finally {
      setLoading(false);
    }
  }

  if (!ready) {
    return (
      <div className="flex min-h-screen">
        <Sidebar />
        <main className="mx-auto w-full max-w-[1400px] flex-1 p-7">
          <p className="text-muted">Loading strategies…</p>
        </main>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="mx-auto w-full max-w-[1400px] flex-1 p-7">
        <PageHeader
          title="Trade Strategies"
          subtitle="Phase 4.2 · Pre-defined rules with ALLOW-only auto-approve"
        />

        <Card className="mb-[18px]">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-bold">Strategy Runner</h2>
              <p className="tg-sub mt-1">
                Enable a strategy, then evaluate or run all. Auto-approve executes only ALLOW verdicts.
              </p>
            </div>
            <Btn onClick={handleRunAll} disabled={loading}>
              {loading ? "Running…" : "Run All Enabled"}
            </Btn>
          </div>
          {lastRun && <p className="tg-sub mt-2 text-sm">Last run: {lastRun}</p>}
        </Card>

        <div className="grid gap-[18px] lg:grid-cols-[1fr_1fr]">
          <Card>
            <h2 className="text-lg font-bold">Your Strategies</h2>
            <ul className="mt-4 space-y-4">
              {strategies.length === 0 && (
                <li className="text-sm text-muted">No strategies yet — defaults seed on API startup.</li>
              )}
              {strategies.map((s) => (
                <li key={s.id} className="rounded-[12px] border border-card-border bg-[#0a1628] p-4">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div>
                      <p className="font-bold">{s.name}</p>
                      <p className="tg-sub mt-1 text-sm">{s.description || s.summary}</p>
                    </div>
                    <span className={s.enabled ? "text-green text-xs font-bold" : "text-muted text-xs"}>
                      {s.enabled ? "ENABLED" : "OFF"}
                    </span>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <Btn onClick={() => toggleEnabled(s)} disabled={loading}>
                      {s.enabled ? "Disable" : "Enable"}
                    </Btn>
                    <Btn onClick={() => toggleAutoApprove(s)} disabled={loading}>
                      Auto-approve: {s.auto_approve ? "ON" : "OFF"}
                    </Btn>
                    <Btn onClick={() => handleEvaluate(s.id)} disabled={loading || !s.enabled}>
                      Evaluate
                    </Btn>
                  </div>
                  {s.auto_approve && (
                    <p className="tg-sub mt-2 text-xs">Auto-executes only when risk verdict is ALLOW</p>
                  )}
                </li>
              ))}
            </ul>
          </Card>

          <Card>
            <h2 className="text-lg font-bold">Proposal History</h2>
            <ul className="mt-4 max-h-[520px] space-y-3 overflow-y-auto">
              {proposals.length === 0 && (
                <li className="text-sm text-muted">No proposals yet. Enable and evaluate a strategy.</li>
              )}
              {proposals.map((p) => (
                <li key={p.id} className="rounded-[12px] border border-card-border bg-[#0a1628] p-3">
                  <div className="flex items-start justify-between gap-2">
                    <span className="font-bold">{p.strategy_name}</span>
                    <span className={`text-xs uppercase ${statusClass(p.status)}`}>{p.status}</span>
                  </div>
                  {p.ticker && (
                    <p className="mt-1 text-sm">
                      {p.side} {p.quantity} {p.ticker}
                      {p.limit_price != null && ` @ $${p.limit_price}`}
                    </p>
                  )}
                  {p.trigger_reason && <p className="tg-sub mt-1 text-sm">{p.trigger_reason}</p>}
                  {p.risk_preview?.verdict && (
                    <p className="mt-1 text-xs text-muted">Verdict: {p.risk_preview.verdict}</p>
                  )}
                  {p.notes && <p className="tg-sub mt-1 text-xs">{p.notes}</p>}
                </li>
              ))}
            </ul>
          </Card>
        </div>
      </main>
    </div>
  );
}
