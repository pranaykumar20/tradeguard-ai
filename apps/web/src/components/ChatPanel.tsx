"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { StructuredChatReply } from "@/components/chat/StructuredChatReply";
import { CitationList, NarrativeWithCitations } from "@/components/chat/NarrativeWithCitations";
import { GroundingBar, SourceDrawer, ToolTracePills } from "@/components/chat/RagUi";
import { ChatMarkdown } from "@/components/ChatMarkdown";
import { Btn, Card } from "@/components/ui/Card";
import { EXAMPLE_STRUCTURED } from "@/lib/chat-types";
import {
  sendChatStream,
  submitChatFeedback,
  type ChatFeedbackRating,
  type ChatResponse,
  type ChatStreamEvent,
} from "@/lib/api";

type Message = {
  role: "user" | "assistant";
  content: string;
  meta?: ChatResponse;
  time: string;
  streaming?: boolean;
  streamingStatus?: string;
  streamingNarrative?: string;
  streamingTools?: string[];
  streamingChunkCount?: number;
};

const STARTER = "Should I buy more NVDA today?";

const ACTION_ROUTES: Record<string, string> = {
  "Show Risk": "/dashboard",
  "View Holdings": "/portfolio",
  "Trade Plan": "/dashboard",
  "Preview Trade": "/dashboard",
};

const ACTION_ICONS: Record<string, string> = {
  "Show Risk": "🛡️",
  "Trade Plan": "📋",
  "Preview Trade": "👁️",
  "View Holdings": "💼",
};

function actionIcon(action: string) {
  if (ACTION_ICONS[action]) return ACTION_ICONS[action];
  if (action.startsWith("Compare ")) return "📊";
  if (action.startsWith("Analyze ")) return "📈";
  return "📊";
}

function verdictBadgeClass(v: string) {
  if (v === "BLOCK") return "border-red/40 bg-red/10 text-red";
  if (v === "CAUTION") return "border-orange/40 bg-orange/10 text-orange";
  return "border-green/40 bg-green/10 text-green";
}

function verdictIcon(v: string) {
  if (v === "BLOCK") return "🛑";
  if (v === "CAUTION") return "⚠";
  return "✓";
}

function AssistantHeader({
  verdict,
  decision,
  onCopy,
  copied,
  onRegenerate,
  onFeedback,
  feedback,
  disableActions,
}: {
  verdict?: string;
  decision?: string;
  onCopy?: () => void;
  copied?: boolean;
  onRegenerate?: () => void;
  onFeedback?: (rating: ChatFeedbackRating) => void;
  feedback?: ChatFeedbackRating | null;
  disableActions?: boolean;
}) {
  return (
    <div className="mb-3 flex items-start justify-between gap-3 border-b border-white/10 pb-2.5">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-semibold text-teal">TradeGuard AI</span>
          <span className="rounded bg-teal/20 px-1.5 py-0.5 text-[10px] font-bold text-teal">AI</span>
          {verdict && (
            <span
              className={`rounded-full border px-2.5 py-0.5 text-[10px] font-bold tracking-wide ${verdictBadgeClass(verdict)}`}
            >
              {verdictIcon(verdict)} {verdict}
            </span>
          )}
        </div>
        {decision ? <p className="mt-1 text-[11px] text-muted">{decision}</p> : null}
      </div>
      <div className="flex shrink-0 flex-wrap items-center gap-1">
        {!disableActions && onFeedback ? (
          <>
            <button
              type="button"
              onClick={() => onFeedback("up")}
              className={`rounded-lg border px-2 py-1 text-[10px] ${feedback === "up" ? "border-green/40 text-green" : "border-white/10 text-muted hover:text-green"}`}
              title="Helpful"
            >
              👍
            </button>
            <button
              type="button"
              onClick={() => onFeedback("down")}
              className={`rounded-lg border px-2 py-1 text-[10px] ${feedback === "down" ? "border-red/40 text-red" : "border-white/10 text-muted hover:text-red"}`}
              title="Not helpful"
            >
              👎
            </button>
          </>
        ) : null}
        {!disableActions && onRegenerate ? (
          <button
            type="button"
            onClick={onRegenerate}
            className="rounded-lg border border-white/10 px-2 py-1 text-[10px] font-semibold text-muted transition hover:border-teal/30 hover:text-teal"
          >
            ↻
          </button>
        ) : null}
        {onCopy ? (
          <button
            type="button"
            onClick={onCopy}
            className="rounded-lg border border-white/10 px-2 py-1 text-[10px] font-semibold text-muted transition hover:border-teal/30 hover:text-teal"
          >
            {copied ? "Copied" : "Copy"}
          </button>
        ) : null}
      </div>
    </div>
  );
}

