"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { AccountRiskWidget } from "@/components/AccountRiskWidget";
import { AuthControls } from "@/components/AuthShell";
import { PushInboxBell } from "@/components/PushInboxBell";

const NAV: { href: string; label: string; icon: string; badge?: string }[] = [
  { href: "/dashboard", label: "Overview", icon: "▦" },
  { href: "/portfolio", label: "Portfolio", icon: "◫" },
  { href: "/portfolio", label: "Risk Analytics", icon: "◉" },
  { href: "/", label: "AI Insights", icon: "✦" },
  { href: "/monitoring", label: "Alerts", icon: "⚑" },
  { href: "/analysis", label: "Stock Analyzer", icon: "↗" },
  { href: "/journal", label: "Reports", icon: "☰" },
  { href: "/approvals", label: "Trade Approval", icon: "✓" },
  { href: "/onboarding", label: "Onboarding", icon: "◎", badge: "new" },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="sticky top-0 flex h-screen w-[265px] shrink-0 flex-col border-r border-card-border bg-[#0a1422]/95 p-[22px]">
      <div className="flex items-center gap-2 text-2xl font-extrabold tracking-tight">
        <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-blue/15 text-lg text-blue">🛡</span>
        <span>
          TradeGuard <span className="text-teal">AI</span>
        </span>
      </div>
      <div className="tg-sub mt-1">Portfolio Risk Platform</div>

      <nav className="mt-7 flex-1 space-y-1">
        {NAV.map((item) => {
          const active = pathname === item.href;
          return (
            <Link
              key={`${item.href}-${item.label}`}
              href={item.href}
              className={`flex w-full items-center gap-3 rounded-[14px] px-[14px] py-[12px] text-left text-sm font-bold transition ${
                active
                  ? "bg-[linear-gradient(90deg,rgba(38,228,196,0.16),rgba(85,185,255,0.08))] text-foreground"
                  : "text-muted hover:bg-white/[0.04] hover:text-foreground"
              }`}
            >
              <span className="w-4 text-center text-xs opacity-80">{item.icon}</span>
              <span className="flex flex-1 items-center justify-between gap-2">
                {item.label}
                {item.badge && (
                  <span className="rounded bg-[#182a42] px-1.5 py-0.5 text-[10px] font-normal">
                    {item.badge}
                  </span>
                )}
              </span>
            </Link>
          );
        })}
      </nav>

      <PushInboxBell />
      <AccountRiskWidget />
      <AuthControls />
    </aside>
  );
}
