'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Sparkles, AlertCircle } from 'lucide-react';
import { CandidateEntry } from '../../outputs/integration-schema';
import { Button } from '@/components/ui/button';

interface AISynthesisPanelProps {
  candidate: CandidateEntry;
}

export function AISynthesisPanel({ candidate }: AISynthesisPanelProps) {
  const [report, setReport] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const generateReport = async () => {
    setLoading(true);
    setReport('');
    setError(null);

    try {
      const response = await fetch('/api/ai-synthesis', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ticId: candidate.signal.ticId,
          candidateName: candidate.signal.name,
          disposition: candidate.signal.disposition,
          sde: candidate.signal.sde,
          fpp: candidate.validation.triceratops.fpp,
        }),
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.error || 'Failed to generate report');
      }

      if (!response.body) throw new Error('ReadableStream not supported');

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let done = false;

      while (!done) {
        const { value, done: readerDone } = await reader.read();
        done = readerDone;
        if (value) {
          const chunk = decoder.decode(value, { stream: true });
          setReport((prev) => prev + chunk);
        }
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="h-full flex flex-col border-border bg-card">
      <CardHeader className="border-b border-border bg-primary/10 pb-4">
        <CardTitle className="text-sm flex items-center justify-between">
          <div className="flex items-center gap-2 text-primary">
            <Sparkles className="w-4 h-4" />
            AI SYNTHESIS RESEARCH REPORT
          </div>
          <Button 
            variant="default" 
            size="sm" 
            onClick={generateReport} 
            disabled={loading}
            className="h-7 text-xs font-semibold"
          >
            {loading ? 'Analyzing...' : 'Generate Report'}
          </Button>
        </CardTitle>
      </CardHeader>

      <CardContent className="flex-1 p-6 flex flex-col">
        {error && (
          <div className="flex items-center gap-2 text-red-500 mb-4 text-sm font-semibold p-3 bg-red-500/10 rounded-md">
            <AlertCircle className="w-4 h-4" /> {error}
          </div>
        )}

        {!report && !loading && !error && (
          <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground text-sm opacity-60">
            <Sparkles className="w-8 h-8 mb-3 opacity-40" />
            <p>Click "Generate Report" to request an AI synthesis of this target.</p>
            <p className="text-xs mt-1 text-center max-w-sm">
              The AI will automatically query the SIMBAD Astronomical Database and evaluate the current pipeline metrics.
            </p>
          </div>
        )}

        {(report || loading) && (
          <div className="flex-1 overflow-y-auto">
            <div className="prose prose-sm prose-invert max-w-none text-foreground leading-relaxed whitespace-pre-wrap">
              {report}
            </div>
            {loading && (
              <div className="flex items-center gap-2 mt-4 text-primary text-xs font-semibold animate-pulse">
                <Sparkles className="w-3 h-3" /> Synthesizing data stream...
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
