"use client";

import { useState } from "react";

interface DiagnosticPlotProps {
  pngPath: string;
  htmlPath: string | null;
  alt: string;
}

export default function DiagnosticPlot({
  pngPath,
  htmlPath,
  alt,
}: DiagnosticPlotProps) {
  const [showInteractive, setShowInteractive] = useState(false);

  return (
    <div className="border border-[var(--border-color)] bg-[var(--surface)]">
      <div className="flex items-center justify-between px-3 py-1.5 border-b border-[var(--border-color)] bg-[var(--panel)]">
        <span className="font-mono text-[9px] text-[var(--fg-dim)] tracking-widest">
          {alt}
        </span>
        {htmlPath && (
          <button
            onClick={() => setShowInteractive(!showInteractive)}
            className="font-mono text-[9px] tracking-widest text-[var(--fg-dim)] hover:text-[var(--fg)] border border-[var(--border-color)] hover:border-[var(--fg-dim)] px-2 py-0.5 transition-colors"
          >
            {showInteractive ? "[ STATIC ]" : "[ INTERACTIVE ]"}
          </button>
        )}
      </div>

      <div className="relative w-full min-h-[300px] bg-[var(--bg)] flex items-center justify-center">
        {showInteractive && htmlPath ? (
          <iframe
            src={htmlPath}
            className="w-full h-[400px] border-0"
            title={alt}
          />
        ) : (
          <img
            src={pngPath}
            alt={alt}
            className="w-full h-full object-contain"
            onError={(e) => {
              (e.target as HTMLImageElement).style.display = "none";
              (e.target as HTMLImageElement).parentElement!.innerHTML =
                '<span class="font-mono text-xs text-[var(--fg-dim)]">// PLOT NOT AVAILABLE</span>';
            }}
          />
        )}
      </div>
    </div>
  );
}
