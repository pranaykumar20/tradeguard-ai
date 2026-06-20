import { ChatPanel } from "@/components/ChatPanel";
import { RiskSnapshotPanel } from "@/components/RiskSnapshotPanel";
import { Sidebar } from "@/components/Sidebar";
import { PageHeader } from "@/components/ui/Card";

export default function HomePage() {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="mx-auto w-full max-w-[1400px] flex-1 p-7">
        <PageHeader
          title="AI Chat"
          subtitle="Connected: Demo portfolio · Phase 1 analysis only"
        />
        <div className="grid gap-[18px] lg:grid-cols-[1.35fr_0.85fr]">
          <ChatPanel />
          <RiskSnapshotPanel />
        </div>
      </main>
    </div>
  );
}
