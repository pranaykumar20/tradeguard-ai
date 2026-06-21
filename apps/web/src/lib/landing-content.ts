export const LANDING_CTAS = {
  primaryHref: "/sign-up",
  primaryLabel: "Get started free",
  secondaryHref: "/sign-in",
  secondaryLabel: "Sign in",
  demoHref: "/sign-up",
  demoLabel: "Try the demo",
} as const;

export const LANDING_MOCK = {
  sectors: {
    Technology: 42.1,
    Communication: 18.4,
    Healthcare: 12.6,
    "Consumer Cyclical": 9.8,
    Financial: 7.2,
  },
  cashPct: 9.9,
  portfolioValue: 128_450,
  correlation: {
    NVDA: { NVDA: 1, META: 0.72, AAPL: 0.58, MSFT: 0.61 },
    META: { NVDA: 0.72, META: 1, AAPL: 0.54, MSFT: 0.49 },
    AAPL: { NVDA: 0.58, META: 0.54, AAPL: 1, MSFT: 0.67 },
    MSFT: { NVDA: 0.61, META: 0.49, AAPL: 0.67, MSFT: 1 },
  },
  alerts: [
    {
      severity: "high",
      title: "High Concentration Risk",
      detail: "Technology sector exposure is 42.1% (limit 30%).",
    },
    {
      severity: "medium",
      title: "NVDA Correlation Spike",
      detail: "NVDA–META correlation rose to 0.72 over the last 30 days.",
    },
    {
      severity: "info",
      title: "Upcoming Earnings",
      detail: "NVDA reports earnings Thursday — review position sizing.",
    },
  ],
  techPct: 42.1,
  techLimit: 30,
  riskScore: 72,
  riskLabel: "Moderate",
} as const;

export const PRICING_TIERS = [
  {
    name: "Beta",
    price: "$0",
    period: "during beta",
    description: "Full access while we refine the platform with early users.",
    highlighted: true,
    cta: "Get started free",
    features: [
      "Portfolio risk dashboard",
      "AI risk copilot chat",
      "Trade preview & guardrails",
      "Basic email alerts",
      "Demo portfolio included",
    ],
  },
  {
    name: "Pro",
    price: "$29",
    period: "/month",
    description: "For active traders who want deeper analytics and automation.",
    highlighted: false,
    cta: "Join waitlist",
    comingSoon: true,
    features: [
      "Everything in Beta",
      "Robinhood MCP connection",
      "Advanced risk metrics",
      "Strategy automation",
      "Priority support",
    ],
  },
  {
    name: "Team",
    price: "Custom",
    period: "",
    description: "For advisors and small funds managing multiple accounts.",
    highlighted: false,
    cta: "Contact us",
    comingSoon: true,
    features: [
      "Multi-user workspaces",
      "Shared risk policies",
      "Audit logs & exports",
      "API access",
      "Dedicated onboarding",
    ],
  },
] as const;

export const TRUST_ITEMS = [
  {
    icon: "🛡",
    title: "Risk engine has veto power",
    description:
      "The LLM explains and recommends — but hard-coded rules can BLOCK trades that breach your limits.",
  },
  {
    icon: "✓",
    title: "Manual approval by default",
    description:
      "Phase 1 is analysis-only. No live orders execute without your explicit approval.",
  },
  {
    icon: "🔒",
    title: "Your portfolio, your data",
    description:
      "Credentials are never stored in plain text. Auth via Clerk with JWT-scoped API access.",
  },
  {
    icon: "📋",
    title: "Full audit trail",
    description:
      "Every trade preview, AI recommendation, and alert is logged in your journal for review.",
  },
] as const;

export const FAQ_ITEMS = [
  {
    q: "Does TradeGuard execute trades automatically?",
    a: "No. TradeGuard is a risk manager, not an auto-trader. The AI analyzes and recommends; you approve every action. Automated execution requires explicit strategy setup and guardrails.",
  },
  {
    q: "How do I connect my Robinhood account?",
    a: "Open Account setup (/onboarding) and click Connect Robinhood. You'll sign in with Robinhood OAuth — no MCP URL to copy. After connecting, fund your separate Agentic account in Robinhood. During beta you can also explore with the demo portfolio.",
  },
  {
    q: "What happens when a trade is blocked?",
    a: "The risk engine returns a BLOCK verdict with specific reasons — sector limits, position size, daily loss caps, etc. The AI explains why and suggests alternatives.",
  },
  {
    q: "Is my financial data secure?",
    a: "API access uses Clerk JWT authentication. Portfolio data is scoped per user in PostgreSQL. We never share or sell your data.",
  },
  {
    q: "Can I use TradeGuard without Robinhood?",
    a: "Yes. Import or use the demo portfolio to access dashboards, AI chat, trade previews, and risk analytics without a brokerage connection.",
  },
  {
    q: "How much does it cost?",
    a: "TradeGuard is free during the beta period. Pro and Team tiers with advanced automation are coming soon — sign up now to lock in early access.",
  },
] as const;

export const FOOTER_LINKS = {
  product: [
    { label: "Product overview", href: "#product" },
    { label: "Features", href: "#features" },
    { label: "Pricing", href: "#pricing" },
    { label: "How it works", href: "#how-it-works" },
    { label: "FAQ", href: "#faq" },
  ],
  app: [
    { label: "Dashboard", href: "/dashboard" },
    { label: "AI Chat", href: "/chat" },
    { label: "Sign in", href: "/sign-in" },
    { label: "Sign up", href: "/sign-up" },
  ],
  resources: [
    { label: "Documentation", href: "https://github.com/pranayrao/tradeguard-ai/blob/main/README.md" },
    { label: "Deploy guide", href: "https://github.com/pranayrao/tradeguard-ai/blob/main/docs/DEPLOY.md" },
    { label: "Roadmap", href: "https://github.com/pranayrao/tradeguard-ai/blob/main/docs/PLAN.md" },
  ],
} as const;
