import { ChatPanel } from "@/components/ChatPanel";
import { RiskSnapshotPanel } from "@/components/RiskSnapshotPanel";
import { AppMain } from "@/components/layout/AppMain";
import { PageHeader } from "@/components/ui/Card";

export default function ChatPage() {
  return (
    <AppMain>
      <PageHeader
        title="AI Chat"
        subtitle="Connected: Demo portfolio · Phase 1 analysis only"
      />
      <div className="grid gap-[18px] lg:grid-cols-[1.35fr_0.85fr]">
        <ChatPanel />
        <RiskSnapshotPanel />
      </div>
    </AppMain>
  );
}
