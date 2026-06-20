import { Sidebar } from "@/components/Sidebar";

export default function PortfolioPage() {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-6">
        <h1 className="text-2xl font-semibold">Portfolio</h1>
        <p className="mt-2 text-muted">
          Live holdings via Robinhood MCP — connect in Phase 3. See docs/MCP-SETUP.md.
        </p>
      </main>
    </div>
  );
}
