"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { useClerk, useUser } from "@clerk/nextjs";
import { usePermissions } from "@/components/PermissionsProvider";
import { useAppSession } from "@/hooks/useAppSession";
import { isClerkEnabled } from "@/lib/auth-config";
import { ROLE_LABELS } from "@/lib/permissions";

function userInitials(name: string, email: string) {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length >= 2) {
    return `${parts[0][0] ?? ""}${parts[parts.length - 1][0] ?? ""}`.toUpperCase();
  }
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return email.slice(0, 2).toUpperCase();
}

function UserAvatar({ name, email, size = "md" }: { name: string; email: string; size?: "md" | "sm" }) {
  const dim = size === "sm" ? "h-8 w-8 text-xs" : "h-9 w-9 text-sm";
  return (
    <span
      className={`flex ${dim} shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-teal/90 to-blue/80 font-bold text-[#041018] shadow-inner`}
    >
      {userInitials(name, email)}
    </span>
  );
}

function MenuItem({
  href,
  onClick,
  icon,
  label,
  tone = "default",
}: {
  href?: string;
  onClick?: () => void;
  icon: string;
  label: string;
  tone?: "default" | "danger";
}) {
  const className = `flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm transition ${
    tone === "danger"
      ? "text-red hover:bg-red/10"
      : "text-foreground/90 hover:bg-white/[0.06]"
  }`;

  if (href) {
    return (
      <Link href={href} onClick={onClick} className={className}>
        <span className="w-4 text-center text-[13px] opacity-70">{icon}</span>
        {label}
      </Link>
    );
  }

  return (
    <button type="button" onClick={onClick} className={className}>
      <span className="w-4 text-center text-[13px] opacity-70">{icon}</span>
      {label}
    </button>
  );
}

function SidebarUserMenuSkeleton() {
  return (
    <div className="flex items-center gap-3 rounded-xl px-2.5 py-2.5">
      <div className="h-9 w-9 shrink-0 animate-pulse rounded-full bg-white/10" />
      <div className="min-w-0 flex-1 space-y-1.5">
        <div className="h-3.5 w-24 animate-pulse rounded bg-white/10" />
        <div className="h-3 w-32 animate-pulse rounded bg-white/10" />
      </div>
    </div>
  );
}

function SignedOutPrompt() {
  return (
    <Link
      href="/sign-in"
      className="flex items-center gap-3 rounded-xl border border-card-border px-3 py-2.5 text-sm font-semibold text-foreground transition hover:border-teal/30 hover:bg-white/[0.04]"
    >
      <span className="flex h-9 w-9 items-center justify-center rounded-full border border-card-border text-muted">
        →
      </span>
      <span>Sign in to TradeGuard</span>
    </Link>
  );
}

function DemoUserMenu() {
  const router = useRouter();
  const { user, loading, isAdmin } = usePermissions();
  const { session, signOutDemo } = useAppSession();
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  const close = useCallback(() => setOpen(false), []);

  useEffect(() => {
    if (!open) return;
    function onPointerDown(e: MouseEvent) {
      if (!rootRef.current?.contains(e.target as Node)) close();
    }
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") close();
    }
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open, close]);

  if (loading || session.loading) return <SidebarUserMenuSkeleton />;

  if (!session.signedIn || !session.user) return <SignedOutPrompt />;

  const displayName = user?.display_name || session.user.name || "User";
  const email = user?.email || session.user.email;
  const roleLabel = user?.role ? (ROLE_LABELS[user.role] ?? user.role) : "Member";

  async function handleSignOut() {
    close();
    await signOutDemo();
    router.push("/sign-in");
    router.refresh();
  }

  return (
    <div ref={rootRef} className="relative">
      {open && (
        <div className="absolute bottom-full left-0 right-0 z-50 mb-2 overflow-hidden rounded-2xl border border-white/10 bg-[#0d1b2d] shadow-[0_-8px_40px_rgba(0,0,0,0.45)]">
          <div className="border-b border-white/8 px-4 py-3.5">
            <div className="flex items-center gap-3">
              <UserAvatar name={displayName} email={email} />
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-bold">{displayName}</p>
                <p className="truncate text-xs text-muted">{email}</p>
              </div>
            </div>
            <span className="mt-2.5 inline-flex rounded-full border border-teal/25 bg-teal/10 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-teal">
              {roleLabel}
            </span>
          </div>

          <div className="p-1.5">
            <MenuItem href="/onboarding" icon="◎" label="Account setup" onClick={close} />
            {isAdmin ? (
              <MenuItem href="/admin/users" icon="⚙" label="Manage users" onClick={close} />
            ) : null}
            <MenuItem href="/onboarding" icon="🛡" label="Risk profile" onClick={close} />
          </div>

          <div className="border-t border-white/8 p-1.5">
            <MenuItem icon="↗" label="Sign out" tone="danger" onClick={() => void handleSignOut()} />
          </div>
        </div>
      )}

      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-haspopup="menu"
        className={`flex w-full items-center gap-3 rounded-xl px-2.5 py-2.5 text-left transition ${
          open ? "bg-white/[0.08]" : "hover:bg-white/[0.06]"
        }`}
      >
        <UserAvatar name={displayName} email={email} />
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold leading-tight">{displayName}</p>
          <p className="truncate text-xs text-muted">{roleLabel}</p>
        </div>
        <svg
          viewBox="0 0 20 20"
          fill="currentColor"
          className={`h-4 w-4 shrink-0 text-muted transition ${open ? "rotate-180" : ""}`}
          aria-hidden
        >
          <path
            fillRule="evenodd"
            d="M5.23 7.21a.75.75 0 011.06.02L10 10.94l3.71-3.71a.75.75 0 111.06 1.06l-4.24 4.25a.75.75 0 01-1.06 0L5.21 8.29a.75.75 0 01.02-1.08z"
            clipRule="evenodd"
          />
        </svg>
      </button>
    </div>
  );
}

