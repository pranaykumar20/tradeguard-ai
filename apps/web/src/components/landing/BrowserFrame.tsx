import type { ReactNode } from "react";

export function BrowserFrame({
  url,
  children,
  className = "",
}: {
  url: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={`tg-card overflow-hidden !rounded-[24px] !p-0 ${className}`}>
      <div className="border-b border-card-border bg-[#0a1422] px-5 py-3">
        <div className="flex items-center gap-2">
          <span className="h-3 w-3 rounded-full bg-red/80" />
          <span className="h-3 w-3 rounded-full bg-orange/80" />
          <span className="h-3 w-3 rounded-full bg-green/80" />
          <span className="ml-3 truncate text-xs font-semibold text-muted">{url}</span>
        </div>
      </div>
      <div className="relative bg-[#070f1a]">{children}</div>
    </div>
  );
}
