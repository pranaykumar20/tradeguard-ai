"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { AccountRiskWidget } from "@/components/AccountRiskWidget";
import { AuthControls } from "@/components/AuthShell";

const NAV: { href: string; label: string; badge?: string }[] = [
  { href: "/", label: "AI Chat" },
  { href: "/dashboard", label: "Dashboard" },
  { href: "/portfolio", label: "Portfolio Risk" },
  { href: "/analysis", label: "Stock Analyzer" },
  { href: "/journal", label: "Trade Journal" },
  { href: "/approvals", label: "Trade Approval" },
  { href: "/monitoring", label: "Monitoring" },
  { href: "/strategies", label: "Strategies" },
  { href: "/validation", label: "Validation Gate" },
  { href: "/automation", label: "Automation" },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="sticky top-0 flex h-screen w-[265px] shrink-0 flex-col border-r border-card-border bg-[rgba(7,17,31,0.86)] p-[22px]">
      <div className="text-2xl font-extrabold tracking-tight">
        TradeGuard <span className="text-teal">AI</span>
      </div>
      <div className="tg-sub mt-1">Phase 6 · Intelligence upgrades</div>

      <nav className="mt-7 flex-1 space-y-1">
        {NAV.map((item) => {
          const active = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`block w-full rounded-[14px] px-[14px] py-[13px] text-left text-sm font-bold transition ${
                active
                  ? "bg-[linear-gradient(90deg,rgba(38,228,196,0.16),rgba(85,185,255,0.08))] text-foreground"
                  : "text-muted hover:bg-[linear-gradient(90deg,rgba(38,228,196,0.16),rgba(85,185,255,0.08))] hover:text-foreground"
              }`}
            >
              <span className="flex items-center justify-between gap-2">
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

      <AccountRiskWidget />
      <AuthControls />
    </aside>
  );
}
