import { cookies } from "next/headers";
import { DEMO_EMAIL_COOKIE, DEMO_SESSION_COOKIE } from "@/lib/auth-config";

export type DemoSession = {
  email: string;
  name: string;
};

export function readDemoSessionFromRequest(request: Request): DemoSession | null {
  const cookieHeader = request.headers.get("cookie") ?? "";
  const hasSession = cookieHeader.includes(`${DEMO_SESSION_COOKIE}=1`);
  if (!hasSession) return null;

  const match = cookieHeader.match(new RegExp(`${DEMO_EMAIL_COOKIE}=([^;]+)`));
  const email = match?.[1] ? decodeURIComponent(match[1]) : "demo@tradeguard.ai";
  const name = email.split("@")[0] || "Demo User";
  return { email, name };
}

export async function readDemoSessionFromCookies(): Promise<DemoSession | null> {
  const jar = await cookies();
  if (jar.get(DEMO_SESSION_COOKIE)?.value !== "1") return null;

  const email = jar.get(DEMO_EMAIL_COOKIE)?.value ?? "demo@tradeguard.ai";
  return { email, name: email.split("@")[0] || "Demo User" };
}

export function demoSessionCookieOptions(maxAgeSeconds = 60 * 60 * 24 * 7) {
  return {
    httpOnly: true,
    sameSite: "lax" as const,
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: maxAgeSeconds,
  };
}

export function demoEmailCookieOptions(maxAgeSeconds = 60 * 60 * 24 * 7) {
  return {
    httpOnly: false,
    sameSite: "lax" as const,
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: maxAgeSeconds,
  };
}