function ClerkUserMenu() {
  const router = useRouter();
  const { user: clerkUser, isLoaded } = useUser();
  const { signOut } = useClerk();
  const { user, loading, isAdmin } = usePermissions();
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  const close = useCallback(() => setOpen(false), []);

  useEffect(() => {
    if (!open) return;
    function onPointerDown(e: MouseEvent) {
      if (!rootRef.current?.contains(e.target as Node)) close();
    }
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") close();
    }
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open, close]);

  if (!isLoaded || loading) return <SidebarUserMenuSkeleton />;

  if (!clerkUser) return <SignedOutPrompt />;

  const displayName =
    user?.display_name ||
    clerkUser.fullName ||
    clerkUser.primaryEmailAddress?.emailAddress?.split("@")[0] ||
    "User";
  const email = user?.email || clerkUser.primaryEmailAddress?.emailAddress || "";
  const roleLabel = user?.role ? (ROLE_LABELS[user.role] ?? user.role) : "Member";

  async function handleSignOut() {
    close();
    await signOut({ redirectUrl: "/sign-in" });
    router.refresh();
  }

  return (
    <div ref={rootRef} className="relative">
      {open && (
        <div className="absolute bottom-full left-0 right-0 z-50 mb-2 overflow-hidden rounded-2xl border border-white/10 bg-[#0d1b2d] shadow-[0_-8px_40px_rgba(0,0,0,0.45)]">
          <div className="border-b border-white/8 px-4 py-3.5">
            <div className="flex items-center gap-3">
              <UserAvatar name={displayName} email={email} />
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-bold">{displayName}</p>
                <p className="truncate text-xs text-muted">{email}</p>
              </div>
            </div>
            <span className="mt-2.5 inline-flex rounded-full border border-teal/25 bg-teal/10 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-teal">
              {roleLabel}
            </span>
          </div>

          <div className="p-1.5">
            <MenuItem href="/onboarding" icon="◎" label="Account setup" onClick={close} />
            {isAdmin ? (
              <MenuItem href="/admin/users" icon="⚙" label="Manage users" onClick={close} />
            ) : null}
            <MenuItem href="/onboarding" icon="🛡" label="Risk profile" onClick={close} />
          </div>

          <div className="border-t border-white/8 p-1.5">
            <MenuItem icon="↗" label="Sign out" tone="danger" onClick={() => void handleSignOut()} />
          </div>
        </div>
      )}

      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-haspopup="menu"
        className={`flex w-full items-center gap-3 rounded-xl px-2.5 py-2.5 text-left transition ${
          open ? "bg-white/[0.08]" : "hover:bg-white/[0.06]"
        }`}
      >
        <UserAvatar name={displayName} email={email} />
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold leading-tight">{displayName}</p>
          <p className="truncate text-xs text-muted">{roleLabel}</p>
        </div>
        <svg
          viewBox="0 0 20 20"
          fill="currentColor"
          className={`h-4 w-4 shrink-0 text-muted transition ${open ? "rotate-180" : ""}`}
          aria-hidden
        >
          <path
            fillRule="evenodd"
            d="M5.23 7.21a.75.75 0 011.06.02L10 10.94l3.71-3.71a.75.75 0 111.06 1.06l-4.24 4.25a.75.75 0 01-1.06 0L5.21 8.29a.75.75 0 01.02-1.08z"
            clipRule="evenodd"
          />
        </svg>
      </button>
    </div>
  );
}

function ClerkUserMenuGate() {
  if (!isClerkEnabled()) return <DemoUserMenu />;
  return <ClerkUserMenu />;
}

export function SidebarUserMenu() {
  return <ClerkUserMenuGate />;
}
