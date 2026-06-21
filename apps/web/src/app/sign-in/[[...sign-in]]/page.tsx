import { Suspense } from "react";
import { SignIn } from "@clerk/nextjs";
import { AuthBrandHeader } from "@/components/auth/AuthBrandHeader";
import { DemoLoginForm } from "@/components/auth/DemoLoginForm";
import { isClerkEnabled } from "@/lib/auth-config";
import { clerkAppearance } from "@/lib/clerk-appearance";

function SignInContent() {
  if (!isClerkEnabled()) {
    return <DemoLoginForm />;
  }

  return (
    <SignIn
      appearance={clerkAppearance}
      routing="path"
      path="/sign-in"
      signUpUrl="/sign-up"
      forceRedirectUrl="/dashboard"
    />
  );
}

export default function SignInPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-6 py-12">
      <AuthBrandHeader />
      <div className="w-full max-w-md">
        <Suspense fallback={<div className="text-sm text-muted">Loading…</div>}>
          <SignInContent />
        </Suspense>
      </div>
    </div>
  );
}
