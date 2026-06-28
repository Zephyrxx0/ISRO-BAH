'use client';

import { useEffect, useRef, useState } from 'react';
import { CandidateEntry } from '../../outputs/integration-schema';
import { Activity, Radio, Cpu, BarChart2 } from 'lucide-react';

interface TransitFitMatrixProps {
  candidate: CandidateEntry;
}

export default function TransitFitMatrix({ candidate }: TransitFitMatrixProps) {
  const plotRef = useRef<HTMLDivElement>(null);
  const [plotlyLoaded, setPlotlyLoaded] = useState(false);
  const plotlyInstance = useRef<any>(null);

  // Color code line based on classification
  let fitColor = '#22C55E'; // Signal Green
  if (candidate.signal.disposition === 'BINARY_STAR_ECLIPSE') {
    fitColor = '#F59E0B'; // Warning Amber
  } else if (candidate.signal.disposition === 'BACKGROUND_STELLAR_CONTAMINATION') {
    fitColor = '#EF4444'; // Blending Red
  }

  useEffect(() => {
    // Dynamic import to prevent SSR (window undefined) error
    import('plotly.js-dist-min')
      .then((module) => {
        plotlyInstance.current = module.default || module;
        setPlotlyLoaded(true);
      })
      .catch((err) => console.error('Failed to load Plotly', err));
  }, []);

  useEffect(() => {
    if (!plotlyLoaded || !plotlyInstance.current || !plotRef.current) return;
    const Plotly = plotlyInstance.current;

    // Layer 1: Raw chaotic TESS light curve data points (Micro-dots, low opacity)
    const rawTrace = {
      x: candidate.lightCurve.rawPhase,
      y: candidate.lightCurve.rawFlux,
      mode: 'markers' as const,
      name: 'RAW VOLATILE TESS FLUX (TESS S-SECTOR)',
      marker: {
        color: '#71717A',
        size: 2,
        opacity: 0.22
      },
      hoverinfo: 'x+y' as const
    };

    // Layer 2: Sharp, geometric AI-predicted model curve
    const fitTrace = {
      x: candidate.lightCurve.modelPhase,
      y: candidate.lightCurve.modelFlux,
      mode: 'lines' as const,
      name: 'AI TRANSIT fit MODEL (PHASE-FOLDED)',
      line: {
        color: fitColor,
        width: 2.5,
        shape: 'linear' as const
      },
      hoverinfo: 'x+y' as const
    };

    const data = [rawTrace, fitTrace];

    const layout = {
      autosize: true,
      height: 340,
      margin: { l: 60, r: 15, t: 15, b: 40 },
      paper_bgcolor: '#FAFAFA',
      plot_bgcolor: '#FAFAFA',
      showlegend: false, // Customized legend built in HTML to preserve density
      xaxis: {
        title: {
          text: 'FOLDED ORBITAL PHASE (OFFSET ΔT0 / DAYS)',
          font: { family: 'var(--font-mono), monospace', size: 9, color: '#71717A' }
        },
        gridcolor: '#E4E4E7',
        linecolor: '#18181B',
        tickcolor: '#18181B',
        tickfont: { family: 'var(--font-mono), monospace', size: 9 },
        zeroline: false
      },
      yaxis: {
        title: {
          text: 'NORMALIZED DETECTOR FLUX INTENSITY',
          font: { family: 'var(--font-mono), monospace', size: 9, color: '#71717A' }
        },
        gridcolor: '#E4E4E7',
        linecolor: '#18181B',
        tickcolor: '#18181B',
        tickfont: { family: 'var(--font-mono), monospace', size: 9 },
        zeroline: false,
        tickformat: '.4f'
      }
    };

    const config = {
      responsive: true,
      displayModeBar: false
    };

    Plotly.newPlot(plotRef.current, data, layout, config);

    // Watch resize
    const handleResize = () => {
      if (plotRef.current) Plotly.Plots.resize(plotRef.current);
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      if (plotRef.current) {
        Plotly.purge(plotRef.current);
      }
    };
  }, [plotlyLoaded, candidate]);

  // Color mappings for status flags
  const statusColors = {
    'CONFIRMED_PLANET': 'text-signal-green border-signal-green bg-green-50',
    'BINARY_STAR_ECLIPSE': 'text-warning-amber border-warning-amber bg-amber-50',
    'BACKGROUND_STELLAR_CONTAMINATION': 'text-blending-red border-blending-red bg-red-50',
    'FALSE_ALARM': 'text-raw-zinc border-raw-zinc bg-zinc-50'
  };

  const statusLabel = {
    'CONFIRMED_PLANET': 'CONFIRMED TRANSIT [TP]',
    'BINARY_STAR_ECLIPSE': 'BINARY ECLIPSE [EB]',
    'BACKGROUND_STELLAR_CONTAMINATION': 'STELLAR CONTAMINATION [BG]',
    'FALSE_ALARM': 'FALSE ALARM [FA]'
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-4 border border-border-brutal bg-[#FAFAFA] divide-y lg:divide-y-0 lg:divide-x divide-border-brutal">
      {/* Telemetry Column */}
      <div className="p-4 flex flex-col justify-between space-y-4">
        <div>
          <div className="flex items-center justify-between border-b border-border-brutal pb-2 mb-3">
            <span className="text-[10px] uppercase font-bold tracking-wider flex items-center gap-1.5 text-zinc-900">
              <Cpu className="w-3.5 h-3.5" /> SIGNAL ANALYSIS METADATA
            </span>
            <span className="text-[9px] px-1.5 py-0.5 border border-border-brutal bg-zinc-100 font-bold">
              {candidate.signal.confidenceTier}
            </span>
          </div>

          <h2 className="text-xl font-bold tracking-tight text-zinc-950 font-mono">
            {candidate.signal.name}
          </h2>
          <p className="text-[10px] text-raw-zinc font-mono mt-0.5">
            IDENTIFIER: {candidate.signal.ticId}
          </p>

          <div className={`mt-3 inline-block text-[9px] font-bold border px-2 py-1 font-mono tracking-wider ${statusColors[candidate.signal.disposition]}`}>
            {statusLabel[candidate.signal.disposition]}
          </div>
        </div>

        {/* Dense telemetry matrix */}
        <div className="grid grid-cols-2 gap-2 border-t border-b border-dashed border-zinc-300 py-3 my-2 text-[10px]">
          <div>
            <div className="text-[8px] text-raw-zinc uppercase">TRANSIT DEPTH</div>
            <div className="font-mono font-bold text-zinc-900 mt-0.5">
              {candidate.signal.depth.toFixed(4)} <span className="text-[8px] text-raw-zinc">ppt</span>
            </div>
          </div>
          <div>
            <div className="text-[8px] text-raw-zinc uppercase">ORBITAL PERIOD</div>
            <div className="font-mono font-bold text-zinc-900 mt-0.5">
              {candidate.signal.period.toFixed(6)} <span className="text-[8px] text-raw-zinc">days</span>
            </div>
          </div>
          <div>
            <div className="text-[8px] text-raw-zinc uppercase">SIG DETECTION EFF (SDE)</div>
            <div className="font-mono font-bold text-zinc-900 mt-0.5">
              {candidate.signal.sde.toFixed(2)}
            </div>
          </div>
          <div>
            <div className="text-[8px] text-raw-zinc uppercase">SIGNAL-TO-NOISE (SNR)</div>
            <div className="font-mono font-bold text-zinc-900 mt-0.5">
              {candidate.signal.snr.toFixed(2)}
            </div>
          </div>
          <div>
            <div className="text-[8px] text-raw-zinc uppercase">EPOCH (T0 BJD)</div>
            <div className="font-mono font-bold text-zinc-900 mt-0.5">
              {candidate.signal.t0.toFixed(4)}
            </div>
          </div>
          <div>
            <div className="text-[8px] text-raw-zinc uppercase">TRANSIT DURATION</div>
            <div className="font-mono font-bold text-zinc-900 mt-0.5">
              {candidate.signal.duration.toFixed(2)} <span className="text-[8px] text-raw-zinc">hrs</span>
            </div>
          </div>
        </div>

        {/* Legend status */}
        <div className="space-y-1.5">
          <div className="flex items-center gap-2 text-[9px] font-mono text-zinc-600">
            <span className="w-2 h-2 rounded-none bg-raw-zinc inline-block"></span>
            <span>RAW DATA POINTS (TESS S-Sectors)</span>
          </div>
          <div className="flex items-center gap-2 text-[9px] font-mono text-zinc-600">
            <span className={`w-2.5 h-0.5 inline-block`} style={{ backgroundColor: fitColor }}></span>
            <span>AI TRAPEZOIDAL MODEL FIT</span>
          </div>
        </div>
      </div>

      {/* Plot Column (occupies 3 out of 4 columns) */}
      <div className="lg:col-span-3 p-4 flex flex-col justify-between min-h-[360px] bg-[#FAFAFA]">
        <div className="flex items-center justify-between border-b border-border-brutal pb-2 mb-2">
          <div className="flex items-center gap-2">
            <Activity className="w-3.5 h-3.5 text-zinc-900" />
            <span className="text-[10px] uppercase font-bold tracking-wider text-zinc-900">
              PHASE-FOLDED FLUX PROFILE & AI FIT MODEL
            </span>
          </div>
          <span className="text-[9px] text-raw-zinc uppercase font-mono">
            {plotlyLoaded ? 'Plotly.js ENGINE LOADED' : 'INITIALIZING PLOT ENGINE...'}
          </span>
        </div>

        <div className="relative flex-1 w-full bg-[#FAFAFA] flex items-center justify-center">
          {!plotlyLoaded && (
            <div className="absolute inset-0 flex flex-col items-center justify-center font-mono text-[10px] text-raw-zinc bg-zinc-50 border border-dashed border-zinc-300">
              <Radio className="w-6 h-6 animate-signal-pulse text-zinc-600 mb-2" />
              RETRIEVING SPECTRAL DE-NOISING COEFFICIENTS...
            </div>
          )}
          <div ref={plotRef} className="w-full h-full" />
        </div>
      </div>
    </div>
  );
}
