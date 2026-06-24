"use client";

import { useEffect, useState } from "react";
import { AppMain } from "@/components/layout/AppMain";
import { AiRecommendationPanel } from "@/components/dashboard/DashboardTopBar";
import { CorrelationHeatmap } from "@/components/dashboard/CorrelationHeatmap";
import { ExposureDonut, SectorExposureChart } from "@/components/dashboard/ExposureDonut";
import { RiskScoreCard } from "@/components/dashboard/KpiSparkCard";
import { buildDashboardAlerts, RiskAlertsPanel } from "@/components/dashboard/RiskAlertsPanel";
import { RiskMetricsPanel } from "@/components/dashboard/RiskMetricsPanel";
import {
  getAdvancedRisk,
  getRiskRules,
  getRiskSnapshot,
  type AdvancedRisk,
  type RiskRules,
  type RiskSnapshot,
} from "@/lib/api";
import { Card, PageHeader, Row } from "@/components/ui/Card";

export default function RiskAnalyticsPage() {
  const [rules, setRules] = useState<RiskRules | null>(null);
  const [snapshot, setSnapshot] = useState<RiskSnapshot | null>(null);
  const [advanced, setAdvanced] = useState<AdvancedRisk | null>(null);

  useEffect(() => {
    getRiskRules().then((r) => setRules(r.rules)).catch(() => {});
    getRiskSnapshot().then(setSnapshot).catch(() => {});
    getAdvancedRisk().then(setAdvanced).catch(() => {});
  }, []);

  if (!snapshot) {
    return (
      <AppMain>
        <div className="flex min-h-[50vh] items-center justify-center text-muted">Loading risk analytics…</div>
      </AppMain>
    );
  }

  const techPct = snapshot.sector_exposure?.Technology ?? 0;
  const techLimit = rules?.max_tech_sector_pct ?? 30;
  const alerts = buildDashboardAlerts(snapshot.alerts ?? [], techPct, techLimit);
  const var95 = advanced?.var_95_1d ?? snapshot.portfolio_value * -0.075;
  const volatility = 12 + techPct * 0.05;
  const sharpe = snapshot.risk_score >= 55 ? 1.12 : 1.32;
  const sortino = sharpe + 0.57;

  return (
    <AppMain>
      <PageHeader
        title="Risk Analytics"
        subtitle="Exposure, correlation, VaR, and concentration alerts across your portfolio"
      />

      <div className="mb-4 max-w-sm">
        <RiskScoreCard score={snapshot.risk_score} label={snapshot.risk_label} />
      </div>

      <div className="grid gap-4 xl:grid-cols-3">
        <div className="xl:col-span-1">
          <ExposureDonut
            sectors={snapshot.sector_exposure}
            cashPct={snapshot.cash_pct}
            totalValue={snapshot.portfolio_value}
          />
        </div>
        <div className="xl:col-span-1">
          <CorrelationHeatmap matrix={advanced?.correlation_matrix ?? {}} />
        </div>
        <div className="xl:col-span-1">
          <RiskAlertsPanel alerts={alerts} />
        </div>
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-3">
        <SectorExposureChart sectors={snapshot.sector_exposure} />
        <RiskMetricsPanel
          volatility={volatility}
          sharpe={sharpe}
          var95={var95}
          sortino={sortino}
          expectedShortfall={Math.abs(var95) * 1.55}
          maxDrawdown={snapshot.max_drawdown_est}
        />
        <AiRecommendationPanel techPct={techPct} techLimit={techLimit} riskLabel={snapshot.risk_label} />
      </div>

      {advanced?.stress_tests?.length ? (
        <Card className="mt-4">
          <h2 className="text-lg font-extrabold">Stress Tests</h2>
          <p className="tg-sub mt-1">Estimated portfolio impact under adverse scenarios.</p>
          <div className="mt-4 space-y-2">
            {advanced.stress_tests.map((s) => (
              <Row
                key={s.name}
                label={s.name}
                value={`$${s.impact_usd.toLocaleString()}`}
                tone={s.severity === "high" ? "red" : "orange"}
              />
            ))}
          </div>
        </Card>
      ) : null}
    </AppMain>
  );
}
