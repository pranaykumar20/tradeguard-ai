import type { Metadata } from "next";
import { LandingPage } from "@/components/landing/LandingPage";

export const metadata: Metadata = {
  title: "TradeGuard AI — Know Your Risk Before Every Trade",
  description:
    "AI-powered portfolio risk management with real-time dashboards, trade guardrails, and an intelligent risk copilot. Free during beta.",
  openGraph: {
    title: "TradeGuard AI — Portfolio Risk Manager",
    description:
      "LLM orchestration, ML signals, and a code-based risk engine to protect your portfolio.",
    type: "website",
  },
};

export default function HomePage() {
  return <LandingPage />;
}
