"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Sidebar } from "@/components/Sidebar";
import {
  backtestStrategy,
  downloadAuditExport,
  getAuditExportSummary,
  getPlatformHealth,
  getStrategies,
  getTradeReplay,
  runPlatformCheck,
  type BacktestReport,
  type ExportSummary,
  type PlatformHealth,
  type ReplayTimeline,
  type TradeStrategy,
} from "@/lib/api";
import { Btn, Card, PageHeader, Row, StatCard } from "@/components/ui/Card";

function TradeReplayPanel({ onError }: { onError: (msg: string) => void }) {
  const searchParams = useSearchParams();
  const deepReplay = searchParams.get("replay");
  const deepType: "approval" | "trade" = searchParams.get("type") === "approval" ? "approval" : "trade";
  const [replayId, setReplayId] = useState(deepReplay ?? "");
  const [replayType, setReplayType] = useState<"approval" | "trade">(deepType);
  const [replay, setReplay] = useState<ReplayTimeline | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!deepReplay) return;
    let cancelled = false;
    void getTradeReplay(deepReplay, deepType)
      .then((data) => {
        if (!cancelled) setReplay(data);
      })
      .catch(() => {
        if (!cancelled) onError("Replay not found");
      });
    return () => {
      cancelled = true;
    };
  }, [deepReplay, deepType, onError]);

  async function handleReplay() {
    if (!replayId.trim()) return;
    setLoading(true);
    onError("");
    try {
      setReplay(await getTradeReplay(replayId.trim(), replayType));
    } catch {
      onError("Replay not found");
      setReplay(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card>
      <h2 className="text-lg font-extrabold">Trade Replay</h2>
      <p className="tg-sub mt-2 text-sm">Post-mortem timeline: decision → risk → execution.</p>
      <div className="mt-4 flex flex-wrap gap-2">
        <select
          className="rounded-lg border border-card-border bg-background px-3 py-2 text-sm"
          value={replayType}
          onChange={(e) => setReplayType(e.target.value as "approval" | "trade")}
        >
          <option value="approval">Approval ID</option>
          <option value="trade">Trade ID</option>
        </select>
        <input
          className="min-w-[220px] flex-1 rounded-lg border border-card-border bg-background px-3 py-2 text-sm"
          placeholder="Paste ID from journal or approvals"
          value={replayId}
          onChange={(e) => setReplayId(e.target.value)}
        />
        <Btn disabled={loading} onClick={() => void handleReplay()}>
          Load replay
        </Btn>
      </div>
      {replay && (
        <div className="mt-4 space-y-3">
          {replay.events.map((event) => (
            <div key={`${event.step}-${event.at}`} className="rounded-[12px] border border-card-border p-3 text-sm">
              <div className="font-bold">{event.title}</div>
              <div className="tg-sub text-xs">
                {event.at} · {event.step}
              </div>
              <div className="mt-1">{event.detail}</div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

export default function ObservabilityPage() {
  const [summary, setSummary] = useState<ExportSummary | null>(null);
  const [platform, setPlatform] = useState<PlatformHealth | null>(null);
  const [strategies, setStrategies] = useState<TradeStrategy[]>([]);
  const [selectedStrategy, setSelectedStrategy] = useState("");
  const [backtest, setBacktest] = useState<BacktestReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const [s, p, st] = await Promise.all([
          getAuditExportSummary(90),
          getPlatformHealth(),
          getStrategies(),
        ]);
        if (!cancelled) {
          setSummary(s);
          setPlatform(p);
          setStrategies(st.strategies);
          if (st.strategies[0]) setSelectedStrategy(st.strategies[0].id);
        }
      } catch {
        if (!cancelled) setError("Could not load observability data");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleExport(format: "json" | "csv") {
    await downloadAuditExport(format, 90);
  }

  async function handlePlatformCheck() {
    setLoading(true);
    try {
      setPlatform(await runPlatformCheck());
    } finally {
      setLoading(false);
    }
  }

  async function handleBacktest() {
    if (!selectedStrategy) return;
    setLoading(true);
    try {
      setBacktest(await backtestStrategy(selectedStrategy, 90));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="mx-auto w-full max-w-[1400px] flex-1 p-7">
        <PageHeader
          title="Observability & Compliance"
          subtitle="Audit exports, trade replay, platform health, strategy backtests"
        />

        {error && <p className="mb-4 text-sm text-red">{error}</p>}

        {summary && (
          <div className="grid grid-cols-2 gap-[18px] lg:grid-cols-4">
            <StatCard label="Journal (90d)" value={summary.counts.journal_trades} />
            <StatCard label="Approvals (90d)" value={summary.counts.approval_requests} tone="blue" />
            <StatCard label="Automation audit" value={summary.counts.automation_audit} />
            <StatCard label="Alerts" value={summary.counts.alert_events} tone="orange" />
          </div>
        )}

        <div className="mt-[18px] grid gap-[18px] lg:grid-cols-2">
          <Card>
            <h2 className="text-lg font-extrabold">90-Day Audit Export</h2>
            <p className="tg-sub mt-2 text-sm">
              One-click regulatory-style export of journal, approvals, and automation log.
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              <Btn variant="secondary" onClick={() => handleExport("json")}>
                Download JSON
              </Btn>
              <Btn variant="secondary" onClick={() => handleExport("csv")}>
                Download CSV
              </Btn>
            </div>
          </Card>

          <Card warning={platform ? !platform.healthy : false}>
            <h2 className="text-lg font-extrabold">Platform Health</h2>
            {platform && (
              <div className="mt-2">
                <Row label="Status" value={platform.healthy ? "Healthy" : "Degraded"} tone={platform.healthy ? "green" : "orange"} />
                <Row label="Readiness" value={platform.readiness.status} />
                <Row label="MCP latency" value={platform.mcp.latency_ms != null ? `${platform.mcp.latency_ms}ms` : "—"} />
                <Row label="Model drift" value={platform.model.drift != null ? String(platform.model.drift) : "—"} />
              </div>
            )}
            <div className="mt-4">
              <Btn disabled={loading} onClick={handlePlatformCheck}>
                Run platform check
              </Btn>
            </div>
          </Card>
        </div>

        <div className="mt-[18px] grid gap-[18px] lg:grid-cols-2">
          <Suspense fallback={<Card><p className="text-muted text-sm">Loading replay…</p></Card>}>
            <TradeReplayPanel onError={(msg) => setError(msg || null)} />
          </Suspense>

          <Card>
            <h2 className="text-lg font-extrabold">Strategy Backtest</h2>
            <p className="tg-sub mt-2 text-sm">Replay strategy rules against journal history.</p>
            <div className="mt-4 flex flex-wrap gap-2">
              <select
                className="rounded-lg border border-card-border bg-background px-3 py-2 text-sm"
                value={selectedStrategy}
                onChange={(e) => setSelectedStrategy(e.target.value)}
              >
                {strategies.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
              <Btn disabled={loading || !selectedStrategy} onClick={handleBacktest}>
                Run backtest
              </Btn>
              <Link href="/strategies" className="text-sm text-teal underline">
                Manage strategies
              </Link>
            </div>
            {backtest && (
              <div className="mt-4">
                <Row label="Signals simulated" value={String(backtest.simulated_signals)} />
                <Row label="Matched trades" value={String(backtest.matched_action_trades)} />
                <Row label="Sharpe (matched)" value={String(backtest.metrics_matched_trades.sharpe_ratio)} tone="blue" />
                <Row label="Win rate (all)" value={`${backtest.metrics_all_trades.win_rate}%`} />
              </div>
            )}
          </Card>
        </div>
      </main>
    </div>
  );
}
