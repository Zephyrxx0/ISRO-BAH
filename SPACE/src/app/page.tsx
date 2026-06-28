'use client';

import { useState, useMemo } from 'react';
import { generateMockPayload } from '../utils/mock-generator';
import TransitFitMatrix from '../components/transit-fit-matrix';
import ValidationEngine from '../components/validation-engine';
import CelestialRadar from '../components/celestial-radar';
import SimulationPanel from '../components/simulation-panel';
import CandidateTable from '../components/candidate-table';
import { Eye, Radio, Sparkles, AlertCircle, Compass } from 'lucide-react';

export default function Home() {
  const [currentHour, setCurrentHour] = useState<number>(0);
  const [selectedTicId, setSelectedTicId] = useState<string>('TIC 22522502'); // Default to WASP-121b

  // Fetch payload based on active simulation hour
  const payload = useMemo(() => {
    return generateMockPayload(currentHour);
  }, [currentHour]);

  // Extract selected candidate details
  const selectedCandidate = useMemo(() => {
    return payload.candidates[selectedTicId] || Object.values(payload.candidates)[0];
  }, [payload, selectedTicId]);

  // List of all candidate signals for the map/table
  const allSignals = useMemo(() => {
    return Object.values(payload.candidates).map((c) => c.signal);
  }, [payload]);

  const handleSelectCandidate = (ticId: string) => {
    setSelectedTicId(ticId);
    // Smooth scroll candidates table or other viewports into focus if needed
  };

  const isH18 = currentHour >= 18;

  return (
    <div className="flex-1 w-full max-w-[1600px] mx-auto p-4 md:p-6 space-y-6 select-none font-mono">
      {/* Brutalist App Header */}
      <header className="border border-border-brutal bg-[#FAFAFA] p-4 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Radio className="w-4 h-4 text-zinc-950 animate-signal-pulse" />
            <span className="text-[10px] font-bold text-zinc-900 tracking-wider uppercase">
              TESS EXOPLANET SIGNAL IDENTIFICATION MATRIX // PHASE 4 FRONTIER
            </span>
          </div>
          <h1 className="text-xl md:text-2xl font-bold tracking-tight text-zinc-950 mt-1 uppercase">
            AI-Enabled Exoplanet Detection from Noisy Light Curves
          </h1>
          <p className="text-[9px] text-raw-zinc uppercase tracking-wide mt-1">
            TRANSIT PHOTOMETRY PIPELINE // BAYESIAN TRICERATOPS MCMC // SHERLOCK SECTOR BENCHMARKING
          </p>
        </div>

        {/* Global Pipeline Indicators */}
        <div className="flex flex-wrap items-center gap-3 text-[10px]">
          <div className="border border-border-brutal bg-zinc-50 px-2.5 py-1 flex items-center gap-1.5 font-bold">
            <Compass className="w-3.5 h-3.5 text-zinc-900" />
            <span>REGION: CELESTIAL SOUTH</span>
          </div>
          
          <div className={`border px-2.5 py-1 flex items-center gap-1.5 font-bold uppercase transition-all ${
            isH18 
              ? 'bg-green-50 text-signal-green border-signal-green' 
              : 'bg-amber-50 text-warning-amber border-warning-amber'
          }`}>
            <Sparkles className="w-3.5 h-3.5" />
            <span>
              {isH18 ? 'INFERENCE ACTIVE (H18+)' : 'RAW BASELINE (H00)'}
            </span>
          </div>

          <div className="border border-border-brutal bg-zinc-50 px-2.5 py-1 text-raw-zinc font-bold">
            VER: {payload.pipelineVersion}
          </div>
        </div>
      </header>

      {/* Main Grid: Component 1 & Component 3 */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Component 1: Transit Plot */}
        <div className="xl:col-span-2">
          <TransitFitMatrix candidate={selectedCandidate} />
        </div>

        {/* Component 3: Celestial Map */}
        <div className="xl:col-span-1 h-full min-h-[400px]">
          <CelestialRadar
            candidates={allSignals}
            selectedTicId={selectedTicId}
            onSelectCandidate={handleSelectCandidate}
          />
        </div>
      </div>

      {/* Secondary Grid: Component 2 & Component 4 */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Component 2: TRICERATOPS + SHERLOCK Validation */}
        <div className="xl:col-span-2">
          <ValidationEngine candidate={selectedCandidate} />
        </div>

        {/* Component 4: Integration controls */}
        <div className="xl:col-span-1">
          <SimulationPanel
            currentHour={currentHour}
            onChangeHour={setCurrentHour}
            payload={payload}
          />
        </div>
      </div>

      {/* Component 5: Filterable Candidates Table */}
      <section className="w-full">
        <CandidateTable
          candidates={allSignals}
          selectedTicId={selectedTicId}
          onSelectCandidate={handleSelectCandidate}
        />
      </section>

      {/* Strict Brutalist Footer */}
      <footer className="border border-border-brutal bg-[#FAFAFA] p-4 flex flex-col md:flex-row justify-between items-center text-[9px] text-raw-zinc">
        <div className="flex items-center gap-1.5">
          <AlertCircle className="w-3.5 h-3.5 text-zinc-950" />
          <span>CONFIRM DATA SYNC SECURITY CERTIFICATE: SSL_SHIELD_V42</span>
        </div>
        <div className="mt-2 md:mt-0 font-bold uppercase tracking-wider">
          NASA ARCHIVE DATA // MIT RESEARCH COLLABORATION // FE-ASTRONOMY INTERCEPT
        </div>
      </footer>
    </div>
  );
}
