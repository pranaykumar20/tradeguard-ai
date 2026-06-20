"use client";

import { ClerkProvider, SignInButton, UserButton, useAuth } from "@clerk/nextjs";
import { useEffect, type ReactNode } from "react";
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
  if (!clerkKey) {
    return <>{children}</>;
  }

  return (
    <ClerkProvider publishableKey={clerkKey}>
      <ClerkTokenBridge>{children}</ClerkTokenBridge>
    </ClerkProvider>
  );
}

function ClerkAuthControls() {
  const { isSignedIn, isLoaded } = useAuth();

  if (!isLoaded) {
    return (
      <div className="mt-4 rounded-[14px] border border-card-border px-3 py-2 text-xs text-muted">
        Loading auth…
      </div>
    );
  }

  if (isSignedIn) {
    return (
      <div className="mt-4 flex items-center justify-center">
        <UserButton />
      </div>
    );
  }

  return (
    <div className="mt-4">
      <SignInButton mode="modal">
        <button
          type="button"
          className="w-full rounded-[14px] border border-teal/40 px-3 py-2 text-xs font-bold text-teal hover:bg-teal/10"
        >
          Sign in
        </button>
      </SignInButton>
    </div>
  );
}

export function AuthControls() {
  if (!clerkKey) {
    return (
      <div className="mt-4 rounded-[14px] border border-card-border px-3 py-2 text-xs text-muted">
        Demo mode · auth disabled
      </div>
    );
  }

  return <ClerkAuthControls />;
}
