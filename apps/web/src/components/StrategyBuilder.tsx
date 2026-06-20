"use client";

import { useState } from "react";
import { createStrategy, type TradeStrategy } from "@/lib/api";
import { Btn } from "@/components/ui/Card";

const SECTORS = ["Technology", "Healthcare", "Financials", "Energy", "Consumer", "Industrials"];

type Props = {
  onCreated?: (strategy: TradeStrategy) => void;
};

export function StrategyBuilder({ onCreated }: Props) {
  const [name, setName] = useState("My sector rule");
  const [description, setDescription] = useState("");
  const [sector, setSector] = useState("Technology");
  const [threshold, setThreshold] = useState(25);
  const [comparison, setComparison] = useState<"above" | "below">("above");
  const [actionTicker, setActionTicker] = useState("QQQ");
  const [actionSide, setActionSide] = useState<"buy" | "sell">("buy");
  const [quantity, setQuantity] = useState(1);
  const [autoApprove, setAutoApprove] = useState(false);
  const [enabled, setEnabled] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  async function handleCreate() {
    setLoading(true);
    setError(null);
    setSuccess(null);
    try {
      const result = await createStrategy({
        name,
        description,
        strategy_type: "sector_exposure",
        config: {
          sector,
          threshold_pct: threshold,
          comparison,
          action_ticker: actionTicker.toUpperCase(),
          action_side: actionSide,
          quantity,
        },
        auto_approve: autoApprove,
        enabled,
      });
      setSuccess(`Created “${result.strategy.name}”`);
      onCreated?.(result.strategy);
    } catch {
      setError("Could not create strategy — check config");
    } finally {
      setLoading(false);
    }
  }

  const preview = `When ${sector} exposure is ${comparison} ${threshold}%, ${actionSide} ${quantity} ${actionTicker.toUpperCase()}`;

  return (
    <div className="space-y-4">
      <p className="tg-sub text-sm">{preview}</p>

      <div className="grid gap-3 sm:grid-cols-2">
        <label className="text-sm sm:col-span-2">
          <span className="tg-label">Name</span>
          <input
            className="mt-1 w-full rounded-lg border border-card-border bg-background px-3 py-2"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </label>
        <label className="text-sm sm:col-span-2">
          <span className="tg-label">Description</span>
          <input
            className="mt-1 w-full rounded-lg border border-card-border bg-background px-3 py-2"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Optional note"
          />
        </label>
        <label className="text-sm">
          <span className="tg-label">Sector</span>
          <select
            className="mt-1 w-full rounded-lg border border-card-border bg-background px-3 py-2"
            value={sector}
            onChange={(e) => setSector(e.target.value)}
          >
            {SECTORS.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          <span className="tg-label">Comparison</span>
          <select
            className="mt-1 w-full rounded-lg border border-card-border bg-background px-3 py-2"
            value={comparison}
            onChange={(e) => setComparison(e.target.value as "above" | "below")}
          >
            <option value="above">Above threshold</option>
            <option value="below">Below threshold</option>
          </select>
        </label>
        <label className="text-sm sm:col-span-2">
          <span className="tg-label">Threshold — {threshold}%</span>
          <input
            type="range"
            min={5}
            max={50}
            step={1}
            className="mt-2 w-full accent-teal"
            value={threshold}
            onChange={(e) => setThreshold(Number(e.target.value))}
          />
        </label>
        <label className="text-sm">
          <span className="tg-label">Action ticker</span>
          <input
            className="mt-1 w-full rounded-lg border border-card-border bg-background px-3 py-2 uppercase"
            value={actionTicker}
            onChange={(e) => setActionTicker(e.target.value.toUpperCase())}
          />
        </label>
        <label className="text-sm">
          <span className="tg-label">Side</span>
          <select
            className="mt-1 w-full rounded-lg border border-card-border bg-background px-3 py-2"
            value={actionSide}
            onChange={(e) => setActionSide(e.target.value as "buy" | "sell")}
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
            value={quantity}
            onChange={(e) => setQuantity(Number(e.target.value))}
          />
        </label>
        <div className="flex flex-col justify-end gap-2 text-sm">
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />
            Enable after create
          </label>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={autoApprove}
              onChange={(e) => setAutoApprove(e.target.checked)}
            />
            Auto-approve ALLOW only
          </label>
        </div>
      </div>

      {error && <p className="text-sm text-red">{error}</p>}
      {success && <p className="text-sm text-green">{success}</p>}

      <Btn onClick={() => void handleCreate()} disabled={loading || !name.trim()}>
        {loading ? "Creating…" : "Create strategy"}
      </Btn>
    </div>
  );
}
