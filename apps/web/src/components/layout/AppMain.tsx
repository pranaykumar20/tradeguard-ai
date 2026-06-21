"use client";

import type { ReactNode } from "react";
import { useSidebarOptional } from "@/components/layout/SidebarContext";

export function AppMain({
  children,
  className = "",
  fullWidth = false,
  showMenuButton = true,
}: {
  children: ReactNode;
  className?: string;
  fullWidth?: boolean;
  showMenuButton?: boolean;
}) {
  const sidebar = useSidebarOptional();

  return (
    <main className={`flex-1 overflow-x-hidden p-5 lg:p-7 ${className}`.trim()}>
      {sidebar && showMenuButton && (
        <button
          type="button"
          aria-label="Open navigation menu"
          onClick={sidebar.openMobile}
          className="mb-4 inline-flex items-center gap-2 rounded-[12px] border border-card-border px-3 py-2 text-sm font-semibold text-muted transition hover:bg-white/[0.04] hover:text-foreground lg:hidden"
        >
          ☰ Menu
        </button>
      )}
      <div className={fullWidth ? "w-full" : "mx-auto w-full max-w-[1400px]"}>{children}</div>
    </main>
  );
}

export function AppPageCenter({ children }: { children: ReactNode }) {
  return (
    <main className="flex flex-1 items-center justify-center p-5 lg:p-7">
      <div className="w-full max-w-md">{children}</div>
    </main>
  );
}
