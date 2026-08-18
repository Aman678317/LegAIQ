"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Gauge, Building2, Users, FolderOpen, ListTodo, Cpu, ScrollText, Bot,
  Loader2, ShieldAlert, ArrowLeft,
} from "lucide-react";
import { createClient } from "@/lib/supabase";
import { cn } from "@/lib/utils";

const ADMIN_NAV = [
  { href: "/admin", label: "Overview", icon: Gauge, exact: true },
  { href: "/admin/organizations", label: "Organizations", icon: Building2 },
  { href: "/admin/users", label: "Users", icon: Users },
  { href: "/admin/cases", label: "Cases", icon: FolderOpen },
  { href: "/admin/jobs", label: "Jobs", icon: ListTodo },
  { href: "/admin/ai-usage", label: "AI Usage", icon: Cpu },
  { href: "/admin/agent-runs", label: "Agent Runs", icon: Bot },
  { href: "/admin/audit", label: "Audit Log", icon: ScrollText },
];

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const rawPathname = usePathname();
  const pathname = rawPathname || "";
  const [isAdmin, setIsAdmin] = useState<boolean | null>(null);

  useEffect(() => {
    async function check() {
      const isDemoSupabase = typeof window !== 'undefined' && window.location.hostname === 'localhost' && (process.env.NEXT_PUBLIC_SUPABASE_URL?.includes('localhost') || !process.env.NEXT_PUBLIC_SUPABASE_URL);
      if (isDemoSupabase) {
        setIsAdmin(true);
        return;
      }
      try {
        const supabase = createClient();
        const { data: { user } } = await supabase.auth.getUser();
        if (!user) {
          router.push("/login");
          return;
        }
        const { data: profile } = await supabase
          .from("profiles").select("is_platform_admin").eq("id", user.id).single();
        // Backend enforces this too — this check only hides the UI
        setIsAdmin(!!profile?.is_platform_admin);
      } catch {
        setIsAdmin(true);
      }
    }
    check();
  }, [router]);

  if (isAdmin === null) {
    return (
      <div className="flex h-96 items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-primary" />
      </div>
    );
  }

  if (!isAdmin) {
    return (
      <div className="flex h-96 flex-col items-center justify-center text-center">
        <ShieldAlert size={32} className="mb-3 text-red-400" />
        <h2 className="text-base font-semibold text-white">Platform administrator access required</h2>
        <p className="mt-2 max-w-sm text-sm text-text-secondary">
          Your account does not have platform admin permissions. Promote your account
          by running the SQL in <code className="text-blue-300">supabase/migrations/011_admin.sql</code>.
        </p>
        <Link href="/dashboard" className="mt-6 flex items-center gap-1.5 text-sm text-primary hover:text-blue-300">
          <ArrowLeft size={14} /> Back to dashboard
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl">
      <div className="mb-6 flex items-center gap-3">
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-2">
          <ShieldAlert size={18} className="text-red-400" />
        </div>
        <div>
          <h1 className="text-xl font-semibold text-white">Platform Admin</h1>
          <p className="text-xs text-text-muted">Server-side enforced · All access is audit-logged</p>
        </div>
      </div>

      <div className="mb-6 flex flex-wrap gap-1.5">
        {ADMIN_NAV.map((item) => {
          const Icon = item.icon;
          const active = item.exact ? pathname === item.href : pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-2 rounded-lg px-3.5 py-2 text-[13px] font-medium transition-colors",
                active
                  ? "bg-primary/15 text-blue-300"
                  : "text-text-secondary hover:bg-bg-elevated hover:text-white"
              )}
            >
              <Icon size={15} />
              {item.label}
            </Link>
          );
        })}
      </div>

      {children}
    </div>
  );
}
