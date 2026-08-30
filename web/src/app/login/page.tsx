"use client";

import { GoogleLogin, GoogleOAuthProvider } from "@react-oauth/google";
import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { BookOpen } from "lucide-react";
import { useAuth } from "@/components/AuthProvider";
import { safeNextPath } from "@/lib/copies-access";

const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || "";

function LoginPanel() {
  const { user, loading, setUser } = useAuth();
  const router = useRouter();
  const search = useSearchParams();
  const next = safeNextPath(search.get("next"));
  const [error, setError] = useState("");

  if (!loading && user) {
    router.replace(next);
    return <div className="h-screen bg-[#1c2d24]" />;
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#1c2d24] px-4">
      <div className="w-full max-w-md rounded-lg border border-white/10 bg-[#17241d] px-8 py-10 text-[#efe6d4]">
        <div className="mb-6 flex items-center gap-2">
          <BookOpen className="size-5 text-[#c4a15a]" />
          <span className="text-[15px] font-semibold tracking-wide">Ken</span>
        </div>
        <p className="text-[11px] tracking-[0.14em] text-[#c4a15a] uppercase">Close-reading tutor</p>
        <h1 className="mt-2 font-[family-name:var(--font-serif)] text-[28px] leading-tight">
          Sign in to save progress.
        </h1>
        <p className="mt-3 text-[14px] leading-relaxed text-[#cbbda4]">
          You can read Smith and try the tutor without an account. Sign in to keep progress or bring a copy you have the right to read.
        </p>
        <div className="mt-8">
          {clientId ? (
            <GoogleLogin
              onSuccess={async (res) => {
                if (!res.credential) return;
                try {
                  const response = await fetch("/api/auth/google", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ credential: res.credential }),
                  });
                  const data = await response.json();
                  if (!response.ok) throw new Error(data.detail || "Sign-in failed");
                  setUser(data);
                  router.replace(next);
                } catch (err) {
                  setError(err instanceof Error ? err.message : "Sign-in failed");
                }
              }}
              onError={() => setError("Google sign-in failed")}
              useOneTap={false}
            />
          ) : (
            <p className="text-[13px] text-[#e2b1a0]">Set NEXT_PUBLIC_GOOGLE_CLIENT_ID to enable Google sign-in.</p>
          )}
        </div>
        <button
          type="button"
          onClick={() => router.push("/")}
          className="mt-6 text-[13px] text-[#cbbda4] underline-offset-2 hover:text-white hover:underline"
        >
          Read Smith without signing in
        </button>
        {error ? <p className="mt-4 text-[13px] text-[#e2b1a0]">{error}</p> : null}
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <GoogleOAuthProvider clientId={clientId}>
      <Suspense fallback={<div className="h-screen bg-[#1c2d24]" />}>
        <LoginPanel />
      </Suspense>
    </GoogleOAuthProvider>
  );
}
