"use client";

import { useCallback, useEffect, useState } from "react";
import { AppMain } from "@/components/layout/AppMain";
import {
  disableAutomation,
  enableAutomation,
  getAutomationAudit,
  getAutomationStatus,
  runAutomation,
  type AutomationAuditEntry,
  type AutomationStatus,
} from "@/lib/api";
import { Btn, Card, PageHeader, StatCard } from "@/components/ui/Card";

function eventClass(type: string) {
  if (type === "auto_executed") return "text-green";
  if (type === "automation_disabled") return "text-red";
  if (type === "auto_blocked") return "text-orange";
  return "text-muted";
}

export default function AutomationPage() {
  const [status, setStatus] = useState<AutomationStatus | null>(null);
  const [audit, setAudit] = useState<AutomationAuditEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [ready, setReady] = useState(false);

  const reload = useCallback(async () => {
    const [s, a] = await Promise.all([getAutomationStatus(), getAutomationAudit()]);
    setStatus(s);
    setAudit(a.audit);
  }, []);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const [s, a] = await Promise.all([getAutomationStatus(), getAutomationAudit()]);
        if (cancelled) return;
        setStatus(s);
        setAudit(a.audit);
      } catch {
        // ignore initial load errors
      } finally {
        if (!cancelled) setReady(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleEnable() {
    setLoading(true);
    try {
      await enableAutomation();
      await reload();
    } finally {
      setLoading(false);
    }
  }

  async function handleDisable() {
    setLoading(true);
    try {
      await disableAutomation("Emergency stop from automation dashboard");
      await reload();
    } finally {
      setLoading(false);
    }
  }

  async function handleRun() {
    setLoading(true);
    try {
      await runAutomation();
      await reload();
    } finally {
      setLoading(false);
    }
  }

  if (!ready || !status) {
    return (
      <AppMain>
          <p className="text-muted">Loading automation…</p>
        </AppMain>
    );
  }

  return (
    <AppMain>
        <PageHeader
          title="Constrained Automation"
          subtitle="Phase 4.4 · ALLOW-only auto-execute within hard caps — instant kill switch"
        />

        <Card className={`mb-[18px] ${status.ready ? "border-green/40 bg-green/10" : "border-orange/40 bg-orange/10"}`}>
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className={`text-lg font-bold ${status.master_enabled ? "text-green" : "text-orange"}`}>
                Master switch: {status.master_enabled ? "ON" : "OFF"}
              </p>
              <p className="tg-sub mt-1">
                {status.ready
                  ? "Automation ready — strategies with auto-approve can auto-execute ALLOW trades."
                  : status.block_reason || "Enable automation after validation gate passes."}
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              {!status.master_enabled ? (
                <Btn onClick={handleEnable} disabled={loading || !status.validation_unlocked}>
                  Enable Automation
                </Btn>
              ) : (
                <Btn onClick={handleDisable} disabled={loading}>
                  Disable Instantly
                </Btn>
              )}
              <Btn onClick={handleRun} disabled={loading || !status.master_enabled}>
                Run Now
              </Btn>
            </div>
          </div>
        </Card>

        <div className="grid grid-cols-2 gap-[18px] lg:grid-cols-4">
          <StatCard
            label="Auto Trades Today"
            value={`${status.auto_trades_today} / ${status.bounds.max_daily_auto_trades}`}
            tone="blue"
          />
          <StatCard
            label="Remaining"
            value={status.auto_trades_remaining}
            tone={status.auto_trades_remaining > 0 ? "green" : "red"}
          />
          <StatCard
            label="Validation"
            value={status.validation_unlocked ? "Unlocked" : "Blocked"}
            tone={status.validation_unlocked ? "green" : "red"}
          />
          <StatCard
            label="Max Trade"
            value={`$${status.bounds.max_trade_usd}`}
            tone="orange"
          />
        </div>

        <div className="mt-[18px] grid gap-[18px] lg:grid-cols-[1fr_1fr]">
          <Card>
            <h2 className="text-lg font-bold">Hard Caps (always enforced)</h2>
            <ul className="mt-4 space-y-2 text-sm">
              <li className="flex justify-between">
                <span className="text-muted">Allowed verdicts</span>
                <span>{status.bounds.allowed_verdicts.join(", ")}</span>
              </li>
              <li className="flex justify-between">
                <span className="text-muted">Options automation</span>
                <span>{status.bounds.options_allowed ? "Allowed" : "Blocked"}</span>
              </li>
              <li className="flex justify-between">
                <span className="text-muted">Trading halted</span>
                <span className={status.trading_halted ? "text-red" : "text-green"}>
                  {status.trading_halted ? "Yes" : "No"}
                </span>
              </li>
              <li className="flex justify-between">
                <span className="text-muted">Manual approval default</span>
                <span>{status.bounds.require_manual_approval_default ? "Required" : "Optional"}</span>
              </li>
            </ul>
            <p className="tg-sub mt-4 text-xs">{status.validation_summary}</p>
          </Card>

          <Card>
            <h2 className="text-lg font-bold">Audit Trail</h2>
            <ul className="mt-4 max-h-[420px] space-y-3 overflow-y-auto">
              {audit.length === 0 && (
                <li className="text-sm text-muted">No automation events yet.</li>
              )}
              {audit.map((a) => (
                <li key={a.id} className="rounded-[12px] border border-card-border bg-[#0a1628] p-3">
                  <div className="flex items-start justify-between gap-2">
                    <span className="font-bold">{a.event_type}</span>
                    <span className={`text-xs ${eventClass(a.event_type)}`}>{a.verdict || ""}</span>
                  </div>
                  <p className="tg-sub mt-1 text-sm">{a.detail}</p>
                  {(a.ticker || a.strategy_name) && (
                    <p className="mt-1 text-xs text-muted">
                      {[a.strategy_name, a.ticker].filter(Boolean).join(" · ")}
                    </p>
                  )}
                  {a.created_at && <p className="tg-sub mt-1 text-xs">{a.created_at}</p>}
                </li>
              ))}
            </ul>
          </Card>
        </div>
      </AppMain>
  );
}
