"use client";

import type { ReactNode } from "react";

function Sparkline({ positive = true }: { positive?: boolean }) {
  const stroke = positive ? "#35d07f" : "#ff5e6c";
  const path = positive
    ? "M0 28 L12 22 L24 24 L36 18 L48 20 L60 12 L72 14 L84 8 L96 10 L108 4"
    : "M0 8 L12 12 L24 10 L36 16 L48 14 L60 20 L72 18 L84 24 L96 22 L108 28";

  return (
    <svg viewBox="0 0 108 32" className="h-10 w-full" preserveAspectRatio="none" aria-hidden>
      <path d={path} fill="none" stroke={stroke} strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

export function KpiSparkCard({
  label,
  value,
  subValue,
  tone = "default",
  sparkPositive = true,
  icon,
}: {
  label: string;
  value: string;
  subValue?: string;
  tone?: "default" | "green" | "red" | "orange" | "yellow";
  sparkPositive?: boolean;
  icon?: ReactNode;
}) {
  const toneClass =
    tone === "green"
      ? "text-green"
      : tone === "red"
        ? "text-red"
        : tone === "orange"
          ? "text-orange"
          : tone === "yellow"
            ? "text-orange"
            : "";

  return (
    <div className="dash-card flex min-h-[132px] flex-col justify-between p-5">
      <div className="flex items-start justify-between gap-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted">{label}</p>
        {icon}
      </div>
      <div>
        <p className={`text-2xl font-bold tracking-tight ${toneClass}`}>{value}</p>
        {subValue ? <p className="mt-1 text-xs text-muted">{subValue}</p> : null}
      </div>
      <Sparkline positive={sparkPositive} />
    </div>
  );
}

export function RiskScoreCard({ score, label }: { score: number; label: string }) {
  const tone =
    score >= 65 ? "text-orange border-orange/30 bg-orange/10" : score >= 40 ? "text-orange border-orange/30 bg-orange/10" : "text-green border-green/30 bg-green/10";

  return (
    <div className="dash-card flex min-h-[132px] flex-col justify-between p-5">
      <div className="flex items-start justify-between">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted">Risk Score</p>
        <span className="text-lg">🛡️</span>
      </div>
      <div className="flex items-end gap-2">
        <span className={`text-4xl font-bold ${tone.split(" ")[0]}`}>{score}</span>
        <span className="pb-1 text-sm text-muted">/ 100</span>
      </div>
      <span className={`inline-flex w-fit rounded-full border px-2.5 py-0.5 text-[11px] font-bold ${tone}`}>
        {label} Risk
      </span>
    </div>
  );
}
