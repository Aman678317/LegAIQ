"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Scale, LayoutDashboard, FolderOpen, FileText, BrainCircuit, Network,
  Clock, GitCompare, AlertTriangle, Search, MessageSquare, PenLine,
  FileBarChart, LogOut, Loader2, ChevronDown, Mic, Settings, ShieldAlert,
  Bot, Table, ScrollText, GitBranch, BarChart3,
} from "lucide-react";
import { createClient } from "@/lib/supabase";
import { getUserOrgs } from "@/lib/auth";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import { OfflineBanner, UpdateAvailableBanner, PWAInstallPrompt, SyncStatusBadge } from "@/components/offline-indicator";
import { pwaManager } from "@/lib/pwa";

const SIDEBAR_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/workflows", label: "Agent Workflows", icon: GitBranch },
  { href: "/command-center", label: "Command Center", icon: BarChart3 },
  { href: "/chat", label: "AI Chatbot (Ollama)", icon: Bot },
  { href: "/settings", label: "Settings", icon: Settings },
];

const CASE_ITEMS = [
  { slug: "", label: "Case Home", icon: FolderOpen },
  { slug: "documents", label: "Documents", icon: FileText },
  { slug: "review", label: "Review Tables", icon: Table },
  { slug: "contracts", label: "Contracts & Playbooks", icon: ScrollText },
  { slug: "analysis", label: "AI Analysis", icon: BrainCircuit },
  { slug: "property", label: "Property", icon: FileText },
  { slug: "ownership", label: "Ownership Chain", icon: Network },
  { slug: "timeline", label: "Property Timeline", icon: Clock },
  { slug: "comparison", label: "Document Comparison", icon: GitCompare },
  { slug: "risks", label: "Risks & Issues", icon: AlertTriangle },
  { slug: "research", label: "Legal Research", icon: Search },
  { slug: "questions", label: "Questions", icon: MessageSquare },
  { slug: "drafting", label: "Drafting", icon: PenLine },
  { slug: "reports", label: "Reports", icon: FileBarChart },
  { slug: "voice", label: "Voice Assistant", icon: Mic },
];

