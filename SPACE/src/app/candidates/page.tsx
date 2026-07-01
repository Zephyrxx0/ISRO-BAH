import { getAllCandidates } from '../../lib/pipeline-data';
import CandidateTable from '../../components/candidate-table';
import { StatCards } from '../../components/stat-cards';

export default function Home() {
  const allCandidates = getAllCandidates();
  const allSignals = allCandidates.map((c) => c.signal);
  
  const totalCandidates = allSignals.length;
  const goldCount = allSignals.filter(s => s.confidenceTier === 'GOLD').length;
  const planetCount = allSignals.filter(s => s.disposition === 'CONFIRMED_PLANET').length;
  const avgSde = allSignals.length > 0 ? allSignals.reduce((acc, s) => acc + s.sde, 0) / allSignals.length : 0;

  return (
    <div className="w-full space-y-6">
      <StatCards
        totalCandidates={totalCandidates}
        goldCount={goldCount}
        planetCount={planetCount}
        avgSde={avgSde}
      />

      <CandidateTable
        candidates={allSignals}
      />
    </div>
  );
}
