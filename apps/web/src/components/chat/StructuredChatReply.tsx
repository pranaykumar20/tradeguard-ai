"use client";

import type {
  ChatFactor,
  ChatHeadline,
  ChatMetric,
  ChatQuote,
  ChatScoreBar,
  ChatTradePreview,
  StructuredReply,
} from "@/lib/chat-types";
import { CitationList } from "@/components/chat/NarrativeWithCitations";

const SEVERITY_STYLES: Record<string, string> = {
  high: "border-red/30 bg-red/[0.06]",
  medium: "border-orange/30 bg-orange/[0.06]",
  low: "border-white/10 bg-white/[0.03]",
  positive: "border-green/30 bg-green/[0.06]",
};

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <h3 className="mb-2.5 text-xs font-semibold uppercase tracking-wide text-teal">{children}</h3>;
}

export function QuoteChip({ quote }: { quote: ChatQuote }) {
  if (quote.last_price == null) return null;
  const change = quote.change_pct ?? 0;
  const up = change >= 0;

  return (
    <div className="mb-3 flex flex-wrap items-center gap-2 rounded-xl border border-white/10 bg-[#07111f]/80 px-3 py-2">
      <span className="text-sm font-bold text-white">{quote.ticker}</span>
      <span className="text-lg font-semibold text-white">${quote.last_price.toFixed(2)}</span>
      <span className={`text-xs font-semibold ${up ? "text-green" : "text-red"}`}>
        {up ? "▲" : "▼"} {change >= 0 ? "+" : ""}
        {change.toFixed(2)}%
      </span>
      {quote.live && <span className="rounded bg-green/15 px-1.5 py-0.5 text-[10px] font-bold text-green">LIVE</span>}
    </div>
  );
}

function FactorRow({ factor }: { factor: ChatFactor }) {
  const style = SEVERITY_STYLES[factor.severity] ?? SEVERITY_STYLES.medium;
  return (
    <li className={`rounded-xl border px-3 py-2.5 ${style}`}>
      <div className="flex gap-2.5">
        <span className="text-base leading-none">{factor.icon}</span>
        <div>
          <p className="text-sm font-semibold text-white">{factor.title}</p>
          <p className="mt-0.5 text-xs leading-relaxed text-white/70">{factor.detail}</p>
        </div>
      </div>
    </li>
  );
}

function SnapshotGrid({ metrics }: { metrics: ChatMetric[] }) {
  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
      {metrics.map((metric) => (
        <div
          key={metric.label}
          className={`rounded-xl border px-3 py-2.5 ${
            metric.highlight ? "border-teal/30 bg-teal/[0.07]" : "border-white/10 bg-white/[0.03]"
          }`}
        >
          <p className="text-[10px] uppercase tracking-wide text-muted">{metric.label}</p>
          <p className="mt-1 text-sm font-semibold text-white">{metric.value}</p>
        </div>
      ))}
    </div>
  );
}

