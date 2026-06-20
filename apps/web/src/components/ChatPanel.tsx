"use client";

import { useEffect, useRef, useState } from "react";
import { sendChat, type ChatResponse } from "@/lib/api";

type Message = {
  role: "user" | "assistant";
  content: string;
  meta?: ChatResponse;
  time: string;
};

const STARTER = "Should I buy more NVDA today?";

function verdictColor(v: string) {
  if (v === "BLOCK") return "text-danger border-danger/40 bg-danger/10";
  if (v === "CAUTION") return "text-warning border-warning/40 bg-warning/10";
  return "text-accent border-accent/40 bg-accent/10";
}

export function ChatPanel() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string>();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function submit(text: string) {
    const trimmed = text.trim();
    if (!trimmed || loading) return;

    const time = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    setMessages((m) => [...m, { role: "user", content: trimmed, time }]);
    setInput("");
    setLoading(true);

    try {
      const res = await sendChat(trimmed, sessionId);
      setSessionId(res.session_id);
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          content: res.reply,
          meta: res,
          time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
    } catch {
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          content:
            "Could not reach the TradeGuard API. Start the backend with `npm run dev:api` on port 8000.",
          time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex h-full flex-col rounded-2xl border border-card-border bg-card">
      <header className="flex items-center justify-between border-b border-card-border px-5 py-4">
        <div>
          <h1 className="text-lg font-semibold">Ask AI</h1>
          <p className="text-sm text-muted">Your AI investing assistant — analysis only in Phase 1</p>
        </div>
        <div className="rounded-lg border border-card-border bg-background px-3 py-1.5 text-xs text-muted">
          Model: TG-Alpha
        </div>
      </header>

      <div className="tg-scroll flex-1 space-y-4 overflow-y-auto p-5">
        {messages.length === 0 && (
          <div className="rounded-xl border border-dashed border-card-border p-6 text-center text-sm text-muted">
            Try: &ldquo;{STARTER}&rdquo;
            <div className="mt-3">
              <button
                type="button"
                onClick={() => submit(STARTER)}
                className="rounded-lg bg-accent/15 px-4 py-2 text-accent hover:bg-accent/25"
              >
                Run example
              </button>
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-[85%] rounded-2xl px-4 py-3 ${
                msg.role === "user"
                  ? "bg-accent/20 text-foreground"
                  : "border border-card-border bg-background"
              }`}
            >
              {msg.meta && (
                <div
                  className={`mb-2 inline-flex rounded-full border px-2 py-0.5 text-xs font-semibold ${verdictColor(msg.meta.risk_verdict)}`}
                >
                  {msg.meta.risk_verdict}
                </div>
              )}
              <div className="whitespace-pre-wrap text-sm leading-relaxed">{msg.content}</div>
              {msg.meta?.suggested_actions?.length ? (
                <div className="mt-3 flex flex-wrap gap-2">
                  {msg.meta.suggested_actions.map((action) => (
                    <button
                      key={action}
                      type="button"
                      onClick={() => submit(action)}
                      className="rounded-lg border border-card-border bg-card px-3 py-1.5 text-xs hover:border-accent/50"
                    >
                      {action}
                    </button>
                  ))}
                </div>
              ) : null}
              <div className="mt-2 text-[10px] text-muted">{msg.time}</div>
            </div>
          </div>
        ))}

        {loading && (
          <div className="text-sm text-muted">TradeGuard is analyzing risk…</div>
        )}
        <div ref={bottomRef} />
      </div>

      <form
        className="flex gap-2 border-t border-card-border p-4"
        onSubmit={(e) => {
          e.preventDefault();
          submit(input);
        }}
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about NVDA, portfolio risk, or trade ideas…"
          className="flex-1 rounded-xl border border-card-border bg-background px-4 py-3 text-sm outline-none focus:border-accent/50"
        />
        <button
          type="submit"
          disabled={loading}
          className="rounded-xl bg-accent px-5 py-3 text-sm font-semibold text-black disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </div>
  );
}
