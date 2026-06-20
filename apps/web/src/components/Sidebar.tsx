"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV = [
  { href: "/", label: "Ask AI", icon: "💬" },
  { href: "/dashboard", label: "Risk Dashboard", icon: "📊" },
  { href: "/portfolio", label: "Portfolio", icon: "💼" },
  { href: "/approvals", label: "Approvals", icon: "✓", badge: "Soon" },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex w-56 shrink-0 flex-col border-r border-card-border bg-[#0a0e13]">
      <div className="flex items-center gap-2 border-b border-card-border px-4 py-5">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent/20 text-lg">
          🛡️
        </div>
        <div>
          <div className="text-sm font-semibold tracking-wide text-accent">TRADEGUARD</div>
          <div className="text-[10px] uppercase tracking-widest text-muted">AI Risk Manager</div>
        </div>
      </div>

      <nav className="flex-1 space-y-1 p-3">
        {NAV.map((item) => {
          const active = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm transition ${
                active
                  ? "bg-accent/15 text-accent"
                  : "text-muted hover:bg-card hover:text-foreground"
              }`}
            >
              <span>{item.icon}</span>
              <span className="flex-1">{item.label}</span>
              {item.badge && (
                <span className="rounded bg-card-border px-1.5 py-0.5 text-[10px]">{item.badge}</span>
              )}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-card-border p-3">
        <div className="rounded-xl border border-card-border bg-card p-3">
          <div className="text-xs text-muted">Account Risk</div>
          <div className="mt-1 text-lg font-semibold">Moderate</div>
          <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-card-border">
            <div className="h-full w-[48%] rounded-full bg-warning" />
          </div>
          <div className="mt-1 text-xs text-muted">48 / 100</div>
        </div>
      </div>
    </aside>
  );
}
