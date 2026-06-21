"use client";

import Link from "next/link";

export function AiRecommendationPanel({
  techPct,
  techLimit,
  riskLabel,
}: {
  techPct: number;
  techLimit: number;
  riskLabel: string;
}) {
  const overweight = techPct > techLimit;

  return (
    <div className="dash-card dash-card-ai p-5">
      <div className="flex items-start gap-3">
        <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-purple/20 text-lg">✨</span>
        <div>
          <p className="text-[10px] font-bold uppercase tracking-wide text-purple">AI Recommendation</p>
          <h3 className="mt-1 text-lg font-bold text-white">
            {overweight ? "Reduce Technology exposure" : "Maintain current risk posture"}
          </h3>
        </div>
      </div>
      <p className="mt-3 text-sm leading-relaxed text-white/75">
        {overweight
          ? `Your portfolio is overweight in Technology (${techPct.toFixed(1)}% vs ${techLimit}% limit). Consider rebalancing to reduce concentration risk while ${riskLabel.toLowerCase()} conditions persist.`
          : `Portfolio risk is ${riskLabel.toLowerCase()}. Continue using limit orders and manual approval for new positions.`}
      </p>
      <ul className="mt-3 space-y-1.5 text-sm text-white/70">
        {overweight ? (
          <>
            <li>• Trim Technology exposure by ~${Math.round((techPct - techLimit) * 500).toLocaleString()}</li>
            <li>• Increase allocation to Healthcare or Industrials</li>
            <li>• Review correlated mega-cap names before adding size</li>
          </>
        ) : (
          <>
            <li>• Keep sector limits enforced on every trade preview</li>
            <li>• Favor limit orders over market orders</li>
          </>
        )}
      </ul>
      <div className="mt-4 flex flex-wrap gap-2">
        <Link href="/portfolio" className="rounded-xl bg-purple px-4 py-2 text-xs font-bold text-white hover:opacity-90">
          View Rebalance Plan
        </Link>
        <Link href="/analysis" className="rounded-xl border border-white/15 px-4 py-2 text-xs font-bold text-white/85 hover:border-purple/40">
          Run Scenario
        </Link>
      </div>
    </div>
  );
}

export function DashboardTopBar() {
  const now = new Date();
  const time = now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  const date = now.toLocaleDateString([], { month: "short", day: "numeric", year: "numeric" });

  return (
    <header className="mb-6 flex flex-wrap items-center justify-between gap-4 border-b border-white/10 pb-4">
      <div className="flex items-center gap-3">
        <button type="button" className="rounded-lg border border-white/10 px-2 py-1 text-sm text-muted lg:hidden">
          ☰
        </button>
        <div>
          <h1 className="text-xl font-bold text-white">Portfolio Risk Dashboard</h1>
          <p className="text-sm text-muted">Real-time risk overview and AI-powered insights</p>
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <span className="flex items-center gap-2 rounded-full border border-green/30 bg-green/10 px-3 py-1 text-xs font-semibold text-green">
          <span className="h-2 w-2 rounded-full bg-green" />
          Markets Open
        </span>
        <span className="text-xs text-muted">{time} ET</span>
        <select className="rounded-xl border border-white/10 bg-[#0b1524] px-3 py-2 text-xs text-white">
          <option>{date}</option>
        </select>
        <select className="rounded-xl border border-white/10 bg-[#0b1524] px-3 py-2 text-xs text-white">
          <option>Demo Portfolio</option>
        </select>
        <button type="button" className="relative rounded-xl border border-white/10 px-3 py-2 text-sm">
          🔔
          <span className="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center rounded-full bg-red text-[10px] font-bold text-white">
            3
          </span>
        </button>
        <div className="flex h-9 w-9 items-center justify-center rounded-full bg-gradient-to-br from-teal to-blue text-xs font-bold">
          PR
        </div>
      </div>
    </header>
  );
}
