import { NextResponse } from "next/server";
import { DEMO_EMAIL_COOKIE, DEMO_SESSION_COOKIE } from "@/lib/auth-config";

export async function POST() {
  const response = NextResponse.json({ ok: true });
  response.cookies.set(DEMO_SESSION_COOKIE, "", { path: "/", maxAge: 0 });
  response.cookies.set(DEMO_EMAIL_COOKIE, "", { path: "/", maxAge: 0 });
  return response;
}
