import Link from "next/link";
import { LANDING_CTAS, PRICING_TIERS } from "@/lib/landing-content";

export function LandingPricing() {
  return (
    <section id="pricing" className="px-6 py-20">
      <div className="mx-auto max-w-6xl">
        <div className="text-center">
          <h2 className="text-3xl font-extrabold md:text-4xl">Simple, transparent pricing</h2>
          <p className="mx-auto mt-4 max-w-2xl text-muted">
            Free during beta. Upgrade when you need automation and team features.
          </p>
        </div>

        <div className="mt-14 grid gap-6 lg:grid-cols-3">
          {PRICING_TIERS.map((tier) => (
            <div
              key={tier.name}
              className={`tg-card flex flex-col !rounded-[24px] ${
                tier.highlighted
                  ? "border-teal/40 shadow-[0_0_40px_rgba(38,228,196,0.12)]"
                  : ""
              }`}
            >
              {tier.highlighted && (
                <span className="mb-3 w-fit rounded-full bg-teal/15 px-3 py-1 text-xs font-bold text-teal">
                  Most popular
                </span>
              )}
              {"comingSoon" in tier && tier.comingSoon && (
                <span className="mb-3 w-fit rounded-full border border-card-border px-3 py-1 text-xs font-bold text-muted">
                  Coming soon
                </span>
              )}

              <h3 className="text-xl font-extrabold">{tier.name}</h3>
              <div className="mt-3 flex items-baseline gap-1">
                <span className="text-4xl font-extrabold text-teal">{tier.price}</span>
                {tier.period && <span className="text-sm text-muted">{tier.period}</span>}
              </div>
              <p className="mt-3 text-sm leading-relaxed text-muted">{tier.description}</p>

              <ul className="mt-6 flex-1 space-y-2.5">
                {tier.features.map((feature) => (
                  <li key={feature} className="flex items-start gap-2 text-sm">
                    <span className="mt-0.5 text-teal">✓</span>
                    <span>{feature}</span>
                  </li>
                ))}
              </ul>

              <Link
                href={tier.highlighted ? LANDING_CTAS.primaryHref : LANDING_CTAS.secondaryHref}
                className={`mt-8 block rounded-[14px] py-3 text-center text-sm font-bold transition ${
                  tier.highlighted
                    ? "bg-teal text-[#041018] hover:brightness-110"
                    : "border border-card-border hover:bg-white/[0.04]"
                }`}
              >
                {tier.cta}
              </Link>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
