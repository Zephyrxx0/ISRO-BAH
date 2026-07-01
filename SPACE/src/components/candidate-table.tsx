"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import {
  ColumnFiltersState,
  SortingState,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

import { candidateColumns } from "./candidate-columns";
import { AstronomicalSignal } from "../../outputs/integration-schema";

interface CandidateTableProps {
  candidates: AstronomicalSignal[];
}

const TIER_OPTIONS = [
  { value: "ALL", label: "ALL TIERS" },
  { value: "GOLD", label: "GOLD" },
  { value: "SILVER", label: "SILVER" },
  { value: "BRONZE", label: "BRONZE" },
  { value: "FALSE_POSITIVE", label: "FALSE POSITIVE" },
];

export default function CandidateTable({
  candidates,
}: CandidateTableProps) {
  const router = useRouter();
  const [sorting, setSorting] = React.useState<SortingState>([]);
  const [columnFilters, setColumnFilters] = React.useState<ColumnFiltersState>(
    []
  );
  const [tierFilter, setTierFilter] = React.useState("ALL");

  const table = useReactTable({
    data: candidates,
    columns: candidateColumns,
    getCoreRowModel: getCoreRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    onSortingChange: setSorting,
    getSortedRowModel: getSortedRowModel(),
    onColumnFiltersChange: setColumnFilters,
    getFilteredRowModel: getFilteredRowModel(),
    state: {
      sorting,
      columnFilters,
    },
    initialState: {
      pagination: { pageSize: 20 },
    },
  });

  const handleTierChange = (value: string) => {
    setTierFilter(value);
    if (value === "ALL") {
      table.getColumn("confidenceTier")?.setFilterValue("");
    } else {
      table.getColumn("confidenceTier")?.setFilterValue(value);
    }
  };

  const pageCount = table.getPageCount();
  const pageIndex = table.getState().pagination.pageIndex;

  return (
    <div className="w-full">
      {/* FILTERS */}
      <div className="flex items-center gap-2 px-4 py-2 border-b border-[var(--border-color)] bg-[var(--panel)]">
        <span className="font-mono text-[10px] text-[var(--fg-dim)] tracking-widest mr-2">
          FILTER //
        </span>
        <input
          placeholder="TIC ID..."
          value={
            (table.getColumn("ticId")?.getFilterValue() as string) ?? ""
          }
          onChange={(e) =>
            table.getColumn("ticId")?.setFilterValue(e.target.value)
          }
          className="font-mono text-xs bg-[var(--surface)] border border-[var(--border-color)] text-[var(--fg)] px-2 py-1 w-40 focus:outline-none focus:border-[var(--fg-dim)] placeholder:text-[var(--fg-dim)]/40"
        />
        <span className="text-[var(--border-color)] font-mono text-xs">//</span>
        <div className="flex gap-1">
          {TIER_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => handleTierChange(opt.value)}
              className={`font-mono text-[10px] tracking-widest px-2 py-1 border transition-colors ${
                tierFilter === opt.value
                  ? "bg-[var(--accent)] border-[var(--accent)] text-[var(--fg)]"
                  : "border-[var(--border-color)] text-[var(--fg-dim)] hover:text-[var(--fg)] hover:border-[var(--fg-dim)]"
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
        <span className="ml-auto font-mono text-[10px] text-[var(--fg-dim)] tracking-widest">
          {table.getFilteredRowModel().rows.length} / {candidates.length} ROWS
        </span>
      </div>

      {/* TABLE */}
      <div className="border-b border-[var(--border-color)] bg-[var(--surface)]">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow
                key={headerGroup.id}
                className="border-b border-[var(--border-color)] hover:bg-transparent"
              >
                {headerGroup.headers.map((header) => (
                  <TableHead
                    key={header.id}
                    className="h-8 px-4 py-1 bg-[var(--panel)] text-left"
                  >
                    {header.isPlaceholder
                      ? null
                      : flexRender(
                          header.column.columnDef.header,
                          header.getContext()
                        )}
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {table.getRowModel().rows?.length ? (
              table.getRowModel().rows.map((row) => {
                return (
                  <TableRow
                    key={row.id}
                    className="cursor-pointer border-b border-[var(--border-color)] transition-colors hover:bg-[var(--panel)]/50"
                    onClick={() => router.push(`/star/${row.original.ticId.replace(/\s/g, "")}`)}
                  >
                    {row.getVisibleCells().map((cell) => (
                      <TableCell key={cell.id} className="px-4 py-2">
                        {flexRender(
                          cell.column.columnDef.cell,
                          cell.getContext()
                        )}
                      </TableCell>
                    ))}
                  </TableRow>
                );
              })
            ) : (
              <TableRow>
                <TableCell
                  colSpan={candidateColumns.length}
                  className="h-24 text-center"
                >
                  <span className="font-mono text-xs text-[var(--fg-dim)]">
                    // NO CANDIDATES MATCH FILTERS
                  </span>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      {/* PAGINATION */}
      <div className="flex items-center justify-between px-4 py-2 bg-[var(--panel)] border-b border-[var(--border-color)]">
        <span className="font-mono text-[10px] text-[var(--fg-dim)] tracking-widest">
          PAGE {pageIndex + 1} / {pageCount || 1}
        </span>
        <div className="flex gap-1">
          <button
            onClick={() => table.previousPage()}
            disabled={!table.getCanPreviousPage()}
            className="font-mono text-[10px] tracking-widest text-[var(--fg-dim)] hover:text-[var(--fg)] border border-[var(--border-color)] hover:border-[var(--fg-dim)] px-3 py-1 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            [ PREV ]
          </button>
          <button
            onClick={() => table.nextPage()}
            disabled={!table.getCanNextPage()}
            className="font-mono text-[10px] tracking-widest text-[var(--fg-dim)] hover:text-[var(--fg)] border border-[var(--border-color)] hover:border-[var(--fg-dim)] px-3 py-1 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            [ NEXT ]
          </button>
        </div>
      </div>
    </div>
  );
}
