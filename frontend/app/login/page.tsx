"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Scale, Loader2 } from "lucide-react";
import { createClient } from "@/lib/supabase";
import { Button } from "@/components/ui";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resetSent, setResetSent] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const isDemoSupabase = typeof window !== 'undefined' && window.location.hostname === 'localhost' && process.env.NEXT_PUBLIC_SUPABASE_URL?.includes('localhost');
    if (isDemoSupabase) {
      // Mock login for local dev without real Supabase
      if (!email || !password) {
        setError("Email and password are required.");
        setLoading(false);
        return;
      }
      setTimeout(() => {
        setLoading(false);
        router.push("/dashboard");
        router.refresh();
      }, 600);
      return;
    }

    const supabase = createClient();
    const { error } = await supabase.auth.signInWithPassword({ email, password });

    if (error) {
      setError(error.message);
      setLoading(false);
      return;
    }
    router.push("/dashboard");
    router.refresh();
  }

  async function handleReset() {
    if (!email) {
      setError("Enter your email first, then click reset.");
      return;
    }
    const isDemoSupabase = typeof window !== 'undefined' && window.location.hostname === 'localhost' && process.env.NEXT_PUBLIC_SUPABASE_URL?.includes('localhost');
    if (isDemoSupabase) {
      setResetSent(true);
      setError(null);
      return;
    }
    const supabase = createClient();
    await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}/auth/callback`,
    });
    setResetSent(true);
    setError(null);
  }

  return (
    <main className="hero-glow flex min-h-screen items-center justify-center px-6">
      <div className="w-full max-w-md">
        <Link href="/" className="mb-8 flex items-center justify-center gap-2.5">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-accent">
            <Scale className="text-white" size={20} />
          </div>
          <span className="text-xl font-semibold text-white">
            Jurisiva<span className="text-primary"> AI</span>
          </span>
        </Link>

        <div className="rounded-2xl border border-border bg-bg-surface p-8">
          <h1 className="text-xl font-semibold text-white">Sign in</h1>
          <p className="mt-1 text-sm text-text-secondary">
            Welcome back. Access your case workspaces.
          </p>

          {resetSent && (
            <div className="mt-4 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-400">
              Password reset email sent. Check your inbox.
            </div>
          )}
          {error && (
            <div className="mt-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            <div>
              <label htmlFor="login-email" className="mb-1.5 block text-sm font-medium text-text-secondary">
                Email
              </label>
              <input
                id="login-email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-lg border border-border bg-bg px-3.5 py-2.5 text-sm text-white placeholder-text-muted outline-none transition-colors focus:border-primary"
                placeholder="you@firm.com"
              />
            </div>
            <div>
              <label htmlFor="login-password" className="mb-1.5 block text-sm font-medium text-text-secondary">
                Password
              </label>
              <input
                id="login-password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-lg border border-border bg-bg px-3.5 py-2.5 text-sm text-white placeholder-text-muted outline-none transition-colors focus:border-primary"
                placeholder="••••••••"
              />
            </div>
            <Button type="submit" className="w-full" disabled={loading}>
              {loading && <Loader2 size={16} className="animate-spin" />}
              Sign in
            </Button>
          </form>

          <button
            onClick={handleReset}
            className="mt-4 w-full text-center text-xs text-text-muted transition-colors hover:text-white"
          >
            Forgot your password?
          </button>

          <div className="mt-6 border-t border-border pt-6 text-center text-sm text-text-secondary">
            New to Jurisiva?{" "}
            <Link href="/signup" className="font-medium text-primary hover:text-blue-300">
              Create an account
            </Link>
          </div>
        </div>
      </div>
    </main>
  );
}
