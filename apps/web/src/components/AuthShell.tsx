"use client";

import { ClerkProvider, UserButton, useAuth } from "@clerk/nextjs";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";
import { PermissionsProvider } from "@/components/PermissionsProvider";
import { useAppSession } from "@/hooks/useAppSession";
import { isClerkEnabled } from "@/lib/auth-config";
import { setAuthTokenGetter } from "@/lib/api";

const clerkKey = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY;

function ClerkTokenBridge({ children }: { children: ReactNode }) {
  const { getToken, isLoaded } = useAuth();

  useEffect(() => {
    if (!isLoaded) return;
    setAuthTokenGetter(async () => {
      try {
        return await getToken();
      } catch {
        return null;
      }
    });
    return () => setAuthTokenGetter(null);
  }, [getToken, isLoaded]);

  return <>{children}</>;
}

export function AuthShell({ children }: { children: ReactNode }) {
  const inner = <PermissionsProvider>{children}</PermissionsProvider>;

  if (!clerkKey) {
    return inner;
  }

  return (
    <ClerkProvider
      publishableKey={clerkKey}
      signInUrl="/sign-in"
      signUpUrl="/sign-up"
      signInFallbackRedirectUrl="/dashboard"
      signUpFallbackRedirectUrl="/onboarding"
    >
      <ClerkTokenBridge>{inner}</ClerkTokenBridge>
    </ClerkProvider>
  );
}

function ClerkAuthControls({ embedded = false }: { embedded?: boolean }) {
  const { isSignedIn, isLoaded } = useAuth();
  const wrap = embedded ? "" : "mt-4";

  if (!isLoaded) {
    return (
      <div className={`${wrap} rounded-[14px] border border-card-border px-3 py-2 text-xs text-muted`.trim()}>
        Loading auth…
      </div>
    );
  }

  if (isSignedIn) {
    return (
      <div className={`${wrap} flex items-center justify-center`.trim()}>
        <UserButton
          appearance={{
            elements: {
              avatarBox: "h-9 w-9",
            },
          }}
        />
      </div>
    );
  }

  return (
    <div className={`${wrap} space-y-2`.trim()}>
      <Link
        href="/sign-in"
        className="block w-full rounded-[14px] border border-teal/40 px-3 py-2 text-center text-xs font-bold text-teal hover:bg-teal/10"
      >
        Sign in
      </Link>
    </div>
  );
}

function DemoAuthControls({ embedded = false }: { embedded?: boolean }) {
  const router = useRouter();
  const { session, signOutDemo } = useAppSession();
  const wrap = embedded ? "" : "mt-4";

  if (session.loading) {
    return (
      <div className={`${wrap} rounded-[14px] border border-card-border px-3 py-2 text-xs text-muted`.trim()}>
        Loading auth…
      </div>
    );
  }

  if (session.signedIn && session.user) {
    return (
      <div className={`${wrap} space-y-2 rounded-[14px] border border-card-border p-3`.trim()}>
        <div className="truncate text-xs font-bold">{session.user.name}</div>
        <div className="truncate text-[11px] text-muted">{session.user.email}</div>
        <button
          type="button"
          onClick={() => {
            void signOutDemo().then(() => {
              router.push("/sign-in");
              router.refresh();
            });
          }}
          className="w-full rounded-[12px] border border-card-border px-2 py-1.5 text-[11px] font-bold text-muted hover:bg-white/[0.04] hover:text-foreground"
        >
          Sign out
        </button>
      </div>
    );
  }

  return (
    <div className={`${wrap} space-y-2`.trim()}>
      <Link
        href="/sign-in"
        className="block w-full rounded-[14px] border border-teal/40 px-3 py-2 text-center text-xs font-bold text-teal hover:bg-teal/10"
      >
        Sign in
      </Link>
    </div>
  );
}

export function AuthControls({ embedded = false }: { embedded?: boolean }) {
  if (isClerkEnabled()) {
    return <ClerkAuthControls embedded={embedded} />;
  }

  return <DemoAuthControls embedded={embedded} />;
}
