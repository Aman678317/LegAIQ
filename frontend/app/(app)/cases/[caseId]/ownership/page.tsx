"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Network, Loader2, RefreshCw, Users, Landmark, Award, Clock } from "lucide-react";
import { api } from "@/lib/api";
import { Button, Card } from "@/components/ui";
import { OwnershipDAG } from "@/components/property/OwnershipDAG";
import { BSACertificateModal } from "@/components/property/BSACertificateModal";

export default function OwnershipPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const [caseData, setCaseData] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [isBSAModalOpen, setIsBSAModalOpen] = useState(false);

  useEffect(() => {
    api.getCase(caseId).then((res) => {
      setCaseData(res);
      setLoading(false);
    });
  }, [caseId]);

  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-white">13-30 Year Ownership Chain DAG</h1>
          <p className="mt-1 text-sm text-text-secondary">
            Chronological DAG reconstruction with title break detection and encumbrance timeline overlay.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={() => setIsBSAModalOpen(true)} className="flex items-center gap-1.5 bg-gradient-to-r from-amber-600 to-orange-600">
            <Award size={15} /> BSA 2023 Certificate
          </Button>
        </div>
      </div>

      {/* Main DAG Component */}
      <OwnershipDAG caseId={caseId} />

      {/* BSA 2023 Section 63 Certificate Modal */}
      <BSACertificateModal
        isOpen={isBSAModalOpen}
        onClose={() => setIsBSAModalOpen(false)}
        caseId={caseId}
        caseName={caseData?.name || "Matter Vault"}
      />
    </div>
  );
}
