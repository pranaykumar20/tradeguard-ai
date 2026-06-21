"use client";

import { AiRecommendationPanel } from "@/components/dashboard/DashboardTopBar";
import { CorrelationHeatmap } from "@/components/dashboard/CorrelationHeatmap";
import { ExposureDonut, SectorExposureChart } from "@/components/dashboard/ExposureDonut";
import { KpiSparkCard, RiskScoreCard } from "@/components/dashboard/KpiSparkCard";
import { RiskAlertsPanel } from "@/components/dashboard/RiskAlertsPanel";
import { RiskMetricsPanel } from "@/components/dashboard/RiskMetricsPanel";
import { BrowserFrame } from "@/components/landing/BrowserFrame";
import { LANDING_MOCK } from "@/lib/landing-content";

export function LandingDashboardPreview() {
  const mock = LANDING_MOCK;

  return (
    <section id="product" className="px-6 pb-20">
      <div className="mx-auto max-w-6xl">
        <div className="mb-10 text-center">
          <h2 className="text-3xl font-extrabold md:text-4xl">See your risk at a glance</h2>
          <p className="mx-auto mt-4 max-w-2xl text-muted">
            The same dashboard you get after sign-up — KPIs, exposure, correlations, alerts, and
            AI recommendations in one view.
          </p>
        </div>

        <BrowserFrame url="tradeguard.ai/dashboard">
          <div className="pointer-events-none select-none p-4 lg:p-5">
            <div className="mb-4 border-b border-white/10 pb-4">
              <h3 className="text-lg font-bold text-white">Portfolio Risk Dashboard</h3>
              <p className="text-sm text-muted">Real-time risk overview and AI-powered insights</p>
            </div>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <KpiSparkCard label="Daily P&L" value="+$1,842" subValue="+1.43%" tone="green" sparkPositive />
              <KpiSparkCard label="Weekly P&L" value="+$6,852" subValue="+5.33%" tone="green" sparkPositive />
              <KpiSparkCard label="Portfolio Value" value="$128,450" subValue="Total Holdings: 8" />
              <RiskScoreCard score={mock.riskScore} label={mock.riskLabel} />
            </div>

            <div className="mt-3 grid gap-3 xl:grid-cols-3">
              <div className="xl:col-span-1">
                <ExposureDonut
                  sectors={mock.sectors}
                  cashPct={mock.cashPct}
                  totalValue={mock.portfolioValue}
                />
              </div>
              <div className="xl:col-span-1">
                <CorrelationHeatmap matrix={mock.correlation} />
              </div>
              <div className="xl:col-span-1">
                <RiskAlertsPanel alerts={[...mock.alerts]} />
              </div>
            </div>

            <div className="mt-3 grid gap-3 lg:grid-cols-3">
              <SectorExposureChart sectors={mock.sectors} />
              <RiskMetricsPanel
                volatility={18.42}
                sharpe={1.12}
                var95={4280}
                sortino={1.69}
                expectedShortfall={5120}
                maxDrawdown={-8.4}
              />
              <AiRecommendationPanel
                techPct={mock.techPct}
                techLimit={mock.techLimit}
                riskLabel={mock.riskLabel}
              />
            </div>
          </div>
        </BrowserFrame>
      </div>
    </section>
  );
}
