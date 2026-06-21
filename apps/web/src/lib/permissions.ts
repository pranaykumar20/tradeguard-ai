/** Permission keys — must match apps/api/app/core/permissions.py */

export const PERMISSIONS = {
  DASHBOARD: "dashboard:view",
  PORTFOLIO: "portfolio:view",
  CHAT: "chat:use",
  MONITORING: "monitoring:view",
  ANALYSIS: "analysis:use",
  JOURNAL: "journal:view",
  APPROVALS: "approvals:manage",
  ONBOARDING: "onboarding:use",
  STRATEGIES: "strategies:use",
  OBSERVABILITY: "observability:view",
  AUTOMATION: "automation:use",
  VALIDATION: "validation:view",
  ADMIN: "admin:manage",
} as const;

export type Permission = (typeof PERMISSIONS)[keyof typeof PERMISSIONS];

export const ROLE_LABELS: Record<string, string> = {
  platform_admin: "Platform Admin",
  trader: "Trader",
  analyst: "Analyst",
  viewer: "Viewer",
  user: "Standard User",
};

export type NavItem = {
  id: string;
  href: string;
  label: string;
  icon: string;
  permission: Permission;
  activePrefix?: string;
  badge?: string;
};

/** Sidebar nav items gated by permission. */
export const APP_NAV: NavItem[] = [
  { id: "overview", href: "/dashboard", label: "Overview", icon: "▦", permission: PERMISSIONS.DASHBOARD },
  { id: "portfolio", href: "/portfolio", label: "Portfolio", icon: "◫", permission: PERMISSIONS.PORTFOLIO },
  {
    id: "risk-analytics",
    href: "/dashboard#risk-analytics",
    label: "Risk Analytics",
    icon: "◉",
    permission: PERMISSIONS.DASHBOARD,
    activePrefix: "/dashboard",
  },
  { id: "chat", href: "/chat", label: "AI Insights", icon: "✦", permission: PERMISSIONS.CHAT },
  { id: "monitoring", href: "/monitoring", label: "Alerts", icon: "⚑", permission: PERMISSIONS.MONITORING },
  { id: "analysis", href: "/analysis", label: "Stock Analyzer", icon: "↗", permission: PERMISSIONS.ANALYSIS },
  { id: "journal", href: "/journal", label: "Reports", icon: "☰", permission: PERMISSIONS.JOURNAL },
  { id: "approvals", href: "/approvals", label: "Trade Approval", icon: "✓", permission: PERMISSIONS.APPROVALS },
  {
    id: "onboarding",
    href: "/onboarding",
    label: "Onboarding",
    icon: "◎",
    permission: PERMISSIONS.ONBOARDING,
    badge: "new",
  },
  { id: "strategies", href: "/strategies", label: "Strategies", icon: "⚡", permission: PERMISSIONS.STRATEGIES },
  {
    id: "observability",
    href: "/observability",
    label: "Observability",
    icon: "◌",
    permission: PERMISSIONS.OBSERVABILITY,
  },
  { id: "automation", href: "/automation", label: "Automation", icon: "⟳", permission: PERMISSIONS.AUTOMATION },
  { id: "validation", href: "/validation", label: "Validation", icon: "◎", permission: PERMISSIONS.VALIDATION },
  { id: "admin", href: "/admin/users", label: "Admin", icon: "⚙", permission: PERMISSIONS.ADMIN },
];

/** Route prefix → required permission (first match wins). */
export const ROUTE_PERMISSIONS: { prefix: string; permission: Permission }[] = [
  { prefix: "/admin", permission: PERMISSIONS.ADMIN },
  { prefix: "/dashboard", permission: PERMISSIONS.DASHBOARD },
  { prefix: "/portfolio", permission: PERMISSIONS.PORTFOLIO },
  { prefix: "/chat", permission: PERMISSIONS.CHAT },
  { prefix: "/monitoring", permission: PERMISSIONS.MONITORING },
  { prefix: "/analysis", permission: PERMISSIONS.ANALYSIS },
  { prefix: "/journal", permission: PERMISSIONS.JOURNAL },
  { prefix: "/approvals", permission: PERMISSIONS.APPROVALS },
  { prefix: "/onboarding", permission: PERMISSIONS.ONBOARDING },
  { prefix: "/strategies", permission: PERMISSIONS.STRATEGIES },
  { prefix: "/observability", permission: PERMISSIONS.OBSERVABILITY },
  { prefix: "/automation", permission: PERMISSIONS.AUTOMATION },
  { prefix: "/validation", permission: PERMISSIONS.VALIDATION },
];

export function permissionForPath(pathname: string): Permission | null {
  for (const entry of ROUTE_PERMISSIONS) {
    if (pathname === entry.prefix || pathname.startsWith(`${entry.prefix}/`)) {
      return entry.permission;
    }
  }
  return null;
}

export function hasPermission(userPermissions: string[] | undefined, permission: Permission): boolean {
  if (!userPermissions) return true;
  return userPermissions.includes(permission);
}
