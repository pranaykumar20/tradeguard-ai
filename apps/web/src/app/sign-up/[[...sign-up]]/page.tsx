import { SignUp } from "@clerk/nextjs";
import { AuthBrandHeader } from "@/components/auth/AuthBrandHeader";
import { DemoSignUpForm } from "@/components/auth/DemoSignUpForm";
import { isClerkEnabled } from "@/lib/auth-config";
import { clerkAppearance } from "@/lib/clerk-appearance";

export default function SignUpPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-6 py-12">
      <AuthBrandHeader />
      <div className="w-full max-w-md">
        {isClerkEnabled() ? (
          <SignUp
            appearance={clerkAppearance}
            routing="path"
            path="/sign-up"
            signInUrl="/sign-in"
            forceRedirectUrl="/onboarding"
          />
        ) : (
          <DemoSignUpForm />
        )}
      </div>
    </div>
  );
}
