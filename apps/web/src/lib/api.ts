const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type ChatResponse = {
  session_id: string;
  reply: string;
  decision: string;
  risk_verdict: string;
  warnings: string[];
  suggested_actions: string[];
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

export async function getHealth(): Promise<{ status: string }> {
  return fetchJson("/health");
}
