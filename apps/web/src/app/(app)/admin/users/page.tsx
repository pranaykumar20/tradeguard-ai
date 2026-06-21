"use client";

import { useEffect, useState } from "react";
import { AppMain } from "@/components/layout/AppMain";
import { usePermissions } from "@/components/PermissionsProvider";
import { PageHeader } from "@/components/ui/Card";
import {
  getAdminPermissionCatalog,
  listAdminUsers,
  updateAdminUser,
  type AdminUser,
} from "@/lib/api";
import { PERMISSIONS, ROLE_LABELS } from "@/lib/permissions";

const ROLES = Object.keys(ROLE_LABELS);

export default function AdminUsersPage() {
  const { isAdmin, refresh: refreshSession } = usePermissions();
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [catalog, setCatalog] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [savingId, setSavingId] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError("");
    try {
      const [usersRes, catalogRes] = await Promise.all([
        listAdminUsers(),
        getAdminPermissionCatalog(),
      ]);
      setUsers(usersRes.users);
      setCatalog(catalogRes.permissions);
    } catch {
      setError("Unable to load users. Admin access required.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (isAdmin) void load();
    else setLoading(false);
  }, [isAdmin]);

  async function handleRoleChange(userId: string, role: string) {
    setSavingId(userId);
    try {
      const updated = await updateAdminUser(userId, { role: role as AdminUser["role"] });
      setUsers((prev) => prev.map((u) => (u.id === userId ? { ...u, ...updated } : u)));
      await refreshSession();
    } catch {
      setError("Failed to update user role.");
    } finally {
      setSavingId(null);
    }
  }

  async function handleToggleActive(user: AdminUser) {
    setSavingId(user.id);
    try {
      const updated = await updateAdminUser(user.id, { is_active: !user.is_active });
      setUsers((prev) => prev.map((u) => (u.id === user.id ? { ...u, ...updated } : u)));
    } catch {
      setError("Failed to update account status.");
    } finally {
      setSavingId(null);
    }
  }

  async function handlePermissionToggle(user: AdminUser, permission: string, enabled: boolean) {
    setSavingId(user.id);
    try {
      const base = new Set(user.custom_permissions ?? user.effective_permissions);
      if (enabled) base.add(permission);
      else base.delete(permission);
      const updated = await updateAdminUser(user.id, {
        permissions: Array.from(base),
      });
      setUsers((prev) => prev.map((u) => (u.id === user.id ? { ...u, ...updated } : u)));
      await refreshSession();
    } catch {
      setError("Failed to update permissions.");
    } finally {
      setSavingId(null);
    }
  }

  return (
    <AppMain>
        <PageHeader
          title="Platform Admin"
          subtitle="Manage user roles and feature access"
        />

        {!isAdmin && !loading && (
          <div className="tg-card mt-6 text-sm text-orange">
            You need platform admin access to manage users.
          </div>
        )}

        {error && (
          <div className="tg-card mt-6 border-red/30 text-sm text-red">{error}</div>
        )}

        {loading ? (
          <p className="mt-8 text-muted">Loading users…</p>
        ) : isAdmin ? (
          <div className="mt-6 space-y-4">
            {users.length === 0 ? (
              <div className="tg-card text-sm text-muted">
                No users yet. Users appear here after their first sign-in.
              </div>
            ) : (
              users.map((user) => (
                <div key={user.id} className="tg-card !rounded-[20px]">
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div>
                      <div className="font-bold">{user.display_name || user.email || user.id}</div>
                      <div className="text-sm text-muted">{user.email || "—"}</div>
                      <div className="mt-1 text-xs text-muted">
                        Role: {user.role_label} · {user.effective_permissions.length} permissions
                      </div>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      <select
                        value={user.role}
                        disabled={savingId === user.id}
                        onChange={(e) => void handleRoleChange(user.id, e.target.value)}
                        className="rounded-[12px] border border-card-border bg-[#10233a] px-3 py-2 text-sm"
                      >
                        {ROLES.map((role) => (
                          <option key={role} value={role}>
                            {ROLE_LABELS[role]}
                          </option>
                        ))}
                      </select>
                      <button
                        type="button"
                        disabled={savingId === user.id}
                        onClick={() => void handleToggleActive(user)}
                        className={`rounded-[12px] border px-3 py-2 text-xs font-bold ${
                          user.is_active
                            ? "border-green/30 text-green hover:bg-green/10"
                            : "border-red/30 text-red hover:bg-red/10"
                        }`}
                      >
                        {user.is_active ? "Active" : "Disabled"}
                      </button>
                    </div>
                  </div>

                  {user.role !== "platform_admin" && (
                    <div className="mt-4 border-t border-card-border pt-4">
                      <div className="text-xs font-bold uppercase tracking-wide text-muted">
                        Custom permissions
                      </div>
                      <div className="mt-3 flex flex-wrap gap-2">
                        {catalog.map((perm) => {
                          const enabled = user.effective_permissions.includes(perm);
                          return (
                            <button
                              key={perm}
                              type="button"
                              disabled={savingId === user.id || perm === PERMISSIONS.ADMIN}
                              onClick={() => void handlePermissionToggle(user, perm, !enabled)}
                              className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold transition ${
                                enabled
                                  ? "border-teal/40 bg-teal/10 text-teal"
                                  : "border-card-border text-muted hover:border-white/20"
                              }`}
                            >
                              {perm}
                            </button>
                          );
                        })}
                      </div>
                      <p className="mt-2 text-[11px] text-muted">
                        Toggle individual permissions or change role for preset bundles.
                      </p>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        ) : null}
      </AppMain>
  );
}
