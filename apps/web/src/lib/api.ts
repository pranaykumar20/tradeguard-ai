import type { StructuredReply, ChatQuote } from "@/lib/chat-types";

export type { StructuredReply, ChatQuote } from "@/lib/chat-types";

function resolveApiBase(): string {
  const raw = (process.env.NEXT_PUBLIC_API_URL ?? "").trim();
  if (!raw) return "";
  const withoutTrailingSlash = raw.replace(/\/+$/, "");
  if (
    withoutTrailingSlash.startsWith("http://") ||
    withoutTrailingSlash.startsWith("https://")
  ) {
    return withoutTrailingSlash;
  }
  return `https://${withoutTrailingSlash}`;
}

/** Empty string = same-origin; Next.js rewrites proxy to the FastAPI backend. */
const API_BASE = resolveApiBase();

type TokenGetter = () => Promise<string | null>;
let authTokenGetter: TokenGetter | null = null;

/** Set by AuthShell when Clerk is configured. */
export function setAuthTokenGetter(getter: TokenGetter | null) {
  authTokenGetter = getter;
}

function getDemoUserEmail(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(/(?:^|;\s*)tg_demo_email=([^;]+)/);
  return match?.[1] ? decodeURIComponent(match[1]) : null;
}

function authHeaders(extra?: Record<string, string>): Record<string, string> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...extra,
  };
  const demoEmail = getDemoUserEmail();
  if (demoEmail) {
    headers["X-Demo-User-Email"] = demoEmail;
  }
  return headers;
}

export type AuthUser = {
  id: string;
  email: string;
  clerk_id: string | null;
  display_name: string;
  is_authenticated: boolean;
  role: string;
  permissions: string[];
  is_active: boolean;
};

export type AuthMeResponse = {
  auth_enabled: boolean;
  user: AuthUser;
};

export type AdminUser = AuthUser & {
  custom_permissions: string[] | null;
  effective_permissions: string[];
  role_label: string;
  created_at?: string;
  updated_at?: string;
};

export type ChatResponse = {
  session_id: string;
  message_id?: string | null;
  reply: string;
  narrative?: string | null;
  structured?: StructuredReply | null;
  decision: string;
  risk_verdict: string;
  warnings: string[];
  suggested_actions: string[];
  trade_preview?: TradePreview;
  rag_sources?: RagSource[];
  rag_tools?: string[];
  web_sources?: WebSource[];
  quote?: ChatQuote;
};

export type ChatStreamEvent =
  | { type: "status"; message: string }
  | {
      type: "retrieval";
      tools: string[];
      chunk_count: number;
      query_plan?: Record<string, unknown>;
    }
  | { type: "structured"; data: StructuredReply | null }
  | { type: "token"; content: string }
  | { type: "done"; data: ChatResponse };

export type ChatFeedbackRating = "up" | "down";

export type WebSource = {
  title: string;
  summary: string;
  source: string;
  published_at: string;
  sentiment: number;
  url: string;
};

export type RagSource = {
  id: string;
  source: string;
  content: string;
  score: number;
  doc_type?: string;
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
  broker_id?: string;
  account_id?: string;
  account_label?: string;
};

export type HouseholdPortfolio = {
  source: string;
  account_count: number;
  total_value: number;
  total_daily_pnl: number;
  accounts: Portfolio[];
  positions: Portfolio["positions"];
  sector_exposure: Record<string, number>;
};

export type BrokerAccount = {
  id: string;
  broker_id: string;
  account_id: string;
  label: string;
  account_type: string;
  enabled: boolean;
};

export type OptionContract = {
  option_type: "call" | "put";
  strike: number;
  expiry: string;
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
  composite_score_adjusted?: number;
  setup_label: string;
  features: Record<string, number | string>;
  risk_verdict: string;
  warnings: string[];
  news?: {
    sentiment_score: number;
    sentiment_label: string;
    headline_count: number;
    headlines: { title: string; summary: string; source: string; sentiment: number; published_at: string }[];
    provider: string;
  };
  filings?: {
    ticker: string;
    filing_count: number;
    filings: { chunk_id: string; source: string; content: string }[];
    rag_excerpts: { source: string; content: string; score: number }[];
  };
  regime?: MacroRegime;
};

