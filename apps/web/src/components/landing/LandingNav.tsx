"use client";

import Link from "next/link";
import { SignInButton, SignUpButton, useAuth } from "@clerk/nextjs";
import { useState } from "react";
import { useAppSession } from "@/hooks/useAppSession";
import { isClerkEnabled } from "@/lib/auth-config";
import { LANDING_CTAS } from "@/lib/landing-content";

const NAV_LINKS = [
  { href: "#product", label: "Product" },
  { href: "#features", label: "Features" },
  { href: "#how-it-works", label: "How it works" },
  { href: "#pricing", label: "Pricing" },
  { href: "#faq", label: "FAQ" },
];

function DemoNavActions({ compact = false }: { compact?: boolean }) {
  const { session } = useAppSession();

  if (session.loading) {
    return <span className="text-sm text-muted">…</span>;
  }

  if (session.signedIn) {
    return (
      <Link
        href="/dashboard"
        className={`rounded-[14px] bg-teal font-bold text-[#041018] transition hover:brightness-110 ${
          compact ? "block px-4 py-2.5 text-center text-sm" : "px-4 py-2 text-sm"
        }`}
      >
        Dashboard
      </Link>
    );
  }

  return (
    <div className={compact ? "space-y-2" : "flex items-center gap-3"}>
      <Link
        href={LANDING_CTAS.secondaryHref}
        className={`rounded-[14px] border border-card-border font-bold text-foreground transition hover:bg-white/[0.04] ${
          compact ? "block px-4 py-2.5 text-center text-sm" : "px-4 py-2 text-sm"
        }`}
      >
        {LANDING_CTAS.secondaryLabel}
      </Link>
      <Link
        href={LANDING_CTAS.primaryHref}
        className={`rounded-[14px] bg-teal font-bold text-[#041018] transition hover:brightness-110 ${
          compact ? "block px-4 py-2.5 text-center text-sm" : "px-4 py-2 text-sm"
        }`}
      >
        {LANDING_CTAS.primaryLabel}
      </Link>
    </div>
  );
}

function ClerkNavActions({ compact = false }: { compact?: boolean }) {
  const { isSignedIn, isLoaded } = useAuth();

  if (!isLoaded) {
    return <span className="text-sm text-muted">…</span>;
  }

  if (isSignedIn) {
    return (
      <Link
        href="/dashboard"
        className={`rounded-[14px] bg-teal font-bold text-[#041018] transition hover:brightness-110 ${
          compact ? "block px-4 py-2.5 text-center text-sm" : "px-4 py-2 text-sm"
        }`}
      >
        Dashboard
      </Link>
    );
  }

  return (
    <div className={compact ? "space-y-2" : "flex items-center gap-3"}>
      <SignInButton mode="redirect" forceRedirectUrl="/dashboard">
        <button
          type="button"
          className={`rounded-[14px] border border-card-border font-bold text-foreground transition hover:bg-white/[0.04] ${
            compact ? "w-full px-4 py-2.5 text-sm" : "px-4 py-2 text-sm"
          }`}
        >
          {LANDING_CTAS.secondaryLabel}
        </button>
      </SignInButton>
      <SignUpButton mode="redirect" forceRedirectUrl="/onboarding">
        <button
          type="button"
          className={`rounded-[14px] bg-teal font-bold text-[#041018] transition hover:brightness-110 ${
            compact ? "w-full px-4 py-2.5 text-sm" : "px-4 py-2 text-sm"
          }`}
        >
          {LANDING_CTAS.primaryLabel}
        </button>
      </SignUpButton>
    </div>
  );
}

function NavActions({ compact = false }: { compact?: boolean }) {
  return isClerkEnabled() ? (
    <ClerkNavActions compact={compact} />
  ) : (
    <DemoNavActions compact={compact} />
  );
}

export function LandingNav() {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 border-b border-card-border/60 bg-[#07111f]/80 backdrop-blur-xl">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <Link href="/" className="flex items-center gap-2 text-xl font-extrabold tracking-tight">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-blue/15 text-lg text-blue">
            🛡
          </span>
          <span>
            TradeGuard <span className="text-teal">AI</span>
          </span>
        </Link>

        <nav className="hidden items-center gap-7 text-sm font-semibold text-muted md:flex">
          {NAV_LINKS.map((link) => (
            <a key={link.href} href={link.href} className="transition hover:text-foreground">
              {link.label}
            </a>
          ))}
        </nav>

        <div className="hidden items-center gap-3 md:flex">
          <NavActions />
        </div>

        <button
          type="button"
          className="rounded-lg border border-card-border px-3 py-2 text-sm md:hidden"
          aria-label="Toggle menu"
          aria-expanded={mobileOpen}
          onClick={() => setMobileOpen((v) => !v)}
        >
          {mobileOpen ? "✕" : "☰"}
        </button>
      </div>

      {mobileOpen && (
        <div className="border-t border-card-border/60 px-6 py-4 md:hidden">
          <nav className="space-y-1">
            {NAV_LINKS.map((link) => (
              <a
                key={link.href}
                href={link.href}
                onClick={() => setMobileOpen(false)}
                className="block rounded-[12px] px-3 py-2.5 text-sm font-semibold text-muted hover:bg-white/[0.04] hover:text-foreground"
              >
                {link.label}
              </a>
            ))}
          </nav>
          <div className="mt-4 border-t border-card-border/60 pt-4">
            <NavActions compact />
          </div>
        </div>
      )}
    </header>
  );
}
