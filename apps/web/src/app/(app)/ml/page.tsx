"use client";

import { useCallback, useEffect, useState } from "react";
import { AppMain } from "@/components/layout/AppMain";
import {
  getMLModelHistory,
  getMLModelStatus,
  retrainMLModel,
  rollbackMLModel,
  type MLModelHistoryEntry,
  type MLModelStatus,
} from "@/lib/api";
import { Btn, Card, PageHeader, StatCard } from "@/components/ui/Card";

function formatPct(value: number | undefined, digits = 1) {
  if (value == null || Number.isNaN(value)) return "—";
  return `${(value * 100).toFixed(digits)}%`;
}

function formatDate(value: string | undefined) {
  if (!value) return "—";
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}

function sourceLabel(source: string | undefined) {
  if (source === "market_and_journal") return "Market + journal";
  if (source === "market_only") return "Market only";
  if (source === "bootstrap") return "Bootstrap";
  return source ?? "—";
}

export default function MLModelsPage() {
  const [status, setStatus] = useState<MLModelStatus | null>(null);
  const [versions, setVersions] = useState<MLModelHistoryEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [ready, setReady] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    const [s, h] = await Promise.all([getMLModelStatus(), getMLModelHistory()]);
    setStatus(s);
    setVersions(h.versions ?? []);
  }, []);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const [s, h] = await Promise.all([getMLModelStatus(), getMLModelHistory()]);
        if (cancelled) return;
        setStatus(s);
        setVersions(h.versions ?? []);
      } catch {
        if (!cancelled) setError("Could not load ML model status.");
      } finally {
        if (!cancelled) setReady(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleRetrain() {
    setLoading(true);
    setError(null);
    setMessage(null);
    try {
      const result = await retrainMLModel();
      if (result.status === "ok") {
        setMessage(
          `Retrain complete — v${result.version ?? "?"} · AUC ${formatPct(result.auc)} · ${sourceLabel(result.source)}`
        );
      } else {
        setError(result.reason ?? "Retrain skipped (deploy gate or insufficient data).");
      }
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Retrain failed");
    } finally {
      setLoading(false);
    }
  }

  async function handleRollback(version: number) {
    if (!window.confirm(`Restore model version ${version}? Current model will be archived first.`)) return;
    setLoading(true);
    setError(null);
    setMessage(null);
    try {
      const result = await rollbackMLModel(version);
      if (result.status === "ok") {
        setMessage(`Rolled back to model v${result.version ?? version}`);
        await reload();
      } else {
        setError(result.reason ?? "Rollback failed");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Rollback failed");
    } finally {
      setLoading(false);
    }
  }

  if (!ready) {
    return (
      <AppMain>
        <p className="text-muted">Loading ML models…</p>
      </AppMain>
    );
  }

  const importance = Object.entries(status?.feature_importance ?? {}).sort((a, b) => b[1] - a[1]);
  const vol = status?.volatility;
  const volImportance = Object.entries(vol?.feature_importance ?? {}).sort((a, b) => b[1] - a[1]);
  const journalReady =
    (status?.journal_trades_used ?? 0) >= (status?.min_trades_required ?? 10);

  return (
    <AppMain>
      <PageHeader
        title="ML Models"
        subtitle="Direction + volatility models · retrain, deploy gate, rollback"
      />

      {message ? (
        <Card className="mb-4 border-green/30">
          <p className="text-sm text-green">{message}</p>
        </Card>
      ) : null}
      {error ? (
        <Card className="mb-4" warning>
          <p className="text-sm text-red">{error}</p>
        </Card>
      ) : null}

      <div className="grid grid-cols-2 gap-[18px] lg:grid-cols-4">
        <StatCard label="Direction v" value={`v${status?.version ?? 0}`} tone="blue" />
        <StatCard label="Direction AUC" value={formatPct(status?.auc)} tone="green" />
        <StatCard label="Vol model v" value={`v${vol?.version ?? 0}`} tone="blue" />
        <StatCard
          label="Journal rows"
          value={`${status?.journal_trades_used ?? 0} / ${status?.min_trades_required ?? 10}`}
          tone={journalReady ? "green" : "orange"}
        />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Card>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="text-lg font-extrabold">Direction model</h2>
              <p className="tg-sub mt-1 text-sm">
                {status?.model_type ?? "none"} · {sourceLabel(status?.source)}
              </p>
            </div>
            <Btn disabled={loading} onClick={() => void handleRetrain()}>
              {loading ? "Working…" : "Retrain now"}
            </Btn>
          </div>

          <dl className="mt-4 grid gap-2 text-sm sm:grid-cols-2">
            <div>
              <dt className="tg-label">Last trained</dt>
              <dd>{formatDate(status?.last_trained_at)}</dd>
            </div>
            <div>
              <dt className="tg-label">Brier score</dt>
              <dd>{status?.brier?.toFixed(3) ?? "—"}</dd>
            </div>
            <div>
              <dt className="tg-label">Walk-forward folds</dt>
              <dd>{status?.walk_forward_folds ?? "—"}</dd>
            </div>
            <div>
              <dt className="tg-label">Training samples</dt>
              <dd>{status?.samples ?? "—"}</dd>
            </div>
            <div>
              <dt className="tg-label">Deploy gate</dt>
              <dd className={status?.deploy_gate_passed ? "text-green" : "text-orange"}>
                {status?.deploy_gate_passed ? "Passed" : "Not passed / bootstrap"}
              </dd>
            </div>
            <div>
              <dt className="tg-label">Journal retrain</dt>
              <dd>{status?.journal_retrain_enabled ? "Enabled" : "Disabled"}</dd>
            </div>
          </dl>

          {importance.length > 0 ? (
            <div className="mt-5">
              <h3 className="text-sm font-bold">Top feature importance</h3>
              <div className="mt-2 space-y-2">
                {importance.map(([name, weight]) => (
                  <div key={name} className="flex items-center gap-3 text-sm">
                    <span className="w-40 shrink-0 truncate text-muted">{name}</span>
                    <div className="tg-bar flex-1">
                      <span style={{ width: `${Math.min(100, weight * 100 * 3)}%` }} />
                    </div>
                    <span className="w-12 text-right tabular-nums">{weight.toFixed(3)}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : null}
        </Card>

        <Card>
          <h2 className="text-lg font-extrabold">Volatility / regime model</h2>
          <p className="tg-sub mt-1 text-sm">
            SPY+QQQ macro classifier · high-vol prob ≥ {(vol?.high_threshold ?? 0.55) * 100}% elevates regime
          </p>

          <div className="mt-4 grid grid-cols-2 gap-[18px]">
            <StatCard label="Vol AUC" value={formatPct(vol?.auc)} tone={vol?.model_exists ? "green" : "orange"} />
            <StatCard label="Vol accuracy" value={formatPct(vol?.accuracy)} />
          </div>

          <dl className="mt-4 grid gap-2 text-sm sm:grid-cols-2">
            <div>
              <dt className="tg-label">Model type</dt>
              <dd>{vol?.model_type ?? "none"}</dd>
            </div>
            <div>
              <dt className="tg-label">Last trained</dt>
              <dd>{formatDate(vol?.last_trained_at)}</dd>
            </div>
            <div>
              <dt className="tg-label">Enabled</dt>
              <dd>{vol?.enabled ? "Yes" : "No"}</dd>
            </div>
            <div>
              <dt className="tg-label">Accuracy</dt>
              <dd>{formatPct(vol?.accuracy)}</dd>
            </div>
          </dl>

          {volImportance.length > 0 ? (
            <div className="mt-5">
              <h3 className="text-sm font-bold">Vol feature importance</h3>
              <div className="mt-2 space-y-2">
                {volImportance.map(([name, weight]) => (
                  <div key={name} className="flex items-center gap-3 text-sm">
                    <span className="w-40 shrink-0 truncate text-muted">{name}</span>
                    <div className="tg-bar flex-1">
                      <span style={{ width: `${Math.min(100, weight * 100 * 3)}%` }} />
                    </div>
                    <span className="w-12 text-right tabular-nums">{weight.toFixed(3)}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : null}
        </Card>
      </div>

      <Card className="mt-6">
        <h2 className="text-lg font-extrabold">Direction version history</h2>
          <p className="tg-sub mt-1 text-sm">
            Archived models kept for rollback ({status?.history_versions ?? versions.length} stored).
          </p>

          {versions.length === 0 ? (
            <p className="mt-4 text-sm text-muted">
              No archived versions yet. Retrain once to archive the current model before deploy.
            </p>
          ) : (
            <div className="mt-4 overflow-x-auto">
              <table className="w-full min-w-[520px] text-left text-sm">
                <thead>
                  <tr className="border-b border-card-border text-muted">
                    <th className="py-2 pr-3 font-semibold">Version</th>
                    <th className="py-2 pr-3 font-semibold">AUC</th>
                    <th className="py-2 pr-3 font-semibold">Source</th>
                    <th className="py-2 pr-3 font-semibold">Trained</th>
                    <th className="py-2 font-semibold">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {versions.map((entry) => (
                    <tr key={entry.version} className="border-b border-card-border/50">
                      <td className="py-2.5 pr-3">
                        <span className="font-bold">v{entry.version}</span>
                        {entry.active ? (
                          <span className="ml-2 rounded bg-green/15 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-green">
                            active
                          </span>
                        ) : null}
                      </td>
                      <td className="py-2.5 pr-3 tabular-nums">{formatPct(entry.auc)}</td>
                      <td className="py-2.5 pr-3">{sourceLabel(entry.source)}</td>
                      <td className="py-2.5 pr-3 text-muted">{formatDate(entry.last_trained_at)}</td>
                      <td className="py-2.5">
                        {entry.active ? (
                          <span className="text-muted">—</span>
                        ) : entry.artifact_exists ? (
                          <button
                            type="button"
                            disabled={loading}
                            onClick={() => void handleRollback(entry.version)}
                            className="text-sm font-bold text-blue hover:underline disabled:opacity-50"
                          >
                            Rollback
                          </button>
                        ) : (
                          <span className="text-orange text-xs">Missing artifact</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
      </Card>

      <Card className="mt-6">
        <h2 className="text-lg font-extrabold">How journal retrain works</h2>
        <ul className="mt-3 list-inside list-disc space-y-1 text-sm text-muted">
          <li>Each trade submit stores a point-in-time <code className="text-foreground">ml_snapshot</code> in the approval.</li>
          <li>Closed trades with PnL contribute journal rows once you hit the minimum trade count.</li>
          <li>Retrain merges market data with journal snapshots; deploy gate blocks worse models.</li>
        </ul>
      </Card>
    </AppMain>
  );
}
