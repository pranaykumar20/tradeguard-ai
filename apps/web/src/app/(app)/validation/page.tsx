"use client";

import { useEffect, useState } from "react";
import { AppMain } from "@/components/layout/AppMain";
import {
  getValidationReport,
  seedValidationDemo,
  type ValidationReport,
} from "@/lib/api";
import { Btn, Card, PageHeader, StatCard } from "@/components/ui/Card";

function checkClass(passed: boolean) {
  return passed ? "text-green" : "text-red";
}

export default function ValidationPage() {
  const [report, setReport] = useState<ValidationReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const next = await getValidationReport();
        if (cancelled) return;
        setReport(next);
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

  async function handleSeed() {
    setLoading(true);
    try {
      const result = await seedValidationDemo();
      setReport(result.report);
    } finally {
      setLoading(false);
    }
  }

  if (!ready || !report) {
    return (
      <AppMain>
          <p className="text-muted">Loading validation report…</p>
        </AppMain>
    );
  }

  const m = report.metrics;
  const unlocked = report.automation_unlocked;

  return (
    <AppMain>
        <PageHeader
          title="Performance Validation"
          subtitle="Phase 4.3 · Gate for Phase 4.4 automation — journal track record required"
        />

        <Card className={`mb-[18px] ${unlocked ? "border-green/40 bg-green/10" : "border-red/40 bg-red/10"}`}>
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className={`text-lg font-bold ${unlocked ? "text-green" : "text-red"}`}>
                {unlocked ? "Automation Unlocked" : "Automation Blocked"}
              </p>
              <p className="tg-sub mt-1">{report.summary}</p>
              {report.dev_bypass_active && (
                <p className="mt-1 text-xs text-orange">Dev bypass is active</p>
              )}
            </div>
            <Btn onClick={handleSeed} disabled={loading}>
              {loading ? "Seeding…" : "Seed Demo Track Record"}
            </Btn>
          </div>
        </Card>

        <div className="grid grid-cols-2 gap-[18px] lg:grid-cols-4">
          <StatCard label="Track Record" value={`${m.track_record_months} mo`} tone="blue" />
          <StatCard
            label="Sharpe Ratio"
            value={m.sharpe_ratio.toFixed(2)}
            tone={m.sharpe_ratio >= report.thresholds.min_sharpe ? "green" : "red"}
          />
          <StatCard
            label="Win Rate"
            value={`${m.win_rate}%`}
            tone={m.win_rate >= report.thresholds.min_win_rate ? "green" : "orange"}
          />
          <StatCard
            label="Total P&L"
            value={`$${m.total_pnl.toFixed(2)}`}
            tone={m.total_pnl > 0 ? "green" : "red"}
          />
        </div>

        <div className="mt-[18px] grid gap-[18px] lg:grid-cols-[1fr_1fr]">
          <Card>
            <h2 className="text-lg font-bold">Gate Checks</h2>
            <ul className="mt-4 space-y-3">
              {report.checks.map((c) => (
                <li key={c.name} className="flex items-center justify-between gap-3 text-sm">
                  <span className="text-muted">{c.label}</span>
                  <span className={checkClass(c.passed)}>
                    {c.actual} · {c.required}
                  </span>
                </li>
              ))}
            </ul>
          </Card>

          <Card>
            <h2 className="text-lg font-bold">Risk Metrics</h2>
            <ul className="mt-4 space-y-2 text-sm">
              <li className="flex justify-between">
                <span className="text-muted">Max drawdown</span>
                <span>{m.max_drawdown_pct}%</span>
              </li>
              <li className="flex justify-between">
                <span className="text-muted">Filled trades</span>
                <span>{m.filled_trades}</span>
              </li>
              <li className="flex justify-between">
                <span className="text-muted">Rule violations</span>
                <span>{m.rule_violation_count}</span>
              </li>
              <li className="flex justify-between">
                <span className="text-muted">Starting capital (sim)</span>
                <span>${m.starting_capital.toLocaleString()}</span>
              </li>
              <li className="flex justify-between">
                <span className="text-muted">Report generated</span>
                <span className="text-xs">{report.generated_at}</span>
              </li>
            </ul>
            <p className="tg-sub mt-4 text-xs">
              Phase 4.4 constrained automation requires all checks to pass. Strategy auto-execute
              respects this gate.
            </p>
          </Card>
        </div>
      </AppMain>
  );
}
