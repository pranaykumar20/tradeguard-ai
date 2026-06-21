export const DEMO_SESSION_COOKIE = "tg_demo_session";
export const DEMO_EMAIL_COOKIE = "tg_demo_email";

export function isClerkEnabled() {
  return Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY?.trim());
}

/** Demo login is active when Clerk is not configured. */
export function isDemoAuthEnabled() {
  return !isClerkEnabled();
}

export const DEMO_CREDENTIALS = {
  email: "demo@tradeguard.ai",
  password: "demo",
} as const;
