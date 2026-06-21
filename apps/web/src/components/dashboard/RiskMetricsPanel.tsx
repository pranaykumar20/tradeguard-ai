"use client";

export function RiskMetricsPanel({
  volatility,
  sharpe,
  var95,
  sortino,
  expectedShortfall,
  maxDrawdown,
}: {
  volatility: number;
  sharpe: number;
  var95: number;
  sortino: number;
  expectedShortfall: number;
  maxDrawdown: number;
}) {
  const metrics = [
    { label: "Portfolio Volatility (1Y)", value: `${volatility.toFixed(2)}%`, tone: "default" },
    { label: "Sharpe Ratio (1Y)", value: sharpe.toFixed(2), tone: sharpe >= 1 ? "green" : "default" },
    { label: "Value at Risk (95%)", value: `$${Math.abs(var95).toLocaleString()}`, tone: "default" },
    { label: "Sortino Ratio (1Y)", value: sortino.toFixed(2), tone: sortino >= 1 ? "green" : "default" },
    { label: "Expected Shortfall (95%)", value: `$${expectedShortfall.toLocaleString()}`, tone: "default" },
    { label: "Max Drawdown (1Y)", value: `${maxDrawdown.toFixed(2)}%`, tone: "red" },
  ] as const;

  return (
    <div className="dash-card p-5">
      <h3 className="text-sm font-bold text-white">Risk Metrics</h3>
      <div className="mt-4 grid grid-cols-2 gap-3">
        {metrics.map((metric) => (
          <div key={metric.label} className="rounded-xl border border-white/10 bg-white/[0.03] px-3 py-3">
            <p className="text-[10px] uppercase tracking-wide text-muted">{metric.label}</p>
            <p
              className={`mt-1 text-lg font-bold ${
                metric.tone === "green" ? "text-green" : metric.tone === "red" ? "text-red" : "text-white"
              }`}
            >
              {metric.value}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
