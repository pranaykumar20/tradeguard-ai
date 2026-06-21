import Link from "next/link";
import { AppPageCenter } from "@/components/layout/AppMain";

export default function AccessDeniedPage() {
  return (
    <AppPageCenter>
      <div className="tg-card text-center !rounded-[24px]">
        <div className="text-4xl">🔒</div>
        <h1 className="mt-4 text-2xl font-extrabold">Access denied</h1>
        <p className="mt-3 text-sm leading-relaxed text-muted">
          You don&apos;t have permission to view this page. Contact your platform admin if you
          need access.
        </p>
        <div className="mt-6 flex flex-wrap justify-center gap-3">
          <Link
            href="/dashboard"
            className="rounded-[14px] bg-teal px-5 py-2.5 text-sm font-bold text-[#041018] hover:brightness-110"
          >
            Go to dashboard
          </Link>
          <Link
            href="/"
            className="rounded-[14px] border border-card-border px-5 py-2.5 text-sm font-bold hover:bg-white/[0.04]"
          >
            Back to home
          </Link>
        </div>
      </div>
    </AppPageCenter>
  );
}
