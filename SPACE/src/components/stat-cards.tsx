"use client";

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
  const stats: { label: string; value: string; accent?: boolean }[] = [
    { label: "TOTAL CANDIDATES", value: String(totalCandidates) },
    { label: "GOLD TIER", value: String(goldCount), accent: true },
    { label: "CONFIRMED PLANETS", value: String(planetCount) },
    { label: "AVG SDE", value: avgSde.toFixed(2) },
  ];

  return (
    <div className="w-full border-b border-[var(--border-color)]">
      <div className="flex">
        {stats.map((stat, i) => (
          <div
            key={stat.label}
            className={`flex-1 px-6 py-3 ${
              i < stats.length - 1 ? "border-r border-[var(--border-color)]" : ""
            }`}
          >
            <span className="block text-[10px] font-mono text-[var(--fg-dim)] tracking-widest mb-1">
              {stat.label}
            </span>
            <span
              className={`font-sans font-black text-2xl tabular-nums ${
                stat.accent ? "text-[var(--accent)]" : "text-[var(--fg)]"
              }`}
            >
              {stat.value}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
