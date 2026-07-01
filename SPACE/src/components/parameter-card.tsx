interface ParameterCardProps {
  params: {
    period?: number;
    period_err?: number;
    depth?: number;
    depth_err?: number;
    duration?: number;
    duration_err?: number;
    sde: number;
    snr: number;
    rp_rs?: number;
    rp_rs_err?: number;
    inclination?: number;
    inclination_err?: number;
    confidence_tier: string;
    disposition: string;
  };
}

function ParamValue({
  label,
  value,
  error,
  unit,
}: {
  label: string;
  value?: number;
  error?: number;
  unit?: string;
}) {
  if (value == null) {
    return (
      <div>
        <span className="block font-mono text-[8px] text-[var(--fg-dim)] tracking-widest mb-0.5">
          {label}
        </span>
        <span className="font-mono text-xs text-[var(--fg-dim)]">&mdash;</span>
      </div>
    );
  }

  const formatted = error != null
    ? `${value.toFixed(4)} ± ${error.toFixed(4)}`
    : value.toFixed(4);

  return (
    <div>
      <span className="block font-mono text-[8px] text-[var(--fg-dim)] tracking-widest mb-0.5">
        {label}
      </span>
      <span className="font-mono text-xs text-[var(--fg)] tabular-nums">
        {formatted}
        {unit && (
          <span className="text-[var(--fg-dim)] ml-0.5">{unit}</span>
        )}
      </span>
    </div>
  );
}

export default function ParameterCard({ params }: ParameterCardProps) {
  const tierColor =
    params.confidence_tier === "GOLD"
      ? "var(--accent)"
      : params.confidence_tier === "SILVER"
        ? "var(--fg-dim)"
        : "#b45309";

  const dispColor =
    params.disposition === "PLANET CANDIDATE"
      ? "var(--terminal-green)"
      : params.disposition === "ECLIPSING BINARY"
        ? "var(--accent)"
        : "var(--fg-dim)";

  return (
    <div className="border border-[var(--border-color)] bg-[var(--surface)]">
      <div className="flex items-center justify-between px-4 py-2 border-b border-[var(--border-color)] bg-[var(--panel)]">
        <span className="font-mono text-[10px] tracking-widest text-[var(--fg-dim)]">
          [ ORBITAL PARAMETERS ]
        </span>
        <div className="flex items-center gap-2">
          <span
            className="font-mono text-[10px] tracking-widest font-bold"
            style={{ color: dispColor }}
          >
            {params.disposition}
          </span>
          <span
            className="font-mono text-[9px] tracking-widest border px-1.5 py-0.5"
            style={{
              borderColor: tierColor,
              color: tierColor,
            }}
          >
            {params.confidence_tier}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-px bg-[var(--border-color)]">
        <div className="bg-[var(--surface)] p-3">
          <ParamValue label="PERIOD" value={params.period} error={params.period_err} unit="d" />
        </div>
        <div className="bg-[var(--surface)] p-3">
          <ParamValue label="DEPTH" value={params.depth} error={params.depth_err} unit="ppt" />
        </div>
        <div className="bg-[var(--surface)] p-3">
          <ParamValue label="DURATION" value={params.duration} error={params.duration_err} unit="h" />
        </div>
        <div className="bg-[var(--surface)] p-3">
          <ParamValue label="SDE" value={params.sde} />
        </div>
        <div className="bg-[var(--surface)] p-3">
          <ParamValue label="SNR" value={params.snr} />
        </div>
        <div className="bg-[var(--surface)] p-3">
          <ParamValue label="Rp/Rs" value={params.rp_rs} error={params.rp_rs_err} />
        </div>
        <div className="bg-[var(--surface)] p-3">
          <ParamValue label="INCLINATION" value={params.inclination} error={params.inclination_err} unit="&deg;" />
        </div>
      </div>
    </div>
  );
}
