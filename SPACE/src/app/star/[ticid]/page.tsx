"use client";

import { use, useMemo, useState } from "react";
import { generateMockPayload } from "@/utils/mock-generator";
import BreadcrumbNav from "@/components/breadcrumb-nav";
import ParameterCard from "@/components/parameter-card";
import DiagnosticPlot from "@/components/diagnostic-plot";
import ValidationEngine from "@/components/validation-engine";
import TransitFitMatrix from "@/components/transit-fit-matrix";
import SimulationPanel from "@/components/simulation-panel";
import { AISynthesisPanel } from "@/components/ai-synthesis-panel";
import CelestialRadar from "@/components/celestial-radar";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export default function StarDetailPage({
  params,
}: {
  params: Promise<{ ticid: string }>;
}) {
  const { ticid } = use(params);
  const [currentHour, setCurrentHour] = useState<number>(18);

  const payload = useMemo(() => generateMockPayload(currentHour), [currentHour]);
  const entry = payload.candidates[ticid.replace("TIC", "TIC ")];
  
  const allSignals = useMemo(() => {
    return Object.values(payload.candidates).map((c) => c.signal);
  }, [payload]);

  if (!entry) {
    return (
      <div className="w-full">
        <BreadcrumbNav ticId={ticid} />
        <div className="flex items-center justify-center h-64">
          <span className="font-mono text-sm text-[var(--accent)]">
            // CANDIDATE {ticid} NOT FOUND IN PIPELINE OUTPUTS
          </span>
        </div>
      </div>
    );
  }

  const { signal } = entry;
  const isGold = signal.confidenceTier === "GOLD" && signal.sde >= 7;

  return (
    <div className="w-full">
      <BreadcrumbNav ticId={signal.ticId} />

      <div className="space-y-0">
        <ParameterCard
          params={{
            period: signal.period,
            depth: signal.depth,
            duration: signal.duration,
            sde: signal.sde,
            snr: signal.snr,
            confidence_tier: signal.confidenceTier,
            disposition: signal.disposition,
          }}
        />

        <Tabs defaultValue="diagnostics" className="w-full mt-4">
          <TabsList className="mb-4 bg-[var(--panel)] border border-[var(--border-color)]">
            <TabsTrigger value="diagnostics" className="font-mono text-xs">Diagnostics</TabsTrigger>
            <TabsTrigger value="inspect" className="font-mono text-xs">Inspect</TabsTrigger>
            <TabsTrigger value="map" className="font-mono text-xs">Star Map</TabsTrigger>
          </TabsList>

          <TabsContent value="inspect" className="space-y-6">
            {isGold ? (
              <>
                {/* 4-Panel Diagnostics */}
                <div className="border border-[var(--border-color)] bg-[var(--surface)]">
                  <div className="px-4 py-2 border-b border-[var(--border-color)] bg-[var(--panel)]">
                    <span className="font-mono text-[10px] tracking-widest text-[var(--fg-dim)]">
                      [ DIAGNOSTICS SUMMARY ]
                    </span>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-px bg-[var(--border-color)]">
                    <DiagnosticPlot
                      pngPath={`/plots/${signal.ticId.replace(" ", "_")}/raw_detrended.png`}
                      htmlPath={`/plots/${signal.ticId.replace(" ", "_")}/raw_detrended.html`}
                      alt="Raw + Detrended Light Curve"
                    />
                    <DiagnosticPlot
                      pngPath={`/plots/${signal.ticId.replace(" ", "_")}/periodogram.png`}
                      htmlPath={`/plots/${signal.ticId.replace(" ", "_")}/periodogram.html`}
                      alt="TLS Periodogram"
                    />
                    <DiagnosticPlot
                      pngPath={`/plots/${signal.ticId.replace(" ", "_")}/phase_folded.png`}
                      htmlPath={`/plots/${signal.ticId.replace(" ", "_")}/phase_folded.html`}
                      alt="Phase-Folded + Model"
                    />
                    <DiagnosticPlot
                      pngPath={`/plots/${signal.ticId.replace(" ", "_")}/softmax.png`}
                      htmlPath={`/plots/${signal.ticId.replace(" ", "_")}/softmax.html`}
                      alt="Classifier Softmax"
                    />
                  </div>
                </div>

                {/* MCMC Corner Plot */}
                <DiagnosticPlot
                  pngPath={`/plots/${signal.ticId.replace(" ", "_")}/corner.png`}
                  htmlPath={null}
                  alt="MCMC Corner Plot"
                />

                {/* Validation Engine */}
                <ValidationEngine candidate={entry} />
              </>
            ) : (
              <div className="border border-[var(--border-color)] bg-[var(--surface)] p-8 text-center">
                <span className="font-mono text-xs text-[var(--fg-dim)]">
                  Full diagnostics available for SDE &ge; 7 Gold-tier candidates only.
                </span>
              </div>
            )}
          </TabsContent>

          <TabsContent value="diagnostics" className="space-y-6">
            {isGold ? (
              <>
                <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
                  <div className="xl:col-span-3">
                    <TransitFitMatrix candidate={entry} />
                  </div>
                  <div className="xl:col-span-1">
                    <SimulationPanel
                      currentHour={currentHour}
                      onChangeHour={setCurrentHour}
                      payload={payload}
                    />
                  </div>
                </div>
                <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
                  <div className="xl:col-span-2">
                    <ValidationEngine candidate={entry} />
                  </div>
                  <div className="xl:col-span-1">
                    <AISynthesisPanel candidate={entry} />
                  </div>
                </div>
              </>
            ) : (
              <div className="border border-[var(--border-color)] bg-[var(--surface)] p-8 text-center">
                <span className="font-mono text-xs text-[var(--fg-dim)]">
                  Interactive diagnostics available for SDE &ge; 7 Gold-tier candidates only.
                </span>
              </div>
            )}
          </TabsContent>

          <TabsContent value="map" className="space-y-4">
            <div className="h-[600px] w-full border border-[var(--border-color)] rounded-md overflow-hidden bg-[var(--surface)]">
              <CelestialRadar
                candidates={allSignals}
                selectedTicId={signal.ticId}
                onSelectCandidate={(id) => {}}
              />
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
