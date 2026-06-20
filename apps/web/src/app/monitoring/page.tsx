"use client";

import { useCallback, useEffect, useState } from "react";
import { Sidebar } from "@/components/Sidebar";
import {
  getMonitoringAlerts,
  getMonitoringStatus,
  resumeTrading,
  runMonitoringCheck,
  type AlertEvent,
  type MonitoringCheck,
  type MonitoringStatus,
} from "@/lib/api";
import { Btn, Card, PageHeader, StatCard } from "@/components/ui/Card";

function severityClass(severity: string) {
  if (severity === "critical") return "text-red";
  if (severity === "high") return "text-orange";
  if (severity === "medium") return "text-yellow";
  return "text-muted";
}

function checkStatusClass(status: string) {
  if (status === "fail") return "text-red";
  if (status === "warn") return "text-orange";
  if (status === "ok") return "text-green";
  return "text-muted";
}

export default function MonitoringPage() {
  const [status, setStatus] = useState<MonitoringStatus | null>(null);
  const [alerts, setAlerts] = useState<AlertEvent[]>([]);
  const [lastCheck, setLastCheck] = useState<MonitoringCheck | null>(null);
  const [loading, setLoading] = useState(false);
  const [ready, setReady] = useState(false);

  const reload = useCallback(async () => {
    const [s, a] = await Promise.all([getMonitoringStatus(), getMonitoringAlerts()]);
    setStatus(s);
    setAlerts(a.alerts);
  }, []);

  useEffect(() => {
    reload()
      .catch(() => {})
      .finally(() => setReady(true));
  }, [reload]);

  async function handleCheck() {
    setLoading(true);
    try {
      const result = await runMonitoringCheck();
      setLastCheck(result);
      await reload();
    } finally {
      setLoading(false);
    }
  }

  async function handleResume() {
    setLoading(true);
    try {
      await resumeTrading();
      await reload();
    } finally {
      setLoading(false);
    }
  }

  if (!ready) {
    return (
      <div className="flex min-h-screen">
        <Sidebar />
        <main className="mx-auto w-full max-w-[1400px] flex-1 p-7">
          <p className="text-muted">Loading monitoring…</p>
        </main>
      </div>
    );
  }

  const halted = status?.trading_halted ?? false;

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="mx-auto w-full max-w-[1400px] flex-1 p-7">
        <PageHeader
          title="Monitoring & Alerts"
          subtitle="Phase 4.1 · Real-time PnL watch, circuit breaker, Slack/email alerts"
        />

        {halted && (
          <Card className="mb-[18px] border-red/40 bg-red/10">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <p className="text-lg font-bold text-red">Trading Halted</p>
                <p className="tg-sub mt-1">{status?.halt_reason ?? "Circuit breaker active"}</p>
              </div>
              <Btn onClick={handleResume} disabled={loading}>
                Resume Trading
              </Btn>
            </div>
          </Card>
        )}

        <div className="grid grid-cols-2 gap-[18px] lg:grid-cols-4">
          <StatCard
            label="Daily P&L"
            value={`$${(status?.daily_pnl ?? 0).toFixed(2)}`}
            tone={(status?.daily_pnl ?? 0) >= 0 ? "green" : "red"}
          />
          <StatCard
            label="Daily Loss Limit"
            value={`$${status?.daily_loss_limit ?? 50}`}
            tone="orange"
          />
          <StatCard
            label="Max Drawdown Est."
            value={`${(status?.max_drawdown_est ?? 0).toFixed(1)}%`}
            tone="blue"
          />
          <StatCard
            label="Alert Provider"
            value={status?.alert_provider ?? "mock"}
            tone="blue"
          />
        </div>

        <div className="mt-[18px] grid gap-[18px] lg:grid-cols-[1fr_1fr]">
          <Card>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-bold">System Status</h2>
                <p className="tg-sub mt-1">
                  Monitoring {status?.monitoring_enabled ? "enabled" : "disabled"} · Portfolio $
                  {(status?.portfolio_value ?? 0).toLocaleString()}
                </p>
              </div>
              <Btn onClick={handleCheck} disabled={loading}>
                {loading ? "Checking…" : "Run Check Now"}
              </Btn>
            </div>

            <div className="mt-4 space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-muted">Trading status</span>
                <span className={halted ? "text-red font-bold" : "text-green font-bold"}>
                  {halted ? "HALTED" : "ACTIVE"}
                </span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted">Drawdown alert threshold</span>
                <span>{status?.drawdown_alert_pct ?? 8}%</span>
              </div>
              {status?.trading_state?.last_check_at != null ? (
                <div className="flex justify-between text-sm">
                  <span className="text-muted">Last check</span>
                  <span>{String(status.trading_state.last_check_at)}</span>
                </div>
              ) : null}
            </div>

            {lastCheck && (
              <div className="mt-5 border-t border-card-border pt-4">
                <p className="text-sm font-bold">Latest check ({lastCheck.checked_at})</p>
                <ul className="mt-2 space-y-1">
                  {lastCheck.checks.map((c) => (
                    <li key={c.name} className="flex justify-between gap-3 text-sm">
                      <span className="text-muted">{c.name}</span>
                      <span className={checkStatusClass(c.status)}>{c.detail}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </Card>

          <Card>
            <h2 className="text-lg font-bold">Alert Feed</h2>
            <p className="tg-sub mt-1">
              BLOCK events, drawdown warnings, MCP failures — mock logs locally until Slack webhook is set.
            </p>
            <ul className="mt-4 max-h-[420px] space-y-3 overflow-y-auto">
              {alerts.length === 0 && (
                <li className="text-sm text-muted">No alerts yet. Run a check or submit a blocked trade.</li>
              )}
              {alerts.map((a) => (
                <li key={a.id} className="rounded-[12px] border border-card-border bg-[#0a1628] p-3">
                  <div className="flex items-start justify-between gap-2">
                    <span className="font-bold">{a.title}</span>
                    <span className={`text-xs uppercase ${severityClass(a.severity)}`}>{a.severity}</span>
                  </div>
                  <p className="tg-sub mt-1 text-sm">{a.detail}</p>
                  <div className="mt-2 flex flex-wrap gap-2 text-xs text-muted">
                    <span>{a.event_type}</span>
                    {a.channels_sent?.map((ch) => (
                      <span key={ch} className="rounded bg-[#182a42] px-1.5 py-0.5">
                        {ch}
                      </span>
                    ))}
                    {a.created_at && <span>{a.created_at}</span>}
                  </div>
                </li>
              ))}
            </ul>
          </Card>
        </div>
      </main>
    </div>
  );
}
