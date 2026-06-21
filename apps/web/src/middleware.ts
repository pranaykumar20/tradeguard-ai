import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";
import { NextResponse, type NextRequest } from "next/server";
import { isClerkEnabled } from "@/lib/auth-config";
import { readDemoSessionFromRequest } from "@/lib/demo-session";

const isPublicRoute = createRouteMatcher([
  "/",
  "/sign-in(.*)",
  "/sign-up(.*)",
  "/auth(.*)",
]);

const isProtectedRoute = createRouteMatcher([
  "/dashboard(.*)",
  "/portfolio(.*)",
  "/analysis(.*)",
  "/chat(.*)",
  "/monitoring(.*)",
  "/journal(.*)",
  "/approvals(.*)",
  "/onboarding(.*)",
  "/strategies(.*)",
  "/observability(.*)",
  "/automation(.*)",
  "/validation(.*)",
  "/admin(.*)",
  "/access-denied",
]);

function demoSignInRedirect(request: NextRequest) {
  const url = new URL("/sign-in", request.url);
  url.searchParams.set("redirect_url", request.nextUrl.pathname);
  return NextResponse.redirect(url);
}

function demoMiddleware(request: NextRequest) {
  if (isPublicRoute(request) || !isProtectedRoute(request)) {
    return NextResponse.next();
  }

  const demoSession = readDemoSessionFromRequest(request);
  if (!demoSession) {
    return demoSignInRedirect(request);
  }

  return NextResponse.next();
}

const clerkEnabled = isClerkEnabled();

export default clerkEnabled
  ? clerkMiddleware(async (auth, req) => {
      if (isPublicRoute(req) || !isProtectedRoute(req)) {
        return NextResponse.next();
      }
      await auth.protect();
      return NextResponse.next();
    })
  : demoMiddleware;

export const config = {
  matcher: [
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    "/(api|trpc)(.*)",
  ],
};
