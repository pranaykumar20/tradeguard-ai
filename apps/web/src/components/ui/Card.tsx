import type { ReactNode } from "react";

export function Card({
  children,
  className = "",
  warning = false,
}: {
  children: ReactNode;
  className?: string;
  warning?: boolean;
}) {
  return (
    <div className={`tg-card ${warning ? "tg-card-warning" : ""} ${className}`.trim()}>
      {children}
    </div>
  );
}

export function StatCard({
  label,
  value,
  tone = "default",
}: {
  label: string;
  value: ReactNode;
  tone?: "default" | "green" | "red" | "orange" | "blue";
}) {
  const toneClass =
    tone === "green"
      ? "text-green"
      : tone === "red"
        ? "text-red"
        : tone === "orange"
          ? "text-orange"
          : tone === "blue"
            ? "text-blue"
            : "";

  return (
    <Card>
      <div className="tg-label">{label}</div>
      <div className={`tg-value ${toneClass}`}>{value}</div>
    </Card>
  );
}

export function StockTile({
  ticker,
  subtitle,
  score,
}: {
  ticker: string;
  subtitle: string;
  score: number;
}) {
  const tone = score > 70 ? "text-green" : score < 50 ? "text-red" : "text-orange";

  return (
    <div className="tg-stock">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="tg-ticker">{ticker}</div>
          <div className="tg-sub">{subtitle}</div>
        </div>
        <div className={`tg-score ${tone}`}>{score}/100</div>
      </div>
      <div className="tg-bar">
        <span style={{ width: `${Math.min(100, score)}%` }} />
      </div>
    </div>
  );
}

export function PageHeader({
  title,
  subtitle,
}: {
  title: string;
  subtitle?: string;
}) {
  return (
    <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
      <div className="min-w-0">
        <h1 className="text-2xl font-extrabold tracking-tight md:text-[32px]">{title}</h1>
        {subtitle && <p className="mt-1.5 text-sm text-muted md:text-[15px]">{subtitle}</p>}
      </div>
      <div className="tg-pill shrink-0 self-start whitespace-normal text-center sm:max-w-[220px] sm:text-left">
        Informational only · Not financial advice
      </div>
    </div>
  );
}

export function Row({
  label,
  value,
  tone = "default",
}: {
  label: string;
  value: ReactNode;
  tone?: "default" | "green" | "red" | "orange" | "blue";
}) {
  const toneClass =
    tone === "green"
      ? "text-green"
      : tone === "red"
        ? "text-red"
        : tone === "orange"
          ? "text-orange"
          : tone === "blue"
            ? "text-blue"
            : "";

  return (
    <div className="tg-row">
      <span className="text-muted">{label}</span>
      <b className={toneClass}>{value}</b>
    </div>
  );
}

export function Btn({
  children,
  variant = "primary",
  className = "",
  type = "button",
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "danger";
}) {
  const variantClass =
    variant === "secondary"
      ? "tg-btn-secondary"
      : variant === "danger"
        ? "tg-btn-danger"
        : "tg-btn-primary";

  return (
    <button type={type} className={`tg-btn ${variantClass} ${className}`.trim()} {...props}>
      {children}
    </button>
  );
}
