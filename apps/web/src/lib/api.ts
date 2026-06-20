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
  alert_provider?: string;
  monitoring_enabled?: boolean;
  mcp_configured: boolean;
  mcp_enabled: boolean;
  llm_configured: boolean;
  polygon_key_set?: boolean;
  openai_key_set?: boolean;
};

export type AlertEvent = {
  id: string;
  event_type: string;
  severity: string;
  title: string;
  detail: string;
  channels_sent?: string[];
  created_at?: string;
};

export type MonitoringStatus = {
  monitoring_enabled: boolean;
  trading_halted: boolean;
  halt_reason?: string | null;
  trading_state: Record<string, unknown>;
  daily_pnl?: number;
  portfolio_value?: number;
  max_drawdown_est?: number;
  daily_loss_limit: number;
  drawdown_alert_pct: number;
  alert_provider: string;
  recent_alerts: AlertEvent[];
};

export type MonitoringCheck = {
  status: string;
  trading_halted: boolean;
  halt_reason?: string | null;
  daily_pnl?: number;
  max_drawdown_est?: number;
  portfolio_value?: number;
  checks: { name: string; status: string; detail: string }[];
  alerts: { severity: string; title: string; detail: string }[];
  alert_provider: string;
  checked_at: string;
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

export async function getMonitoringStatus(): Promise<MonitoringStatus> {
  return fetchJson<MonitoringStatus>("/api/monitoring/status");
}

export async function runMonitoringCheck(): Promise<MonitoringCheck> {
  return fetchJson<MonitoringCheck>("/api/monitoring/check", { method: "POST" });
}

export async function getMonitoringAlerts(limit = 50): Promise<{ alerts: AlertEvent[] }> {
  return fetchJson(`/api/monitoring/alerts?limit=${limit}`);
}

export async function resumeTrading(): Promise<{ status: string; trading_state: Record<string, unknown> }> {
  return fetchJson("/api/monitoring/resume-trading", { method: "POST" });
}

export type TradeStrategy = {
  id: string;
  name: string;
  description: string;
  strategy_type: string;
  config: {
    sector?: string;
    threshold_pct?: number;
    comparison?: string;
    action_ticker: string;
    action_side: "buy" | "sell";
    quantity: number;
  };
  auto_approve: boolean;
  enabled: boolean;
  summary?: string;
  created_at?: string;
  updated_at?: string;
};

export type StrategyProposal = {
  id: string;
  strategy_id: string;
  strategy_name: string;
  ticker: string;
  side: string;
  quantity: number;
  limit_price?: number | null;
  trigger_reason: string;
  trigger_context?: Record<string, unknown>;
  risk_preview?: TradePreview;
  status: string;
  approval_id?: string | null;
  notes?: string;
  created_at?: string;
};

export type StrategyEvalResult = {
  status: string;
  strategy?: TradeStrategy;
  intent?: Record<string, unknown>;
  preview?: ExecutionPreview;
  proposal?: StrategyProposal;
  approval?: ApprovalRequest;
  execution?: Record<string, unknown>;
};

export async function getStrategyTemplates(): Promise<{ templates: TradeStrategy[] }> {
  return fetchJson("/api/strategies/templates");
}

export async function getStrategies(): Promise<{ strategies: TradeStrategy[] }> {
  return fetchJson("/api/strategies");
}

export async function createStrategy(body: {
  name: string;
  description?: string;
  strategy_type?: string;
  config: TradeStrategy["config"];
  auto_approve?: boolean;
  enabled?: boolean;
}): Promise<{ strategy: TradeStrategy }> {
  return fetchJson("/api/strategies", { method: "POST", body: JSON.stringify(body) });
}

export async function updateStrategy(
  strategyId: string,
  body: Partial<{
    name: string;
    description: string;
    config: TradeStrategy["config"];
    auto_approve: boolean;
    enabled: boolean;
  }>
): Promise<{ strategy: TradeStrategy }> {
  return fetchJson(`/api/strategies/${strategyId}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export async function evaluateStrategy(strategyId: string): Promise<StrategyEvalResult> {
  return fetchJson(`/api/strategies/${strategyId}/evaluate`, { method: "POST" });
}

export async function runAllStrategies(): Promise<{
  status: string;
  evaluated: number;
  results: StrategyEvalResult[];
}> {
  return fetchJson("/api/strategies/run-all", { method: "POST" });
}

export async function getStrategyProposals(
  strategyId?: string
): Promise<{ proposals: StrategyProposal[] }> {
  const q = strategyId ? `?strategy_id=${encodeURIComponent(strategyId)}` : "";
  return fetchJson(`/api/strategies/proposals${q}`);
}

export type ValidationCheck = {
  name: string;
  label: string;
  passed: boolean;
  actual: number;
  required: string;
};

export type ValidationReport = {
  passed: boolean;
  automation_unlocked: boolean;
  dev_bypass_active: boolean;
  gate_enabled: boolean;
  summary: string;
  metrics: {
    track_record_months: number;
    total_trades: number;
    filled_trades: number;
    total_pnl: number;
    win_rate: number;
    sharpe_ratio: number;
    max_drawdown_pct: number;
    rule_violation_count: number;
    starting_capital: number;
  };
  thresholds: Record<string, number>;
  checks: ValidationCheck[];
  generated_at: string;
};

export async function getValidationReport(): Promise<ValidationReport> {
  return fetchJson<ValidationReport>("/api/validation/report");
}

export async function getValidationGate(): Promise<{ automation_unlocked: boolean; report: ValidationReport }> {
  return fetchJson("/api/validation/gate");
}

export async function seedValidationDemo(): Promise<{ seeded_trades: number; report: ValidationReport }> {
  return fetchJson("/api/validation/seed-demo", { method: "POST" });
}

export type AutomationAuditEntry = {
  id: string;
  event_type: string;
  detail: string;
  ticker?: string;
  strategy_name?: string;
  verdict?: string;
  created_at?: string;
};

export type AutomationStatus = {
  master_enabled: boolean;
  ready: boolean;
  block_reason: string;
  trading_halted: boolean;
  validation_unlocked: boolean;
  auto_trades_today: number;
  auto_trades_remaining: number;
  validation_summary?: string;
  bounds: {
    max_daily_auto_trades: number;
    max_trade_usd: number;
    allowed_verdicts: string[];
    options_allowed: boolean;
    require_manual_approval_default: boolean;
  };
  recent_audit: AutomationAuditEntry[];
};

export async function getAutomationStatus(): Promise<AutomationStatus> {
  return fetchJson<AutomationStatus>("/api/automation/status");
}

export async function enableAutomation(): Promise<{ status: string }> {
  return fetchJson("/api/automation/enable", { method: "POST" });
}

export async function disableAutomation(reason?: string): Promise<{ status: string }> {
  return fetchJson("/api/automation/disable", {
    method: "POST",
    body: JSON.stringify({ reason: reason ?? "Disabled by user" }),
  });
}

export async function runAutomation(): Promise<{ status: string; run?: unknown }> {
  return fetchJson("/api/automation/run", { method: "POST" });
}

export async function getAutomationAudit(limit = 50): Promise<{ audit: AutomationAuditEntry[] }> {
  return fetchJson(`/api/automation/audit?limit=${limit}`);
}
