import { Sidebar } from "@/components/Sidebar";

export default function ApprovalsPage() {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-6">
        <h1 className="text-2xl font-semibold">Trade Approvals</h1>
        <p className="mt-2 text-muted">
          Manual approve/reject flow for Agentic account orders — Phase 3.
        </p>
      </main>
    </div>
  );
}
