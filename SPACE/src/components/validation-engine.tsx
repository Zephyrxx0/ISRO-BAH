'use client';

import { CandidateEntry } from '../../outputs/integration-schema';
import { ShieldCheck, BarChart, CheckCircle2, XCircle, AlertTriangle } from 'lucide-react';

interface ValidationEngineProps {
  candidate: CandidateEntry;
}

export default function ValidationEngine({ candidate }: ValidationEngineProps) {
  const { triceratops, sherlock } = candidate.validation;

  // Convert probability to percentage string
  const toPercent = (val: number) => (val * 100).toFixed(4) + '%';

  // Sector status colors
  const statusIcon = (status: 'PASS' | 'FAIL') => {
    return status === 'PASS' ? (
      <span className="text-signal-green flex items-center gap-1">
        <CheckCircle2 className="w-3.5 h-3.5" /> PASS
      </span>
    ) : (
      <span className="text-blending-red flex items-center gap-1">
        <XCircle className="w-3.5 h-3.5" /> FAIL
      </span>
    );
  };

  const getRecoveryBadge = (status: string) => {
    switch (status) {
      case 'RECOVERED':
        return <span className="bg-signal-green/10 text-signal-green border border-signal-green/20 px-2 py-0.5 font-bold">RECOVERED</span>;
      case 'NOT_RECOVERED':
        return <span className="bg-blending-red/10 text-blending-red border border-blending-red/20 px-2 py-0.5 font-bold">NOT RECOVERED</span>;
      default:
        return <span className="bg-warning-amber/10 text-warning-amber border border-warning-amber/20 px-2 py-0.5 font-bold">INCOMPLETE DATA</span>;
    }
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {/* TRICERATOPS PANEL */}
      <div className="border border-border-brutal bg-background flex flex-col justify-between">
        <div className="p-4 border-b border-border-brutal bg-background flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-zinc-950" />
            <span className="text-[10px] uppercase font-bold tracking-wider text-zinc-900">
              TRICERATOPS MCMC VALIDATION INTERFACE
            </span>
          </div>
          <span className="text-[9px] text-raw-zinc uppercase font-mono">
            BAYESIAN PROBABILITY engine
          </span>
        </div>

        {/* Probability Tracks */}
        <div className="p-4 space-y-4 border-b border-border-brutal flex-1">
          {/* FPP Track */}
          <div>
            <div className="flex justify-between items-baseline mb-1">
              <span className="text-[10px] uppercase font-bold text-zinc-700">
                FALSE POSITIVE PROBABILITY (FPP)
              </span>
              <span className="text-xs font-mono font-bold text-zinc-900">
                {triceratops.fpp.toFixed(6)}
              </span>
            </div>
            <div className="h-4 border border-border-brutal bg-zinc-100 relative">
              <div 
                className={`h-full border-r border-border-brutal ${
                  triceratops.fpp > 0.5 
                    ? 'bg-blending-red' 
                    : triceratops.fpp > 0.01 
                    ? 'bg-warning-amber' 
                    : 'bg-signal-green'
                }`}
                style={{ width: `${Math.min(100, Math.max(1, triceratops.fpp * 100))}%` }}
              />
              <span className="absolute right-2 top-0 text-[8px] text-raw-zinc leading-4 font-mono font-bold">
                THRESHOLD &lt; 0.01
              </span>
            </div>
          </div>

          {/* NFPP Track */}
          <div>
            <div className="flex justify-between items-baseline mb-1">
              <span className="text-[10px] uppercase font-bold text-zinc-700">
                NON-TRANSITING FALSE POSITIVE PROBABILITY (NFPP)
              </span>
              <span className="text-xs font-mono font-bold text-zinc-900">
                {triceratops.nfpp.toFixed(6)}
              </span>
            </div>
            <div className="h-4 border border-border-brutal bg-zinc-100 relative">
              <div 
                className={`h-full border-r border-border-brutal ${
                  triceratops.nfpp > 0.1 
                    ? 'bg-blending-red' 
                    : triceratops.nfpp > 0.005 
                    ? 'bg-warning-amber' 
                    : 'bg-signal-green'
                }`}
                style={{ width: `${Math.min(100, Math.max(1, triceratops.nfpp * 100))}%` }}
              />
              <span className="absolute right-2 top-0 text-[8px] text-raw-zinc leading-4 font-mono font-bold">
                THRESHOLD &lt; 0.005
              </span>
            </div>
          </div>
        </div>

        {/* 3-way Split probability inspect */}
        <div className="grid grid-cols-3 divide-x divide-border-brutal border-t border-border-brutal bg-zinc-50 text-[10px]">
          <div className="p-3">
            <span className="text-[8px] text-raw-zinc uppercase font-bold">TRUE PLANET (TP)</span>
            <div className="text-sm font-mono font-bold mt-1 text-signal-green">
              {toPercent(triceratops.modes.tp)}
            </div>
            <div className="text-[8px] text-raw-zinc mt-1 uppercase font-mono truncate">
              Scenario: Keplerian Transit
            </div>
          </div>
          <div className="p-3">
            <span className="text-[8px] text-raw-zinc uppercase font-bold">ECLIPSING BINARY (EB)</span>
            <div className={`text-sm font-mono font-bold mt-1 ${triceratops.modes.eb > 0.1 ? 'text-warning-amber' : 'text-zinc-700'}`}>
              {toPercent(triceratops.modes.eb)}
            </div>
            <div className="text-[8px] text-raw-zinc mt-1 uppercase font-mono truncate">
              Scenario: Stellar Eclipse
            </div>
          </div>
          <div className="p-3">
            <span className="text-[8px] text-raw-zinc uppercase font-bold">BLEND (HEB/BGOB)</span>
            <div className={`text-sm font-mono font-bold mt-1 ${triceratops.modes.bgob + triceratops.modes.heb > 0.1 ? 'text-blending-red' : 'text-zinc-700'}`}>
              {toPercent(triceratops.modes.bgob + triceratops.modes.heb)}
            </div>
            <div className="text-[8px] text-raw-zinc mt-1 uppercase font-mono truncate">
              Scenario: Contaminated Backg
            </div>
          </div>
        </div>
      </div>

      {/* SHERLOCK BENCHMARK PANEL */}
      <div className="border border-border-brutal bg-background flex flex-col justify-between">
        <div className="p-4 border-b border-border-brutal bg-background flex items-center justify-between">
          <div className="flex items-center gap-2">
            <BarChart className="w-4 h-4 text-zinc-950" />
            <span className="text-[10px] uppercase font-bold tracking-wider text-zinc-900">
              SHERLOCK PIPELINE RECOVERY CRITERIA
            </span>
          </div>
          <span className="text-[9px] text-raw-zinc uppercase font-mono">
            SECTOR STABILITY MATRIX
          </span>
        </div>

        {/* Sectors pass/fail grid */}
        <div className="p-4 flex-1">
          <div className="flex justify-between items-center mb-3">
            <span className="text-[10px] text-zinc-900 font-bold uppercase">
              OBSERVED SECTORS: [{sherlock.sectors.join(', ')}]
            </span>
            <div className="text-[9px] font-mono font-bold">
              STATUS: {getRecoveryBadge(sherlock.overallRecoveryStatus)}
            </div>
          </div>

          <div className="overflow-x-auto border border-border-brutal">
            <table className="w-full text-left border-collapse text-[10px] font-mono">
              <thead>
                <tr className="bg-zinc-100 border-b border-border-brutal text-[8px] text-zinc-600">
                  <th className="p-2 uppercase border-r border-border-brutal">SECTOR</th>
                  <th className="p-2 uppercase border-r border-border-brutal">PERIOD MATCH</th>
                  <th className="p-2 uppercase border-r border-border-brutal">DEPTH CONSISTENCY</th>
                  <th className="p-2 uppercase border-r border-border-brutal">RECOV SNR</th>
                  <th className="p-2 uppercase">DISPOSITION</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-brutal">
                {sherlock.passFailMatrix.map((val) => (
                  <tr key={val.sector} className="hover:bg-zinc-50">
                    <td className="p-2 font-bold border-r border-border-brutal bg-zinc-50">{val.sector.toString().padStart(2, '0')}</td>
                    <td className="p-2 border-r border-border-brutal">
                      {val.periodMatch ? 'TRUE' : 'FALSE'}
                    </td>
                    <td className="p-2 border-r border-border-brutal">
                      {val.depthConsistency ? 'CONSISTENT' : 'DEVIATING'}
                    </td>
                    <td className="p-2 border-r border-border-brutal font-bold">
                      {val.snr > 0 ? val.snr.toFixed(1) : '—'}
                    </td>
                    <td className="p-2 font-bold">
                      {statusIcon(val.status)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Warning messages if FPP is high or SHERLOCK failed */}
        <div className="p-3 border-t border-border-brutal bg-zinc-50 flex items-center justify-between text-[9px] font-mono">
          <div className="flex items-center gap-1.5 text-zinc-700">
            <AlertTriangle className="w-3.5 h-3.5 text-warning-amber" />
            {candidate.signal.disposition === 'CONFIRMED_PLANET' ? (
              <span>SIGNAL DETECTOR CLEAR. CONFIDENCE FIT METRICS STABLE.</span>
            ) : candidate.signal.disposition === 'BINARY_STAR_ECLIPSE' ? (
              <span className="text-warning-amber font-bold">WARNING: HIGH FPP INDICATES LIKELY ECLIPSING BINARY CONTAMINATION.</span>
            ) : (
              <span className="text-blending-red font-bold">CRITICAL: BACKGROUND STAR DETECTED IN SHERLOCK APERTURE BLEND.</span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
