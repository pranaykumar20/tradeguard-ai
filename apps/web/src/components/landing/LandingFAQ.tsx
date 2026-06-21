"use client";

import { useState } from "react";
import { FAQ_ITEMS } from "@/lib/landing-content";

export function LandingFAQ() {
  const [openIndex, setOpenIndex] = useState<number | null>(0);

  return (
    <section id="faq" className="px-6 py-20">
      <div className="mx-auto max-w-3xl">
        <div className="text-center">
          <h2 className="text-3xl font-extrabold md:text-4xl">Frequently asked questions</h2>
          <p className="mx-auto mt-4 max-w-xl text-muted">
            Everything you need to know before getting started with TradeGuard AI.
          </p>
        </div>

        <div className="mt-12 space-y-3">
          {FAQ_ITEMS.map((item, index) => {
            const open = openIndex === index;
            return (
              <div
                key={item.q}
                className="tg-card !rounded-[18px] !p-0 overflow-hidden transition hover:border-teal/20"
              >
                <button
                  type="button"
                  onClick={() => setOpenIndex(open ? null : index)}
                  className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left"
                  aria-expanded={open}
                >
                  <span className="font-bold">{item.q}</span>
                  <span className="shrink-0 text-teal">{open ? "−" : "+"}</span>
                </button>
                {open && (
                  <div className="border-t border-card-border px-5 pb-4 pt-1 text-sm leading-relaxed text-muted">
                    {item.a}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
