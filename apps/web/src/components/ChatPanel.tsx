"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { sendChat, type ChatResponse } from "@/lib/api";
import { Btn, Card } from "@/components/ui/Card";

type Message = {
  role: "user" | "assistant";
  content: string;
  meta?: ChatResponse;
  time: string;
};

const STARTER = "Should I buy more NVDA today?";

const ACTION_ROUTES: Record<string, string> = {
  "Show Risk": "/dashboard",
  "View Holdings": "/portfolio",
  "Trade Plan": "/dashboard",
  "Preview Trade": "/dashboard",
};

function verdictColor(v: string) {
  if (v === "BLOCK") return "text-red";
  if (v === "CAUTION") return "text-orange";
  return "text-green";
}

export function ChatPanel() {
  const router = useRouter();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string>();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  function handleAction(action: string) {
    if (ACTION_ROUTES[action]) {
      router.push(ACTION_ROUTES[action]);
      return;
    }
    if (action.startsWith("Analyze ")) {
      const ticker = action.replace("Analyze ", "").trim();
      router.push(`/analysis?ticker=${ticker}`);
      return;
    }
    submit(action);
  }

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
    <Card className="flex h-full min-h-[390px] flex-col gap-3.5">
      <div className="tg-scroll flex flex-1 flex-col gap-3.5 overflow-y-auto">
        {messages.length === 0 && (
          <div className="space-y-3.5">
            <div className="tg-bubble-user">Should I buy more NVDA today?</div>
            <div className="tg-bubble-ai">
              Ask TradeGuard about any allowed ticker. Phase 1 is analysis-only — no live trades.
            </div>
            <Btn variant="secondary" onClick={() => submit(STARTER)}>
              Run example
            </Btn>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`flex flex-col ${msg.role === "user" ? "items-end" : "items-start"}`}>
            <div className={msg.role === "user" ? "tg-bubble-user" : "tg-bubble-ai"}>
              {msg.meta && (
                <div className="mb-2 flex flex-wrap items-center gap-2">
                  <span className={`text-xs font-bold ${verdictColor(msg.meta.risk_verdict)}`}>
                    {msg.meta.risk_verdict}
                  </span>
                  {msg.meta.decision && (
                    <span className="text-xs text-muted">· {msg.meta.decision}</span>
                  )}
                </div>
              )}
              {msg.meta?.warnings && msg.meta.warnings.length > 0 && (
                <ul className="mb-2 space-y-1 text-xs text-orange">
                  {msg.meta.warnings.map((w) => (
                    <li key={w}>⚠ {w}</li>
                  ))}
                </ul>
              )}
              <div className="whitespace-pre-wrap text-sm leading-relaxed">{msg.content}</div>
            </div>
            {msg.meta?.suggested_actions?.length ? (
              <div className="mt-2 flex flex-wrap gap-2">
                {msg.meta.suggested_actions.map((action) => (
                  <Btn key={action} variant="secondary" className="!px-3 !py-2 !text-xs" onClick={() => handleAction(action)}>
                    {action}
                  </Btn>
                ))}
              </div>
            ) : null}
            <div className="mt-1 text-[10px] text-muted">{msg.time}</div>
          </div>
        ))}

        {loading && <div className="text-sm text-muted">TradeGuard is analyzing risk…</div>}
        <div ref={bottomRef} />
      </div>

      <form
        className="flex gap-2.5"
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
        />
        <Btn type="submit" disabled={loading}>
          Send
        </Btn>
      </form>
    </Card>
  );
}
