"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Scale, Loader2 } from "lucide-react";
import { createClient } from "@/lib/supabase";
import { Button } from "@/components/ui";

export default function SignupPage() {
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [needsVerification, setNeedsVerification] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      setLoading(false);
      return;
    }

    // Quick local dev bypass for demo Supabase – avoids hanging spinner when services aren't up
    const isDemoSupabase = typeof window !== 'undefined' && window.location.hostname === 'localhost' && process.env.NEXT_PUBLIC_SUPABASE_URL?.includes('localhost');
    if (isDemoSupabase) {
      // Simulate successful signup locally
      setTimeout(() => {
        setLoading(false);
        router.push("/dashboard");
        router.refresh();
      }, 600);
      return;
    }

    const supabase = createClient();
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        data: { full_name: fullName },
        emailRedirectTo: `${window.location.origin}/auth/callback`,
      },
    });

    if (error) {
      setError(error.message);
      setLoading(false);
      return;
    }

    if (data.session) {
      // Email confirmation disabled — go straight in
      router.push("/dashboard");
      router.refresh();
    } else {
      setNeedsVerification(true);
      setLoading(false);
    }
  }

  if (needsVerification) {
    return (
      <main className="hero-glow flex min-h-screen items-center justify-center px-6">
        <div className="w-full max-w-md rounded-2xl border border-border bg-bg-surface p-8 text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-accent">
            <Scale className="text-white" size={24} />
          </div>
          <h1 className="text-xl font-semibold text-white">Verify your email</h1>
          <p className="mt-3 text-sm leading-relaxed text-text-secondary">
            We sent a confirmation link to <span className="text-white">{email}</span>.
            Click it to activate your Jurisiva account, then sign in.
          </p>
          <Button href="/login" variant="secondary" className="mt-6">
            Back to sign in
          </Button>
        </div>
      </main>
    );
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
          <h1 className="text-xl font-semibold text-white">Create your account</h1>
          <p className="mt-1 text-sm text-text-secondary">
            Start your first property case in minutes.
          </p>

          {error && (
            <div className="mt-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            <div>
              <label htmlFor="signup-name" className="mb-1.5 block text-sm font-medium text-text-secondary">
                Full name
              </label>
              <input
                id="signup-name"
                type="text"
                required
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className="w-full rounded-lg border border-border bg-bg px-3.5 py-2.5 text-sm text-white placeholder-text-muted outline-none transition-colors focus:border-primary"
                placeholder="Adv. Priya Sharma"
              />
            </div>
            <div>
              <label htmlFor="signup-email" className="mb-1.5 block text-sm font-medium text-text-secondary">
                Email
              </label>
              <input
                id="signup-email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-lg border border-border bg-bg px-3.5 py-2.5 text-sm text-white placeholder-text-muted outline-none transition-colors focus:border-primary"
                placeholder="you@firm.com"
              />
            </div>
            <div>
              <label htmlFor="signup-password" className="mb-1.5 block text-sm font-medium text-text-secondary">
                Password
              </label>
              <input
                id="signup-password"
                type="password"
                required
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-lg border border-border bg-bg px-3.5 py-2.5 text-sm text-white placeholder-text-muted outline-none transition-colors focus:border-primary"
                placeholder="At least 8 characters"
              />
            </div>
            <Button type="submit" className="w-full" disabled={loading}>
              {loading && <Loader2 size={16} className="animate-spin" />}
              Create account
            </Button>
          </form>

          <div className="mt-6 border-t border-border pt-6 text-center text-sm text-text-secondary">
            Already have an account?{" "}
            <Link href="/login" className="font-medium text-primary hover:text-blue-300">
              Sign in
            </Link>
          </div>
        </div>
      </div>
    </main>
  );
}
