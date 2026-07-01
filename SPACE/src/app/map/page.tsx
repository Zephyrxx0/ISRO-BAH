"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import CelestialRadar from "@/components/celestial-radar";
import { generateMockPayload } from "@/utils/mock-generator";

export default function MapPage() {
  const router = useRouter();
  const [payload] = useState(() => generateMockPayload(18));
  const allSignals = Object.values(payload.candidates).map((c) => c.signal);
  const [selectedTicId, setSelectedTicId] = useState("TIC 22522502");

  const handleSelectCandidate = (ticId: string) => {
    setSelectedTicId(ticId);
    router.push(`/star/${ticId.replace(" ", "")}`);
  };

  return (
    <div className="h-[calc(100vh-3rem)] w-full">
      <CelestialRadar
        candidates={allSignals}
        selectedTicId={selectedTicId}
        onSelectCandidate={handleSelectCandidate}
      />
    </div>
  );
}
