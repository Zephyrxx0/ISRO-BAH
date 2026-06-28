'use client';

import { useState } from 'react';
import { AstronomicalSignal, ConfidenceTier, PipelineDisposition } from '../../outputs/integration-schema';
import { Database, Filter, Search, ArrowUpDown } from 'lucide-react';

interface CandidateTableProps {
  candidates: AstronomicalSignal[];
  selectedTicId: string;
  onSelectCandidate: (ticId: string) => void;
}

type SortField = 'name' | 'period' | 'depth' | 'sde' | 'snr' | 'confidenceTier';
type SortOrder = 'asc' | 'desc';

export default function CandidateTable({
  candidates,
  selectedTicId,
  onSelectCandidate
}: CandidateTableProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterTier, setFilterTier] = useState<string>('ALL');
  const [sortField, setSortField] = useState<SortField>('sde');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortOrder('desc');
    }
  };

  const getTierColor = (tier: ConfidenceTier) => {
    switch (tier) {
      case 'GOLD':
        return 'text-signal-green border-signal-green bg-green-50';
      case 'SILVER':
        return 'text-warning-amber border-warning-amber bg-amber-50';
      case 'BRONZE':
        return 'text-zinc-600 border-zinc-300 bg-zinc-50';
      case 'FALSE_POSITIVE':
        return 'text-blending-red border-blending-red bg-red-50';
    }
  };

  const getDispositionLabel = (disp: PipelineDisposition) => {
    switch (disp) {
      case 'CONFIRMED_PLANET':
        return 'CONFIRMED';
      case 'BINARY_STAR_ECLIPSE':
        return 'EB ECLIPSE';
      case 'BACKGROUND_STELLAR_CONTAMINATION':
        return 'BG BLEND';
      case 'FALSE_ALARM':
        return 'FALSE ALARM';
    }
  };

  // Filter & Sort candidates
  const processedCandidates = candidates
    .filter((cand) => {
      const matchesSearch = 
        cand.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        cand.ticId.toLowerCase().includes(searchTerm.toLowerCase());
      
      const matchesTier = filterTier === 'ALL' || cand.confidenceTier === filterTier;
      
      return matchesSearch && matchesTier;
    })
    .sort((a, b) => {
      let comparison = 0;
      if (sortField === 'name') {
        comparison = a.name.localeCompare(b.name);
      } else if (sortField === 'confidenceTier') {
        comparison = a.confidenceTier.localeCompare(b.confidenceTier);
      } else {
        comparison = a[sortField] - b[sortField];
      }
      return sortOrder === 'asc' ? comparison : -comparison;
    });

  return (
    <div className="border border-border-brutal bg-[#FAFAFA] flex flex-col h-full">
      {/* Header Controls */}
      <div className="p-4 border-b border-border-brutal bg-[#FAFAFA] flex flex-col lg:flex-row lg:items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Database className="w-4 h-4 text-zinc-950" />
          <span className="text-[10px] uppercase font-bold tracking-wider text-zinc-900">
            TESS SECTOR TARGET DATA MATRIX
          </span>
        </div>
        
        {/* Search & Filter Inputs */}
        <div className="flex items-center gap-2 text-[10px] font-mono">
          <div className="relative flex items-center">
            <Search className="w-3.5 h-3.5 text-raw-zinc absolute left-2" />
            <input
              type="text"
              placeholder="SEARCH TIC ID / TARGET NAME"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-7 pr-2 py-1 border border-border-brutal bg-[#FAFAFA] focus:outline-none focus:bg-zinc-50 w-[180px] uppercase placeholder-zinc-400 font-bold"
            />
          </div>

          <div className="flex items-center gap-1.5 border border-border-brutal px-2 py-1 bg-zinc-50">
            <Filter className="w-3.5 h-3.5 text-zinc-800" />
            <select
              value={filterTier}
              onChange={(e) => setFilterTier(e.target.value)}
              className="bg-transparent focus:outline-none font-bold uppercase cursor-pointer"
            >
              <option value="ALL">ALL TIERS</option>
              <option value="GOLD">GOLD</option>
              <option value="SILVER">SILVER</option>
              <option value="BRONZE">BRONZE</option>
              <option value="FALSE_POSITIVE">FALSE POSITIVE</option>
            </select>
          </div>
        </div>
      </div>

      {/* Candidates Data Log Table */}
      <div className="flex-1 overflow-x-auto">
        <table className="w-full text-left border-collapse text-[10px] font-mono">
          <thead>
            <tr className="bg-zinc-100 border-b border-border-brutal text-[8px] text-zinc-600 select-none">
              <th className="p-3 border-r border-border-brutal uppercase">TIC ID</th>
              <th className="p-3 border-r border-border-brutal uppercase cursor-pointer hover:bg-zinc-200" onClick={() => handleSort('name')}>
                <div className="flex items-center gap-1.5">
                  TARGET ID <ArrowUpDown className="w-3 h-3 text-zinc-500" />
                </div>
              </th>
              <th className="p-3 border-r border-border-brutal uppercase cursor-pointer hover:bg-zinc-200" onClick={() => handleSort('period')}>
                <div className="flex items-center gap-1.5">
                  PERIOD (D) <ArrowUpDown className="w-3 h-3 text-zinc-500" />
                </div>
              </th>
              <th className="p-3 border-r border-border-brutal uppercase cursor-pointer hover:bg-zinc-200" onClick={() => handleSort('depth')}>
                <div className="flex items-center gap-1.5">
                  DEPTH (PPT) <ArrowUpDown className="w-3 h-3 text-zinc-500" />
                </div>
              </th>
              <th className="p-3 border-r border-border-brutal uppercase cursor-pointer hover:bg-zinc-200" onClick={() => handleSort('sde')}>
                <div className="flex items-center gap-1.5">
                  SDE <ArrowUpDown className="w-3 h-3 text-zinc-500" />
                </div>
              </th>
              <th className="p-3 border-r border-border-brutal uppercase cursor-pointer hover:bg-zinc-200" onClick={() => handleSort('snr')}>
                <div className="flex items-center gap-1.5">
                  SNR <ArrowUpDown className="w-3 h-3 text-zinc-500" />
                </div>
              </th>
              <th className="p-3 border-r border-border-brutal uppercase cursor-pointer hover:bg-zinc-200" onClick={() => handleSort('confidenceTier')}>
                <div className="flex items-center gap-1.5">
                  CONFIDENCE <ArrowUpDown className="w-3 h-3 text-zinc-500" />
                </div>
              </th>
              <th className="p-3 uppercase">DISPOSITION</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border-brutal">
            {processedCandidates.length > 0 ? (
              processedCandidates.map((cand) => {
                const isSelected = cand.ticId === selectedTicId;
                return (
                  <tr
                    key={cand.ticId}
                    onClick={() => onSelectCandidate(cand.ticId)}
                    className={`cursor-pointer transition-all select-none hover:bg-zinc-50 ${
                      isSelected ? 'bg-zinc-100 font-bold border-l-4 border-l-zinc-900 border-r border-y-zinc-200' : ''
                    }`}
                  >
                    <td className="p-3 border-r border-border-brutal font-mono text-zinc-600">{cand.ticId}</td>
                    <td className="p-3 border-r border-border-brutal text-zinc-950 font-bold">{cand.name}</td>
                    <td className="p-3 border-r border-border-brutal font-mono">{cand.period.toFixed(6)}</td>
                    <td className="p-3 border-r border-border-brutal font-mono font-bold text-zinc-900">{cand.depth.toFixed(3)}</td>
                    <td className="p-3 border-r border-border-brutal font-mono">{cand.sde.toFixed(2)}</td>
                    <td className="p-3 border-r border-border-brutal font-mono">{cand.snr.toFixed(2)}</td>
                    <td className="p-3 border-r border-border-brutal">
                      <span className={`px-2 py-0.5 border font-bold text-[8px] ${getTierColor(cand.confidenceTier)}`}>
                        {cand.confidenceTier}
                      </span>
                    </td>
                    <td className="p-3">
                      <span className={`font-mono text-[9px] font-bold ${
                        cand.disposition === 'CONFIRMED_PLANET' ? 'text-signal-green' : 
                        cand.disposition === 'BINARY_STAR_ECLIPSE' ? 'text-warning-amber' : 'text-blending-red'
                      }`}>
                        {getDispositionLabel(cand.disposition)}
                      </span>
                    </td>
                  </tr>
                );
              })
            ) : (
              <tr>
                <td colSpan={8} className="p-8 text-center text-raw-zinc uppercase font-bold bg-zinc-50">
                  NO SIGNALS DETECTED IN SELECTED SEARCH RANGE
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Database Footer Status */}
      <div className="p-3 border-t border-border-brutal bg-zinc-50 text-[9px] text-raw-zinc font-mono flex items-center justify-between">
        <span>TOTAL RECORDED DATABASE ENTRIES: {candidates.length} CANDIDATES</span>
        <span>SHERLOCK APERTURE ALGORITHM ACTIVE</span>
      </div>
    </div>
  );
}
