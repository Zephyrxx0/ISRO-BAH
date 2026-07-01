"use client";

import { useEffect, useRef, useState } from "react";
import { CandidateEntry } from "../../outputs/integration-schema";

interface TransitFitMatrixProps {
  candidate: CandidateEntry;
}

export default function TransitFitMatrix({ candidate }: TransitFitMatrixProps) {
  const plotRef = useRef<HTMLDivElement>(null);
  const [plotlyLoaded, setPlotlyLoaded] = useState(false);
  const plotlyInstance = useRef<any>(null);

  let fitColor = "#4af626";
  if (candidate.signal.disposition === "BINARY_STAR_ECLIPSE") {
    fitColor = "#e61919";
  } else if (
    candidate.signal.disposition === "BACKGROUND_STELLAR_CONTAMINATION"
  ) {
    fitColor = "#e61919";
  }

  useEffect(() => {
    import("plotly.js-dist-min")
      .then((module) => {
        plotlyInstance.current = module.default || module;
        setPlotlyLoaded(true);
      })
      .catch((err) => console.error("Failed to load Plotly", err));
  }, []);

  useEffect(() => {
    if (!plotlyLoaded || !plotlyInstance.current || !plotRef.current) return;
    const Plotly = plotlyInstance.current;

    const rawTrace = {
      x: candidate.lightCurve.rawPhase,
      y: candidate.lightCurve.rawFlux,
      mode: "markers" as const,
      name: "RAW TESS FLUX",
      marker: {
        color: "#555555",
        size: 2,
        opacity: 0.4,
      },
      hoverinfo: "x+y" as const,
    };

    const fitTrace = {
      x: candidate.lightCurve.modelPhase,
      y: candidate.lightCurve.modelFlux,
      mode: "lines" as const,
      name: "TRANSIT MODEL",
      line: {
        color: fitColor,
        width: 2,
        shape: "linear" as const,
      },
      hoverinfo: "x+y" as const,
    };

    const data = [rawTrace, fitTrace];

    const layout = {
      autosize: true,
      height: 420,
      margin: { l: 60, r: 20, t: 10, b: 50 },
      paper_bgcolor: "#0d0d0d",
      plot_bgcolor: "#0d0d0d",
      showlegend: false,
      xaxis: {
        title: {
          text: "FOLDED ORBITAL PHASE",
          font: { family: "JetBrains Mono", size: 9, color: "#999999" },
        },
        gridcolor: "#1a1a1a",
        linecolor: "#2a2a2a",
        tickcolor: "#2a2a2a",
        tickfont: {
          family: "JetBrains Mono",
          size: 9,
          color: "#999999",
        },
        zeroline: false,
      },
      yaxis: {
        title: {
          text: "NORMALIZED FLUX",
          font: { family: "JetBrains Mono", size: 9, color: "#999999" },
        },
        gridcolor: "#1a1a1a",
        linecolor: "#2a2a2a",
        tickcolor: "#2a2a2a",
        tickfont: {
          family: "JetBrains Mono",
          size: 9,
          color: "#999999",
        },
        zeroline: false,
        tickformat: ".4f",
      },
    };

    const config = {
      responsive: true,
      displayModeBar: false,
    };

    Plotly.newPlot(plotRef.current, data, layout, config);

    const handleResize = () => {
      if (plotRef.current) Plotly.Plots.resize(plotRef.current);
    };
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      if (plotRef.current) {
        Plotly.purge(plotRef.current);
      }
    };
  }, [plotlyLoaded, candidate, fitColor]);

  const getDispositionLabel = (disposition: string) => {
    switch (disposition) {
      case "CONFIRMED_PLANET":
        return { text: "CONFIRMED PLANET", className: "text-[var(--terminal-green)]" };
      case "BINARY_STAR_ECLIPSE":
        return { text: "ECLIPSING BINARY", className: "text-[var(--accent)]" };
      case "BACKGROUND_STELLAR_CONTAMINATION":
        return { text: "BACKGROUND BLEND", className: "text-[var(--accent)]" };
      default:
        return { text: "FALSE ALARM", className: "text-[var(--fg-dim)]" };
    }
  };

  const disp = getDispositionLabel(candidate.signal.disposition);

  return (
    <div className="border border-[var(--border-color)] bg-[var(--surface)]">
      {/* HEADER */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-[var(--border-color)] bg-[var(--panel)]">
        <div className="flex items-center gap-3">
          <span className="font-mono text-[10px] tracking-widest text-[var(--fg-dim)]">
            [ PHASE-FOLDED FLUX PROFILE ]
          </span>
          <span className="font-mono text-[10px] tracking-widest text-[var(--fg-dim)]">
            SECTOR {candidate.validation.sherlock.sectors.join("/")}
          </span>
        </div>
        <span className={`font-mono text-[10px] tracking-widest font-bold ${disp.className}`}>
          {disp.text}
        </span>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-5">
        {/* TELEMETRY COLUMN */}
        <div className="p-4 border-b xl:border-b-0 xl:border-r border-[var(--border-color)]">
          <div className="mb-4">
            <h2 className="font-sans font-black text-lg text-[var(--fg)] tracking-tighter">
              {candidate.signal.name}
            </h2>
            <p className="font-mono text-[10px] text-[var(--fg-dim)] tracking-widest mt-1">
              {candidate.signal.ticId}
            </p>
          </div>

          <div className="space-y-3">
            {[
              ["PERIOD", `${candidate.signal.period.toFixed(6)} d`],
              ["DEPTH", `${candidate.signal.depth.toFixed(4)} ppt`],
              ["DURATION", `${candidate.signal.duration.toFixed(2)} h`],
              ["SDE", candidate.signal.sde.toFixed(2)],
              ["SNR", candidate.signal.snr.toFixed(2)],
              [
                "TIER",
                candidate.signal.confidenceTier,
                candidate.signal.confidenceTier === "GOLD"
                  ? "text-[var(--accent)]"
                  : "text-[var(--fg-dim)]",
              ],
            ].map(([label, value, extraClass]) => (
              <div key={label as string}>
                <span className="block font-mono text-[9px] text-[var(--fg-dim)] tracking-widest mb-0.5">
                  {label}
                </span>
                <span
                  className={`font-mono text-xs text-[var(--fg)] tabular-nums ${extraClass || ""}`}
                >
                  {value}
                </span>
              </div>
            ))}
          </div>

          {/* LEGEND */}
          <div className="mt-6 pt-4 border-t border-[var(--border-color)] space-y-2">
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 bg-[#555555] inline-block"></span>
              <span className="font-mono text-[9px] text-[var(--fg-dim)] tracking-widest">
                RAW DATA POINTS
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span
                className="w-3 h-[3px] inline-block"
                style={{ backgroundColor: fitColor }}
              ></span>
              <span className="font-mono text-[9px] text-[var(--fg-dim)] tracking-widest">
                MODEL FIT
              </span>
            </div>
          </div>
        </div>

        {/* PLOT COLUMN */}
        <div className="xl:col-span-4 p-4">
          <div className="relative w-full h-full min-h-[420px]">
            {!plotlyLoaded && (
              <div className="absolute inset-0 flex items-center justify-center bg-[var(--surface)]">
                <span className="font-mono text-xs text-[var(--fg-dim)]">
                  INITIALIZING PLOTLY ENGINE...
                </span>
              </div>
            )}
            <div ref={plotRef} className="w-full h-full" />
          </div>
        </div>
      </div>
    </div>
  );
}
