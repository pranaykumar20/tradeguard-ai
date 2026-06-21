"use client";

type Alert = { severity: string; title: string; detail: string };

const SEVERITY_STYLES: Record<string, { badge: string; dot: string; label: string }> = {
  high: { badge: "border-red/30 bg-red/10 text-red", dot: "bg-red", label: "High" },
  medium: { badge: "border-orange/30 bg-orange/10 text-orange", dot: "bg-orange", label: "Medium" },
  info: { badge: "border-blue/30 bg-blue/10 text-blue", dot: "bg-blue", label: "Info" },
  low: { badge: "border-teal/30 bg-teal/10 text-teal", dot: "bg-teal", label: "Low" },
};

function styleFor(severity: string) {
  return SEVERITY_STYLES[severity] ?? SEVERITY_STYLES.medium;
}

export function RiskAlertsPanel({ alerts }: { alerts: Alert[] }) {
  return (
    <div className="dash-card flex h-full flex-col p-5">
      <h3 className="text-sm font-bold text-white">Risk Alerts</h3>
      <ul className="mt-4 flex-1 space-y-3">
        {alerts.length === 0 ? (
          <li className="rounded-xl border border-green/20 bg-green/5 px-3 py-3 text-sm text-white/75">
            No active risk alerts. Portfolio is within guardrails.
          </li>
        ) : (
          alerts.map((alert, i) => {
            const style = styleFor(alert.severity);
            return (
              <li key={`${alert.title}-${i}`} className="rounded-xl border border-white/10 bg-white/[0.03] px-3 py-3">
                <div className="flex items-center gap-2">
                  <span className={`h-2 w-2 rounded-full ${style.dot}`} />
                  <span className={`rounded-full border px-2 py-0.5 text-[10px] font-bold ${style.badge}`}>
                    {style.label}
                  </span>
                </div>
                <p className="mt-2 text-sm font-semibold text-white">{alert.title}</p>
                <p className="mt-1 text-xs leading-relaxed text-white/65">{alert.detail}</p>
              </li>
            );
          })
        )}
      </ul>
    </div>
  );
}

export function buildDashboardAlerts(
  alerts: Alert[],
  techPct: number,
  techLimit = 30,
): Alert[] {
  const merged = [...alerts];
  if (techPct > techLimit && !merged.some((a) => a.title.includes("Sector"))) {
    merged.unshift({
      severity: "high",
      title: "High Concentration Risk",
      detail: `Technology sector exposure is ${techPct.toFixed(1)}% (limit ${techLimit}%).`,
    });
  }
  if (merged.length < 3) {
    merged.push({
      severity: "info",
      title: "Upcoming Earnings",
      detail: "Several holdings may report earnings this week — review position sizing.",
    });
  }
  return merged.slice(0, 4);
}
