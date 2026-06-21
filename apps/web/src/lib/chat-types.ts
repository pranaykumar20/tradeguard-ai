export type FactorSeverity = "high" | "medium" | "low" | "positive";

export type ChatFactor = {
  icon: string;
  title: string;
  detail: string;
  severity: FactorSeverity;
};

export type ChatMetric = {
  label: string;
  value: string;
  highlight?: boolean;
};

export type ChatScoreBar = {
  label: string;
  value: number;
  max: number;
};

export type ChatHeadline = {
  title: string;
  source?: string;
  summary?: string;
  url?: string;
  sentiment?: number | null;
};

export type ChatQuote = {
  ticker: string;
  last_price?: number | null;
  change_pct?: number | null;
  volume?: number | null;
  provider?: string | null;
  live?: boolean | null;
};

export type ChatTradePreview = {
  ticker: string;
  side: string;
  quantity: number;
  limit_price: number;
  order_value: number;
  verdict: string;
};

export type ChatComparison = {
  tickers: string[];
  rows: { label: string; values: string[] }[];
};

export type ChatCitation = {
  id: number;
  kind: string;
  label: string;
  title: string;
  url?: string;
  snippet?: string;
};

export type StructuredReply = {
  layout: string;
  summary: string;
  factors?: ChatFactor[];
  snapshot?: ChatMetric[];
  scores?: ChatScoreBar[];
  quote?: ChatQuote | null;
  trade_preview?: ChatTradePreview | null;
  headlines?: ChatHeadline[];
  citations?: ChatCitation[];
  comparison?: ChatComparison | null;
  disclaimer?: string | null;
  follow_up?: string | null;
};

export const EXAMPLE_STRUCTURED: StructuredReply = {
  layout: "trade",
  summary: "I don't recommend buying more NVDA today.",
  factors: [
    {
      icon: "⚠️",
      title: "High Tech Sector Exposure",
      detail: "Technology is 42% of the portfolio (limit 30%).",
      severity: "high",
    },
    {
      icon: "📉",
      title: "QQQ Showing Weakness",
      detail: "Macro score is weak and momentum is deteriorating.",
      severity: "medium",
    },
    {
      icon: "👤",
      title: "Manual Approval Required",
      detail: "Phase 1 is analysis-only; any order needs your explicit approval.",
      severity: "medium",
    },
  ],
  snapshot: [
    { label: "Setup score", value: "52/100 (Watch)", highlight: true },
    { label: "Last price", value: "$892.40" },
    { label: "Portfolio risk", value: "Moderate (48/100)" },
    { label: "Tech exposure", value: "42% (limit 30%)" },
  ],
  scores: [
    { label: "Technical", value: 55, max: 100 },
    { label: "Macro", value: 38, max: 100 },
    { label: "News", value: 50, max: 100 },
    { label: "ML", value: 62, max: 100 },
    { label: "Risk", value: 45, max: 100 },
  ],
  quote: { ticker: "NVDA", last_price: 892.4, change_pct: -1.25, live: true, provider: "market" },
  disclaimer: "Phase 1 is analysis-only — no live trades without your approval.",
  follow_up: "Would you like me to run additional analysis or show alternative ideas?",
};
