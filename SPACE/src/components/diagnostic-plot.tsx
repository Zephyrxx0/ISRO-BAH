"use client";

import { useEffect, useRef, useState } from "react";
import { CandidateEntry } from "../../outputs/integration-schema";
import Plotly from "plotly.js-dist-min";

interface DiagnosticPlotProps {
  plotType: "raw_detrended" | "periodogram" | "phase_folded" | "softmax" | "corner";
  candidate: CandidateEntry;
  alt: string;
}

export default function DiagnosticPlot({
  plotType,
  candidate,
  alt,
}: DiagnosticPlotProps) {
  const plotDivRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!plotDivRef.current) return;

    try {
      let data: Plotly.Data[] = [];
      const layout: Partial<Plotly.Layout> = {
        paper_bgcolor: "transparent",
        plot_bgcolor: "transparent",
        font: { family: "monospace", color: "#8b949e", size: 10 },
        margin: { t: 20, r: 20, b: 30, l: 40 },
        showlegend: false,
        xaxis: { gridcolor: "#30363d", zerolinecolor: "#30363d" },
        yaxis: { gridcolor: "#30363d", zerolinecolor: "#30363d" },
      };

      if (plotType === "raw_detrended") {
        data = [
          {
            x: candidate.lightCurve.rawPhase,
            y: candidate.lightCurve.rawFlux,
            mode: "markers",
            type: "scatter",
            marker: { size: 3, color: "#8b949e", opacity: 0.5 },
            name: "Raw",
          },
        ];
        layout.xaxis!.title = { text: "Phase" };
        layout.yaxis!.title = { text: "Normalized Flux" };
      } else if (plotType === "phase_folded") {
        data = [
          {
            x: candidate.lightCurve.rawPhase,
            y: candidate.lightCurve.rawFlux,
            mode: "markers",
            type: "scatter",
            marker: { size: 3, color: "#8b949e", opacity: 0.5 },
            name: "Data",
          },
          {
            x: candidate.lightCurve.modelPhase,
            y: candidate.lightCurve.modelFlux,
            mode: "lines",
            type: "scatter",
            line: { color: "#3fb950", width: 2 },
            name: "Model",
          },
        ];
        layout.xaxis!.title = { text: "Phase" };
        layout.yaxis!.title = { text: "Normalized Flux" };
      } else if (plotType === "softmax") {
        const modes = candidate.validation.triceratops.modes;
        data = [
          {
            x: ["TP", "EB", "HEB", "BGOB"],
            y: [modes.tp, modes.eb, modes.heb, modes.bgob],
            type: "bar",
            marker: { color: ["#3fb950", "#e3b341", "#f85149", "#f85149"] },
          },
        ];
        layout.yaxis!.range = [0, 1];
        layout.yaxis!.title = { text: "Probability" };
      } else {
        // 'periodogram' and 'corner' don't have mock data
        console.warn(`Plot data unavailable in mock payload for plot type: ${plotType}`);
        setError("PLOT DATA UNAVAILABLE");
        return;
      }

      Plotly.newPlot(plotDivRef.current, data, layout, {
        displayModeBar: false,
        responsive: true,
      });

      return () => {
        if (plotDivRef.current) {
          Plotly.purge(plotDivRef.current);
        }
      };
    } catch (err) {
      console.error("Plotly error", err);
      setError("FAILED TO RENDER PLOT");
    }
  }, [plotType, candidate]);

  return (
    <div className="border border-[var(--border-color)] bg-[var(--surface)] flex flex-col h-full">
      <div className="flex items-center justify-between px-3 py-1.5 border-b border-[var(--border-color)] bg-[var(--panel)]">
        <span className="font-mono text-[9px] text-[var(--fg-dim)] tracking-widest">
          {alt}
        </span>
      </div>

      <div className="relative w-full h-[300px] bg-[var(--bg)] flex flex-col items-center justify-center p-2">
        {error ? (
          <span className="font-mono text-xs text-[var(--fg-dim)]">
            // {error}
          </span>
        ) : (
          <div ref={plotDivRef} className="w-full h-full" />
        )}
      </div>
    </div>
  );
}
