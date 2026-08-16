"use client";

import { useParams } from "next/navigation";
import VoicePanel from "@/components/voice/VoicePanel";

export default function VoicePage() {
  const { caseId } = useParams<{ caseId: string }>();
  if (!caseId) return null;
  return <VoicePanel caseId={caseId} />;
}
