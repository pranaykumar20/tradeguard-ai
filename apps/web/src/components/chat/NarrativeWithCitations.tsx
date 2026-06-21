"use client";

import type { ChatCitation } from "@/lib/chat-types";
import { ChatMarkdown } from "@/components/ChatMarkdown";

type NarrativeWithCitationsProps = {
  text: string;
  citations?: ChatCitation[];
  streaming?: boolean;
};

function renderWithCitationLinks(text: string, citations: ChatCitation[]) {
  const byId = new Map(citations.map((c) => [c.id, c]));
  const parts = text.split(/(\[\d+\])/g);

  return parts.map((part, i) => {
    const match = part.match(/^\[(\d+)\]$/);
    if (!match) return <span key={i}>{part}</span>;

    const citation = byId.get(Number(match[1]));
    if (!citation) return <span key={i}>{part}</span>;

    if (citation.url) {
      return (
        <a
          key={i}
          href={citation.url}
          target="_blank"
          rel="noopener noreferrer"
          className="mx-0.5 inline-flex h-4 min-w-4 items-center justify-center rounded bg-teal/20 px-1 text-[10px] font-bold text-teal hover:bg-teal/30"
          title={citation.title}
        >
          {citation.id}
        </a>
      );
    }

    return (
      <button
        key={i}
        type="button"
        className="mx-0.5 inline-flex h-4 min-w-4 items-center justify-center rounded bg-teal/20 px-1 text-[10px] font-bold text-teal"
        title={citation.title}
      >
        {citation.id}
      </button>
    );
  });
}

export function NarrativeWithCitations({ text, citations = [], streaming }: NarrativeWithCitationsProps) {
  if (!text.trim()) return null;

  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.03] px-3 py-2.5">
      <p className="mb-1.5 text-[10px] font-bold uppercase tracking-wide text-muted">
        {streaming ? "Composing…" : "Insight"}
      </p>
      {citations.length > 0 ? (
        <p className="text-sm leading-relaxed text-white/85">
          {renderWithCitationLinks(text, citations)}
          {streaming ? <span className="ml-0.5 inline-block h-3 w-1 animate-pulse bg-teal" /> : null}
        </p>
      ) : (
        <div className="text-sm leading-relaxed text-white/85">
          <ChatMarkdown content={text + (streaming ? "▍" : "")} />
        </div>
      )}
    </div>
  );
}

export function CitationList({ citations }: { citations: ChatCitation[] }) {
  if (!citations.length) return null;

  return (
    <div className="mt-2 space-y-1.5">
      <p className="text-[10px] font-bold uppercase tracking-wide text-muted">Sources</p>
      <ol className="space-y-1">
        {citations.map((citation) => (
          <li key={citation.id} className="flex gap-2 text-xs text-white/70">
            <span className="font-bold text-teal">[{citation.id}]</span>
            <span>
              {citation.url ? (
                <a href={citation.url} target="_blank" rel="noopener noreferrer" className="text-teal hover:underline">
                  {citation.title}
                </a>
              ) : (
                citation.title
              )}
              {citation.label ? <span className="text-muted"> · {citation.label}</span> : null}
            </span>
          </li>
        ))}
      </ol>
    </div>
  );
}
