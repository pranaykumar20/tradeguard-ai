"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import { getAuthMe, type AuthUser } from "@/lib/api";
import { hasPermission, permissionForPath, type Permission } from "@/lib/permissions";

type PermissionsContextValue = {
  loading: boolean;
  user: AuthUser | null;
  permissions: string[];
  can: (permission: Permission) => boolean;
  isAdmin: boolean;
  refresh: () => Promise<void>;
};

const PermissionsContext = createContext<PermissionsContextValue | null>(null);

export function PermissionsProvider({ children }: { children: ReactNode }) {
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState<AuthUser | null>(null);
  const pathname = usePathname();
  const router = useRouter();

  const refresh = useCallback(async () => {
    try {
      const data = await getAuthMe();
      setUser(data.user);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const permissions = user?.permissions ?? [];

  const can = useCallback(
    (permission: Permission) => hasPermission(permissions, permission),
    [permissions],
  );

  const value = useMemo(
    () => ({
      loading,
      user,
      permissions,
      can,
      isAdmin: user?.role === "platform_admin",
      refresh,
    }),
    [loading, user, permissions, can, refresh],
  );

  useEffect(() => {
    if (loading || !pathname) return;
    const required = permissionForPath(pathname);
    if (!required) return;
    if (!hasPermission(permissions, required)) {
      router.replace("/access-denied");
    }
  }, [loading, pathname, permissions, router]);

  return <PermissionsContext.Provider value={value}>{children}</PermissionsContext.Provider>;
}

export function usePermissions() {
  const ctx = useContext(PermissionsContext);
  if (!ctx) {
    throw new Error("usePermissions must be used within PermissionsProvider");
  }
  return ctx;
}