function ActionCards({ actions, onAction }: { actions: string[]; onAction: (action: string) => void }) {
  return (
    <div className="mt-2 flex w-full max-w-[92%] flex-wrap gap-2">
      {actions.map((action) => (
        <button
          key={action}
          type="button"
          onClick={() => onAction(action)}
          className="flex min-w-[120px] flex-1 items-center gap-2 rounded-xl border border-white/10 bg-white/[0.04] px-3 py-2.5 text-left text-xs font-semibold transition hover:border-teal/30 hover:bg-teal/5"
        >
          <span>{actionIcon(action)}</span>
          {action}
        </button>
      ))}
    </div>
  );
}

function FollowUpChips({ text, onSelect }: { text: string; onSelect: (text: string) => void }) {
  const chips = text
    .split(/[?]/)
    .flatMap((part) => part.split(/\bor\b/i))
    .map((s) => s.trim())
    .filter((s) => s.length > 8 && s.length < 80);

  if (chips.length <= 1) return null;

  return (
    <div className="mt-2 flex flex-wrap gap-2">
      {chips.slice(0, 3).map((chip) => (
        <button
          key={chip}
          type="button"
          onClick={() => onSelect(chip.endsWith("?") ? chip : `${chip}?`)}
          className="rounded-full border border-teal/25 bg-teal/5 px-3 py-1 text-xs text-teal transition hover:bg-teal/10"
        >
          {chip}
        </button>
      ))}
    </div>
  );
}

function AssistantBody({
  msg,
  onFollowUp,
}: {
  msg: Message;
  onFollowUp: (text: string) => void;
}) {
  const narrative =
    msg.streamingNarrative || msg.meta?.narrative || (!msg.meta?.structured ? msg.content : "");
  const citations = msg.meta?.structured?.citations;

  if (msg.meta?.structured) {
    return (
      <>
        <GroundingBar
          sourceCount={msg.meta.rag_sources?.length ?? 0}
          toolCount={msg.meta.rag_tools?.length ?? 0}
          verdict={msg.meta.risk_verdict}
        />
        {(msg.streamingTools?.length || msg.meta.rag_tools?.length) ? (
          <ToolTracePills
            tools={msg.streamingTools ?? msg.meta.rag_tools ?? []}
            chunkCount={
              msg.streamingChunkCount ?? msg.meta.rag_sources?.length
            }
          />
        ) : null}
        <StructuredChatReply structured={msg.meta.structured} onFollowUp={onFollowUp} />
        <div className="mt-3">
          <NarrativeWithCitations
            text={narrative}
            citations={citations}
            streaming={msg.streaming && !!msg.streamingNarrative}
          />
        </div>
        {!msg.streaming && msg.meta.rag_sources && msg.meta.rag_sources.length > 0 ? (
          <SourceDrawer sources={msg.meta.rag_sources} />
        ) : null}
        {msg.meta.structured.follow_up && !msg.streaming ? (
          <FollowUpChips text={msg.meta.structured.follow_up} onSelect={onFollowUp} />
        ) : null}
      </>
    );
  }

  if (msg.streaming && msg.streamingStatus) {
    return <p className="text-sm text-muted">{msg.streamingStatus}</p>;
  }

  return <ChatMarkdown content={msg.content} />;
}

function copyText(msg: Message) {
  const parts = [
    msg.meta?.structured?.summary,
    msg.meta?.narrative || msg.streamingNarrative,
    msg.content,
  ].filter(Boolean);
  return parts.join("\n\n");
}

