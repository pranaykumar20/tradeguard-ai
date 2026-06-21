"use client";

import { useCallback, useEffect, useState } from "react";
import { AppMain } from "@/components/layout/AppMain";
import {
  getRagEvalReport,
  getRagStatus,
  migrateRagEmbeddings,
  refreshRagIndex,
  runRagEval,
  type RagEvalReport,
  type RagStatus,
} from "@/lib/api";
import { Btn, Card, PageHeader, StatCard } from "@/components/ui/Card";

function formatDate(value: string | undefined) {
  if (!value) return "—";
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}

export default function RagAdminPage() {
  const [status, setStatus] = useState<RagStatus | null>(null);
  const [evalReport, setEvalReport] = useState<RagEvalReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [ready, setReady] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    const [s, e] = await Promise.all([getRagStatus(), getRagEvalReport()]);
    setStatus(s);
    if (e.status !== "no_report") setEvalReport(e);
  }, []);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const [s, e] = await Promise.all([getRagStatus(), getRagEvalReport()]);
        if (cancelled) return;
        setStatus(s);
        if (e.status !== "no_report") setEvalReport(e);
      } catch {
        if (!cancelled) setError("Could not load RAG status.");
      } finally {
        if (!cancelled) setReady(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleEval() {
    setLoading(true);
    setError(null);
    setMessage(null);
    try {
      const report = await runRagEval();
      setEvalReport(report);
      setMessage(
        `Eval complete — ${report.tool_selection_accuracy_pct ?? 0}% tool accuracy · ACL leak ${report.acl_leak_rate_pct ?? 0}%`
      );
      await reload();
    } catch {
      setError("RAG eval failed.");
    } finally {
      setLoading(false);
    }
  }

  async function handleRefresh(source?: string) {
    setLoading(true);
    setError(null);
    setMessage(null);
    try {
      await refreshRagIndex(source);
      setMessage(source ? `Re-indexed ${source}.` : "Full RAG refresh started.");
      await reload();
    } catch {
      setError("RAG refresh failed.");
    } finally {
      setLoading(false);
    }
  }

  async function handleMigrate() {
    setLoading(true);
    setError(null);
    setMessage(null);
    try {
      const result = await migrateRagEmbeddings();
      setMessage(`Embedding migration — reembedded ${result.reembedded ?? 0} chunks.`);
      await reload();
    } catch {
      setError("Embedding migration failed.");
    } finally {
      setLoading(false);
    }
  }

  if (!ready) {
    return (
      <AppMain>
        <PageHeader title="RAG" subtitle="Loading retrieval pipeline status…" />
      </AppMain>
    );
  }

  const byType = status?.documents_by_type ?? {};
  const typeSummary = Object.entries(byType)
    .map(([k, v]) => `${k}: ${v}`)
    .join(" · ");

  return (
    <AppMain>
      <PageHeader
        title="RAG Pipeline"
        subtitle="Corpus health, eval metrics, and index management"
      />

      {message ? (
        <Card className="mb-4 border-green/30 bg-green/5 text-sm text-green">{message}</Card>
      ) : null}
      {error ? (
        <Card className="mb-4 border-red/30 bg-red/5 text-sm text-red">{error}</Card>
      ) : null}

      <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Documents" value={String(status?.documents_total ?? 0)} />
        <StatCard label="Embedding v" value={String(status?.embedding_version ?? "—")} />
        <StatCard
          label="Tool accuracy"
          value={
            evalReport?.tool_selection_accuracy_pct != null
              ? `${evalReport.tool_selection_accuracy_pct}%`
              : "—"
          }
        />
        <StatCard
          label="ACL leak rate"
          value={
            evalReport?.acl_leak_rate_pct != null ? `${evalReport.acl_leak_rate_pct}%` : "—"
          }
        />
      </div>

      <Card className="mb-6">
        <h2 className="mb-2 font-bold">Corpus</h2>
        <p className="text-sm text-muted">{typeSummary || "No documents indexed yet."}</p>
        <p className="mt-2 text-xs text-muted">
          Router {status?.router_enabled ? "on" : "off"} · Eval{" "}
          {status?.eval_enabled ? "on" : "off"}
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          <Btn disabled={loading} onClick={() => void handleRefresh()}>
            Refresh all
          </Btn>
          <Btn disabled={loading} onClick={() => void handleRefresh("playbooks")}>
            Playbooks
          </Btn>
          <Btn disabled={loading} onClick={() => void handleRefresh("journal")}>
            Journal
          </Btn>
          <Btn disabled={loading} onClick={() => void handleEval()}>
            Run eval
          </Btn>
          <Btn disabled={loading} onClick={() => void handleMigrate()}>
            Migrate embeddings
          </Btn>
        </div>
      </Card>

      {evalReport && evalReport.status === "ok" ? (
        <Card>
          <h2 className="mb-2 font-bold">Last eval</h2>
          <p className="text-xs text-muted">
            {formatDate(evalReport.ran_at)} · {evalReport.elapsed_ms}ms ·{" "}
            {evalReport.cases_passed}/{evalReport.cases_total} passed
          </p>
          <ul className="mt-3 space-y-2">
            {(evalReport.cases ?? []).map((c) => (
              <li
                key={c.id}
                className={`rounded-lg border px-3 py-2 text-xs ${c.passed ? "border-green/30" : "border-red/30"}`}
              >
                <span className="font-semibold">{c.passed ? "✓" : "✗"} {c.id}</span>
                <span className="text-muted"> — {c.query}</span>
                <div className="mt-1 text-muted">Tools: {c.plan_tools.join(", ") || "none"}</div>
              </li>
            ))}
          </ul>
        </Card>
      ) : null}
    </AppMain>
  );
}
