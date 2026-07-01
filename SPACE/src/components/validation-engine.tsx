'use client';

import { CandidateEntry } from '../../outputs/integration-schema';
import { ShieldCheck, BarChart, CheckCircle2, XCircle, AlertTriangle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';

interface ValidationEngineProps {
  candidate: CandidateEntry;
}

export default function ValidationEngine({ candidate }: ValidationEngineProps) {
  const { triceratops, sherlock } = candidate.validation;

  const toPercent = (val: number) => (val * 100).toFixed(4) + '%';

  const statusIcon = (status: 'PASS' | 'FAIL') => {
    return status === 'PASS' ? (
      <span className="text-green-500 flex items-center gap-1 font-semibold">
        <CheckCircle2 className="w-4 h-4" /> PASS
      </span>
    ) : (
      <span className="text-red-500 flex items-center gap-1 font-semibold">
        <XCircle className="w-4 h-4" /> FAIL
      </span>
    );
  };

  const getRecoveryBadge = (status: string) => {
    switch (status) {
      case 'RECOVERED':
        return <Badge className="bg-green-500 hover:bg-green-600">RECOVERED</Badge>;
      case 'NOT_RECOVERED':
        return <Badge variant="destructive">NOT RECOVERED</Badge>;
      default:
        return <Badge variant="secondary" className="text-yellow-500">INCOMPLETE</Badge>;
    }
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      {/* TRICERATOPS PANEL */}
      <Card>
        <CardHeader className="border-b border-border bg-muted/20">
          <CardTitle className="text-sm flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-4 h-4" />
              TRICERATOPS MCMC VALIDATION
            </div>
            <span className="text-xs font-normal text-muted-foreground uppercase">Bayesian Engine</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="p-6 space-y-6">
            <div>
              <div className="flex justify-between items-baseline mb-2">
                <span className="text-xs uppercase font-semibold text-muted-foreground">False Positive Probability (FPP)</span>
                <span className="text-sm font-bold">{triceratops.fpp.toFixed(6)}</span>
              </div>
              <div className="h-2 w-full rounded-full bg-secondary overflow-hidden">
                <div 
                  className={`h-full ${
                    triceratops.fpp > 0.5 ? 'bg-red-500' : triceratops.fpp > 0.01 ? 'bg-yellow-500' : 'bg-green-500'
                  }`}
                  style={{ width: `${Math.min(100, Math.max(1, triceratops.fpp * 100))}%` }}
                />
              </div>
              <p className="text-right text-xs mt-1 text-muted-foreground">Threshold &lt; 0.01</p>
            </div>

            <div>
              <div className="flex justify-between items-baseline mb-2">
                <span className="text-xs uppercase font-semibold text-muted-foreground">Non-Transiting FPP (NFPP)</span>
                <span className="text-sm font-bold">{triceratops.nfpp.toFixed(6)}</span>
              </div>
              <div className="h-2 w-full rounded-full bg-secondary overflow-hidden">
                <div 
                  className={`h-full ${
                    triceratops.nfpp > 0.1 ? 'bg-red-500' : triceratops.nfpp > 0.005 ? 'bg-yellow-500' : 'bg-green-500'
                  }`}
                  style={{ width: `${Math.min(100, Math.max(1, triceratops.nfpp * 100))}%` }}
                />
              </div>
              <p className="text-right text-xs mt-1 text-muted-foreground">Threshold &lt; 0.005</p>
            </div>
          </div>

          <div className="grid grid-cols-3 divide-x divide-border border-t border-border bg-muted/10 text-sm">
            <div className="p-4 text-center">
              <span className="text-xs text-muted-foreground uppercase font-semibold block mb-1">True Planet</span>
              <div className="font-bold text-green-500">{toPercent(triceratops.modes.tp)}</div>
            </div>
            <div className="p-4 text-center">
              <span className="text-xs text-muted-foreground uppercase font-semibold block mb-1">Eclipsing Binary</span>
              <div className={`font-bold ${triceratops.modes.eb > 0.1 ? 'text-yellow-500' : 'text-foreground'}`}>{toPercent(triceratops.modes.eb)}</div>
            </div>
            <div className="p-4 text-center">
              <span className="text-xs text-muted-foreground uppercase font-semibold block mb-1">Background Blend</span>
              <div className={`font-bold ${triceratops.modes.bgob + triceratops.modes.heb > 0.1 ? 'text-red-500' : 'text-foreground'}`}>
                {toPercent(triceratops.modes.bgob + triceratops.modes.heb)}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* SHERLOCK BENCHMARK PANEL */}
      <Card>
        <CardHeader className="border-b border-border bg-muted/20">
          <CardTitle className="text-sm flex items-center justify-between">
            <div className="flex items-center gap-2">
              <BarChart className="w-4 h-4" />
              SHERLOCK STABILITY RECOVERY
            </div>
            <span className="text-xs font-normal text-muted-foreground uppercase">Sector Matrix</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0 flex flex-col justify-between h-full">
          <div className="p-6 flex-1">
            <div className="flex justify-between items-center mb-6">
              <span className="text-sm font-semibold uppercase">
                Sectors: {sherlock.sectors.join(', ')}
              </span>
              <div>{getRecoveryBadge(sherlock.overallRecoveryStatus)}</div>
            </div>

            <div className="rounded-md border bg-card">
              <Table>
                <TableHeader className="bg-muted/30">
                  <TableRow>
                    <TableHead>Sector</TableHead>
                    <TableHead>Period Match</TableHead>
                    <TableHead>Depth Consist.</TableHead>
                    <TableHead>Recov SNR</TableHead>
                    <TableHead>Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {sherlock.passFailMatrix.map((val) => (
                    <TableRow key={val.sector}>
                      <TableCell className="font-semibold">{val.sector.toString().padStart(2, '0')}</TableCell>
                      <TableCell>{val.periodMatch ? 'True' : 'False'}</TableCell>
                      <TableCell>{val.depthConsistency ? 'Consistent' : 'Deviating'}</TableCell>
                      <TableCell>{val.snr > 0 ? val.snr.toFixed(1) : '—'}</TableCell>
                      <TableCell>{statusIcon(val.status)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </div>

          <div className="p-4 border-t border-border bg-muted/20 flex items-center gap-2 text-sm">
            <AlertTriangle className="w-4 h-4 text-yellow-500 shrink-0" />
            {candidate.signal.disposition === 'CONFIRMED_PLANET' ? (
              <span className="text-muted-foreground font-medium">Signal clear. Confidence metrics stable.</span>
            ) : candidate.signal.disposition === 'BINARY_STAR_ECLIPSE' ? (
              <span className="text-yellow-500 font-semibold">WARNING: High FPP indicates likely eclipsing binary.</span>
            ) : (
              <span className="text-red-500 font-semibold">CRITICAL: Background star detected in aperture blend.</span>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
