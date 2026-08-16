"use client";

import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import { Card, Badge } from "@/components/ui";
import { formatDate } from "@/lib/utils";

export default function AdminOrganizationsPage() {
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.adminOrganizations(100).then(setData).catch((e) => setError(e.message));
  }, []);

  if (error) return <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">{error}</div>;
  if (!data) return <div className="flex h-64 items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-primary" /></div>;

  return (
    <Card className="overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left text-xs uppercase tracking-wider text-text-muted">
              <th className="px-5 py-3 font-medium">Organization</th>
              <th className="px-5 py-3 font-medium">Plan</th>
              <th className="px-5 py-3 font-medium">Members</th>
              <th className="px-5 py-3 font-medium">Cases</th>
              <th className="px-5 py-3 font-medium">Created</th>
            </tr>
          </thead>
          <tbody>
            {data.items.map((org: any) => (
              <tr key={org.id} className="border-b border-border/50 hover:bg-bg-elevated/50">
                <td className="px-5 py-3">
                  <div className="font-medium text-white">{org.name}</div>
                  <div className="font-mono text-[11px] text-text-muted">{org.slug}</div>
                </td>
                <td className="px-5 py-3">
                  <Badge>{org.plan}</Badge>
                </td>
                <td className="px-5 py-3 text-white">{org.member_count}</td>
                <td className="px-5 py-3 text-white">{org.case_count}</td>
                <td className="px-5 py-3 text-text-secondary">{formatDate(org.created_at)}</td>
              </tr>
            ))}
            {data.items.length === 0 && (
              <tr><td colSpan={5} className="px-5 py-8 text-center text-text-muted">No organizations yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
