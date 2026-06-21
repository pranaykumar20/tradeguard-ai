import Link from "next/link";

export function AuthBrandHeader() {
  return (
    <Link
      href="/"
      className="mb-8 flex items-center gap-2 text-xl font-extrabold tracking-tight"
    >
        <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-blue/15 text-lg text-blue">
          🛡
        </span>
        <span className="text-2xl">
          TradeGuard <span className="text-teal">AI</span>
        </span>
    </Link>
  );
}
