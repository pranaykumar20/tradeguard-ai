"use client";

import { StructuredChatReply } from "@/components/chat/StructuredChatReply";
import { BrowserFrame } from "@/components/landing/BrowserFrame";
import { EXAMPLE_STRUCTURED } from "@/lib/chat-types";

const SUGGESTED_ACTIONS = ["Show Risk", "Trade Plan", "Compare META"];

export function LandingChatPreview() {
  return (
    <section id="ai-chat" className="border-y border-card-border/60 bg-[#0a1422]/50 px-6 py-20">
      <div className="mx-auto max-w-6xl">
        <div className="mb-10 text-center">
          <h2 className="text-3xl font-extrabold md:text-4xl">Ask AI anything about your portfolio</h2>
          <p className="mx-auto mt-4 max-w-2xl text-muted">
            Natural-language trade analysis with structured answers, risk factors, live quotes, and
            actionable next steps.
          </p>
        </div>

        <BrowserFrame url="tradeguard.ai/chat">
          <div className="pointer-events-none select-none p-4 lg:p-5">
            <div className="mb-4 flex items-center justify-between border-b border-white/10 pb-3">
              <div>
                <h3 className="text-lg font-bold text-white">AI Chat</h3>
                <p className="text-sm text-muted">Connected: Demo portfolio</p>
              </div>
            </div>

            <div className="space-y-4">
              <div className="ml-auto max-w-[85%] rounded-[18px] border border-teal/20 bg-teal/10 px-4 py-3 text-sm">
                Should I buy more NVDA today?
              </div>

              <div className="rounded-[18px] border border-card-border bg-[#0d1b2d] p-4">
                <div className="mb-3 flex items-center gap-2 border-b border-white/10 pb-2.5">
                  <span className="text-xs font-semibold text-teal">TradeGuard AI</span>
                  <span className="rounded bg-teal/20 px-1.5 py-0.5 text-[10px] font-bold text-teal">
                    AI
                  </span>
                  <span className="rounded-full border border-orange/40 bg-orange/10 px-2.5 py-0.5 text-[10px] font-bold text-orange">
                    ⚠ CAUTION
                  </span>
                </div>

                <StructuredChatReply structured={EXAMPLE_STRUCTURED} />

                <div className="mt-4 flex flex-wrap gap-2">
                  {SUGGESTED_ACTIONS.map((action) => (
                    <span
                      key={action}
                      className="rounded-xl border border-white/10 bg-white/[0.04] px-3 py-2 text-xs font-bold text-white/85"
                    >
                      {action === "Show Risk" ? "🛡️" : action === "Trade Plan" ? "📋" : "📊"}{" "}
                      {action}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </BrowserFrame>
      </div>
    </section>
  );
}
