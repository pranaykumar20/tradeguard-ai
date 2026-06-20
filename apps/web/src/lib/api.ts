const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type ChatResponse = {
  session_id: string;
  reply: string;
  decision: string;
  risk_verdict: string;
  warnings: string[];
  suggested_actions: string[];
  trade_preview?: TradePreview;
};

export type RiskSnapshot = {
  risk_score: number;
  risk_label: string;
  portfolio_value: number;
  daily_pnl: number;
  beta: number;
  max_drawdown_est: number;
  diversification: string;
  cash_pct: number;
  sector_exposure: Record<string, number>;
  alerts: { severity: string; title: string; detail: string }[];
};

export type Portfolio = {
  account_value: number;
  buying_power: number;
  daily_pnl: number;
  daily_pnl_pct: number;
  sector_exposure: Record<string, number>;
  positions: Record<string, { shares: number; weight_pct: number; sector: string }>;
  source?: string;
};

export type RiskRules = {
  max_trade_usd: number;
  max_daily_loss_usd: number;
  max_single_name_pct: number;
  max_tech_sector_pct: number;
  require_manual_approval: boolean;
  allow_options: boolean;
  allow_market_orders: boolean;
  no_trade_first_minutes: number;
  allowed_tickers: string[];
  blocked_asset_types: string[];
};

export type TradePreview = {
  allowed: boolean;
  verdict: string;
  order_value: number;
  warnings: string[];
  blocks: string[];
  requires_approval: boolean;
  ticker?: string;
  side?: string;
  quantity?: number;
  limit_price?: number;
  setup_label?: string;
  composite_score?: number;
};

export type TickerAnalysis = {
  ticker: string;
  scores: Record<string, number>;
  composite_score: number;
  setup_label: string;
  features: Record<string, number | string>;
  risk_verdict: string;
  warnings: string[];
};

export type Readiness = {
  status: string;
  phase?: number;
  storage_backend?: string;
  market_data_provider?: string;
  embedding_provider?: string;
  mcp_provider?: string;
  mcp_configured: boolean;
  mcp_enabled: boolean;
  llm_configured: boolean;
  polygon_key_set?: boolean;
  openai_key_set?: boolean;
};

export type PaperTrade = {
  id: string;
  ticker: string;
  side: string;
  quantity: number;
  limit_price: number;
  fill_price?: number | null;
  status: string;
  verdict: string;
  reason: string;
  pnl?: number | null;
  created_at?: string;
};

export type JournalStats = {
  total_trades: number;
  filled_trades: number;
  win_rate: number;
  total_pnl: number;
  goal: number;
  progress_pct: number;
};

export type AdvancedRisk = {
  var_95_1d: number;
  max_drawdown_est: number;
  correlation_matrix: Record<string, Record<string, number>>;
  stress_tests: { name: string; impact_usd: number; severity: string }[];
  tickers_analyzed: string[];
  data_provider?: string;
};

export type ApprovalRequest = {
  id: string;
  ticker: string;
  side: string;
  quantity: number;
  limit_price: number;
  order_type: string;
  status: string;
  risk_preview?: TradePreview;
  mcp_preview?: Record<string, unknown>;
  execution_result?: Record<string, unknown>;
  order_id?: string | null;
  notes?: string;
  created_at?: string;
  resolved_at?: string | null;
};

export type ExecutionPreview = {
  risk: TradePreview;
  mcp: Record<string, unknown>;
  order: {
    ticker: string;
    side: string;
    quantity: number;
    limit_price: number;
    order_type: string;
  };
  mcp_provider: string;
};

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });
  if (!res.ok) {
    throw new Error(`API ${path} failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export async function sendChat(message: string, sessionId?: string): Promise<ChatResponse> {
  return fetchJson<ChatResponse>("/api/chat", {
    method: "POST",
    body: JSON.stringify({ message, session_id: sessionId }),
  });
}

export async function getRiskSnapshot(): Promise<RiskSnapshot> {
  return fetchJson<RiskSnapshot>("/api/risk/snapshot");
}

export async function getPortfolio(): Promise<Portfolio> {
  return fetchJson<Portfolio>("/api/portfolio");
}

export async function getHealth(): Promise<{ status: string; service: string }> {
  return fetchJson("/health");
}

export async function getReadiness(): Promise<Readiness> {
  return fetchJson<Readiness>("/api/ready");
}

export async function getRiskRules(): Promise<{ rules: RiskRules }> {
  return fetchJson<{ rules: RiskRules }>("/api/risk/rules");
}

export async function previewTrade(body: {
  ticker: string;
  side: "buy" | "sell";
  quantity: number;
  limit_price: number;
  order_type?: string;
  asset_type?: string;
}): Promise<TradePreview> {
  return fetchJson<TradePreview>("/api/risk/preview", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function getTickerAnalysis(ticker: string): Promise<TickerAnalysis> {
  return fetchJson<TickerAnalysis>(`/api/analysis/ticker/${encodeURIComponent(ticker)}`);
}

export async function compareTickers(tickers: string[]): Promise<{
  tickers: { ticker: string; composite_score: number; setup_label: string; risk_verdict: string }[];
}> {
  return fetchJson(`/api/analysis/compare?tickers=${tickers.join(",")}`);
}

export async function getJournalTrades(limit = 100): Promise<{ trades: PaperTrade[] }> {
  return fetchJson(`/api/journal?limit=${limit}`);
}

export async function getJournalStats(): Promise<JournalStats> {
  return fetchJson<JournalStats>("/api/journal/stats");
}

export async function createPaperTrade(body: {
  ticker: string;
  side: "buy" | "sell";
  quantity: number;
  limit_price: number;
  reason?: string;
}): Promise<{ trade: PaperTrade; preview: TradePreview }> {
  return fetchJson("/api/journal/plan", { method: "POST", body: JSON.stringify(body) });
}

export async function getAdvancedRisk(): Promise<AdvancedRisk> {
  return fetchJson<AdvancedRisk>("/api/risk/advanced");
}

export async function previewExecution(body: {
  ticker: string;
  side: "buy" | "sell";
  quantity: number;
  limit_price?: number;
  order_type?: string;
}): Promise<ExecutionPreview> {
  return fetchJson<ExecutionPreview>("/api/execution/preview", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function submitExecution(body: {
  ticker: string;
  side: "buy" | "sell";
  quantity: number;
  limit_price?: number;
  order_type?: string;
  notes?: string;
}): Promise<{ status: string; approval: ApprovalRequest }> {
  return fetchJson("/api/execution/submit", { method: "POST", body: JSON.stringify(body) });
}

export async function getExecutionApprovals(
  status?: string
): Promise<{ approvals: ApprovalRequest[] }> {
  const q = status ? `?status=${encodeURIComponent(status)}` : "";
  return fetchJson(`/api/execution/approvals${q}`);
}

export async function approveExecution(
  requestId: string
): Promise<{ status: string; approval: ApprovalRequest }> {
  return fetchJson(`/api/execution/approvals/${requestId}/approve`, { method: "POST" });
}

export async function rejectExecution(
  requestId: string,
  reason?: string
): Promise<{ status: string; approval: ApprovalRequest }> {
  return fetchJson(`/api/execution/approvals/${requestId}/reject`, {
    method: "POST",
    body: JSON.stringify({ reason: reason ?? "" }),
  });
}
