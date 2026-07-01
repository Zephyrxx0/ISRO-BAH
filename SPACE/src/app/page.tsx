'use client';

import { useState, useMemo } from 'react';
import { generateMockPayload } from '../utils/mock-generator';
import TransitFitMatrix from '../components/transit-fit-matrix';
import ValidationEngine from '../components/validation-engine';
import CelestialRadar from '../components/celestial-radar';
import SimulationPanel from '../components/simulation-panel';
import CandidateTable from '../components/candidate-table';
import { StatCards } from '../components/stat-cards';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

export default function Home() {
  const [currentHour, setCurrentHour] = useState<number>(0);
  const [selectedTicId, setSelectedTicId] = useState<string>('TIC 22522502');

  const payload = useMemo(() => {
    return generateMockPayload(currentHour);
  }, [currentHour]);

  const selectedCandidate = useMemo(() => {
    return payload.candidates[selectedTicId] || Object.values(payload.candidates)[0];
  }, [payload, selectedTicId]);

  const allSignals = useMemo(() => {
    return Object.values(payload.candidates).map((c) => c.signal);
  }, [payload]);

  const handleSelectCandidate = (ticId: string) => {
    setSelectedTicId(ticId);
  };

  const totalCandidates = allSignals.length;
  const goldCount = allSignals.filter(s => s.confidenceTier === 'GOLD').length;
  const planetCount = allSignals.filter(s => s.disposition === 'CONFIRMED_PLANET').length;
  const avgSde = allSignals.length > 0 ? allSignals.reduce((acc, s) => acc + s.sde, 0) / allSignals.length : 0;

  return (
    <div className="w-full p-4 md:p-6 space-y-6">
      <StatCards
        totalCandidates={totalCandidates}
        goldCount={goldCount}
        planetCount={planetCount}
        avgSde={avgSde}
      />

      <Tabs defaultValue="candidates" className="w-full">
        <TabsList className="mb-4 bg-secondary">
          <TabsTrigger value="candidates" className="data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:border-b-2 data-[state=active]:border-accent">Candidates</TabsTrigger>
          <TabsTrigger value="diagnostics" className="data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:border-b-2 data-[state=active]:border-accent">Diagnostics ({selectedTicId})</TabsTrigger>
          <TabsTrigger value="map" className="data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:border-b-2 data-[state=active]:border-accent">Star Map</TabsTrigger>
        </TabsList>

        <TabsContent value="candidates" className="space-y-4">
          <CandidateTable
            candidates={allSignals}
            selectedTicId={selectedTicId}
            onSelectCandidate={handleSelectCandidate}
          />
        </TabsContent>

        <TabsContent value="diagnostics" className="space-y-6">
          <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
            <div className="xl:col-span-2">
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
          <div className="grid grid-cols-1">
            <ValidationEngine candidate={selectedCandidate} />
          </div>
        </TabsContent>

        <TabsContent value="map" className="space-y-4">
          <div className="h-[600px] w-full border rounded-md overflow-hidden border-border">
            <CelestialRadar
              candidates={allSignals}
              selectedTicId={selectedTicId}
              onSelectCandidate={handleSelectCandidate}
            />
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
