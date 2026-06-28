'use client';

import { useEffect, useState, useRef } from 'react';
import { PipelinePayload } from '../../outputs/integration-schema';
import { Terminal, Play, RotateCcw, AlertTriangle, ShieldCheck } from 'lucide-react';

interface SimulationPanelProps {
  currentHour: number;
  onChangeHour: (hour: number) => void;
  payload: PipelinePayload;
}

export default function SimulationPanel({
  currentHour,
  onChangeHour,
  payload
}: SimulationPanelProps) {
  const [logs, setLogs] = useState<string[]>([]);
  const consoleEndRef = useRef<HTMLDivElement>(null);

  // Generate logs based on hour
  useEffect(() => {
    const time = new Date(payload.timestamp).toLocaleTimeString();
    if (currentHour === 0) {
      setLogs([
        `[${time}] [SYS_INIT] EXOPLANET SIGNAL ENGINE BOOTSTRAP COMPLETE.`,
        `[${time}] [DAT_LOAD] LOADING TESS LIGHT CURVE ARCHIVES (SECTORS 1-26).`,
        `[${time}] [WARN] HIGH NOISE LEVEL DETECTED: UN-DETRENDED DATA MATRIX ACTIVE.`,
        `[${time}] [WARN] TRICERATOPS MCMC COMPUTE IS PENDING GPU ALLOCATION.`,
        `[${time}] [WARN] SHERLOCK RECOVERY TIMEOUT ON LOW SNR TARGETS (TIC 150428135).`,
        `[${time}] [SYS_WAIT] STATUS: STANDBY. AWAITING HOUR 18 DE-NOISED INFERENCE LAYER...`
      ]);
    } else {
      setLogs([
        `[${time}] [SYS_INIT] PIPELINE INFERENCE TRIGGERS AUTOMATIC RE-RUN.`,
        `[${time}] [PROC_DETREND] APPLIED BIWEIGHT DETRENDING & SHIELD FILTER OVERLAYS.`,
        `[${time}] [PROC_MCMC] TRICERATOPS RUNNING: 1,000,000 MCMC SAMPLE GENERATIONS COMPLETE.`,
        `[${time}] [PROC_SHERLOCK] SHERLOCK COMPLETED BLEND AND PERIODICITY STABILITY SWEEPS.`,
        `[${time}] [SYS_SYNC] HOUR 18 INFERENCE METRICS LANDED AT FRONTEND MEMORY BUFFER.`,
        `[${time}] [SYS_SUCCESS] PIPELINE TARGETS RE-VALUATED: GOLD:[3] SILVER:[0] BRONZE:[0] FP:[2]`,
        `[${time}] [SYS_STREAM] STREAMING REAL-TIME SPECTRAL PARAMETRIC COEFFICIENTS...`
      ]);
    }
  }, [currentHour, payload.timestamp]);

  // Scroll to bottom of terminal logs
  useEffect(() => {
    if (consoleEndRef.current) {
      consoleEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs]);

  const isH18 = currentHour >= 18;

  return (
    <div className="border border-border-brutal bg-[#FAFAFA] flex flex-col h-full">
      {/* Panel Header */}
      <div className="p-4 border-b border-border-brutal bg-[#FAFAFA] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Terminal className="w-4 h-4 text-zinc-950" />
          <span className="text-[10px] uppercase font-bold tracking-wider text-zinc-900">
            INTEGRATION CONTROL & PHASE 4 SIMULATION DECK
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${isH18 ? 'bg-signal-green animate-ping' : 'bg-warning-amber animate-pulse'}`}></span>
          <span className="text-[9px] text-zinc-900 uppercase font-mono font-bold">
            {isH18 ? 'STATUS: PIPELINE STREAMING' : 'STATUS: BASELINE STANDBY'}
          </span>
        </div>
      </div>

      <div className="p-4 flex-1 flex flex-col space-y-4 justify-between">
        {/* State Selection Controls */}
        <div className="grid grid-cols-2 gap-3">
          <button
            onClick={() => onChangeHour(0)}
            className={`flex items-center justify-center gap-2 border px-3 py-2 text-[10px] uppercase font-bold cursor-pointer transition-all ${
              !isH18
                ? 'bg-zinc-900 text-zinc-50 border-zinc-900'
                : 'bg-zinc-50 text-zinc-800 border-border-brutal hover:bg-zinc-100'
            }`}
          >
            <RotateCcw className="w-3.5 h-3.5" />
            Engage Hour 0 [Static Baseline]
          </button>
          <button
            onClick={() => onChangeHour(18)}
            className={`flex items-center justify-center gap-2 border px-3 py-2 text-[10px] uppercase font-bold cursor-pointer transition-all ${
              isH18
                ? 'bg-signal-green text-zinc-900 border-signal-green font-bold'
                : 'bg-zinc-50 text-zinc-800 border-border-brutal hover:bg-zinc-100'
            }`}
          >
            <Play className="w-3.5 h-3.5" />
            Engage Hour 18 [Live Inference]
          </button>
        </div>

        {/* Technical schema stats grid */}
        <div className="grid grid-cols-3 gap-2 bg-zinc-50 border border-border-brutal p-3 text-[9px] font-mono">
          <div>
            <div className="text-raw-zinc uppercase">SCHEMA CONTRACT</div>
            <div className="font-bold text-zinc-950 mt-0.5">/outputs/integration-schema.ts</div>
          </div>
          <div>
            <div className="text-raw-zinc uppercase">PAYLOAD TIMESTAMP</div>
            <div className="font-bold text-zinc-950 mt-0.5 truncate">{payload.timestamp}</div>
          </div>
          <div>
            <div className="text-raw-zinc uppercase">PIPELINE VERSION</div>
            <div className="font-bold text-zinc-950 mt-0.5">{payload.pipelineVersion}</div>
          </div>
          <div>
            <div className="text-raw-zinc uppercase">ACTIVE CANDIDATES</div>
            <div className="font-bold text-zinc-950 mt-0.5">{Object.keys(payload.candidates).length} STAR TARGETS</div>
          </div>
          <div>
            <div className="text-raw-zinc uppercase">VALIDATION ENGINES</div>
            <div className="font-bold text-zinc-950 mt-0.5">TRICERATOPS + SHERLOCK</div>
          </div>
          <div>
            <div className="text-raw-zinc uppercase">SIMULATION HOURS</div>
            <div className="font-bold text-zinc-950 mt-0.5">ELAPSED: H{currentHour.toString().padStart(2, '0')}:00</div>
          </div>
        </div>

        {/* Terminal Logs Display */}
        <div className="flex-1 flex flex-col justify-between">
          <span className="text-[8px] text-raw-zinc uppercase font-bold mb-1.5 flex items-center gap-1">
            TERMINAL STDOUT PIPELINE BUFFER
          </span>
          <div className="h-[140px] border border-border-brutal bg-zinc-950 text-zinc-50 p-2 font-mono text-[9px] overflow-y-auto space-y-1 select-none">
            {logs.map((log, idx) => (
              <div 
                key={idx} 
                className={`${
                  log.includes('[WARN]') 
                    ? 'text-warning-amber' 
                    : log.includes('[SYS_SUCCESS]') 
                    ? 'text-signal-green' 
                    : log.includes('[CRITICAL]') 
                    ? 'text-blending-red' 
                    : 'text-zinc-300'
                }`}
              >
                {log}
              </div>
            ))}
            <div ref={consoleEndRef} />
          </div>
        </div>
      </div>
    </div>
  );
}
