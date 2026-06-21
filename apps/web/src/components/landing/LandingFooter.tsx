import Link from "next/link";
import { FOOTER_LINKS, LANDING_CTAS } from "@/lib/landing-content";

export function LandingFooter() {
  return (
    <footer className="border-t border-card-border/60 px-6 py-14">
      <div className="mx-auto max-w-6xl">
        <div className="grid gap-10 md:grid-cols-2 lg:grid-cols-4">
          <div>
            <div className="flex items-center gap-2 text-lg font-extrabold">
              <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-blue/15 text-lg text-blue">
                🛡
              </span>
              TradeGuard <span className="text-teal">AI</span>
            </div>
            <p className="mt-3 text-sm leading-relaxed text-muted">
              AI-powered portfolio risk management. Know your risk before every trade.
            </p>
            <Link
              href={LANDING_CTAS.primaryHref}
              className="mt-4 inline-block rounded-[12px] bg-teal px-4 py-2 text-xs font-bold text-[#041018] hover:brightness-110"
            >
              {LANDING_CTAS.primaryLabel}
            </Link>
          </div>

          <div>
            <h4 className="text-xs font-bold uppercase tracking-wide text-muted">Product</h4>
            <ul className="mt-4 space-y-2.5">
              {FOOTER_LINKS.product.map((link) => (
                <li key={link.label}>
                  <a href={link.href} className="text-sm text-muted transition hover:text-foreground">
                    {link.label}
                  </a>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h4 className="text-xs font-bold uppercase tracking-wide text-muted">App</h4>
            <ul className="mt-4 space-y-2.5">
              {FOOTER_LINKS.app.map((link) => (
                <li key={link.label}>
                  <Link href={link.href} className="text-sm text-muted transition hover:text-foreground">
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h4 className="text-xs font-bold uppercase tracking-wide text-muted">Resources</h4>
            <ul className="mt-4 space-y-2.5">
              {FOOTER_LINKS.resources.map((link) => (
                <li key={link.label}>
                  <a
                    href={link.href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-muted transition hover:text-foreground"
                  >
                    {link.label}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div className="mt-12 flex flex-col items-center justify-between gap-4 border-t border-card-border/60 pt-8 md:flex-row">
          <p className="text-xs text-muted">
            © {new Date().getFullYear()} TradeGuard AI. All rights reserved.
          </p>
          <p className="text-xs text-muted">
            Not financial advice. Past performance does not guarantee future results.
          </p>
        </div>
      </div>
    </footer>
  );
}
