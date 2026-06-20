"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Sidebar } from "@/components/Sidebar";
import {
  completeOnboardingStep,
  getOnboardingStatus,
  resetOnboarding,
  type OnboardingStatus,
} from "@/lib/api";
import { Btn, Card, PageHeader } from "@/components/ui/Card";

export default function OnboardingPage() {
  const [status, setStatus] = useState<OnboardingStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    const data = await getOnboardingStatus();
    setStatus(data);
  }, []);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const data = await getOnboardingStatus();
        if (!cancelled) setStatus(data);
      } catch {
        if (!cancelled) setError("Could not load onboarding status");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleComplete(stepId: string) {
    setLoading(true);
    setError(null);
    try {
      const data = await completeOnboardingStep(stepId);
      setStatus(data);
    } catch {
      setError("Could not mark step complete");
    } finally {
      setLoading(false);
    }
  }

  async function handleReset() {
    setLoading(true);
    try {
      const data = await resetOnboarding();
      setStatus(data);
    } finally {
      setLoading(false);
    }
  }

  if (!status) {
    return (
      <div className="flex min-h-screen">
        <Sidebar />
        <main className="mx-auto w-full max-w-[900px] flex-1 p-7">
          <p className="text-muted">Loading onboarding…</p>
        </main>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="mx-auto w-full max-w-[900px] flex-1 p-7">
        <PageHeader
          title="Agentic Onboarding"
          subtitle="Connect MCP, fund your account, and confirm risk limits — no MCP-SETUP.md required"
        />

        {error && <p className="mb-4 text-sm text-red">{error}</p>}

        <Card className="mb-[18px]">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-bold">Setup progress</h2>
              <p className="tg-sub mt-1">
                {status.completed_count} of {status.total_steps} steps complete ({status.progress_pct}%)
              </p>
            </div>
            {status.complete && (
              <Link href="/approvals" className="text-sm font-bold text-teal hover:underline">
                Go to approvals →
              </Link>
            )}
          </div>
          <div className="mt-4 h-2 overflow-hidden rounded-full bg-[#182a42]">
            <div
              className="h-full rounded-full bg-teal transition-all"
              style={{ width: `${status.progress_pct}%` }}
            />
          </div>
        </Card>

        <ul className="space-y-3">
          {status.steps.map((step, idx) => (
            <li key={step.id}>
              <Card className={step.completed ? "border-teal/30" : ""}>
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-xs font-bold uppercase text-muted">Step {idx + 1}</p>
                    <h3 className="mt-1 text-lg font-extrabold">{step.title}</h3>
                    <p className="tg-sub mt-1 text-sm">{step.description}</p>
                    {step.id === "set_limits" && (
                      <ul className="tg-sub mt-2 list-inside list-disc text-xs">
                        <li>Max trade: ${status.risk_limits.max_trade_usd}</li>
                        <li>Max daily loss: ${status.risk_limits.max_daily_loss_usd}</li>
                        <li>Manual approval: {status.risk_limits.require_manual_approval ? "on" : "off"}</li>
                      </ul>
                    )}
                    {step.id === "connect_mcp" && (
                      <p className="tg-sub mt-2 text-xs">
                        MCP enabled: {status.mcp.enabled ? "yes" : "no"} · configured:{" "}
                        {status.mcp.configured ? "yes" : "no"}
                      </p>
                    )}
                  </div>
                  <span
                    className={
                      step.completed
                        ? "rounded bg-teal/20 px-2 py-1 text-xs font-bold text-teal"
                        : "rounded bg-[#182a42] px-2 py-1 text-xs text-muted"
                    }
                  >
                    {step.completed ? "Done" : step.manual_confirm ? "Confirm" : "Pending"}
                  </span>
                </div>
                {step.manual_confirm && !step.completed && (
                  <div className="mt-4">
                    <Btn disabled={loading} onClick={() => void handleComplete(step.id)}>
                      Mark complete
                    </Btn>
                  </div>
                )}
              </Card>
            </li>
          ))}
        </ul>

        <div className="mt-6">
          <Btn variant="secondary" disabled={loading} onClick={() => void handleReset()}>
            Reset wizard
          </Btn>
        </div>
      </main>
    </div>
  );
}
