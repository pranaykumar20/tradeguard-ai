"use client";

import { useCallback, useEffect, useState } from "react";
import { Sidebar } from "@/components/Sidebar";
import { Btn, Card, PageHeader, Row } from "@/components/ui/Card";
import {
  approveExecution,
  getExecutionApprovals,
  previewExecution,
  rejectExecution,
  submitExecution,
  type ApprovalRequest,
  type ExecutionPreview,
} from "@/lib/api";

type OrderForm = {
  ticker: string;
  side: "buy" | "sell";
  quantity: number;
  limit_price: string;
  notes: string;
};

const EMPTY_FORM: OrderForm = {
  ticker: "NVDA",
  side: "buy",
  quantity: 1,
  limit_price: "",
  notes: "",
};

function verdictToneClass(verdict: string) {
  if (verdict === "ALLOW") return "text-green";
  if (verdict === "BLOCK") return "text-red";
  return "text-orange";
}

export default function ApprovalsPage() {
  const [approvals, setApprovals] = useState<ApprovalRequest[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [preview, setPreview] = useState<ExecutionPreview | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionMsg, setActionMsg] = useState<string | null>(null);

  const selected = approvals.find((a) => a.id === selectedId) ?? approvals[0] ?? null;

  const loadApprovals = useCallback(async () => {
    try {
      const data = await getExecutionApprovals("pending");
      setApprovals(data.approvals);
      if (!selectedId && data.approvals.length > 0) {
        setSelectedId(data.approvals[0].id);
      }
    } catch {
      setError("Could not load approval queue");
    }
  }, [selectedId]);

  useEffect(() => {
    loadApprovals();
  }, [loadApprovals]);

  async function handlePreview() {
    setLoading(true);
    setError(null);
    setActionMsg(null);
    try {
      const limit = form.limit_price ? Number(form.limit_price) : undefined;
      const result = await previewExecution({
        ticker: form.ticker,
        side: form.side,
        quantity: form.quantity,
        limit_price: limit,
      });
      setPreview(result);
    } catch {
      setError("Preview failed");
    } finally {
      setLoading(false);
    }
  }

  async function handleSubmit() {
    setLoading(true);
    setError(null);
    setActionMsg(null);
    try {
      const limit = form.limit_price ? Number(form.limit_price) : undefined;
      await submitExecution({
        ticker: form.ticker,
        side: form.side,
        quantity: form.quantity,
        limit_price: limit,
        notes: form.notes,
      });
      setActionMsg("Order submitted for approval");
      setPreview(null);
      setForm(EMPTY_FORM);
      await loadApprovals();
    } catch {
      setError("Order blocked or submit failed — check risk rules");
    } finally {
      setLoading(false);
    }
  }

  async function handleApprove(id: string) {
    setLoading(true);
    setError(null);
    try {
      await approveExecution(id);
      setActionMsg("Trade approved and executed");
      await loadApprovals();
    } catch {
      setError("Approval failed");
    } finally {
      setLoading(false);
    }
  }

  async function handleReject(id: string) {
    setLoading(true);
    setError(null);
    try {
      await rejectExecution(id, "Rejected from approval UI");
      setActionMsg("Trade rejected");
      await loadApprovals();
    } catch {
      setError("Reject failed");
    } finally {
      setLoading(false);
    }
  }

  const risk = selected?.risk_preview;
  const mcp = selected?.mcp_preview;

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="mx-auto w-full max-w-[1400px] flex-1 p-7">
        <PageHeader
          title="Trade Approval"
          subtitle="Risk gate → MCP preview → manual approve → guarded execution"
        />

        {error && <p className="mb-4 text-sm text-red">{error}</p>}
        {actionMsg && <p className="mb-4 text-sm text-green">{actionMsg}</p>}

        <div className="mb-[18px] grid gap-[18px] lg:grid-cols-3">
          <Card className="lg:col-span-1">
            <h2 className="text-lg font-extrabold">Pending Queue</h2>
            <div className="mt-3 space-y-2">
              {approvals.length === 0 && (
                <p className="tg-sub text-sm">No pending approvals — submit a trade below.</p>
              )}
              {approvals.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => setSelectedId(item.id)}
                  className={`w-full rounded-[12px] border px-3 py-2 text-left text-sm transition ${
                    selected?.id === item.id
                      ? "border-teal bg-[rgba(38,228,196,0.1)]"
                      : "border-card-border hover:border-teal/40"
                  }`}
                >
                  <div className="font-bold">
                    {item.side.toUpperCase()} {item.quantity} {item.ticker}
                  </div>
                  <div className="tg-sub text-xs">
                    ${item.limit_price.toFixed(2)} · {item.risk_preview?.verdict ?? "—"}
                  </div>
                </button>
              ))}
            </div>
          </Card>

          <div className="grid gap-[18px] lg:col-span-2 lg:grid-cols-2">
            <Card>
              <h2 className="text-xl font-extrabold">
                {selected
                  ? `Trade Preview: ${selected.ticker}`
                  : "Select or submit a trade"}
              </h2>
              {selected ? (
                <>
                  <div className="mt-2">
                    <Row label="Action" value={selected.side.toUpperCase()} tone="green" />
                    <Row label="Order Type" value={selected.order_type} />
                    <Row label="Quantity" value={`${selected.quantity} shares`} />
                    <Row
                      label="Limit Price"
                      value={`$${selected.limit_price.toFixed(2)}`}
                    />
                    <Row
                      label="Est. Cost"
                      value={`$${(selected.quantity * selected.limit_price).toFixed(2)}`}
                    />
                    {typeof mcp?.provider === "string" && (
                      <Row label="MCP" value={mcp.provider} />
                    )}
                  </div>
                  <div className="mt-4 flex flex-wrap gap-2">
                    <Btn disabled={loading} onClick={() => handleApprove(selected.id)}>
                      Approve Trade
                    </Btn>
                    <Btn variant="danger" disabled={loading} onClick={() => handleReject(selected.id)}>
                      Reject
                    </Btn>
                  </div>
                </>
              ) : (
                <p className="tg-sub mt-3">Submit a new order to start the approval flow.</p>
              )}
            </Card>

            <Card warning>
              <h2 className="text-xl font-extrabold">Risk Check</h2>
              {risk ? (
                <>
                  <p className="tg-sub mt-3">
                    Verdict:{" "}
                    <span className={verdictToneClass(risk.verdict)}>{risk.verdict}</span>
                    {risk.warnings?.length
                      ? ` — ${risk.warnings[0]}`
                      : " — within policy limits"}
                  </p>
                  <div className="mt-2">
                    <Row
                      label="Order value"
                      value={`$${risk.order_value?.toFixed(2) ?? "—"}`}
                    />
                    <Row
                      label="Setup score"
                      value={`${risk.composite_score ?? "—"}/100`}
                      tone="blue"
                    />
                    {risk.blocks?.map((b) => (
                      <Row key={b} label="Block" value={b} tone="red" />
                    ))}
                    {risk.warnings?.slice(0, 2).map((w) => (
                      <Row key={w} label="Warning" value={w} tone="orange" />
                    ))}
                  </div>
                </>
              ) : (
                <p className="tg-sub mt-3">Risk preview appears when a trade is selected.</p>
              )}
            </Card>
          </div>
        </div>

        <Card>
          <h2 className="text-lg font-extrabold">Submit New Order</h2>
          <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            <label className="text-sm">
              <span className="tg-label">Ticker</span>
              <input
                className="mt-1 w-full rounded-lg border border-card-border bg-background px-3 py-2"
                value={form.ticker}
                onChange={(e) => setForm({ ...form, ticker: e.target.value.toUpperCase() })}
              />
            </label>
            <label className="text-sm">
              <span className="tg-label">Side</span>
              <select
                className="mt-1 w-full rounded-lg border border-card-border bg-background px-3 py-2"
                value={form.side}
                onChange={(e) =>
                  setForm({ ...form, side: e.target.value as "buy" | "sell" })
                }
              >
                <option value="buy">Buy</option>
                <option value="sell">Sell</option>
              </select>
            </label>
            <label className="text-sm">
              <span className="tg-label">Quantity</span>
              <input
                type="number"
                min={0.01}
                step={0.01}
                className="mt-1 w-full rounded-lg border border-card-border bg-background px-3 py-2"
                value={form.quantity}
                onChange={(e) => setForm({ ...form, quantity: Number(e.target.value) })}
              />
            </label>
            <label className="text-sm">
              <span className="tg-label">Limit (optional)</span>
              <input
                type="number"
                min={0.01}
                step={0.01}
                placeholder="Auto from quote"
                className="mt-1 w-full rounded-lg border border-card-border bg-background px-3 py-2"
                value={form.limit_price}
                onChange={(e) => setForm({ ...form, limit_price: e.target.value })}
              />
            </label>
            <label className="text-sm">
              <span className="tg-label">Notes</span>
              <input
                className="mt-1 w-full rounded-lg border border-card-border bg-background px-3 py-2"
                value={form.notes}
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
              />
            </label>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <Btn variant="secondary" disabled={loading} onClick={handlePreview}>
              Preview
            </Btn>
            <Btn disabled={loading} onClick={handleSubmit}>
              Submit for Approval
            </Btn>
          </div>
          {preview && (
            <div className="mt-4 rounded-[12px] border border-card-border p-3 text-sm">
              <div>
                Risk: {preview.risk.verdict} · MCP:{" "}
                {typeof preview.mcp.provider === "string"
                  ? preview.mcp.provider
                  : preview.mcp_provider}
              </div>
              <div className="tg-sub">
                {preview.risk.allowed
                  ? "Eligible for approval queue"
                  : `Blocked: ${preview.risk.blocks?.join("; ")}`}
              </div>
            </div>
          )}
        </Card>
      </main>
    </div>
  );
}
