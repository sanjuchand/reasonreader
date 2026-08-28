"use client";

import { GoogleLogin, GoogleOAuthProvider } from "@react-oauth/google";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { BookOpen } from "lucide-react";
import { useAuth } from "@/components/AuthProvider";

const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || "";

function LoginPanel() {
  const { user, loading, setUser } = useAuth();
  const router = useRouter();
  const [error, setError] = useState("");

  if (!loading && user) {
    router.replace("/");
    return <div className="h-screen bg-[#1c2d24]" />;
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#1c2d24] px-4">
      <div className="w-full max-w-md rounded-lg border border-white/10 bg-[#17241d] px-8 py-10 text-[#efe6d4]">
        <div className="mb-6 flex items-center gap-2">
          <BookOpen className="size-5 text-[#c4a15a]" />
          <span className="text-[15px] font-semibold tracking-wide">The Wealth of Nations</span>
        </div>
        <p className="text-[11px] tracking-[0.14em] text-[#c4a15a] uppercase">Chapter-mastery tutor</p>
        <h1 className="mt-2 font-[family-name:var(--font-serif)] text-[28px] leading-tight">
          Sign in to keep your place in Smith.
        </h1>
        <p className="mt-3 text-[14px] leading-relaxed text-[#cbbda4]">
          Progress is stored per Google account. Another reader on this machine will not overwrite yours.
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
                  router.replace("/");
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
        {error ? <p className="mt-4 text-[13px] text-[#e2b1a0]">{error}</p> : null}
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <GoogleOAuthProvider clientId={clientId}>
      <LoginPanel />
    </GoogleOAuthProvider>
  );
}
