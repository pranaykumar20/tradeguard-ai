"use client";

import { Suspense } from "react";
import OnboardingPageContent from "./OnboardingPageContent";

export default function OnboardingPage() {
  return (
    <Suspense fallback={<p className="p-8 text-muted">Loading onboarding…</p>}>
      <OnboardingPageContent />
    </Suspense>
  );
}
