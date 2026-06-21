"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { AppMain } from "@/components/layout/AppMain";
import {
  completeOnboardingStep,
  disconnectRobinhood,
  getOnboardingStatus,
  resetOnboarding,
  startRobinhoodConnect,
  type OnboardingStatus,
} from "@/lib/api";
import { Btn, Card, PageHeader } from "@/components/ui/Card";

export default function OnboardingPageContent() {
  const searchParams = useSearchParams();
  const [status, setStatus] = useState<OnboardingStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [connectLoading, setConnectLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [banner, setBanner] = useState<string | null>(null);

  async function refreshStatus() {
    const data = await getOnboardingStatus();
    setStatus(data);
    return data;
  }

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const data = await refreshStatus();
        if (!cancelled) setStatus(data);
      } catch {
        if (!cancelled) setError("Could not load onboarding status");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const result = searchParams.get("robinhood");
    if (!result) return;
    if (result === "connected") {
      setBanner("Robinhood connected successfully.");
      void refreshStatus();
    } else if (result === "error") {
      const reason = searchParams.get("reason") ?? "unknown";
      setBanner(`Robinhood connection failed (${reason.replaceAll("_", " ")}).`);
    }
  }, [searchParams]);

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

  async function handleConnectRobinhood() {
    setConnectLoading(true);
    setError(null);
    setBanner(null);
    try {
      const { authorization_url } = await startRobinhoodConnect("/onboarding");
      window.location.href = authorization_url;
    } catch {
      setError("Could not start Robinhood connection. Check that you are signed in.");
      setConnectLoading(false);
    }
  }

  async function handleDisconnectRobinhood() {
    setConnectLoading(true);
    setError(null);
    try {
      await disconnectRobinhood();
      const data = await refreshStatus();
      setStatus(data);
      setBanner("Robinhood disconnected.");
    } catch {
      setError("Could not disconnect Robinhood");
    } finally {
      setConnectLoading(false);
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
      <AppMain>
        <p className="text-muted">Loading onboarding…</p>
      </AppMain>
    );
  }

  const robinhoodConnected = status.robinhood?.connected ?? status.mcp.connected ?? false;

  return (
    <AppMain>
      <PageHeader
        title="Agentic Onboarding"
        subtitle="Connect Robinhood, fund your Agentic account, and confirm risk limits"
      />

      {banner && (
        <p className="mb-4 rounded-lg border border-teal/30 bg-teal/10 px-3 py-2 text-sm text-teal">
          {banner}
        </p>
      )}
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
                <div className="min-w-0 flex-1">
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
                    <div className="mt-3 space-y-2">
                      <p className="tg-sub text-xs">
                        Status:{" "}
                        {robinhoodConnected ? (
                          <span className="font-bold text-teal">Connected</span>
                        ) : (
                          <span className="text-muted">Not connected</span>
                        )}
                        {status.robinhood?.connected_at && robinhoodConnected && (
                          <> · since {new Date(status.robinhood.connected_at).toLocaleDateString()}</>
                        )}
                      </p>
                      <ol className="tg-sub list-inside list-decimal text-xs">
                        <li>Enable Agentic Trading in Robinhood (desktop required).</li>
                        <li>Click Connect — you&apos;ll sign in with Robinhood OAuth.</li>
                        <li>Complete Agentic account setup and fund it ($500–$1,000).</li>
                      </ol>
                      <div className="flex flex-wrap gap-2 pt-1">
                        {!robinhoodConnected ? (
                          <Btn disabled={connectLoading} onClick={() => void handleConnectRobinhood()}>
                            {connectLoading ? "Redirecting…" : "Connect Robinhood"}
                          </Btn>
                        ) : (
                          <Btn
                            variant="secondary"
                            disabled={connectLoading}
                            onClick={() => void handleDisconnectRobinhood()}
                          >
                            Disconnect
                          </Btn>
                        )}
                      </div>
                    </div>
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
    </AppMain>
  );
}