export function ChatPanel() {
  const router = useRouter();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string>();
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);
  const [feedbackByIndex, setFeedbackByIndex] = useState<Record<number, ChatFeedbackRating>>({});
  const bottomRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  useEffect(() => {
    return () => abortRef.current?.abort();
  }, []);

  function handleAction(action: string) {
    if (ACTION_ROUTES[action]) {
      router.push(ACTION_ROUTES[action]);
      return;
    }
    if (action.startsWith("Analyze ") || action.startsWith("Compare ")) {
      const ticker = action.replace(/^(Analyze|Compare)\s+/, "").trim();
      router.push(`/analysis?ticker=${ticker}`);
      return;
    }
    submit(action);
  }

  function updateStreamingMessage(updater: (msg: Message) => Message) {
    setMessages((current) => {
      const next = [...current];
      const idx = next.findIndex((m) => m.streaming);
      if (idx === -1) return current;
      next[idx] = updater(next[idx]);
      return next;
    });
  }

  async function submit(text: string, options?: { skipUserBubble?: boolean; regenerate?: boolean }) {
    const trimmed = text.trim();
    if (!trimmed || loading) return;

    abortRef.current?.abort();
    abortRef.current = new AbortController();

    const time = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

    if (!options?.skipUserBubble) {
      setMessages((m) => [...m, { role: "user", content: trimmed, time }]);
    }

    setInput("");
    setLoading(true);

    const placeholder: Message = {
      role: "assistant",
      content: "",
      time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      streaming: true,
      streamingStatus: "Parsing your question…",
      streamingNarrative: "",
    };
    setMessages((m) => [...m, placeholder]);

    try {
      const res = await sendChatStream(trimmed, sessionId, {
        signal: abortRef.current.signal,
        onEvent: (event: ChatStreamEvent) => {
          if (event.type === "status") {
            updateStreamingMessage((msg) => ({ ...msg, streamingStatus: event.message }));
          }
          if (event.type === "retrieval") {
            updateStreamingMessage((msg) => ({
              ...msg,
              streamingTools: event.tools,
              streamingChunkCount: event.chunk_count,
              streamingStatus: `Retrieved ${event.chunk_count} chunks…`,
            }));
          }
          if (event.type === "structured" && event.data) {
            updateStreamingMessage((msg) => ({
              ...msg,
              meta: {
                ...(msg.meta ?? {
                  session_id: sessionId ?? "",
                  reply: "",
                  decision: "",
                  risk_verdict: "CAUTION",
                  warnings: [],
                  suggested_actions: [],
                }),
                structured: event.data,
              },
            }));
          }
          if (event.type === "token") {
            updateStreamingMessage((msg) => ({
              ...msg,
              streamingNarrative: (msg.streamingNarrative ?? "") + event.content,
            }));
          }
        },
      });

      setSessionId(res.session_id);
      setMessages((current) => {
        const next = [...current];
        const idx = next.findIndex((m) => m.streaming);
        const finalized: Message = {
          role: "assistant",
          content: res.reply,
          meta: res,
          time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        };
        if (idx === -1) return [...next, finalized];
        next[idx] = finalized;
        return next;
      });
    } catch (err) {
      if (err instanceof Error && err.name === "AbortError") return;
      setMessages((current) => {
        const next = current.filter((m) => !m.streaming);
        return [
          ...next,
          {
            role: "assistant",
            content:
              "Could not reach the TradeGuard API. Start the backend with `npm run dev:api` on port 8000.",
            time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
          },
        ];
      });
    } finally {
      setLoading(false);
    }
  }

  function regenerateAt(assistantIndex: number) {
    const userIndex = assistantIndex - 1;
    if (userIndex < 0 || messages[userIndex]?.role !== "user") return;
    const text = messages[userIndex].content;
    setMessages((m) => m.slice(0, assistantIndex));
    submit(text, { skipUserBubble: true, regenerate: true });
  }

  async function handleFeedback(index: number, msg: Message, rating: ChatFeedbackRating) {
    if (!msg.meta?.session_id) return;
    try {
      await submitChatFeedback(msg.meta.session_id, rating, msg.meta.message_id);
      setFeedbackByIndex((prev) => ({ ...prev, [index]: rating }));
    } catch {
      /* ignore feedback errors */
    }
  }

  async function handleCopy(index: number, msg: Message) {
    try {
      await navigator.clipboard.writeText(copyText(msg));
      setCopiedIndex(index);
      setTimeout(() => setCopiedIndex(null), 1500);
    } catch {
      /* clipboard unavailable */
    }
  }

  return (
    <Card className="flex h-full min-h-[390px] flex-col gap-3.5">
      <div className="tg-scroll flex flex-1 flex-col gap-3.5 overflow-y-auto">
        {messages.length === 0 && (
          <div className="space-y-3.5">
            <div className="flex flex-col items-end">
              <div className="tg-bubble-user">Should I buy more NVDA today?</div>
            </div>
            <div className="tg-bubble-ai">
              <AssistantHeader verdict="CAUTION" decision="Watch — manual review required" disableActions />
              <StructuredChatReply structured={EXAMPLE_STRUCTURED} onFollowUp={submit} />
              <div className="mt-3">
                <CitationList citations={EXAMPLE_STRUCTURED.citations ?? []} />
              </div>
            </div>
            <ActionCards actions={["Show Risk", "Trade Plan", "Compare META"]} onAction={handleAction} />
            <Btn variant="secondary" onClick={() => submit(STARTER)}>
              Run live example
            </Btn>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`flex flex-col ${msg.role === "user" ? "items-end" : "items-start"}`}>
            <div className={`relative ${msg.role === "user" ? "tg-bubble-user" : "tg-bubble-ai"}`}>
              {msg.role === "assistant" && (
                <AssistantHeader
                  verdict={msg.meta?.risk_verdict}
                  decision={msg.meta?.decision}
                  onCopy={() => handleCopy(i, msg)}
                  copied={copiedIndex === i}
                  onRegenerate={msg.streaming ? undefined : () => regenerateAt(i)}
                  onFeedback={msg.streaming ? undefined : (rating) => handleFeedback(i, msg, rating)}
                  feedback={feedbackByIndex[i] ?? null}
                  disableActions={msg.streaming}
                />
              )}
              {msg.streaming && msg.streamingStatus && !msg.meta?.structured ? (
                <p className="mb-2 text-xs text-muted">{msg.streamingStatus}</p>
              ) : null}
              {msg.meta?.rag_sources && msg.meta.rag_sources.length > 0 && !msg.streaming && (
                <details className="mb-3 rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2">
                  <summary className="cursor-pointer text-xs font-bold text-teal">
                    RAG sources ({msg.meta.rag_sources.length})
                  </summary>
                  <ul className="mt-2 space-y-2">
                    {msg.meta.rag_sources.map((source) => (
                      <li key={source.id} className="text-xs text-muted">
                        <span className="font-bold text-teal">{source.source}</span>
                        <span className="ml-2 opacity-60">({source.score.toFixed(2)})</span>
                        <p className="mt-1 leading-relaxed text-white/70">{source.content}</p>
                      </li>
                    ))}
                  </ul>
                </details>
              )}
              {msg.role === "assistant" ? (
                <AssistantBody msg={msg} onFollowUp={submit} />
              ) : (
                <div className="text-sm leading-relaxed">{msg.content}</div>
              )}
            </div>
            {msg.meta?.suggested_actions?.length && !msg.streaming ? (
              <ActionCards actions={msg.meta.suggested_actions} onAction={handleAction} />
            ) : null}
            <div className="mt-1 text-[10px] text-muted">{msg.time}</div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      <form
        className="flex items-center gap-2.5"
        onSubmit={(e) => {
          e.preventDefault();
          submit(input);
        }}
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask TradeGuard AI..."
          className="tg-input"
          disabled={loading}
        />
        <Btn type="submit" className="shrink-0" disabled={loading}>
          Send
        </Btn>
      </form>
    </Card>
  );
}
