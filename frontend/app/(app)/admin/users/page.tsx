"use client";

import { useEffect, useState } from "react";
import { Loader2, Search, ShieldCheck, ShieldOff } from "lucide-react";
import { api } from "@/lib/api";
import { Card, Badge, Button } from "@/components/ui";
import { formatDate } from "@/lib/utils";

export default function AdminUsersPage() {
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState<string | null>(null);

  async function load(query?: string) {
    setData(null);
    api.adminUsers(100, 0, query).then(setData).catch((e) => setError(e.message));
  }

  useEffect(() => { load(); }, []);

  async function toggleAdmin(user: any) {
    setBusy(user.id);
    setError(null);
    try {
      await api.adminSetPlatformAdmin(user.id, !user.is_platform_admin);
      await load(q || undefined);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(null);
    }
  }

  if (error && !data) {
    return <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">{error}</div>;
  }

  return (
    <div className="space-y-4">
      {error && <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">{error}</div>}

      <form
        onSubmit={(e) => { e.preventDefault(); load(q || undefined); }}
        className="flex max-w-md gap-2"
      >
        <div className="flex flex-1 items-center gap-2 rounded-lg border border-border bg-bg-surface px-3">
          <Search size={14} className="text-text-muted" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search by email…"
            className="w-full bg-transparent py-2 text-sm text-white placeholder-text-muted outline-none"
          />
        </div>
        <Button type="submit" variant="secondary" size="sm">Search</Button>
      </form>

      {!data ? (
        <div className="flex h-64 items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-primary" /></div>
      ) : (
        <Card className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-xs uppercase tracking-wider text-text-muted">
                  <th className="px-5 py-3 font-medium">User</th>
                  <th className="px-5 py-3 font-medium">Signed up</th>
                  <th className="px-5 py-3 font-medium">Platform admin</th>
                  <th className="px-5 py-3 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((user: any) => (
                  <tr key={user.id} className="border-b border-border/50 hover:bg-bg-elevated/50">
                    <td className="px-5 py-3">
                      <div className="font-medium text-white">{user.full_name || "—"}</div>
                      <div className="text-xs text-text-muted">{user.email}</div>
                    </td>
                    <td className="px-5 py-3 text-text-secondary">{formatDate(user.created_at)}</td>
                    <td className="px-5 py-3">
                      {user.is_platform_admin ? (
                        <Badge className="border-amber-500/30 bg-amber-500/15 text-amber-400">
                          <ShieldCheck size={11} className="mr-1" /> Admin
                        </Badge>
                      ) : (
                        <Badge className="border-slate-500/30 bg-slate-500/15 text-slate-400">Standard</Badge>
                      )}
                    </td>
                    <td className="px-5 py-3 text-right">
                      <Button
                        size="sm"
                        variant={user.is_platform_admin ? "danger" : "secondary"}
                        disabled={busy === user.id}
                        onClick={() => toggleAdmin(user)}
                      >
                        {busy === user.id ? (
                          <Loader2 size={13} className="animate-spin" />
                        ) : user.is_platform_admin ? (
                          <><ShieldOff size={13} /> Revoke</>
                        ) : (
                          <><ShieldCheck size={13} /> Grant</>
                        )}
                      </Button>
                    </td>
                  </tr>
                ))}
                {data.items.length === 0 && (
                  <tr><td colSpan={4} className="px-5 py-8 text-center text-text-muted">No users found.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
