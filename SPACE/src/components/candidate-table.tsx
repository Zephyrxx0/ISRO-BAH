'use client';

import * as React from 'react';
import {
  ColumnFiltersState,
  SortingState,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
} from '@tanstack/react-table';

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

import { candidateColumns } from './candidate-columns';
import { AstronomicalSignal } from '../../outputs/integration-schema';

interface CandidateTableProps {
  candidates: AstronomicalSignal[];
  selectedTicId: string;
  onSelectCandidate: (ticId: string) => void;
}

export default function CandidateTable({
  candidates,
  selectedTicId,
  onSelectCandidate,
}: CandidateTableProps) {
  const [sorting, setSorting] = React.useState<SortingState>([]);
  const [columnFilters, setColumnFilters] = React.useState<ColumnFiltersState>([]);

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
    meta: {
      onSelectCandidate,
    },
    initialState: {
      pagination: { pageSize: 20 },
    },
  });

  return (
    <div className="w-full space-y-4">
      <div className="flex flex-col sm:flex-row items-center gap-4">
        <Input
          placeholder="Filter by TIC ID..."
          value={(table.getColumn('ticId')?.getFilterValue() as string) ?? ''}
          onChange={(event) =>
            table.getColumn('ticId')?.setFilterValue(event.target.value)
          }
          className="max-w-sm"
        />
        <Select
          onValueChange={(value) => {
            if (value === 'ALL') table.getColumn('confidenceTier')?.setFilterValue('');
            else table.getColumn('confidenceTier')?.setFilterValue(value);
          }}
        >
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="All Tiers" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="ALL">All Tiers</SelectItem>
            <SelectItem value="GOLD">Gold</SelectItem>
            <SelectItem value="SILVER">Silver</SelectItem>
            <SelectItem value="BRONZE">Bronze</SelectItem>
            <SelectItem value="FALSE_POSITIVE">False Positive</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="rounded-md border bg-card">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => {
                  return (
                    <TableHead key={header.id}>
                      {header.isPlaceholder
                        ? null
                        : flexRender(
                            header.column.columnDef.header,
                            header.getContext()
                          )}
                    </TableHead>
                  );
                })}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {table.getRowModel().rows?.length ? (
              table.getRowModel().rows.map((row) => {
                const isSelected = row.original.ticId === selectedTicId;
                return (
                  <TableRow
                    key={row.id}
                    data-state={isSelected ? 'selected' : undefined}
                    className={`cursor-pointer ${isSelected ? 'bg-muted/50 border-l-2 border-primary' : ''}`}
                    onClick={() => onSelectCandidate(row.original.ticId)}
                  >
                    {row.getVisibleCells().map((cell) => (
                      <TableCell key={cell.id}>
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
                  No candidates match your filters
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      <div className="flex items-center justify-end space-x-2 py-4">
        <Button
          variant="outline"
          size="sm"
          onClick={() => table.previousPage()}
          disabled={!table.getCanPreviousPage()}
        >
          Previous
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => table.nextPage()}
          disabled={!table.getCanNextPage()}
        >
          Next
        </Button>
      </div>
    </div>
  );
}
