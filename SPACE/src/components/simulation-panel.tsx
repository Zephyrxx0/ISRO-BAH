'use client';

import { useEffect, useState, useRef } from 'react';
import { PipelinePayload } from '../../outputs/integration-schema';
import { Terminal, Play, RotateCcw } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

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

  useEffect(() => {
    if (consoleEndRef.current) {
      consoleEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs]);

  const isH18 = currentHour >= 18;

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="border-b border-border bg-muted/20 pb-4">
        <CardTitle className="text-sm flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Terminal className="w-4 h-4" />
            INTEGRATION CONTROL
          </div>
          <Badge variant={isH18 ? "default" : "secondary"} className={isH18 ? 'bg-green-500 hover:bg-green-600' : ''}>
            {isH18 ? 'STREAMING' : 'STANDBY'}
          </Badge>
        </CardTitle>
      </CardHeader>

      <CardContent className="flex-1 flex flex-col justify-between p-6 space-y-6">
        <div className="grid grid-cols-2 gap-4">
          <Button
            variant={!isH18 ? "secondary" : "outline"}
            onClick={() => onChangeHour(0)}
            className="w-full text-xs font-semibold"
          >
            <RotateCcw className="w-4 h-4 mr-2" />
            Hour 0 (Baseline)
          </Button>
          <Button
            variant={isH18 ? "default" : "outline"}
            onClick={() => onChangeHour(18)}
            className={`w-full text-xs font-semibold ${isH18 ? 'bg-green-500 hover:bg-green-600 text-white' : ''}`}
          >
            <Play className="w-4 h-4 mr-2" />
            Hour 18 (Inference)
          </Button>
        </div>

        <div className="grid grid-cols-2 gap-4 bg-muted/30 border border-border p-4 rounded-md text-sm">
          <div>
            <div className="text-xs text-muted-foreground uppercase mb-1">Payload Timestamp</div>
            <div className="font-semibold truncate">{payload.timestamp}</div>
          </div>
          <div>
            <div className="text-xs text-muted-foreground uppercase mb-1">Pipeline Version</div>
            <div className="font-semibold">{payload.pipelineVersion}</div>
          </div>
          <div>
            <div className="text-xs text-muted-foreground uppercase mb-1">Active Candidates</div>
            <div className="font-semibold">{Object.keys(payload.candidates).length} Targets</div>
          </div>
          <div>
            <div className="text-xs text-muted-foreground uppercase mb-1">Simulation Time</div>
            <div className="font-semibold">H{currentHour.toString().padStart(2, '0')}:00</div>
          </div>
        </div>

        <div className="flex-1 flex flex-col min-h-[160px]">
          <span className="text-xs text-muted-foreground uppercase font-semibold mb-2 block">
            Terminal Pipeline Buffer
          </span>
          <div className="flex-1 bg-black rounded-md border border-border p-3 font-mono text-xs overflow-y-auto space-y-1.5 h-full">
            {logs.map((log, idx) => (
              <div 
                key={idx} 
                className={`${
                  log.includes('[WARN]') 
                    ? 'text-yellow-400' 
                    : log.includes('[SYS_SUCCESS]') 
                    ? 'text-green-400' 
                    : log.includes('[CRITICAL]') 
                    ? 'text-red-400' 
                    : 'text-slate-300'
                }`}
              >
                {log}
              </div>
            ))}
            <div ref={consoleEndRef} />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
