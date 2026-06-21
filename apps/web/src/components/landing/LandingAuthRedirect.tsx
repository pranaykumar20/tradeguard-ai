"use client";

import { useAuth } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAppSession } from "@/hooks/useAppSession";
import { isClerkEnabled } from "@/lib/auth-config";

function ClerkLandingRedirect() {
  const router = useRouter();
  const { isSignedIn, isLoaded } = useAuth();

  useEffect(() => {
    if (isLoaded && isSignedIn) {
      router.replace("/dashboard");
    }
  }, [isLoaded, isSignedIn, router]);

  return null;
}

function DemoLandingRedirect() {
  const router = useRouter();
  const { session } = useAppSession();

  useEffect(() => {
    if (!session.loading && session.signedIn) {
      router.replace("/dashboard");
    }
  }, [router, session.loading, session.signedIn]);

  return null;
}

/** Sends signed-in users straight to the dashboard. */
export function LandingAuthRedirect() {
  return isClerkEnabled() ? <ClerkLandingRedirect /> : <DemoLandingRedirect />;
}
