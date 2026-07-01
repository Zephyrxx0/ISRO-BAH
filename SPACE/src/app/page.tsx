"use client";

import { useState, useMemo } from "react";
import { generateMockPayload } from "../utils/mock-generator";
import TransitFitMatrix from "../components/transit-fit-matrix";
import ValidationEngine from "../components/validation-engine";
import CelestialRadar from "../components/celestial-radar";
import SimulationPanel from "../components/simulation-panel";
import CandidateTable from "../components/candidate-table";
import { StatCards } from "../components/stat-cards";

export default function Home() {
  const [currentHour, setCurrentHour] = useState<number>(0);
  const [selectedTicId, setSelectedTicId] = useState<string>("TIC 22522502");
  const [activeTab, setActiveTab] = useState<string>("candidates");

  const tabs = [
    { id: "candidates", label: "[ CANDIDATES ]" },
    { id: "diagnostics", label: `[ DIAGNOSTICS: ${selectedTicId} ]` },
    { id: "map", label: "[ STAR MAP ]" },
  ] as const;

  const payload = useMemo(() => {
    return generateMockPayload(currentHour);
  }, [currentHour]);

  const selectedCandidate = useMemo(() => {
    return (
      payload.candidates[selectedTicId] ||
      Object.values(payload.candidates)[0]
    );
  }, [payload, selectedTicId]);

  const allSignals = useMemo(() => {
    return Object.values(payload.candidates).map((c) => c.signal);
  }, [payload]);

  const handleSelectCandidate = (ticId: string) => {
    setSelectedTicId(ticId);
  };

  const totalCandidates = allSignals.length;
  const goldCount = allSignals.filter(
    (s) => s.confidenceTier === "GOLD"
  ).length;
  const planetCount = allSignals.filter(
    (s) => s.disposition === "CONFIRMED_PLANET"
  ).length;
  const avgSde =
    allSignals.length > 0
      ? allSignals.reduce((acc, s) => acc + s.sde, 0) / allSignals.length
      : 0;

  return (
    <div className="w-full">
      {/* STATS BAR */}
      <StatCards
        totalCandidates={totalCandidates}
        goldCount={goldCount}
        planetCount={planetCount}
        avgSde={avgSde}
      />

      {/* TAB NAVIGATION */}
      <div className="flex border-b border-[var(--border-color)] bg-[var(--panel)]">
        {tabs.map((tab, i) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`font-mono text-[10px] tracking-widest px-4 py-2 transition-colors ${
              i < tabs.length - 1
                ? "border-r border-[var(--border-color)]"
                : ""
            } ${
              activeTab === tab.id
                ? "bg-[var(--surface)] text-[var(--fg)] border-b-2 border-b-[var(--accent)]"
                : "text-[var(--fg-dim)] hover:text-[var(--fg)] hover:bg-[var(--surface)]"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* TAB CONTENT */}
      <div className="p-0">
        {activeTab === "candidates" && (
          <div>
            <CandidateTable
              candidates={allSignals}
              selectedTicId={selectedTicId}
              onSelectCandidate={handleSelectCandidate}
            />
          </div>
        )}

        {activeTab === "diagnostics" && (
          <div className="space-y-0">
            <div className="grid grid-cols-1 xl:grid-cols-4">
              <div className="xl:col-span-3">
                <TransitFitMatrix candidate={selectedCandidate} />
              </div>
              <div className="xl:col-span-1">
                <SimulationPanel
                  currentHour={currentHour}
                  onChangeHour={setCurrentHour}
                  payload={payload}
                />
              </div>
            </div>
            <ValidationEngine candidate={selectedCandidate} />
          </div>
        )}

        {activeTab === "map" && (
          <div className="h-[calc(100vh-9rem)] w-full">
            <CelestialRadar
              candidates={allSignals}
              selectedTicId={selectedTicId}
              onSelectCandidate={handleSelectCandidate}
            />
          </div>
        )}
      </div>
    </div>
  );
}
