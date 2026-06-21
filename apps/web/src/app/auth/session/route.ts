import { NextResponse } from "next/server";
import { isClerkEnabled } from "@/lib/auth-config";
import { readDemoSessionFromCookies } from "@/lib/demo-session";

export async function GET() {
  if (isClerkEnabled()) {
    return NextResponse.json({ mode: "clerk" });
  }

  const session = await readDemoSessionFromCookies();
  if (!session) {
    return NextResponse.json({ mode: "demo", signedIn: false });
  }

  return NextResponse.json({
    mode: "demo",
    signedIn: true,
    user: session,
  });
}
