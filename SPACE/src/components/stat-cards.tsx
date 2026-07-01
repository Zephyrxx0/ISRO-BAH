'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface StatCardsProps {
  totalCandidates: number;
  goldCount: number;
  planetCount: number;
  avgSde: number;
}

export function StatCards({
  totalCandidates,
  goldCount,
  planetCount,
  avgSde,
}: StatCardsProps) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium uppercase text-muted-foreground">
            Total Candidates
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{totalCandidates}</div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium uppercase text-muted-foreground">
            Gold Tier
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-[#f59e0b]">{goldCount}</div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium uppercase text-muted-foreground">
            Planet Candidates
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{planetCount}</div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium uppercase text-muted-foreground">
            Avg SDE
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{avgSde.toFixed(2)}</div>
        </CardContent>
      </Card>
    </div>
  );
}
