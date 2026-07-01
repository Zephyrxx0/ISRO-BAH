"use client";

import { ColumnDef } from "@tanstack/react-table";
import {
  AstronomicalSignal,
  ConfidenceTier,
  PipelineDisposition,
} from "../../outputs/integration-schema";

export const candidateColumns: ColumnDef<AstronomicalSignal>[] = [
  {
    accessorKey: "ticId",
    header: () => (
      <span className="font-mono text-[10px] text-[var(--fg-dim)] tracking-widest">
        TIC ID
      </span>
    ),
    cell: ({ row }) => (
      <span className="font-mono text-xs text-[var(--fg)] tabular-nums">
        {row.getValue("ticId") as string}
      </span>
    ),
  },
  {
    accessorKey: "name",
    header: () => (
      <span className="font-mono text-[10px] text-[var(--fg-dim)] tracking-widest">
        TARGET
      </span>
    ),
    cell: ({ row }) => (
      <span className="font-sans font-bold text-xs text-[var(--fg)]">
        {row.getValue("name") as string}
      </span>
    ),
  },
  {
    accessorKey: "period",
    header: () => (
      <span className="font-mono text-[10px] text-[var(--fg-dim)] tracking-widest">
        PERIOD (D)
      </span>
    ),
    cell: ({ row }) => (
      <span className="font-mono text-xs text-[var(--fg)] tabular-nums">
        {(row.getValue("period") as number).toFixed(6)}
      </span>
    ),
  },
  {
    accessorKey: "depth",
    header: () => (
      <span className="font-mono text-[10px] text-[var(--fg-dim)] tracking-widest">
        DEPTH (PPT)
      </span>
    ),
    cell: ({ row }) => (
      <span className="font-mono text-xs text-[var(--fg)] tabular-nums">
        {(row.getValue("depth") as number).toFixed(3)}
      </span>
    ),
  },
  {
    accessorKey: "sde",
    header: () => (
      <span className="font-mono text-[10px] text-[var(--fg-dim)] tracking-widest">
        SDE
      </span>
    ),
    cell: ({ row }) => (
      <span className="font-mono text-xs text-[var(--fg)] tabular-nums">
        {(row.getValue("sde") as number).toFixed(2)}
      </span>
    ),
  },
  {
    accessorKey: "snr",
    header: () => (
      <span className="font-mono text-[10px] text-[var(--fg-dim)] tracking-widest">
        SNR
      </span>
    ),
    cell: ({ row }) => (
      <span className="font-mono text-xs text-[var(--fg)] tabular-nums">
        {(row.getValue("snr") as number).toFixed(2)}
      </span>
    ),
  },
  {
    accessorKey: "confidenceTier",
    header: () => (
      <span className="font-mono text-[10px] text-[var(--fg-dim)] tracking-widest">
        TIER
      </span>
    ),
    cell: ({ row }) => {
      const tier = row.getValue("confidenceTier") as ConfidenceTier;
      const colors: Record<string, string> = {
        GOLD: "border-[var(--accent)] text-[var(--accent)]",
        SILVER: "border-[var(--fg-dim)] text-[var(--fg-dim)]",
        BRONZE: "border-[#b45309] text-[#b45309]",
        FALSE_POSITIVE: "border-[var(--fg-dim)] text-[var(--fg-dim)]",
      };
      return (
        <span
          className={`inline-block font-mono text-[10px] tracking-widest border px-2 py-0.5 ${
            colors[tier] || ""
          }`}
        >
          {tier}
        </span>
      );
    },
  },
  {
    accessorKey: "disposition",
    header: () => (
      <span className="font-mono text-[10px] text-[var(--fg-dim)] tracking-widest">
        DISPOSITION
      </span>
    ),
    cell: ({ row }) => {
      const disp = row.getValue("disposition") as PipelineDisposition;
      const labels: Record<string, { text: string; className: string }> = {
        CONFIRMED_PLANET: {
          text: "CONFIRMED PLANET",
          className: "text-[var(--terminal-green)]",
        },
        BINARY_STAR_ECLIPSE: {
          text: "ECLIPSING BINARY",
          className: "text-[var(--accent)]",
        },
        BACKGROUND_STELLAR_CONTAMINATION: {
          text: "BG BLEND",
          className: "text-[var(--accent)]",
        },
      };
      const info = labels[disp] || {
        text: "FALSE ALARM",
        className: "text-[var(--fg-dim)]",
      };
      return (
        <span
          className={`font-mono text-[10px] tracking-widest font-bold ${info.className}`}
        >
          {info.text}
        </span>
      );
    },
  },
  {
    id: "actions",
    header: () => null,
    cell: ({ row }) => {
      const ticId = row.original.ticId.replace(/\s/g, "");
      return (
        <a
          href={`/star/${ticId}`}
          onClick={(e) => e.stopPropagation()}
          className="inline-block font-mono text-[10px] tracking-widest text-[var(--fg-dim)] hover:text-[var(--fg)] border border-[var(--border-color)] hover:border-[var(--fg-dim)] px-3 py-1 transition-colors no-underline"
        >
          [ INSPECT ]
        </a>
      );
    },
  },
];
