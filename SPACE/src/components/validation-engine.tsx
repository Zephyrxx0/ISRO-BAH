"use client";

import { CandidateEntry } from "../../outputs/integration-schema";

interface ValidationEngineProps {
  candidate: CandidateEntry;
}

export default function ValidationEngine({ candidate }: ValidationEngineProps) {
  const { triceratops, sherlock } = candidate.validation;

  const toPercent = (val: number) => (val * 100).toFixed(4) + "%";

  const fppColor =
    triceratops.fpp > 0.5
      ? "var(--accent)"
      : triceratops.fpp > 0.01
        ? "#b45309"
        : "var(--terminal-green)";

  const nfppColor =
    triceratops.nfpp > 0.1
      ? "var(--accent)"
      : triceratops.nfpp > 0.005
        ? "#b45309"
        : "var(--terminal-green)";

  const recoveryColor =
    sherlock.overallRecoveryStatus === "RECOVERED"
      ? "var(--terminal-green)"
      : sherlock.overallRecoveryStatus === "NOT_RECOVERED"
        ? "var(--accent)"
        : "#b45309";

  return (
    <div className="border border-[var(--border-color)] bg-[var(--surface)]">
      {/* HEADER */}
      <div className="flex items-center gap-4 px-4 py-2 border-b border-[var(--border-color)] bg-[var(--panel)]">
        <span className="font-mono text-[10px] tracking-widest text-[var(--fg-dim)]">
          [ VALIDATION REPORT ]
        </span>
        <span className="font-mono text-[10px] tracking-widest text-[var(--fg-dim)]">
          REF: TRICERATOPS+ MCMC
        </span>
        <span className="font-mono text-[10px] tracking-widest text-[var(--fg-dim)]">
          SHERLOCK MATRIX
        </span>
        <span className="ml-auto font-mono text-[10px] tracking-widest text-[var(--fg-dim)]">
          REV 2.6 // CONFIDENTIAL
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2">
        {/* TRICERATOPS PANEL */}
        <div className="border-b md:border-b-0 md:border-r border-[var(--border-color)]">
          <div className="px-4 py-2 border-b border-[var(--border-color)] bg-[var(--panel)]/50">
            <span className="font-mono text-[10px] tracking-widest text-[var(--fg-dim)]">
              TRICERATOPS BAYESIAN VALIDATION
            </span>
          </div>

          <div className="p-4 space-y-4">
            {/* FPP */}
            <div>
              <div className="flex justify-between items-baseline mb-1">
                <span className="font-mono text-[9px] text-[var(--fg-dim)] tracking-widest">
                  FALSE POSITIVE PROBABILITY
                </span>
                <span className="font-mono text-xs text-[var(--fg)] tabular-nums">
                  {triceratops.fpp.toFixed(6)}
                </span>
              </div>
              <div className="h-2 w-full bg-[var(--panel)] border border-[var(--border-color)]">
                <div
                  className="h-full transition-all"
                  style={{
                    width: `${Math.min(100, Math.max(1, triceratops.fpp * 100))}%`,
                    backgroundColor: fppColor,
                  }}
                />
              </div>
              <span className="block text-right font-mono text-[8px] text-[var(--fg-dim)] mt-0.5">
                THRESHOLD &lt; 0.01
              </span>
            </div>

            {/* NFPP */}
            <div>
              <div className="flex justify-between items-baseline mb-1">
                <span className="font-mono text-[9px] text-[var(--fg-dim)] tracking-widest">
                  NON-TRANSITING FPP
                </span>
                <span className="font-mono text-xs text-[var(--fg)] tabular-nums">
                  {triceratops.nfpp.toFixed(6)}
                </span>
              </div>
              <div className="h-2 w-full bg-[var(--panel)] border border-[var(--border-color)]">
                <div
                  className="h-full transition-all"
                  style={{
                    width: `${Math.min(100, Math.max(1, triceratops.nfpp * 100))}%`,
                    backgroundColor: nfppColor,
                  }}
                />
              </div>
              <span className="block text-right font-mono text-[8px] text-[var(--fg-dim)] mt-0.5">
                THRESHOLD &lt; 0.005
              </span>
            </div>
          </div>

          {/* MODE BREAKDOWN */}
          <div className="grid grid-cols-3 border-t border-[var(--border-color)]">
            {[
              ["TRUE PLANET", triceratops.modes.tp, "var(--terminal-green)"],
              ["ECLIPSING BINARY", triceratops.modes.eb, triceratops.modes.eb > 0.1 ? "var(--accent)" : "var(--fg)"],
              ["BG BLEND", triceratops.modes.bgob + triceratops.modes.heb, (triceratops.modes.bgob + triceratops.modes.heb) > 0.1 ? "var(--accent)" : "var(--fg)"],
            ].map(([label, val, color], i) => (
              <div
                key={label as string}
                className={`p-3 text-center bg-[var(--panel)]/50 ${
                  i < 2 ? "border-r border-[var(--border-color)]" : ""
                }`}
              >
                <span className="block font-mono text-[8px] text-[var(--fg-dim)] tracking-widest mb-1">
                  {label}
                </span>
                <span
                  className="font-mono text-sm tabular-nums font-bold"
                  style={{ color: color as string }}
                >
                  {toPercent(val as number)}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* SHERLOCK PANEL */}
        <div>
          <div className="px-4 py-2 border-b border-[var(--border-color)] bg-[var(--panel)]/50 flex items-center justify-between">
            <span className="font-mono text-[10px] tracking-widest text-[var(--fg-dim)]">
              SHERLOCK STABILITY RECOVERY
            </span>
            <span
              className="font-mono text-[10px] tracking-widest font-bold"
              style={{ color: recoveryColor }}
            >
              {sherlock.overallRecoveryStatus}
            </span>
          </div>

          <div className="p-4">
            <div className="mb-4">
              <span className="font-mono text-[9px] text-[var(--fg-dim)] tracking-widest">
                SECTORS: {sherlock.sectors.join(" / ")}
              </span>
            </div>

            {/* PASS/FAIL MATRIX */}
            <table className="w-full border-collapse">
              <thead>
                <tr className="border border-[var(--border-color)]">
                  {["SECTOR", "PERIOD", "DEPTH", "SNR", "STATUS"].map((h) => (
                    <th
                      key={h}
                      className="font-mono text-[9px] text-[var(--fg-dim)] tracking-widest p-2 text-left border-r border-[var(--border-color)] bg-[var(--panel)]"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {sherlock.passFailMatrix.map((val) => (
                  <tr
                    key={val.sector}
                    className="border border-[var(--border-color)]"
                  >
                    <td className="font-mono text-xs text-[var(--fg)] p-2 border-r border-[var(--border-color)] tabular-nums">
                      {val.sector.toString().padStart(2, "0")}
                    </td>
                    <td className="font-mono text-xs p-2 border-r border-[var(--border-color)]">
                      <span
                        className={
                          val.periodMatch
                            ? "text-[var(--terminal-green)]"
                            : "text-[var(--accent)]"
                        }
                      >
                        {val.periodMatch ? "MATCH" : "FAIL"}
                      </span>
                    </td>
                    <td className="font-mono text-xs p-2 border-r border-[var(--border-color)]">
                      <span
                        className={
                          val.depthConsistency
                            ? "text-[var(--terminal-green)]"
                            : "text-[var(--fg-dim)]"
                        }
                      >
                        {val.depthConsistency ? "CONSISTENT" : "DEVIATING"}
                      </span>
                    </td>
                    <td className="font-mono text-xs text-[var(--fg)] p-2 border-r border-[var(--border-color)] tabular-nums">
                      {val.snr > 0 ? val.snr.toFixed(1) : "\u2014"}
                    </td>
                    <td className="p-2">
                      <span
                        className={`font-mono text-[10px] tracking-widest font-bold ${
                          val.status === "PASS"
                            ? "text-[var(--terminal-green)]"
                            : "text-[var(--accent)]"
                        }`}
                      >
                        {val.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* VERDICT */}
          <div className="px-4 py-2 border-t border-[var(--border-color)] bg-[var(--panel)]/50 flex items-center gap-3">
            <span className="font-mono text-[10px] tracking-widest text-[var(--fg-dim)]">
              VERDICT:
            </span>
            {candidate.signal.disposition === "CONFIRMED_PLANET" ? (
              <span className="font-mono text-[10px] tracking-widest text-[var(--terminal-green)] font-bold">
                SIGNAL CLEAR. CONFIDENCE METRICS STABLE.
              </span>
            ) : candidate.signal.disposition === "BINARY_STAR_ECLIPSE" ? (
              <span className="font-mono text-[10px] tracking-widest text-[var(--accent)] font-bold">
                WARNING: HIGH FPP INDICATES LIKELY ECLIPSING BINARY.
              </span>
            ) : (
              <span className="font-mono text-[10px] tracking-widest text-[var(--accent)] font-bold">
                CRITICAL: BACKGROUND STAR DETECTED IN APERTURE BLEND.
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
