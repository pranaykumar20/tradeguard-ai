"use client";

import { useCallback, useEffect, useState } from "react";

export type AppSessionUser = {
  email: string;
  name: string;
};

export type AppSession =
  | { loading: true; signedIn: false; mode: "demo" | "clerk" | null; user: null }
  | { loading: false; signedIn: false; mode: "demo" | "clerk"; user: null }
  | { loading: false; signedIn: true; mode: "demo" | "clerk"; user: AppSessionUser };

export function useAppSession() {
  const [session, setSession] = useState<AppSession>({
    loading: true,
    signedIn: false,
    mode: null,
    user: null,
  });

  const refresh = useCallback(async () => {
    try {
      const res = await fetch("/auth/session", { cache: "no-store" });
      const data = (await res.json()) as {
        mode?: string;
        signedIn?: boolean;
        user?: AppSessionUser;
      };

      if (data.mode === "demo") {
        if (data.signedIn && data.user) {
          setSession({
            loading: false,
            signedIn: true,
            mode: "demo",
            user: data.user,
          });
        } else {
          setSession({
            loading: false,
            signedIn: false,
            mode: "demo",
            user: null,
          });
        }
        return;
      }

      setSession({
        loading: false,
        signedIn: false,
        mode: "clerk",
        user: null,
      });
    } catch {
      setSession({
        loading: false,
        signedIn: false,
        mode: "demo",
        user: null,
      });
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const signOutDemo = useCallback(async () => {
    await fetch("/auth/demo-logout", { method: "POST" });
    await refresh();
  }, [refresh]);

  return { session, refresh, signOutDemo };
}
