import { ChatPanel } from "@/components/ChatPanel";
import { RiskSnapshotPanel } from "@/components/RiskSnapshotPanel";
import { Sidebar } from "@/components/Sidebar";

export default function HomePage() {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex flex-1 flex-col lg:flex-row">
        <section className="flex flex-1 flex-col p-4 lg:p-6">
          <div className="mb-4">
            <p className="text-xs uppercase tracking-widest text-accent">Phase 1 · Analysis Only</p>
            <h1 className="text-2xl font-semibold">Ask AI: Your investing risk assistant</h1>
          </div>
          <div className="min-h-[70vh] flex-1">
            <ChatPanel />
          </div>
        </section>
        <aside className="w-full border-t border-card-border p-4 lg:w-80 lg:border-t-0 lg:border-l lg:p-6">
          <RiskSnapshotPanel />
        </aside>
      </main>
    </div>
  );
}
