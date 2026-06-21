"use client";

import type { RagSource } from "@/lib/api";

const TOOL_LABELS: Record<string, string> = {
  search_playbooks: "Playbooks",
  search_filings: "Filings",
  search_journal: "Journal",
  search_analysis_history: "Analysis history",
  search_ml_runs: "ML runs",
  get_quote: "Live quote",
  portfolio_snapshot: "Portfolio",
  query_trades: "Trades",
  run_ticker_analysis: "Analysis",
  check_risk_limits: "Risk check",
  ml_status: "ML status",
};

type ToolTracePillsProps = {
  tools: string[];
  chunkCount?: number;
};

export function ToolTracePills({ tools, chunkCount }: ToolTracePillsProps) {
  if (!tools.length) return null;

  return (
    <div className="mb-2 flex flex-wrap items-center gap-1.5">
      <span className="text-[10px] font-bold uppercase tracking-wide text-muted">Tools</span>
      {tools.map((tool) => (
        <span
          key={tool}
          className="rounded-full border border-teal/25 bg-teal/5 px-2 py-0.5 text-[10px] font-semibold text-teal"
        >
          {TOOL_LABELS[tool] ?? tool}
        </span>
      ))}
      {typeof chunkCount === "number" && chunkCount > 0 ? (
        <span className="text-[10px] text-muted">· {chunkCount} chunks</span>
      ) : null}
    </div>
  );
}

const DOC_TYPE_LABELS: Record<string, string> = {
  playbook: "Playbook",
  filing: "Filing",
  news: "News",
  journal: "Journal",
  analysis_snapshot: "Analysis",
  ml_run: "ML",
  document: "Doc",
};

type SourceDrawerProps = {
  sources: RagSource[];
};

export function SourceDrawer({ sources }: SourceDrawerProps) {
  if (!sources.length) return null;

  return (
    <details className="mt-2 rounded-xl border border-white/10 bg-white/[0.02]">
      <summary className="cursor-pointer px-3 py-2 text-[10px] font-bold uppercase tracking-wide text-muted">
        RAG sources ({sources.length})
      </summary>
      <ul className="space-y-2 border-t border-white/10 px-3 py-2">
        {sources.map((source) => (
          <li key={source.id} className="text-xs">
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded bg-white/10 px-1.5 py-0.5 text-[10px] font-semibold text-teal">
                {DOC_TYPE_LABELS[source.doc_type ?? "document"] ?? source.doc_type}
              </span>
              <span className="font-semibold text-white/80">{source.source}</span>
              <span className="text-muted">score {source.score.toFixed(2)}</span>
            </div>
            <p className="mt-1 line-clamp-3 text-white/60">{source.content}</p>
          </li>
        ))}
      </ul>
    </details>
  );
}

export function GroundingBar({
  sourceCount,
  toolCount,
  verdict,
}: {
  sourceCount: number;
  toolCount: number;
  verdict?: string;
}) {
  if (!sourceCount && !toolCount && !verdict) return null;

  return (
    <p className="mb-2 text-[10px] text-muted">
      {sourceCount > 0 ? `${sourceCount} retrieved` : null}
      {toolCount > 0 ? `${sourceCount > 0 ? " · " : ""}${toolCount} tools` : null}
      {verdict ? `${sourceCount || toolCount ? " · " : ""}Risk: ${verdict}` : null}
    </p>
  );
}
