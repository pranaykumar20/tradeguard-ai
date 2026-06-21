import Link from "next/link";
import { LandingAuthRedirect } from "@/components/landing/LandingAuthRedirect";
import { LandingChatPreview } from "@/components/landing/LandingChatPreview";
import { LandingDashboardPreview } from "@/components/landing/LandingDashboardPreview";
import { LandingFAQ } from "@/components/landing/LandingFAQ";
import { LandingFooter } from "@/components/landing/LandingFooter";
import { LandingNav } from "@/components/landing/LandingNav";
import { LandingPricing } from "@/components/landing/LandingPricing";
import { LandingTrust } from "@/components/landing/LandingTrust";
import { LANDING_CTAS } from "@/lib/landing-content";

const FEATURES = [
  {
    icon: "▦",
    title: "Portfolio Risk Dashboard",
    description:
      "Real-time VaR, beta, sector exposure, and correlation heatmaps so you see concentration before it hurts.",
  },
  {
    icon: "✦",
    title: "AI Risk Copilot",
    description:
      "Ask natural-language questions about trades, tickers, and portfolio risk — with structured answers and citations.",
  },
  {
    icon: "✓",
    title: "Trade Guardrails",
    description:
      "Pre-trade checks against your rules: position limits, sector caps, and drawdown thresholds before you click buy.",
  },
  {
    icon: "⚑",
    title: "Smart Alerts",
    description:
      "Get notified when volatility spikes, correlations shift, or a position breaches your risk budget.",
  },
  {
    icon: "↗",
    title: "Stock Analyzer",
    description:
      "Deep-dive any ticker with ML signals, sentiment, and factor scores integrated into one view.",
  },
  {
    icon: "☰",
    title: "Reports & Journal",
    description:
      "Track decisions, export risk reports, and build an audit trail for every trade recommendation.",
  },
];

const STEPS = [
  {
    step: "01",
    title: "Connect your portfolio",
    description: "Link Robinhood or import holdings to build your risk profile in minutes.",
  },
  {
    step: "02",
    title: "Set your guardrails",
    description: "Define position limits, sector caps, and max drawdown rules that match your strategy.",
  },
  {
    step: "03",
    title: "Trade with confidence",
    description: "Every trade is scored by AI and validated against your rules before execution.",
  },
];

