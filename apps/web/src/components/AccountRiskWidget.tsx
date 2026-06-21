"use client";

import { useEffect, useState } from "react";
import { getReadiness, getRiskSnapshot, type Readiness, type RiskSnapshot } from "@/lib/api";

function riskTone(label: string) {
  const upper = label.toUpperCase();
  if (upper.includes("ELEVATED") || upper.includes("HIGH")) return "text-orange";
  if (upper.includes("LOW")) return "text-green";
  return "text-orange";
}

export function AccountRiskWidget({ compact = false }: { compact?: boolean }) {
  const [snapshot, setSnapshot] = useState<RiskSnapshot | null>(null);
  const [readiness, setReadiness] = useState<Readiness | null>(null);

  useEffect(() => {
    getRiskSnapshot().then(setSnapshot).catch(() => setSnapshot(null));
    getReadiness().then(setReadiness).catch(() => setReadiness(null));
  }, []);

  const label = snapshot?.risk_label?.toUpperCase() ?? "MODERATE";
  const techPct = snapshot?.sector_exposure?.Technology ?? 42;
  const detail =
    snapshot?.alerts?.[0]?.detail ??
    `Tech exposure is ${techPct.toFixed(0)}%. Manual approval recommended for all trades.`;

  return (
    <div
      className={`rounded-[18px] border border-[rgba(255,184,77,0.35)] bg-[rgba(255,184,77,0.08)] p-3.5 ${
        compact ? "" : "mt-6"
      }`}
    >
      <div className="tg-label">Current Risk</div>
      <div className={`tg-value ${riskTone(label)}`}>{label}</div>
      <p className="tg-sub mt-2">{detail}</p>
      <div className="mt-3 space-y-1 text-xs text-muted">
        <div className="flex justify-between">
          <span>API</span>
          <span className="text-green">● Online</span>
        </div>
        <div className="flex justify-between">
          <span>Market</span>
          <span className="text-teal">{readiness?.market_data_provider ?? "mock"}</span>
        </div>
        <div className="flex justify-between">
          <span>RAG</span>
          <span className="text-teal">{readiness?.embedding_provider ?? "mock"}</span>
        </div>
        <div className="flex justify-between">
          <span>Storage</span>
          <span className="text-teal">{readiness?.storage_backend ?? "memory"}</span>
        </div>
        <div className="flex justify-between">
          <span>MCP</span>
          <span className={readiness?.mcp_enabled ? "text-teal" : "text-muted"}>
            {readiness?.mcp_enabled
              ? readiness?.mcp_provider ?? "mock"
              : "Disabled"}
          </span>
        </div>
        <div className="flex justify-between">
          <span>LLM</span>
          <span className={readiness?.llm_configured ? "text-green" : "text-orange"}>
            {readiness?.llm_configured ? "Configured" : "Template mode"}
          </span>
        </div>
      </div>
    </div>
  );
}