function ScoreBreakdown({ scores }: { scores: ChatScoreBar[] }) {
  return (
    <div className="space-y-2">
      {scores.map((score) => {
        const pct = Math.min(100, Math.round((score.value / score.max) * 100));
        const color = pct >= 65 ? "bg-green" : pct >= 45 ? "bg-orange" : "bg-red";
        return (
          <div key={score.label}>
            <div className="mb-1 flex justify-between text-xs">
              <span className="text-white/70">{score.label}</span>
              <span className="font-semibold text-white">{score.value}</span>
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-white/10">
              <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}

function ComparisonTable({ tickers, rows }: { tickers: string[]; rows: { label: string; values: string[] }[] }) {
  return (
    <div className="overflow-x-auto rounded-xl border border-white/10">
      <table className="w-full min-w-[280px] border-collapse text-left text-xs">
        <thead className="bg-white/[0.05]">
          <tr>
            <th className="px-3 py-2 font-semibold uppercase tracking-wide text-muted">Metric</th>
            {tickers.map((t) => (
              <th key={t} className="px-3 py-2 font-semibold text-teal">
                {t}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-white/10">
          {rows.map((row) => (
            <tr key={row.label}>
              <td className="px-3 py-2 text-white/70">{row.label}</td>
              {row.values.map((value, i) => (
                <td key={`${row.label}-${i}`} className="px-3 py-2 font-medium text-white">
                  {value}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function TradePreviewCard({ preview }: { preview: ChatTradePreview }) {
  return (
    <div className="rounded-xl border border-teal/25 bg-teal/[0.06] px-3 py-2.5">
      <p className="text-[10px] font-bold uppercase tracking-wide text-teal">Trade preview</p>
      <p className="mt-1 text-sm font-semibold text-white">
        {preview.side.toUpperCase()} {preview.quantity} {preview.ticker} @ ${preview.limit_price.toFixed(2)}
      </p>
      <p className="mt-0.5 text-xs text-white/70">
        Order value ${preview.order_value.toFixed(2)} · Verdict {preview.verdict}
      </p>
    </div>
  );
}

function HeadlineCards({ headlines }: { headlines: ChatHeadline[] }) {
  return (
    <ul className="space-y-2">
      {headlines.map((headline, i) => (
        <li key={`${headline.title}-${i}`} className="rounded-xl border border-white/10 bg-white/[0.03] px-3 py-2.5">
          {headline.url ? (
            <a
              href={headline.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm font-medium text-teal hover:underline"
            >
              {headline.title}
            </a>
          ) : (
            <p className="text-sm font-medium text-white">{headline.title}</p>
          )}
          <p className="mt-0.5 text-[11px] text-muted">{headline.source}</p>
          {headline.summary ? <p className="mt-1 text-xs leading-relaxed text-white/65">{headline.summary}</p> : null}
        </li>
      ))}
    </ul>
  );
}

type StructuredChatReplyProps = {
  structured: StructuredReply;
  onFollowUp?: (text: string) => void;
};

export function StructuredChatReply({ structured, onFollowUp }: StructuredChatReplyProps) {
  const showScores = structured.scores && structured.scores.length > 0 && structured.layout !== "price";

  return (
    <div className="space-y-4">
      <p className="text-[15px] font-semibold leading-snug text-white">{structured.summary}</p>

      {structured.quote ? <QuoteChip quote={structured.quote} /> : null}
      {structured.trade_preview ? <TradePreviewCard preview={structured.trade_preview} /> : null}

      {structured.comparison ? (
        <div>
          <SectionTitle>Comparison</SectionTitle>
          <ComparisonTable tickers={structured.comparison.tickers} rows={structured.comparison.rows} />
        </div>
      ) : null}

      {structured.factors && structured.factors.length > 0 ? (
        <div>
          <SectionTitle>Key factors</SectionTitle>
          <ul className="space-y-2">{structured.factors.map((f) => <FactorRow key={f.title} factor={f} />)}</ul>
        </div>
      ) : null}

      {structured.snapshot && structured.snapshot.length > 0 ? (
        <div>
          <SectionTitle>Snapshot</SectionTitle>
          <SnapshotGrid metrics={structured.snapshot} />
        </div>
      ) : null}

      {showScores ? (
        <div>
          <SectionTitle>Score breakdown</SectionTitle>
          <ScoreBreakdown scores={structured.scores!} />
        </div>
      ) : null}

      {structured.headlines && structured.headlines.length > 0 ? (
        <div>
          <SectionTitle>Recent headlines</SectionTitle>
          <HeadlineCards headlines={structured.headlines} />
        </div>
      ) : null}

      {structured.citations && structured.citations.length > 0 ? (
        <CitationList citations={structured.citations} />
      ) : null}

      {structured.disclaimer ? (
        <blockquote className="border-l-2 border-teal/40 bg-white/[0.03] py-2 pl-3 pr-2 text-xs italic text-white/70">
          {structured.disclaimer}
        </blockquote>
      ) : null}

      {structured.follow_up ? (
        onFollowUp ? (
          <button
            type="button"
            onClick={() => onFollowUp(structured.follow_up!)}
            className="text-left text-sm text-teal/90 transition hover:text-teal"
          >
            {structured.follow_up}
          </button>
        ) : (
          <p className="text-sm text-white/75">{structured.follow_up}</p>
        )
      ) : null}
    </div>
  );
}
