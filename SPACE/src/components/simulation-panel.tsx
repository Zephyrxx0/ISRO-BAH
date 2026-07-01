"use client";

import { useEffect, useState, useRef } from "react";
import { PipelinePayload } from "../../outputs/integration-schema";

interface SimulationPanelProps {
  currentHour: number;
  onChangeHour: (hour: number) => void;
  payload: PipelinePayload;
}

export default function SimulationPanel({
  currentHour,
  onChangeHour,
  payload,
}: SimulationPanelProps) {
  const [logs, setLogs] = useState<string[]>([]);
  const consoleEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const time = new Date(payload.timestamp).toLocaleTimeString();
    if (currentHour === 0) {
      setLogs([
        `[${time}] [SYS_INIT] EXOPLANET SIGNAL ENGINE BOOTSTRAP COMPLETE.`,
        `[${time}] [DAT_LOAD] LOADING TESS LIGHT CURVE ARCHIVES (SECTORS 1-3).`,
        `[${time}] [WARN] HIGH NOISE LEVEL DETECTED: UN-DETRENDED DATA MATRIX ACTIVE.`,
        `[${time}] [WARN] TRICERATOPS MCMC COMPUTE IS PENDING GPU ALLOCATION.`,
        `[${time}] [WARN] SHERLOCK RECOVERY TIMEOUT ON LOW SNR TARGETS.`,
        `[${time}] [SYS_WAIT] STATUS: STANDBY. AWAITING HOUR 18 DE-NOISED INFERENCE...`,
      ]);
    } else {
      setLogs([
        `[${time}] [SYS_INIT] PIPELINE INFERENCE TRIGGERS AUTOMATIC RE-RUN.`,
        `[${time}] [PROC_DETREND] APPLIED BIWEIGHT DETRENDING & SHIELD FILTER OVERLAYS.`,
        `[${time}] [PROC_MCMC] TRICERATOPS RUNNING: 1,000,000 MCMC SAMPLES COMPLETE.`,
        `[${time}] [PROC_SHERLOCK] SHERLOCK COMPLETED BLEND AND PERIODICITY STABILITY SWEEPS.`,
        `[${time}] [SYS_SYNC] HOUR 18 INFERENCE METRICS LANDED AT FRONTEND MEMORY BUFFER.`,
        `[${time}] [SYS_SUCCESS] PIPELINE TARGETS RE-VALUATED: GOLD:[3] SILVER:[0] BRONZE:[0] FP:[2]`,
        `[${time}] [SYS_STREAM] STREAMING REAL-TIME SPECTRAL PARAMETRIC COEFFICIENTS...`,
      ]);
    }
  }, [currentHour, payload.timestamp]);

  useEffect(() => {
    if (consoleEndRef.current) {
      consoleEndRef.current.scrollIntoView({ behavior: "auto" });
    }
  }, [logs]);

  const isH18 = currentHour >= 18;

  return (
    <div className="h-full flex flex-col border border-[var(--border-color)] bg-[var(--surface)]">
      {/* HEADER */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-[var(--border-color)] bg-[var(--panel)]">
        <span className="font-mono text-[10px] tracking-widest text-[var(--fg-dim)]">
          [ INTEGRATION CONTROL ]
        </span>
        <span
          className={`font-mono text-[10px] tracking-widest font-bold ${
            isH18 ? "text-[var(--terminal-green)]" : "text-[var(--fg-dim)]"
          }`}
        >
          {isH18 ? "STREAMING" : "STANDBY"}
        </span>
      </div>

      <div className="flex-1 flex flex-col p-4 space-y-4">
        {/* CONTROLS */}
        <div className="grid grid-cols-2 gap-2">
          <button
            onClick={() => onChangeHour(0)}
            className={`font-mono text-[10px] tracking-widest px-3 py-2 border transition-colors ${
              !isH18
                ? "bg-[var(--accent)] border-[var(--accent)] text-[var(--fg)]"
                : "border-[var(--border-color)] text-[var(--fg-dim)] hover:text-[var(--fg)] hover:border-[var(--fg-dim)]"
            }`}
          >
            [ H00 BASELINE ]
          </button>
          <button
            onClick={() => onChangeHour(18)}
            className={`font-mono text-[10px] tracking-widest px-3 py-2 border transition-colors ${
              isH18
                ? "bg-[var(--terminal-green)] border-[var(--terminal-green)] text-[var(--bg)] font-bold"
                : "border-[var(--border-color)] text-[var(--fg-dim)] hover:text-[var(--fg)] hover:border-[var(--fg-dim)]"
            }`}
          >
            [ H18 INFERENCE ]
          </button>
        </div>

        {/* TELEMETRY */}
        <div className="grid grid-cols-2 gap-1 bg-[var(--border-color)]">
          {[
            ["PAYLOAD", payload.timestamp],
            ["VERSION", payload.pipelineVersion],
            [
              "TARGETS",
              `${Object.keys(payload.candidates).length} ACTIVE`,
            ],
            ["SIM TIME", `H${currentHour.toString().padStart(2, "0")}:00`],
          ].map(([label, value]) => (
            <div key={label} className="bg-[var(--panel)] p-2">
              <span className="block font-mono text-[8px] text-[var(--fg-dim)] tracking-widest mb-0.5">
                {label}
              </span>
              <span className="font-mono text-[11px] text-[var(--fg)] tabular-nums font-bold">
                {value}
              </span>
            </div>
          ))}
        </div>

        {/* TERMINAL BUFFER */}
        <div className="flex-1 flex flex-col min-h-[140px]">
          <span className="font-mono text-[9px] text-[var(--fg-dim)] tracking-widest mb-2">
            [ TERMINAL PIPELINE BUFFER ]
          </span>
          <div className="flex-1 bg-[var(--bg)] border border-[var(--border-color)] p-3 font-mono text-[11px] overflow-y-auto space-y-1">
            {logs.map((log, idx) => (
              <div
                key={idx}
                className={
                  log.includes("[WARN]")
                    ? "text-[#b45309]"
                    : log.includes("[SYS_SUCCESS]")
                      ? "text-[var(--terminal-green)]"
                      : log.includes("[CRITICAL]")
                        ? "text-[var(--accent)]"
                        : "text-[var(--fg-dim)]"
                }
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
