"use client";

function cellColor(value: number) {
  if (value >= 0.75) return "rgba(255, 94, 108, 0.85)";
  if (value >= 0.5) return "rgba(255, 94, 108, 0.55)";
  if (value >= 0.25) return "rgba(255, 184, 77, 0.45)";
  if (value >= 0) return "rgba(85, 185, 255, 0.35)";
  if (value >= -0.25) return "rgba(38, 228, 196, 0.35)";
  return "rgba(85, 185, 255, 0.65)";
}

export function CorrelationHeatmap({ matrix }: { matrix: Record<string, Record<string, number>> }) {
  const tickers = Object.keys(matrix);
  if (tickers.length === 0) {
    return (
      <div className="dash-card p-5">
        <h3 className="text-sm font-bold text-white">Correlation Heatmap</h3>
        <p className="mt-4 text-sm text-muted">Insufficient market data for correlation matrix.</p>
      </div>
    );
  }

  return (
    <div className="dash-card p-5">
      <h3 className="text-sm font-bold text-white">Correlation Heatmap</h3>
      <div className="mt-4 overflow-x-auto">
        <table className="w-full min-w-[320px] border-separate border-spacing-1 text-center text-[11px]">
          <thead>
            <tr>
              <th />
              {tickers.map((t) => (
                <th key={t} className="px-1 py-1 font-bold text-teal">
                  {t}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {tickers.map((row) => (
              <tr key={row}>
                <td className="px-1 py-1 text-left font-bold text-white/70">{row}</td>
                {tickers.map((col) => {
                  const val = matrix[row]?.[col] ?? 0;
                  return (
                    <td
                      key={col}
                      className="rounded px-1 py-2 font-semibold text-white"
                      style={{ background: cellColor(val) }}
                    >
                      {val.toFixed(2)}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
