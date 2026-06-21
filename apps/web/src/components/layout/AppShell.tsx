"use client";

import type { ReactNode } from "react";
import { Sidebar, SIDEBAR_WIDTH_CLASS } from "@/components/Sidebar";
import { SidebarProvider, useSidebar } from "@/components/layout/SidebarContext";

function AppShellInner({ children }: { children: ReactNode }) {
  const { mobileOpen, closeMobile } = useSidebar();

  return (
    <div className="min-h-screen bg-[#070f1a]">
      <Sidebar />
      {mobileOpen && (
        <button
          type="button"
          aria-label="Close navigation menu"
          className="fixed inset-0 z-40 bg-black/60 lg:hidden"
          onClick={closeMobile}
        />
      )}
      <div className={`flex min-h-screen min-w-0 flex-col ${SIDEBAR_WIDTH_CLASS}`}>
        {children}
      </div>
    </div>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <SidebarProvider>
      <AppShellInner>{children}</AppShellInner>
    </SidebarProvider>
  );
}