export type MacroRegime = {
  regime: string;
  label: string;
  enabled: boolean;
  risk_score_adjustment: number;
  signals: Record<string, number | string>;
  guidance?: string;
};

export type MLModelStatus = {
  model_exists: boolean;
  version: number;
  model_type?: string;
  last_trained_at?: string;
  source?: string;
  accuracy?: number;
  auc?: number;
  brier?: number;
  deploy_gate_passed?: boolean;
  feature_importance?: Record<string, number>;
  walk_forward_folds?: number;
  samples?: number;
  journal_trades_used?: number;
  journal_retrain_enabled?: boolean;
  min_trades_required?: number;
  history_versions?: number;
  volatility?: {
    enabled?: boolean;
    model_exists?: boolean;
    version?: number;
    model_type?: string;
    last_trained_at?: string;
    auc?: number;
    accuracy?: number;
    feature_importance?: Record<string, number>;
    high_threshold?: number;
  };
};

export type MLModelHistoryEntry = {
  version: number;
  model_type?: string;
  auc?: number;
  accuracy?: number;
  brier?: number;
  source?: string;
  last_trained_at?: string;
  journal_trades_used?: number;
  archived_at?: string;
  active?: boolean;
  artifact_exists?: boolean;
};

export type MLModelHistory = {
  active: Record<string, unknown>;
  versions: MLModelHistoryEntry[];
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
  approval_id?: string | null;
  source?: string;
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
  asset_type?: string;
  broker_id?: string;
  account_id?: string;
  option_contract?: OptionContract;
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
  broker?: Record<string, unknown>;
  order: {
    ticker: string;
    side: string;
    quantity: number;
    limit_price: number;
    order_type: string;
    asset_type?: string;
  };
  tax?: Record<string, unknown>;
  broker_id?: string;
  mcp_provider: string;
};

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = authHeaders(init?.headers as Record<string, string> | undefined);
  if (authTokenGetter) {
    const token = await authTokenGetter();
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }
  }
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
  });
  if (!res.ok) {
    throw new Error(`API ${path} failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export async function getAuthMe(): Promise<AuthMeResponse> {
  return fetchJson<AuthMeResponse>("/api/auth/me");
}

export async function listAdminUsers(): Promise<{ users: AdminUser[] }> {
  return fetchJson<{ users: AdminUser[] }>("/api/admin/users");
}

export async function updateAdminUser(
  userId: string,
  body: Partial<Pick<AdminUser, "role" | "is_active" | "display_name">> & {
    permissions?: string[] | null;
  },
): Promise<AdminUser> {
  return fetchJson<AdminUser>(`/api/admin/users/${userId}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export async function getAdminPermissionCatalog(): Promise<{
  permissions: string[];
  roles: { id: string; label: string; permissions: string[] }[];
}> {
  return fetchJson("/api/admin/permissions");
}

export async function sendChat(message: string, sessionId?: string): Promise<ChatResponse> {
  return fetchJson<ChatResponse>("/api/chat", {
    method: "POST",
    body: JSON.stringify({ message, session_id: sessionId }),
  });
}

export async function sendChatStream(
  message: string,
  sessionId: string | undefined,
  handlers: {
    onEvent: (event: ChatStreamEvent) => void;
    signal?: AbortSignal;
  },
): Promise<ChatResponse> {
  const headers = authHeaders();
  if (authTokenGetter) {
    const token = await authTokenGetter();
    if (token) headers.Authorization = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}/api/chat/stream`, {
    method: "POST",
    headers,
    body: JSON.stringify({ message, session_id: sessionId }),
    signal: handlers.signal,
  });

  if (!res.ok || !res.body) {
    throw new Error(`API /api/chat/stream failed: ${res.status}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let finalResponse: ChatResponse | null = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() ?? "";

    for (const chunk of chunks) {
      const line = chunk.trim();
      if (!line.startsWith("data:")) continue;
      const payload = JSON.parse(line.slice(5).trim()) as ChatStreamEvent;
      handlers.onEvent(payload);
      if (payload.type === "done") {
        finalResponse = payload.data;
      }
    }
  }

  if (!finalResponse) {
    throw new Error("Stream ended without a final response");
  }
  return finalResponse;
}

export async function submitChatFeedback(
  sessionId: string,
  rating: ChatFeedbackRating,
  messageId?: string | null,
): Promise<void> {
  await fetchJson("/api/chat/feedback", {
    method: "POST",
    body: JSON.stringify({
      session_id: sessionId,
      message_id: messageId,
      rating,
    }),
  });
}

export async function getRiskSnapshot(): Promise<RiskSnapshot> {
  return fetchJson<RiskSnapshot>("/api/risk/snapshot");
}

export async function getPortfolio(): Promise<Portfolio> {
  return fetchJson<Portfolio>("/api/portfolio");
}

export async function getHouseholdPortfolio(): Promise<HouseholdPortfolio> {
  return fetchJson<HouseholdPortfolio>("/api/portfolio?view=household");
}

export async function getBrokerAccounts(): Promise<{ accounts: BrokerAccount[] }> {
  return fetchJson("/api/accounts");
}

export async function getHealth(): Promise<{ status: string; service: string }> {
  return fetchJson("/health");
}

export async function getReadiness(): Promise<Readiness> {
  return fetchJson<Readiness>("/api/health/ready");
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
  tickers: {
    ticker: string;
    composite_score: number;
    composite_score_adjusted?: number;
    setup_label: string;
    risk_verdict: string;
  }[];
  regime?: MacroRegime;
}> {
  return fetchJson(`/api/analysis/compare?tickers=${tickers.join(",")}`);
}

export async function getMacroRegime(): Promise<MacroRegime> {
  return fetchJson<MacroRegime>("/api/intelligence/regime");
}

export async function getMLModelStatus(): Promise<MLModelStatus> {
  return fetchJson<MLModelStatus>("/api/intelligence/ml/status");
}

export async function retrainMLModel(): Promise<{
  status: string;
  version?: number;
  accuracy?: number;
  auc?: number;
  journal_trades_used?: number;
  source?: string;
  reason?: string;
}> {
  return fetchJson("/api/intelligence/ml/retrain", { method: "POST" });
}

export async function getMLModelHistory(): Promise<MLModelHistory> {
  return fetchJson<MLModelHistory>("/api/intelligence/ml/history");
}

export async function rollbackMLModel(version: number): Promise<{
  status: string;
  version?: number;
  meta?: Record<string, unknown>;
  reason?: string;
}> {
  return fetchJson(`/api/intelligence/ml/rollback/${version}`, { method: "POST" });
}

export type RagEvalCase = {
  id: string;
  query: string;
  passed: boolean;
  plan_tools: string[];
  freshness: string;
  expected_tools: string[];
};

export type RagEvalReport = {
  status: string;
  ran_at?: string;
  elapsed_ms?: number;
  cases_total?: number;
  cases_passed?: number;
  tool_selection_accuracy_pct?: number;
  acl_leak_rate_pct?: number;
  acl_check?: { passed: boolean; leak_detected: boolean };
  cases?: RagEvalCase[];
  message?: string;
};

export type RagStatus = {
  documents_total: number;
  documents_by_type: Record<string, number>;
  embedding_version: number;
  router_enabled: boolean;
  eval_enabled: boolean;
  last_eval: RagEvalReport | null;
};

export async function getRagStatus(): Promise<RagStatus> {
  return fetchJson<RagStatus>("/api/intelligence/rag/status");
}

export async function getRagEvalReport(): Promise<RagEvalReport> {
  return fetchJson<RagEvalReport>("/api/intelligence/rag/eval");
}

export async function runRagEval(): Promise<RagEvalReport> {
  return fetchJson<RagEvalReport>("/api/intelligence/rag/eval/run", { method: "POST" });
}

export async function refreshRagIndex(source?: string): Promise<Record<string, unknown>> {
  const path = source
    ? `/api/intelligence/rag/refresh/${source}`
    : "/api/intelligence/rag/refresh";
  return fetchJson(path, { method: "POST" });
}

export async function migrateRagEmbeddings(): Promise<Record<string, unknown>> {
  return fetchJson("/api/intelligence/rag/migrate/embeddings", { method: "POST" });
}

export async function getTickerNews(ticker: string): Promise<TickerAnalysis["news"]> {
  return fetchJson(`/api/intelligence/news/${encodeURIComponent(ticker)}`);
}

export type MarketNewsPulse = {
  query: string;
  sentiment_score?: number;
  sentiment_label?: string;
  headline_count: number;
  headlines: {
    title: string;
    summary: string;
    source: string;
    published_at: string;
    sentiment: number;
    url?: string;
  }[];
  provider: string;
  live_search: boolean;
  hint?: string;
};

export async function getMarketNews(limit = 8): Promise<MarketNewsPulse> {
  return fetchJson<MarketNewsPulse>(`/api/intelligence/market-news?limit=${limit}`);
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
  asset_type?: "equity" | "option";
  broker_id?: string;
  account_id?: string;
  option_contract?: OptionContract;
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
  asset_type?: "equity" | "option";
  broker_id?: string;
  account_id?: string;
  option_contract?: OptionContract;
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

export type ExportSummary = {
  generated_at: string;
  period_days: number;
  counts: {
    journal_trades: number;
    approval_requests: number;
    automation_audit: number;
    alert_events: number;
  };
};

export type ReplayEvent = {
  step: string;
  at?: string;
  title: string;
  detail: string;
  data?: Record<string, unknown>;
};

export type ReplayTimeline = {
  entry_type: string;
  entry_id: string;
  events: ReplayEvent[];
  event_count: number;
  approval?: Record<string, unknown> | null;
  journal_trade?: PaperTrade | null;
};

export type PlatformHealth = {
  checked_at?: string;
  healthy: boolean;
  readiness: { status: string; checks?: Record<string, unknown> };
  mcp: { enabled: boolean; ok: boolean; latency_ms?: number | null; error?: string | null; latency_alert?: boolean };
  model: { drift?: number | null; drift_alert?: boolean; accuracy?: number; baseline_accuracy?: number | null };
};

export type BacktestReport = {
  strategy: { id: string; name: string; strategy_type: string; config: Record<string, unknown> };
  period_days: number;
  journal_trades_in_period: number;
  matched_action_trades: number;
  simulated_signals: number;
  proposal_count: number;
  proposal_outcomes: Record<string, number>;
  metrics_all_trades: JournalStats & { sharpe_ratio?: number; max_drawdown_pct?: number };
  metrics_matched_trades: JournalStats & { sharpe_ratio?: number; max_drawdown_pct?: number };
  signals: { at?: string; trigger_reason?: string }[];
};

export async function getAuditExportSummary(days = 90): Promise<ExportSummary> {
  return fetchJson(`/api/observability/export/summary?days=${days}`);
}

export async function downloadAuditExport(format: "json" | "csv", days = 90): Promise<void> {
  const headers: Record<string, string> = {};
  if (authTokenGetter) {
    const token = await authTokenGetter();
    if (token) headers.Authorization = `Bearer ${token}`;
  }
  const res = await fetch(`${API_BASE}/api/observability/export?format=${format}&days=${days}`, { headers });
  if (!res.ok) throw new Error("Export failed");
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `tradeguard-audit-${days}d.${format}`;
  anchor.click();
  URL.revokeObjectURL(url);
}

export async function getPlatformHealth(): Promise<PlatformHealth> {
  return fetchJson<PlatformHealth>("/api/observability/platform");
}

export async function runPlatformCheck(): Promise<PlatformHealth> {
  return fetchJson<PlatformHealth>("/api/observability/platform/check", { method: "POST" });
}

export async function getTradeReplay(id: string, type: "approval" | "trade"): Promise<ReplayTimeline> {
  const path =
    type === "approval"
      ? `/api/observability/replay/approval/${encodeURIComponent(id)}`
      : `/api/observability/replay/trade/${encodeURIComponent(id)}`;
  return fetchJson<ReplayTimeline>(path);
}

export async function backtestStrategy(strategyId: string, days = 90): Promise<BacktestReport> {
  return fetchJson<BacktestReport>(`/api/observability/backtest/${encodeURIComponent(strategyId)}?days=${days}`);
}

export type PushNotification = {
  id: string;
  title: string;
  body: string;
  event_type: string;
  severity: string;
  read: boolean;
  created_at?: string;
};

export type PushConfig = {
  enabled: boolean;
  vapid_public_key: string | null;
};

export async function getPushConfig(): Promise<PushConfig> {
  return fetchJson<PushConfig>("/api/push/config");
}

export async function subscribePush(subscription: {
  endpoint: string;
  keys?: Record<string, string>;
}): Promise<{ status: string; count: number }> {
  return fetchJson("/api/push/subscribe", {
    method: "POST",
    body: JSON.stringify(subscription),
  });
}

export async function getPushInbox(
  limit = 20,
  unreadOnly = false
): Promise<{ notifications: PushNotification[]; unread: number }> {
  return fetchJson(`/api/push/inbox?limit=${limit}&unread_only=${unreadOnly}`);
}

export async function markPushRead(notificationId: string): Promise<{ notification: PushNotification }> {
  return fetchJson(`/api/push/inbox/${encodeURIComponent(notificationId)}/read`, { method: "POST" });
}

export async function markAllPushRead(): Promise<{ marked_read: number }> {
  return fetchJson("/api/push/inbox/read-all", { method: "POST" });
}

export type OnboardingStep = {
  id: string;
  title: string;
  description: string;
  auto: boolean;
  completed: boolean;
  manual_confirm: boolean;
};

export type OnboardingStatus = {
  steps: OnboardingStep[];
  completed_count: number;
  total_steps: number;
  progress_pct: number;
  complete: boolean;
  risk_limits: {
    max_trade_usd: number;
    max_daily_loss_usd: number;
    require_manual_approval: boolean;
    allow_options: boolean;
  };
  mcp: { enabled: boolean; configured: boolean; connected?: boolean; connected_at?: string | null; mcp_url?: string };
  robinhood?: RobinhoodConnectionStatus;
  monitoring_enabled: boolean;
};

export type RobinhoodConnectionStatus = {
  connected: boolean;
  connected_at?: string | null;
  broker_id: string;
  account_id: string;
  mcp_url: string;
  oauth_available: boolean;
};

export async function getRobinhoodConnectionStatus(): Promise<RobinhoodConnectionStatus & { user_id?: string }> {
  return fetchJson("/api/brokers/robinhood/status");
}

export async function startRobinhoodConnect(returnPath = "/onboarding"): Promise<{
  authorization_url: string;
  state: string;
  redirect_uri: string;
}> {
  return fetchJson("/api/brokers/robinhood/connect", {
    method: "POST",
    body: JSON.stringify({ return_path: returnPath }),
  });
}

export async function disconnectRobinhood(): Promise<RobinhoodConnectionStatus> {
  return fetchJson("/api/brokers/robinhood/disconnect", { method: "POST" });
}

export async function getOnboardingStatus(): Promise<OnboardingStatus> {
  return fetchJson<OnboardingStatus>("/api/onboarding/status");
}

export async function completeOnboardingStep(stepId: string): Promise<OnboardingStatus> {
  return fetchJson<OnboardingStatus>("/api/onboarding/complete", {
    method: "POST",
    body: JSON.stringify({ step_id: stepId }),
  });
}

export async function resetOnboarding(): Promise<OnboardingStatus> {
  return fetchJson<OnboardingStatus>("/api/onboarding/reset", { method: "POST" });
}
