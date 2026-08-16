"use client";

import { Suspense, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { createClient } from "@/lib/supabase";

function CallbackHandler() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    async function handle() {
      const supabase = createClient();
      const code = searchParams.get("code");
      if (code) {
        await supabase.auth.exchangeCodeForSession(code);
      }
      const { data: { session } } = await supabase.auth.getSession();
      router.push(session ? "/dashboard" : "/login");
      router.refresh();
    }
    handle();
  }, [router, searchParams]);

  return (
    <main className="flex min-h-screen items-center justify-center bg-bg">
      <div className="flex items-center gap-3 text-text-secondary">
        <div className="h-5 w-5 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        <span className="text-sm">Completing sign-in…</span>
      </div>
    </main>
  );
}

export default function AuthCallbackPage() {
  return (
    <Suspense>
      <CallbackHandler />
    </Suspense>
  );
}
