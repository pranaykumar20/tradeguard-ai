import { TRUST_ITEMS } from "@/lib/landing-content";

export function LandingTrust() {
  return (
    <section id="trust" className="border-y border-card-border/60 bg-[#0a1422]/50 px-6 py-20">
      <div className="mx-auto max-w-6xl">
        <div className="text-center">
          <h2 className="text-3xl font-extrabold md:text-4xl">Built for trust, not hype</h2>
          <p className="mx-auto mt-4 max-w-2xl text-muted">
            TradeGuard is designed as a risk manager first. The AI assists — your rules decide.
          </p>
        </div>

        <div className="mt-14 grid gap-5 sm:grid-cols-2">
          {TRUST_ITEMS.map((item) => (
            <div key={item.title} className="tg-card flex gap-4 !rounded-[20px]">
              <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-teal/10 text-2xl">
                {item.icon}
              </span>
              <div>
                <h3 className="text-lg font-bold">{item.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted">{item.description}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
