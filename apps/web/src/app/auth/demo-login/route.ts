import { NextResponse } from "next/server";
import {
  DEMO_CREDENTIALS,
  DEMO_EMAIL_COOKIE,
  DEMO_SESSION_COOKIE,
} from "@/lib/auth-config";
import { demoEmailCookieOptions, demoSessionCookieOptions } from "@/lib/demo-session";

type LoginBody = {
  email?: string;
  password?: string;
  name?: string;
};

export async function POST(request: Request) {
  let body: LoginBody = {};
  try {
    body = (await request.json()) as LoginBody;
  } catch {
    return NextResponse.json({ error: "Invalid request body" }, { status: 400 });
  }

  const email = (body.email ?? "").trim().toLowerCase();
  const password = body.password ?? "";

  if (!email) {
    return NextResponse.json({ error: "Email is required" }, { status: 400 });
  }

  if (password !== DEMO_CREDENTIALS.password) {
    return NextResponse.json({ error: "Invalid email or password" }, { status: 401 });
  }

  const response = NextResponse.json({
    ok: true,
    user: {
      email,
      name: body.name?.trim() || email.split("@")[0] || "Demo User",
    },
  });

  response.cookies.set(DEMO_SESSION_COOKIE, "1", demoSessionCookieOptions());
  response.cookies.set(DEMO_EMAIL_COOKIE, email, demoEmailCookieOptions());

  return response;
}
