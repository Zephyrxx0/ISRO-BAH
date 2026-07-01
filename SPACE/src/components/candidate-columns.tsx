'use client';

import { ColumnDef } from '@tanstack/react-table';
import { AstronomicalSignal, ConfidenceTier, PipelineDisposition } from '../../outputs/integration-schema';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { ArrowUpDown } from 'lucide-react';

export const candidateColumns: ColumnDef<AstronomicalSignal>[] = [
  {
    accessorKey: 'ticId',
    header: 'TIC ID',
  },
  {
    accessorKey: 'name',
    header: ({ column }) => {
      return (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
        >
          TARGET ID
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      );
    },
  },
  {
    accessorKey: 'period',
    header: ({ column }) => {
      return (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
        >
          PERIOD (D)
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      );
    },
    cell: ({ row }) => {
      return <div>{(row.getValue('period') as number).toFixed(6)}</div>;
    },
  },
  {
    accessorKey: 'depth',
    header: ({ column }) => {
      return (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
        >
          DEPTH (PPT)
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      );
    },
    cell: ({ row }) => {
      return <div>{(row.getValue('depth') as number).toFixed(3)}</div>;
    },
  },
  {
    accessorKey: 'sde',
    header: ({ column }) => {
      return (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
        >
          SDE
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      );
    },
    cell: ({ row }) => {
      return <div>{(row.getValue('sde') as number).toFixed(2)}</div>;
    },
  },
  {
    accessorKey: 'snr',
    header: ({ column }) => {
      return (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
        >
          SNR
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      );
    },
    cell: ({ row }) => {
      return <div>{(row.getValue('snr') as number).toFixed(2)}</div>;
    },
  },
  {
    accessorKey: 'confidenceTier',
    header: 'CONFIDENCE',
    cell: ({ row }) => {
      const tier = row.getValue('confidenceTier') as ConfidenceTier;
      let badgeClass = '';
      switch (tier) {
        case 'GOLD':
          badgeClass = 'bg-[#f59e0b] text-black hover:bg-[#f59e0b]/80';
          break;
        case 'SILVER':
          badgeClass = 'bg-[#94a3b8] text-black hover:bg-[#94a3b8]/80';
          break;
        case 'BRONZE':
          badgeClass = 'bg-[#d97706] text-white hover:bg-[#d97706]/80';
          break;
        case 'FALSE_POSITIVE':
          badgeClass = 'bg-red-500 text-white hover:bg-red-600';
          break;
      }
      return <Badge className={badgeClass}>{tier}</Badge>;
    },
  },
  {
    accessorKey: 'disposition',
    header: 'DISPOSITION',
    cell: ({ row }) => {
      const disp = row.getValue('disposition') as PipelineDisposition;
      let label = 'FALSE ALARM';
      let colorClass = 'text-red-500';
      if (disp === 'CONFIRMED_PLANET') {
        label = 'CONFIRMED';
        colorClass = 'text-green-500';
      } else if (disp === 'BINARY_STAR_ECLIPSE') {
        label = 'EB ECLIPSE';
        colorClass = 'text-yellow-500';
      } else if (disp === 'BACKGROUND_STELLAR_CONTAMINATION') {
        label = 'BG BLEND';
        colorClass = 'text-red-500';
      }
      return <div className={`font-semibold ${colorClass}`}>{label}</div>;
    },
  },
  {
    id: 'actions',
    cell: ({ row, table }) => {
      return (
        <Button 
          variant="outline"
          size="sm"
          onClick={(e) => {
            e.stopPropagation(); // Prevent row selection trigger
            (table.options.meta as any)?.onSelectCandidate(row.original.ticId);
          }}
        >
          Explore Candidate
        </Button>
      );
    },
  }
];
