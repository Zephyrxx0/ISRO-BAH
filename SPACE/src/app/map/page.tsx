"use client";

import { useState } from "react";
import CelestialRadar from "@/components/celestial-radar";
import { generateMockPayload } from "@/utils/mock-generator";

export default function MapPage() {
  const [payload] = useState(() => generateMockPayload(18));
  const allSignals = Object.values(payload.candidates).map((c) => c.signal);
  const [selectedTicId, setSelectedTicId] = useState("TIC 22522502");

  return (
    <div className="h-[calc(100vh-3rem)] w-full">
      <CelestialRadar
        candidates={allSignals}
        selectedTicId={selectedTicId}
        onSelectCandidate={setSelectedTicId}
      />
    </div>
  );
}
