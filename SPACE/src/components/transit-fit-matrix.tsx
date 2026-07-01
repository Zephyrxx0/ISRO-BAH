'use client';

import { useEffect, useRef, useState } from 'react';
import { CandidateEntry } from '../../outputs/integration-schema';
import { Activity, Radio, Cpu } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

interface TransitFitMatrixProps {
  candidate: CandidateEntry;
}

export default function TransitFitMatrix({ candidate }: TransitFitMatrixProps) {
  const plotRef = useRef<HTMLDivElement>(null);
  const [plotlyLoaded, setPlotlyLoaded] = useState(false);
  const plotlyInstance = useRef<any>(null);

  // Color code line based on classification
  let fitColor = '#10b981'; // Signal Green
  if (candidate.signal.disposition === 'BINARY_STAR_ECLIPSE') {
    fitColor = '#f59e0b'; // Warning Amber
  } else if (candidate.signal.disposition === 'BACKGROUND_STELLAR_CONTAMINATION') {
    fitColor = '#ef4444'; // Blending Red
  }

  useEffect(() => {
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

    const rawTrace = {
      x: candidate.lightCurve.rawPhase,
      y: candidate.lightCurve.rawFlux,
      mode: 'markers' as const,
      name: 'RAW VOLATILE TESS FLUX (TESS S-SECTOR)',
      marker: {
        color: '#64748b',
        size: 3,
        opacity: 0.3
      },
      hoverinfo: 'x+y' as const
    };

    const fitTrace = {
      x: candidate.lightCurve.modelPhase,
      y: candidate.lightCurve.modelFlux,
      mode: 'lines' as const,
      name: 'AI TRANSIT fit MODEL (PHASE-FOLDED)',
      line: {
        color: fitColor,
        width: 3,
        shape: 'linear' as const
      },
      hoverinfo: 'x+y' as const
    };

    const data = [rawTrace, fitTrace];

    const layout = {
      autosize: true,
      height: 380,
      margin: { l: 60, r: 15, t: 15, b: 40 },
      paper_bgcolor: 'transparent',
      plot_bgcolor: 'transparent',
      showlegend: false,
      xaxis: {
        title: {
          text: 'FOLDED ORBITAL PHASE (OFFSET ΔT0 / DAYS)',
          font: { family: 'var(--font-sans)', size: 10, color: '#94a3b8' }
        },
        gridcolor: '#334155',
        linecolor: '#334155',
        tickcolor: '#334155',
        tickfont: { family: 'var(--font-sans)', size: 10, color: '#94a3b8' },
        zeroline: false
      },
      yaxis: {
        title: {
          text: 'NORMALIZED DETECTOR FLUX INTENSITY',
          font: { family: 'var(--font-sans)', size: 10, color: '#94a3b8' }
        },
        gridcolor: '#334155',
        linecolor: '#334155',
        tickcolor: '#334155',
        tickfont: { family: 'var(--font-sans)', size: 10, color: '#94a3b8' },
        zeroline: false,
        tickformat: '.4f'
      }
    };

    const config = {
      responsive: true,
      displayModeBar: false
    };

    Plotly.newPlot(plotRef.current, data, layout, config);

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
  }, [plotlyLoaded, candidate, fitColor]);

  const getStatusBadge = (disposition: string) => {
    switch (disposition) {
      case 'CONFIRMED_PLANET':
        return <Badge className="bg-green-500/20 text-green-500 hover:bg-green-500/30">CONFIRMED PLANET</Badge>;
      case 'BINARY_STAR_ECLIPSE':
        return <Badge className="bg-yellow-500/20 text-yellow-500 hover:bg-yellow-500/30">ECLIPSING BINARY</Badge>;
      case 'BACKGROUND_STELLAR_CONTAMINATION':
        return <Badge className="bg-red-500/20 text-red-500 hover:bg-red-500/30">BACKGROUND BLEND</Badge>;
      default:
        return <Badge variant="outline">FALSE ALARM</Badge>;
    }
  };

  return (
    <Card className="h-full border-border bg-card">
      <div className="grid grid-cols-1 xl:grid-cols-4 h-full">
        {/* Telemetry Column */}
        <div className="p-6 flex flex-col justify-between border-b xl:border-b-0 xl:border-r border-border">
          <div>
            <div className="flex items-center justify-between mb-4">
              <span className="text-xs uppercase font-semibold text-muted-foreground flex items-center gap-2">
                <Cpu className="w-4 h-4" /> Parameters
              </span>
              <Badge variant="outline" className="text-xs">{candidate.signal.confidenceTier}</Badge>
            </div>
            <h2 className="text-2xl font-bold text-foreground">
              {candidate.signal.name}
            </h2>
            <p className="text-sm text-muted-foreground mt-1">
              TIC ID: {candidate.signal.ticId}
            </p>
            <div className="mt-4">
              {getStatusBadge(candidate.signal.disposition)}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4 py-6 text-sm">
            <div>
              <div className="text-xs text-muted-foreground uppercase mb-1">Depth</div>
              <div className="font-semibold text-foreground">
                {candidate.signal.depth.toFixed(4)} <span className="text-xs font-normal text-muted-foreground">ppt</span>
              </div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground uppercase mb-1">Period</div>
              <div className="font-semibold text-foreground">
                {candidate.signal.period.toFixed(6)} <span className="text-xs font-normal text-muted-foreground">days</span>
              </div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground uppercase mb-1">SDE</div>
              <div className="font-semibold text-foreground">
                {candidate.signal.sde.toFixed(2)}
              </div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground uppercase mb-1">SNR</div>
              <div className="font-semibold text-foreground">
                {candidate.signal.snr.toFixed(2)}
              </div>
            </div>
          </div>

          <div className="space-y-2 mt-4 text-xs text-muted-foreground">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-slate-500"></span>
              <span>Raw Data Points</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-1 rounded-sm" style={{ backgroundColor: fitColor }}></span>
              <span>Model Fit</span>
            </div>
          </div>
        </div>

        {/* Plot Column */}
        <div className="xl:col-span-3 p-6 flex flex-col justify-between h-full bg-card/50">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2 text-foreground">
              <Activity className="w-4 h-4" />
              <span className="text-sm uppercase font-bold">
                Phase-Folded Flux Profile
              </span>
            </div>
            <span className="text-xs text-muted-foreground uppercase">
              {plotlyLoaded ? 'Interactive Plot' : 'Loading Engine...'}
            </span>
          </div>

          <div className="relative flex-1 w-full flex items-center justify-center min-h-[400px]">
            {!plotlyLoaded && (
              <div className="absolute inset-0 flex flex-col items-center justify-center text-xs text-muted-foreground">
                <Radio className="w-6 h-6 animate-pulse text-muted-foreground mb-3" />
                Initializing WebGL Engine...
              </div>
            )}
            <div ref={plotRef} className="w-full h-full" />
          </div>
        </div>
      </div>
    </Card>
  );
}