function CaseSidebar({ caseId }: { caseId: string }) {
  const rawPath = usePathname();
  const pathname = rawPath || "";
  const base = `/cases/${caseId}`;
  return (
    <div className="space-y-1">
      {CASE_ITEMS.map((item) => {
        const href = item.slug ? `${base}/${item.slug}` : base;
        const active = pathname === href;
        const Icon = item.icon;
        return (
          <Link
            key={item.label}
            href={href}
            className={cn(
              "flex items-center gap-2.5 rounded-lg px-3 py-2 text-[13px] font-medium transition-colors",
              active
                ? "bg-primary/15 text-blue-300"
                : "text-text-secondary hover:bg-bg-elevated hover:text-white"
            )}
          >
            <Icon size={16} className={active ? "text-primary" : "text-text-muted"} />
            {item.label}
          </Link>
        );
      })}
    </div>
  );
}

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const rawPathname = usePathname();
  const pathname = rawPathname || "";
  const [user, setUser] = useState<any>(null);
  const [orgs, setOrgs] = useState<any[]>([]);
  const [activeOrg, setActiveOrg] = useState<any>(null);
  const [caseName, setCaseName] = useState<string | null>(null);
  const [isPlatformAdmin, setIsPlatformAdmin] = useState(false);
  const [loading, setLoading] = useState(true);
  const [orgMenuOpen, setOrgMenuOpen] = useState(false);

  const caseMatch = pathname.match(/^\/cases\/([^/]+)/);

  // Initialize PWA
  useEffect(() => {
    pwaManager.initialize();
  }, []);

  useEffect(() => {
    async function init() {
      const h = typeof window !== 'undefined' ? window.location.hostname : '';
      const isLocal =
        h === 'localhost' ||
        h === '127.0.0.1' ||
        h.startsWith('192.168.') ||
        h.startsWith('10.') ||
        /^172\.(1[6-9]|2[0-9]|3[0-1])\./.test(h) ||
        h.endsWith('.local');
      const isDemoSupabase =
        isLocal &&
        (process.env.NEXT_PUBLIC_SUPABASE_URL?.includes('localhost') ||
         process.env.NEXT_PUBLIC_SUPABASE_URL?.includes('127.0.0.1') ||
         !process.env.NEXT_PUBLIC_SUPABASE_URL);

      if (isDemoSupabase) {
        // Mock user for local dev / local network testing
        setUser({ email: 'demo@example.com', id: 'demo-id' });
        setOrgs([{ organization: { id: 'demo-org', name: 'Jurisiva Workspace', slug: 'jurisiva' }, role: 'OWNER' }]);
        setActiveOrg({ id: 'demo-org', name: 'Jurisiva Workspace', slug: 'jurisiva' });
        setIsPlatformAdmin(true);
        setLoading(false);

        if (caseMatch) {
          try {
            const c = await api.getCase(caseMatch[1]);
            setCaseName(c?.name || "Case");
          } catch {
            setCaseName("Case");
          }
        } else {
          setCaseName(null);
        }
        return;
      }

      try {
        const supabase = createClient();
        const { data: { user } } = await supabase.auth.getUser();
        if (!user) {
          router.push("/login");
          return;
        }
        setUser(user);
        const orgMemberships = await getUserOrgs();
        setOrgs(orgMemberships);
        setActiveOrg(orgMemberships[0]?.organization || null);

        const { data: profile } = await supabase
          .from("profiles").select("is_platform_admin").eq("id", user.id).single();
        setIsPlatformAdmin(!!profile?.is_platform_admin);
      } catch {
        // Graceful fallback to demo workspace if Supabase fails on local network
        setUser({ email: 'demo@example.com', id: 'demo-id' });
        setOrgs([{ organization: { id: 'demo-org', name: 'Jurisiva Workspace', slug: 'jurisiva' }, role: 'OWNER' }]);
        setActiveOrg({ id: 'demo-org', name: 'Jurisiva Workspace', slug: 'jurisiva' });
        setIsPlatformAdmin(true);
      } finally {
        setLoading(false);
      }

      if (caseMatch) {
        const { data: c } = await supabase
          .from("cases").select("name").eq("id", caseMatch[1]).single();
        setCaseName(c?.name || "Case");
      } else {
        setCaseName(null);
      }
    }
    init();
  }, [pathname]);

  async function signOut() {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push("/");
    router.refresh();
  }

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-bg">
        <Loader2 className="h-6 w-6 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="flex min-h-screen bg-bg">
      {/* PWA & Offline UI - rendered at top level for proper positioning */}
      <OfflineBanner />
      <UpdateAvailableBanner />
      <PWAInstallPrompt />

      {/* Sidebar */}
      <aside className="fixed inset-y-0 left-0 z-40 flex w-60 flex-col border-r border-border bg-bg-surface">
        <Link href="/dashboard" className="flex h-16 items-center gap-2.5 border-b border-border px-5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-accent">
            <Scale className="text-white" size={16} />
          </div>
          <span className="text-base font-semibold text-white">
            Jurisiva<span className="text-primary"> AI</span>
          </span>
        </Link>

        <nav className="flex-1 space-y-6 overflow-y-auto p-3">
          <div className="space-y-1">
            {SIDEBAR_ITEMS.map((item) => {
              const Icon = item.icon;
              const active = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "flex items-center gap-2.5 rounded-lg px-3 py-2 text-[13px] font-medium transition-colors",
                    active
                      ? "bg-primary/15 text-blue-300"
                      : "text-text-secondary hover:bg-bg-elevated hover:text-white"
                  )}
                >
                  <Icon size={16} className={active ? "text-primary" : "text-text-muted"} />
                  {item.label}
                </Link>
              );
            })}
          </div>

          {caseMatch && (
            <div>
              <div className="mb-2 px-3 text-[11px] font-semibold uppercase tracking-wider text-text-muted">
                {caseName || "Case"}
              </div>
              <CaseSidebar caseId={caseMatch[1]} />
            </div>
          )}

          {isPlatformAdmin && (
            <div>
              <div className="mb-2 px-3 text-[11px] font-semibold uppercase tracking-wider text-red-400/80">
                Platform
              </div>
              <Link
                href="/admin"
                className={cn(
                  "flex items-center gap-2.5 rounded-lg px-3 py-2 text-[13px] font-medium transition-colors",
                  pathname.startsWith("/admin")
                    ? "bg-red-500/15 text-red-300"
                    : "text-text-secondary hover:bg-bg-elevated hover:text-white"
                )}
              >
                <ShieldAlert size={16} className={pathname.startsWith("/admin") ? "text-red-400" : "text-text-muted"} />
                Admin Panel
              </Link>
            </div>
          )}
        </nav>

        <div className="border-t border-border p-3">
          <button
            onClick={signOut}
            className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-[13px] font-medium text-text-secondary transition-colors hover:bg-bg-elevated hover:text-white"
          >
            <LogOut size={16} className="text-text-muted" />
            Sign out
          </button>
        </div>
      </aside>

      {/* Main */}
      <div className="ml-60 flex min-h-screen flex-1 flex-col">
        <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-border bg-bg/90 px-6 backdrop-blur-xl">
          <div className="flex items-center gap-3">
            {caseMatch && caseName && (
              <div className="flex items-center gap-2 text-sm">
                <Link href="/dashboard" className="text-text-muted hover:text-white">
                  Cases
                </Link>
                <span className="text-text-muted">/</span>
                <span className="font-medium text-white">{caseName}</span>
              </div>
            )}
          </div>

          <div className="flex items-center gap-4">
            <SyncStatusBadge />
            <div className="relative">
              <button
                onClick={() => setOrgMenuOpen(!orgMenuOpen)}
                className="flex items-center gap-2.5 rounded-lg border border-border bg-bg-surface px-3 py-1.5 text-sm text-text-secondary transition-colors hover:text-white"
              >
                <div className="flex h-6 w-6 items-center justify-center rounded bg-amber-500/20 text-xs font-semibold text-amber-300 border border-amber-500/30">
                  {(activeOrg?.name || "?")[0].toUpperCase()}
                </div>
                <span className="max-w-40 truncate">{activeOrg?.name || "No organization"}</span>
                <ChevronDown size={14} />
              </button>
              {orgMenuOpen && (
                <div className="absolute right-0 top-full mt-2 w-56 rounded-xl border border-border bg-bg-surface p-1.5 shadow-xl">
                  {orgs.map((m) => (
                    <button
                      key={m.organization.id}
                      onClick={() => {
                        setActiveOrg(m.organization);
                        setOrgMenuOpen(false);
                      }}
                      className="flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-sm text-text-secondary hover:bg-bg-elevated hover:text-white"
                    >
                      <span className="truncate">{m.organization.name}</span>
                      <span className="text-[10px] uppercase text-text-muted">{m.role}</span>
                    </button>
                  ))}
                  <div className="mt-1 border-t border-border pt-1.5">
                    <div className="px-3 py-2 text-xs text-text-muted">
                      Signed in as
                      <div className="truncate text-text-secondary">{user?.email}</div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </header>

        <main className="flex-1 p-6 lg:p-8">{children}</main>
      </div>
    </div>
  );
}
