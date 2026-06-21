"use client";

const SECTOR_COLORS: Record<string, string> = {
  Technology: "#55b9ff",
  Communication: "#a78bfa",
  "Consumer Cyclical": "#ffb84d",
  Healthcare: "#35d07f",
  Financial: "#26e4c4",
  Industrials: "#f472b6",
  Energy: "#fb7185",
  Other: "#64748b",
  Cash: "#94a3b8",
};

function colorForSector(sector: string, index: number) {
  return SECTOR_COLORS[sector] ?? ["#55b9ff", "#a78bfa", "#ffb84d", "#35d07f", "#26e4c4", "#64748b"][index % 6];
}

export function ExposureDonut({
  sectors,
  cashPct,
  totalValue,
}: {
  sectors: Record<string, number>;
  cashPct: number;
  totalValue: number;
}) {
  const slices = [
    ...Object.entries(sectors).map(([name, pct]) => ({ name, pct })),
    ...(cashPct > 0 ? [{ name: "Cash", pct: cashPct }] : []),
  ].filter((s) => s.pct > 0);

  const totalPct = slices.reduce((sum, s) => sum + s.pct, 0) || 100;
  let cursor = 0;
  const gradientParts = slices.map((slice, i) => {
    const start = (cursor / totalPct) * 100;
    cursor += slice.pct;
    const end = (cursor / totalPct) * 100;
    return `${colorForSector(slice.name, i)} ${start}% ${end}%`;
  });

  const largest = [...slices].sort((a, b) => b.pct - a.pct)[0];
  const techPct = sectors.Technology ?? 0;

  return (
    <div className="dash-card p-5">
      <h3 className="text-sm font-bold text-white">Exposure Overview</h3>
      <div className="mt-4 flex flex-col items-center gap-5 lg:flex-row lg:items-start">
        <div className="relative h-44 w-44 shrink-0">
          <div
            className="h-full w-full rounded-full"
            style={{ background: `conic-gradient(${gradientParts.join(", ")})` }}
          />
          <div className="absolute inset-5 flex flex-col items-center justify-center rounded-full bg-[#0b1524] text-center">
            <p className="text-[10px] uppercase tracking-wide text-muted">Total Exposure</p>
            <p className="text-sm font-bold text-white">${totalValue.toLocaleString()}</p>
            <p className="text-[10px] text-muted">100%</p>
          </div>
        </div>
        <div className="w-full flex-1 space-y-2">
          {slices.map((slice, i) => (
            <div key={slice.name} className="flex items-center justify-between text-xs">
              <div className="flex items-center gap-2">
                <span
                  className="h-2.5 w-2.5 rounded-full"
                  style={{ background: colorForSector(slice.name, i) }}
                />
                <span className="text-white/80">{slice.name}</span>
              </div>
              <span className="font-semibold text-white">{slice.pct.toFixed(1)}%</span>
            </div>
          ))}
        </div>
      </div>
      <div className="mt-4 grid gap-2 border-t border-white/10 pt-4 text-xs text-muted sm:grid-cols-2">
        <p>
          Largest sector: <span className="font-semibold text-white">{largest?.name ?? "—"}</span> (
          {largest?.pct.toFixed(1)}%)
        </p>
        <p>
          Top concentration: <span className="font-semibold text-orange">Technology ({techPct.toFixed(1)}%)</span>
        </p>
      </div>
    </div>
  );
}

export function SectorExposureChart({ sectors }: { sectors: Record<string, number> }) {
  const entries = Object.entries(sectors).sort((a, b) => b[1] - a[1]);

  return (
    <div className="dash-card p-5">
      <h3 className="text-sm font-bold text-white">Sector Exposure</h3>
      <div className="mt-4 space-y-3">
        {entries.map(([sector, pct], i) => (
          <div key={sector}>
            <div className="mb-1 flex justify-between text-xs">
              <span className="text-white/75">{sector}</span>
              <span className="font-semibold text-white">{pct.toFixed(1)}%</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-white/10">
              <div
                className="h-full rounded-full"
                style={{
                  width: `${Math.min(100, pct)}%`,
                  background: colorForSector(sector, i),
                }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
