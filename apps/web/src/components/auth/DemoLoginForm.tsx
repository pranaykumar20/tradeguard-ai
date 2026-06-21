"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { DEMO_CREDENTIALS } from "@/lib/auth-config";

export function DemoLoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirectUrl = searchParams.get("redirect_url") || "/dashboard";

  const [email, setEmail] = useState<string>(DEMO_CREDENTIALS.email);
  const [password, setPassword] = useState<string>(DEMO_CREDENTIALS.password);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const res = await fetch("/auth/demo-login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      const data = (await res.json()) as { error?: string };
      if (!res.ok) {
        setError(data.error ?? "Sign in failed");
        return;
      }

      router.push(redirectUrl);
      router.refresh();
    } catch {
      setError("Unable to sign in. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="w-full">
      <div className="tg-card !rounded-[24px]">
        <h1 className="text-2xl font-extrabold">Welcome back</h1>
        <p className="mt-2 text-sm text-muted">Sign in to your TradeGuard account</p>

        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          <label className="block">
            <span className="tg-label">Email</span>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              required
              className="mt-1.5 w-full rounded-[14px] border border-card-border bg-[#10233a] px-4 py-3 text-sm outline-none ring-teal/40 focus:ring-2"
            />
          </label>

          <label className="block">
            <span className="tg-label">Password</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
              className="mt-1.5 w-full rounded-[14px] border border-card-border bg-[#10233a] px-4 py-3 text-sm outline-none ring-teal/40 focus:ring-2"
            />
          </label>

          {error && (
            <p className="rounded-[12px] border border-red/30 bg-red/10 px-3 py-2 text-sm text-red">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-[14px] bg-teal py-3 text-sm font-bold text-[#041018] transition hover:brightness-110 disabled:opacity-60"
          >
            {loading ? "Signing in…" : "Sign in"}
          </button>
        </form>

        <p className="mt-5 text-center text-xs text-muted">
          Demo credentials:{" "}
          <span className="font-mono text-foreground">{DEMO_CREDENTIALS.email}</span> /{" "}
          <span className="font-mono text-foreground">{DEMO_CREDENTIALS.password}</span>
        </p>

        <p className="mt-4 text-center text-sm text-muted">
          No account?{" "}
          <Link href="/sign-up" className="font-bold text-teal hover:text-blue">
            Create one
          </Link>
        </p>
      </div>
    </div>
  );
}