export function LandingPage() {
  return (
    <div className="min-h-screen">
      <LandingAuthRedirect />
      <LandingNav />

      {/* Hero */}
      <section className="relative overflow-hidden px-6 pb-20 pt-16 md:pb-28 md:pt-24">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_80%_50%_at_50%_-20%,rgba(38,228,196,0.15),transparent)]" />
        <div className="pointer-events-none absolute right-0 top-20 h-96 w-96 rounded-full bg-blue/5 blur-3xl" />

        <div className="relative mx-auto max-w-6xl">
          <div className="inline-flex items-center gap-2 rounded-full border border-teal/30 bg-teal/10 px-4 py-1.5 text-xs font-bold text-teal">
            <span className="h-1.5 w-1.5 rounded-full bg-teal animate-pulse" />
            AI-powered portfolio risk management
          </div>

          <h1 className="mt-6 max-w-3xl text-4xl font-extrabold leading-[1.1] tracking-tight md:text-6xl">
            Know your risk{" "}
            <span className="bg-gradient-to-r from-teal to-blue bg-clip-text text-transparent">
              before every trade
            </span>
          </h1>

          <p className="mt-6 max-w-2xl text-lg leading-relaxed text-muted md:text-xl">
            TradeGuard AI combines LLM orchestration, ML signals, and a code-based risk engine to
            protect your portfolio — not just analyze it.
          </p>

          <div className="mt-10 flex flex-wrap items-center gap-4">
            <Link
              href={LANDING_CTAS.primaryHref}
              className="rounded-[16px] bg-teal px-7 py-3.5 text-base font-bold text-[#041018] shadow-[0_0_40px_rgba(38,228,196,0.25)] transition hover:brightness-110"
            >
              {LANDING_CTAS.primaryLabel}
            </Link>
            <Link
              href={LANDING_CTAS.secondaryHref}
              className="rounded-[16px] border border-card-border px-7 py-3.5 text-base font-bold transition hover:bg-white/[0.04]"
            >
              {LANDING_CTAS.secondaryLabel}
            </Link>
          </div>

          <div className="mt-14 grid grid-cols-2 gap-6 md:grid-cols-4">
            {[
              { value: "12+", label: "Risk metrics tracked" },
              { value: "<2s", label: "Trade preview latency" },
              { value: "24/7", label: "Portfolio monitoring" },
              { value: "100%", label: "Rule-based guardrails" },
            ].map((stat) => (
              <div key={stat.label} className="tg-card !rounded-[18px] !p-4">
                <div className="text-2xl font-extrabold text-teal">{stat.value}</div>
                <div className="mt-1 text-xs font-semibold text-muted">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <LandingDashboardPreview />
      <LandingChatPreview />

      {/* Features */}
      <section id="features" className="px-6 py-20">
        <div className="mx-auto max-w-6xl">
          <div className="text-center">
            <h2 className="text-3xl font-extrabold md:text-4xl">
              Everything you need to trade smarter
            </h2>
            <p className="mx-auto mt-4 max-w-2xl text-muted">
              From real-time dashboards to AI-powered trade analysis — one platform for the full
              risk lifecycle.
            </p>
          </div>

          <div className="mt-14 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map((feature) => (
              <div
                key={feature.title}
                className="tg-card group transition hover:border-teal/30 hover:shadow-[0_0_30px_rgba(38,228,196,0.08)]"
              >
                <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-teal/10 text-lg text-teal transition group-hover:bg-teal/20">
                  {feature.icon}
                </span>
                <h3 className="mt-4 text-lg font-bold">{feature.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section id="how-it-works" className="border-y border-card-border/60 bg-[#0a1422]/50 px-6 py-20">
        <div className="mx-auto max-w-6xl">
          <div className="text-center">
            <h2 className="text-3xl font-extrabold md:text-4xl">Up and running in three steps</h2>
            <p className="mx-auto mt-4 max-w-xl text-muted">
              No complex setup. Connect, configure, and start trading with guardrails.
            </p>
          </div>

          <div className="mt-14 grid gap-8 md:grid-cols-3">
            {STEPS.map((item) => (
              <div key={item.step} className="relative">
                <div className="text-5xl font-extrabold text-teal/20">{item.step}</div>
                <h3 className="mt-2 text-xl font-bold">{item.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted">{item.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <LandingTrust />
      <LandingPricing />
      <LandingFAQ />

      {/* Final CTA */}
      <section className="px-6 py-20">
        <div className="mx-auto max-w-6xl">
          <div className="tg-card !rounded-[24px] bg-gradient-to-br from-teal/10 to-blue/5 text-center">
            <h2 className="text-3xl font-extrabold">Ready to trade with guardrails?</h2>
            <p className="mx-auto mt-4 max-w-lg text-muted">
              Join the beta free. Set up your portfolio, configure risk rules, and ask AI about
              every trade.
            </p>
            <div className="mt-8 flex flex-wrap items-center justify-center gap-4">
              <Link
                href={LANDING_CTAS.primaryHref}
                className="rounded-[16px] bg-teal px-7 py-3.5 text-base font-bold text-[#041018] transition hover:brightness-110"
              >
                {LANDING_CTAS.primaryLabel}
              </Link>
              <Link
                href={LANDING_CTAS.secondaryHref}
                className="rounded-[16px] border border-card-border px-7 py-3.5 text-base font-bold transition hover:bg-white/[0.04]"
              >
                {LANDING_CTAS.secondaryLabel}
              </Link>
            </div>
          </div>
        </div>
      </section>

      <LandingFooter />
    </div>
  );
}
