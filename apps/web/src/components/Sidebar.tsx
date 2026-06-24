"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { AccountRiskWidget } from "@/components/AccountRiskWidget";
import { SidebarUserMenu } from "@/components/layout/SidebarUserMenu";
import { useSidebar } from "@/components/layout/SidebarContext";
import { usePermissions } from "@/components/PermissionsProvider";
import { PushInboxBell } from "@/components/PushInboxBell";
import { APP_NAV, type NavItem } from "@/lib/permissions";

const SIDEBAR_WIDTH = "w-[280px]";

/** Left padding on main content to clear the fixed desktop sidebar. */
export const SIDEBAR_WIDTH_CLASS = "lg:pl-[280px]";

function NavLink({
  item,
  active,
  onNavigate,
}: {
  item: NavItem;
  active: boolean;
  onNavigate: () => void;
}) {
  return (
    <Link
      href={item.href}
      onClick={onNavigate}
      className={`flex items-center gap-3 rounded-[14px] px-3 py-2.5 text-sm font-bold transition ${
        active
          ? "bg-[linear-gradient(90deg,rgba(38,228,196,0.16),rgba(85,185,255,0.08))] text-foreground"
          : "text-muted hover:bg-white/[0.04] hover:text-foreground"
      }`}
    >
      <span className="flex h-5 w-5 shrink-0 items-center justify-center text-[13px] leading-none">
        {item.icon}
      </span>
      <span className="min-w-0 flex-1 leading-snug">{item.label}</span>
      {item.badge ? (
        <span className="shrink-0 rounded bg-[#182a42] px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-muted">
          {item.badge}
        </span>
      ) : null}
    </Link>
  );
}

export function Sidebar() {
  const pathname = usePathname();
  const { loading, can } = usePermissions();
  const { mobileOpen, closeMobile } = useSidebar();

  const visibleNav = loading
    ? APP_NAV.filter((item) => ["/dashboard", "/portfolio", "/chat"].includes(item.href))
    : APP_NAV.filter((item) => can(item.permission));

  function isActive(item: NavItem) {
    const hrefPath = item.href.split("#")[0];
    const prefix = item.activePrefix ?? hrefPath;
    return pathname === prefix || pathname.startsWith(`${prefix}/`);
  }

  return (
    <aside
      className={`fixed inset-y-0 left-0 z-50 flex h-dvh max-h-dvh ${SIDEBAR_WIDTH} shrink-0 flex-col border-r border-card-border bg-[#0a1422]/98 transition-transform duration-200 ease-out lg:translate-x-0 ${
        mobileOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
      }`}
    >
      {/* Brand */}
      <div className="shrink-0 border-b border-card-border/50 px-4 pb-4 pt-5">
        <div className="flex items-center justify-between gap-2">
          <Link
            href="/dashboard"
            onClick={closeMobile}
            className="flex min-w-0 flex-1 items-center gap-2.5"
          >
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-blue/15 text-lg text-blue">
              🛡
            </span>
            <span className="truncate text-xl font-extrabold leading-tight tracking-tight">
              TradeGuard <span className="text-teal">AI</span>
            </span>
          </Link>
          <button
            type="button"
            aria-label="Close menu"
            onClick={closeMobile}
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-card-border text-sm text-muted lg:hidden"
          >
            ✕
          </button>
        </div>
        <p className="tg-sub mt-2 pl-[46px]">Portfolio Risk Platform</p>
      </div>

      {/* Scrollable nav */}
      <nav className="tg-scroll min-h-0 flex-1 space-y-0.5 overflow-y-auto px-3 py-3">
        {visibleNav.map((item) => (
          <NavLink
            key={item.id}
            item={item}
            active={isActive(item)}
            onNavigate={closeMobile}
          />
        ))}
      </nav>

      {/* Footer — risk snapshot + user account */}
      <div className="shrink-0 space-y-3 border-t border-card-border/60 px-3 py-3">
        <PushInboxBell />
        <AccountRiskWidget compact />
        <SidebarUserMenu />
      </div>
    </aside>
  );
}
