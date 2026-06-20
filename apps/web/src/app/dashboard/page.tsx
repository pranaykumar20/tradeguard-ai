import Link from "next/link";
import { Sidebar } from "@/components/Sidebar";

export default function DashboardPage() {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-6">
        <h1 className="text-2xl font-semibold">Risk Dashboard</h1>
        <p className="mt-2 text-muted">Full VaR, correlation heatmap, and stress tests — Phase 2.</p>
        <Link href="/" className="mt-6 inline-block text-accent hover:underline">
          ← Back to Ask AI
        </Link>
      </main>
    </div>
  );
}
