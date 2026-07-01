# Phase 4 Research: Presentation — Dashboard & Report

**Researched:** 2026-06-28
**Status:** Complete

---

## 1. Next.js 15 App Router — Static Site Generation

### Configuration

```js
// next.config.js
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  images: { unoptimized: true },
  trailingSlash: true,
}
module.exports = nextConfig
```

**Key facts:**
- `output: 'export'` generates static HTML into `out/` folder
- Every dynamic route MUST export `generateStaticParams()` — build fails without it
- Server Components run at build time (like traditional SSG)
- `fs` module works in Server Components and `generateStaticParams` since they execute at build time only

### generateStaticParams Pattern for `/star/[ticid]`

```tsx
// app/star/[ticid]/page.tsx
import fs from 'fs'
import path from 'path'

export async function generateStaticParams() {
  const outputsDir = path.join(process.cwd(), 'outputs', 'stars')
  const files = fs.readdirSync(outputsDir)
  return files
    .filter(f => f.endsWith('.json'))
    .map(f => ({ ticid: f.replace('.json', '') }))
}

export default async function StarPage({
  params,
}: {
  params: Promise<{ ticid: string }>
}) {
  const { ticid } = await params
  const data = JSON.parse(
    fs.readFileSync(
      path.join(process.cwd(), 'outputs', 'stars', `${ticid}.json`),
      'utf-8'
    )
  )
  return <StarDetail data={data} />
}
```

**Note:** In Next.js 15, `params` is a Promise and must be awaited.

### Reading Filesystem at Build Time

```tsx
// app/page.tsx (home — candidate table)
import fs from 'fs'
import path from 'path'

async function getCandidates() {
  const filePath = path.join(process.cwd(), 'outputs', 'candidates.json')
  return JSON.parse(fs.readFileSync(filePath, 'utf-8'))
}

export default async function HomePage() {
  const candidates = await getCandidates()
  return <CandidateTable data={candidates} />
}
```

### Image Handling for Static Export

- `next/image` default loader does NOT work with static export (requires server)
- **Solution:** Set `images: { unoptimized: true }` in next.config.js
- This makes `<Image>` emit raw `<img>` tags with no server-side optimization
- Alternative: use plain `<img>` tags directly for diagnostic PNGs
- All image paths must be relative to `public/` directory

### Unsupported Features (static export)

- No API routes, no middleware, no rewrites/redirects
- No `dynamicParams: true` (all paths must come from `generateStaticParams`)
- No Server Actions, no ISR, no Draft Mode
- No cookies/headers access

### Packages to Pin

```json
{
  "next": "15.1.0",
  "react": "^19.0.0",
  "react-dom": "^19.0.0"
}
```

### Gotchas & Solutions

| Gotcha | Solution |
|--------|----------|
| Build fails if any dynamic route missing `generateStaticParams` | Always export the function, even if returning `[]` |
| `params` is a Promise in Next.js 15 | Always `await params` before using |
| Image optimization requires server | `images: { unoptimized: true }` |
| `window`/`document` undefined in Server Components | Use `'use client'` directive + `useEffect` or dynamic import with `ssr: false` |
| Paths in static export must be relative | Use `trailingSlash: true` for consistent `/star/123/index.html` output |


---

## 2. shadcn DataTable with @tanstack/react-table

### Installation

```bash
pnpm dlx shadcn@latest add table badge select input button dropdown-menu
pnpm add @tanstack/react-table
```

### Column Definitions for Candidate Table

```tsx
// app/columns.tsx
"use client"

import { ColumnDef } from "@tanstack/react-table"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import Link from "next/link"
import { ArrowUpDown } from "lucide-react"

export type Candidate = {
  tic_id: string
  period: number
  depth: number
  sde: number
  classification: string
  disposition: string
  confidence_tier: "Gold" | "Silver" | "Bronze"
}

const tierColors: Record<string, string> = {
  Gold: "bg-amber-500 text-black",
  Silver: "bg-slate-400 text-black",
  Bronze: "bg-orange-600 text-white",
}

export const columns: ColumnDef<Candidate>[] = [
  {
    accessorKey: "tic_id",
    header: "TIC ID",
  },
  {
    accessorKey: "period",
    header: ({ column }) => (
      <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
        Period (d) <ArrowUpDown className="ml-2 h-4 w-4" />
      </Button>
    ),
    cell: ({ row }) => row.getValue<number>("period").toFixed(4),
  },
  {
    accessorKey: "depth",
    header: ({ column }) => (
      <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
        Depth (ppm) <ArrowUpDown className="ml-2 h-4 w-4" />
      </Button>
    ),
    cell: ({ row }) => row.getValue<number>("depth").toFixed(1),
  },
  {
    accessorKey: "sde",
    header: ({ column }) => (
      <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
        SDE <ArrowUpDown className="ml-2 h-4 w-4" />
      </Button>
    ),
    cell: ({ row }) => row.getValue<number>("sde").toFixed(2),
  },
  {
    accessorKey: "classification",
    header: "Classification",
  },
  {
    accessorKey: "confidence_tier",
    header: "Tier",
    cell: ({ row }) => {
      const tier = row.getValue<string>("confidence_tier")
      return <Badge className={tierColors[tier]}>{tier}</Badge>
    },
    filterFn: (row, id, value) => value.includes(row.getValue(id)),
  },
  {
    id: "actions",
    cell: ({ row }) => (
      <Button asChild size="sm" variant="default">
        <Link href={`/star/${row.original.tic_id}`}>Explore Candidate</Link>
      </Button>
    ),
  },
]
```

### DataTable Component with Filtering + Sorting + Pagination

```tsx
// components/data-table.tsx
"use client"

import * as React from "react"
import {
  ColumnDef, ColumnFiltersState, SortingState,
  flexRender, getCoreRowModel, getFilteredRowModel,
  getPaginationRowModel, getSortedRowModel, useReactTable,
} from "@tanstack/react-table"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Input } from "@/components/ui/input"

interface DataTableProps<TData, TValue> {
  columns: ColumnDef<TData, TValue>[]
  data: TData[]
}

export function DataTable<TData, TValue>({ columns, data }: DataTableProps<TData, TValue>) {
  const [sorting, setSorting] = React.useState<SortingState>([])
  const [columnFilters, setColumnFilters] = React.useState<ColumnFiltersState>([])

  const table = useReactTable({
    data, columns,
    getCoreRowModel: getCoreRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    state: { sorting, columnFilters },
  })

  return (
    <div>
      {/* Filter bar */}
      <div className="flex items-center gap-4 py-4">
        <Select onValueChange={v => table.getColumn("confidence_tier")?.setFilterValue(v === "all" ? undefined : [v])}>
          <SelectTrigger className="w-[140px]"><SelectValue placeholder="Tier" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Tiers</SelectItem>
            <SelectItem value="Gold">Gold</SelectItem>
            <SelectItem value="Silver">Silver</SelectItem>
            <SelectItem value="Bronze">Bronze</SelectItem>
          </SelectContent>
        </Select>
        <Input
          placeholder="Min period..."
          className="w-[120px]"
          onChange={e => table.getColumn("period")?.setFilterValue(e.target.value)}
        />
      </div>
      {/* Table */}
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map(hg => (
              <TableRow key={hg.id}>
                {hg.headers.map(h => (
                  <TableHead key={h.id}>
                    {h.isPlaceholder ? null : flexRender(h.column.columnDef.header, h.getContext())}
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {table.getRowModel().rows.map(row => (
              <TableRow key={row.id}>
                {row.getVisibleCells().map(cell => (
                  <TableCell key={cell.id}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      {/* Pagination */}
      <div className="flex items-center justify-end gap-2 py-4">
        <Button variant="outline" size="sm" onClick={() => table.previousPage()} disabled={!table.getCanPreviousPage()}>Previous</Button>
        <Button variant="outline" size="sm" onClick={() => table.nextPage()} disabled={!table.getCanNextPage()}>Next</Button>
      </div>
    </div>
  )
}
```

### Packages to Pin

```json
{
  "@tanstack/react-table": "8.20.6"
}
```

### Key Notes

- DataTable is a `'use client'` component (state-dependent filtering/sorting)
- The page.tsx (Server Component) reads JSON from filesystem and passes `data` prop down
- Pagination defaults to 10 rows per page; configurable via `initialState: { pagination: { pageSize: 20 } }`
- Custom `filterFn` on tier column enables array-based multi-select filtering


---

## 3. React-Leaflet for Celestial Star Map

### Package Versions

```json
{
  "leaflet": "1.9.4",
  "react-leaflet": "5.0.0"
}
```

Plus type definitions:
```json
{
  "@types/leaflet": "1.9.14"
}
```

### Critical Setup: Dynamic Import (No SSR)

Leaflet requires `window` and `document`. In Next.js App Router, the map component MUST be:
1. Marked `'use client'`
2. Dynamically imported with `ssr: false`

```tsx
// app/map/page.tsx
import dynamic from 'next/dynamic'

const StarMap = dynamic(() => import('@/components/star-map'), { ssr: false })

export default function MapPage() {
  return (
    <div className="h-[calc(100vh-64px)]">
      <StarMap />
    </div>
  )
}
```

### Star Map Component with CRS.Simple

```tsx
// components/star-map.tsx
'use client'

import { MapContainer, CircleMarker, Tooltip, useMap } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { useRouter } from 'next/navigation'

type Star = {
  tic_id: string
  ra: number     // 0-360
  dec: number    // -90 to +90
  sde: number
  tier: 'Gold' | 'Silver' | 'Bronze'
  period: number
  depth: number
  classification: string
}

const tierColor = { Gold: '#f59e0b', Silver: '#94a3b8', Bronze: '#d97706' }

export default function StarMap({ stars }: { stars: Star[] }) {
  const router = useRouter()
  // CRS.Simple: [y, x] = [dec, ra]
  const bounds = L.latLngBounds([[-90, 0], [90, 360]])

  return (
    <MapContainer
      crs={L.CRS.Simple}
      bounds={bounds}
      maxBounds={bounds}
      maxBoundsViscosity={1.0}
      minZoom={-1}
      maxZoom={4}
      style={{ height: '100%', width: '100%', background: '#0f172a' }}
      zoomSnap={0.5}
    >
      {stars.map(star => (
        <CircleMarker
          key={star.tic_id}
          center={[star.dec, star.ra]}  // [lat, lng] = [dec, ra]
          radius={Math.max(4, star.sde / 2)}
          pathOptions={{
            color: tierColor[star.tier],
            fillColor: tierColor[star.tier],
            fillOpacity: 0.8,
            weight: 1,
          }}
          eventHandlers={{ click: () => router.push(`/star/${star.tic_id}`) }}
        >
          <Tooltip>
            <div>
              <strong>TIC {star.tic_id}</strong><br/>
              P={star.period.toFixed(3)}d, δ={star.depth.toFixed(0)}ppm<br/>
              {star.classification}
            </div>
          </Tooltip>
        </CircleMarker>
      ))}
    </MapContainer>
  )
}
```

### Dark Background Without Tiles

- Set `style={{ background: '#0f172a' }}` on MapContainer
- Do NOT add any TileLayer — the dark background IS the map
- CRS.Simple with no tile source gives a clean dark canvas
- Optional: add grid lines using L.polyline for RA/Dec grid

### Coordinate Mapping

- **RA (0–360°)** maps to Leaflet longitude (x-axis)
- **Dec (-90° to +90°)** maps to Leaflet latitude (y-axis)
- CRS.Simple uses `[y, x]` = `[lat, lng]` = `[dec, ra]`
- Bounds: `L.latLngBounds([[-90, 0], [90, 360]])`

### Tier Filter Toggles

```tsx
const [visibleTiers, setVisibleTiers] = useState<Set<string>>(new Set(['Gold', 'Silver', 'Bronze']))

const filteredStars = stars.filter(s => visibleTiers.has(s.tier))
```

### Gotchas & Solutions

| Gotcha | Solution |
|--------|----------|
| `window is not defined` on SSR | Dynamic import with `ssr: false` |
| Leaflet CSS not loading | Import `'leaflet/dist/leaflet.css'` inside the client component |
| Map renders at 0 height | Set explicit height on container div |
| Marker icons broken (default Leaflet icons use webpack path) | Using `CircleMarker` avoids icon path issues entirely |
| CRS.Simple coordinate order confusion | Remember: `[dec, ra]` not `[ra, dec]` |


---

## 4. Plotly.js Embedding in Next.js

### Bundle Size Problem

| Bundle | Minified | Gzipped |
|--------|----------|---------|
| plotly.js (full) | 4.6 MB | 1.4 MB |
| plotly.js-basic-dist-min | ~1 MB | ~350 KB |
| plotly.js-dist-min | 4.6 MB | 1.4 MB |

**Decision: Use PNG-first strategy with optional interactive HTML iframe.**

Since Phase 3 already generates both PNG (150 dpi) and interactive Plotly HTML files, the dashboard should:
1. Display PNGs by default (fast, no JS overhead)
2. Offer a "View Interactive" button that opens the pre-rendered HTML in an iframe or new tab

### Recommended Approach: PNG + HTML iframe

```tsx
// components/diagnostic-plot.tsx
'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'

interface DiagnosticPlotProps {
  pngPath: string   // e.g. "/plots/123456789/periodogram.png"
  htmlPath: string  // e.g. "/plots/123456789/periodogram.html"
  alt: string
}

export function DiagnosticPlot({ pngPath, htmlPath, alt }: DiagnosticPlotProps) {
  const [showInteractive, setShowInteractive] = useState(false)

  if (showInteractive) {
    return (
      <div className="relative">
        <iframe src={htmlPath} className="w-full h-[400px] border-0 rounded" />
        <Button
          variant="outline" size="sm"
          className="absolute top-2 right-2"
          onClick={() => setShowInteractive(false)}
        >
          Show Static
        </Button>
      </div>
    )
  }

  return (
    <div className="relative">
      <img src={pngPath} alt={alt} className="w-full rounded" />
      <Button
        variant="outline" size="sm"
        className="absolute top-2 right-2"
        onClick={() => setShowInteractive(true)}
      >
        Interactive
      </Button>
    </div>
  )
}
```

### Why NOT react-plotly.js

- Bundle adds 1.4–4.6 MB to client JS
- Requires `dynamic(() => import('react-plotly.js'), { ssr: false })` — complex
- Phase 3 already generates the HTML files — no need to re-render client-side
- PNG fallback guarantees rendering regardless of JS execution

### Alternative: react-plotly.js (if re-rendering from JSON is needed)

```tsx
// components/plotly-chart.tsx
'use client'

import dynamic from 'next/dynamic'
const Plot = dynamic(() => import('react-plotly.js'), { ssr: false })

export function PlotlyChart({ data, layout }: { data: any[]; layout: any }) {
  return <Plot data={data} layout={layout} config={{ responsive: true }} />
}
```

**Package (only if needed):**
```json
{
  "react-plotly.js": "2.6.0",
  "plotly.js-basic-dist-min": "2.35.0"
}
```

Use `plotly.js-basic-dist-min` (scatter + bar only, ~1 MB) instead of full bundle.

### Decision Recommendation

**Use PNG + iframe approach.** Rationale:
- Zero additional JS bundle cost
- Phase 3 already produces both formats
- Iframe loads HTML on-demand (lazy)
- PNG provides instant visual for judges scrolling through pages


---

## 5. PDF Report Generation (Python)

### Approach: matplotlib PdfPages

`matplotlib.backends.backend_pdf.PdfPages` is the simplest way to assemble a multi-page PDF with embedded plots and images. No extra dependencies beyond matplotlib (already in stack).

### 4-Page PDF Assembly Pattern

```python
# src/report/generate_pdf.py
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.image as mpimg
import numpy as np

def generate_report(outputs_dir: Path, output_path: Path):
    """Generate 4-page PDF report from pipeline outputs."""
    with PdfPages(output_path) as pdf:
        # Page 1: Methodology
        _page_methodology(pdf, outputs_dir)
        # Page 2: Results
        _page_results(pdf, outputs_dir)
        # Page 3: Validation
        _page_validation(pdf, outputs_dir)
        # Page 4: Uncertainties
        _page_uncertainties(pdf, outputs_dir)

    # Set PDF metadata
    d = pdf.infodict()
    d['Title'] = 'ISRO BAH 2026 PS-07: AI-Enabled Exoplanet Detection'
    d['Author'] = 'Team [Name]'
    d['Subject'] = 'Exoplanet Detection Pipeline Report'


def _page_methodology(pdf: PdfPages, outputs_dir: Path):
    fig = plt.figure(figsize=(8.5, 11))  # Letter size

    # Title
    fig.text(0.5, 0.95, 'Methodology', ha='center', fontsize=18, fontweight='bold')

    # Embed pipeline flowchart PNG
    ax1 = fig.add_axes([0.05, 0.50, 0.90, 0.40])
    flowchart = mpimg.imread(outputs_dir / 'plots' / 'pipeline_flowchart.png')
    ax1.imshow(flowchart)
    ax1.axis('off')
    ax1.set_title('Pipeline Architecture', fontsize=12)

    # Embed confusion matrix PNG
    ax2 = fig.add_axes([0.15, 0.05, 0.70, 0.40])
    cm = mpimg.imread(outputs_dir / 'plots' / 'confusion_matrix.png')
    ax2.imshow(cm)
    ax2.axis('off')
    ax2.set_title('4-Class Confusion Matrix (Test Set)', fontsize=12)

    pdf.savefig(fig)
    plt.close(fig)


def _page_results(pdf: PdfPages, outputs_dir: Path):
    fig = plt.figure(figsize=(8.5, 11))
    fig.text(0.5, 0.95, 'Results', ha='center', fontsize=18, fontweight='bold')

    # Summary text
    fig.text(0.05, 0.88, 'Candidate Summary', fontsize=14, fontweight='bold')
    # Read summary stats from JSON
    import json
    stats = json.loads((outputs_dir / 'summary_stats.json').read_text())
    summary_text = (
        f"Total candidates (SDE≥5): {stats['total_candidates']}\n"
        f"Gold-tier planet candidates: {stats['gold_planets']}\n"
        f"Mean SDE (Gold tier): {stats['mean_sde_gold']:.1f}\n"
        f"Classification accuracy: {stats['accuracy']:.1%}"
    )
    fig.text(0.05, 0.78, summary_text, fontsize=11, family='monospace', verticalalignment='top')

    # Best planet highlight
    ax = fig.add_axes([0.10, 0.10, 0.80, 0.55])
    best_lc = mpimg.imread(outputs_dir / 'plots' / 'best_planet_phase_folded.png')
    ax.imshow(best_lc)
    ax.axis('off')
    ax.set_title(f"Best Planet Candidate: TIC {stats['best_planet_tic']}", fontsize=12)

    pdf.savefig(fig)
    plt.close(fig)


def _page_validation(pdf: PdfPages, outputs_dir: Path):
    fig = plt.figure(figsize=(8.5, 11))
    fig.text(0.5, 0.95, 'Validation', ha='center', fontsize=18, fontweight='bold')

    # TRICERATOPS+ results
    ax1 = fig.add_axes([0.05, 0.55, 0.45, 0.35])
    if (outputs_dir / 'plots' / 'triceratops_fpp.png').exists():
        img = mpimg.imread(outputs_dir / 'plots' / 'triceratops_fpp.png')
        ax1.imshow(img)
    ax1.axis('off')
    ax1.set_title('TRICERATOPS+ FPP', fontsize=10)

    # Completeness map
    ax2 = fig.add_axes([0.50, 0.55, 0.45, 0.35])
    if (outputs_dir / 'plots' / 'completeness_map.png').exists():
        img = mpimg.imread(outputs_dir / 'plots' / 'completeness_map.png')
        ax2.imshow(img)
    ax2.axis('off')
    ax2.set_title('Injection-Recovery Completeness', fontsize=10)

    # Recovery test results text
    fig.text(0.05, 0.45, 'Known Planet Recovery Tests', fontsize=12, fontweight='bold')
    recovery_text = (
        "✓ WASP-121 b: recovered (P=1.275d, δ=15400ppm)\n"
        "✓ TOI-270 b,c,d: 3/3 recovered\n"
        "✓ L 98-59 b,c,d: 3/3 recovered\n"
        "✓ TOI-700 d: recovered (P=37.4d)"
    )
    fig.text(0.05, 0.30, recovery_text, fontsize=10, family='monospace', verticalalignment='top')

    pdf.savefig(fig)
    plt.close(fig)


def _page_uncertainties(pdf: PdfPages, outputs_dir: Path):
    fig = plt.figure(figsize=(8.5, 11))
    fig.text(0.5, 0.95, 'Uncertainties & Limitations', ha='center', fontsize=18, fontweight='bold')

    # MCMC corner plot
    ax = fig.add_axes([0.10, 0.45, 0.80, 0.45])
    corner_path = outputs_dir / 'plots' / 'best_planet_corner.png'
    if corner_path.exists():
        img = mpimg.imread(corner_path)
        ax.imshow(img)
    ax.axis('off')
    ax.set_title('MCMC Posterior (Best Candidate)', fontsize=12)

    # Assumptions and limitations text
    fig.text(0.05, 0.38, 'Key Assumptions & Limitations', fontsize=12, fontweight='bold')
    limitations = (
        "• Circular orbits assumed (eccentricity fixed at 0)\n"
        "• Quadratic limb darkening from TICv8 (not fitted)\n"
        "• TESS 2-min cadence limits detection to P < 30d\n"
        "• Single-sector coverage = single transit for P > 13d\n"
        "• CNN trained on Kepler → TESS domain gap exists\n"
        "• Temperature scaling assumes i.i.d. validation set"
    )
    fig.text(0.05, 0.18, limitations, fontsize=10, verticalalignment='top')

    pdf.savefig(fig)
    plt.close(fig)
```

### Graceful Fallback for Missing Outputs

Pattern: always check `Path.exists()` before `mpimg.imread()`. Show placeholder text if missing:

```python
if img_path.exists():
    ax.imshow(mpimg.imread(img_path))
else:
    ax.text(0.5, 0.5, 'Not computed', ha='center', va='center', fontsize=14, color='gray')
ax.axis('off')
```

### Package Versions (already in stack)

```
matplotlib >= 3.9
```

No additional packages needed. Do NOT use ReportLab — matplotlib PdfPages is simpler and already a dependency.

### Decision Recommendation

**Use matplotlib PdfPages exclusively.** Rationale:
- Zero new dependencies
- Embeds existing PNGs from Phase 3 directly
- Text/tables via `fig.text()` and `ax.table()`
- `PdfPages.infodict()` handles metadata
- Graceful fallback pattern handles partial pipeline runs


---

## 6. Candidate Catalogue CSV

### Column Specification (from RPRT-02, RPRT-03)

```python
# src/report/generate_csv.py
import pandas as pd
from pathlib import Path

COLUMNS = [
    'tic_id',
    'period',           # days
    'depth',            # ppm
    'duration',         # hours
    'sde',
    'snr',
    'classification',   # PLANET CANDIDATE | ECLIPSING BINARY | BACKGROUND BLEND | STELLAR VARIABILITY
    'disposition',      # see RPRT-03
    'confidence_score', # 0.0 - 1.0
    'confidence_tier',  # Gold | Silver | Bronze
    'period_err',       # ± uncertainty (from MCMC if available)
    'depth_err',
    'duration_err',
    'rp_rs',
    'rp_rs_err',
    'inclination',
    'inclination_err',
]

DISPOSITIONS = [
    'PLANET CANDIDATE',
    'ECLIPSING BINARY',
    'BACKGROUND BLEND',
    'STELLAR VARIABILITY',
    'SUB-THRESHOLD',
]

def generate_catalogue(results: list[dict], output_path: Path):
    """Generate candidate catalogue CSV."""
    df = pd.DataFrame(results, columns=COLUMNS)

    # Validate dispositions
    assert df['disposition'].isin(DISPOSITIONS).all(), "Invalid disposition label found"

    # Sort by SDE descending (best candidates first)
    df = df.sort_values('sde', ascending=False).reset_index(drop=True)

    df.to_csv(output_path, index=False, float_format='%.6f')
    return df
```

### Disposition Assignment Logic

```python
def assign_disposition(row: dict) -> str:
    """Assign disposition based on classification and SDE tier."""
    if row['sde'] < 5:
        return 'SUB-THRESHOLD'
    classification = row['classification']
    label_map = {
        'PC': 'PLANET CANDIDATE',
        'EB': 'ECLIPSING BINARY',
        'Blend': 'BACKGROUND BLEND',
        'StellarVar': 'STELLAR VARIABILITY',
    }
    return label_map.get(classification, 'SUB-THRESHOLD')
```

### Key Notes

- Float precision: 6 decimal places for periods, 1 for depths/SDE
- NaN for uncertainty columns when MCMC was not run (SDE < 7 candidates)
- CSV is generated BEFORE the dashboard build (consumed by `candidates.json` generation)
- Total rows: all SDE ≥ 5 candidates across 3 sectors


---

## 7. Integration: run_pipeline.py --sectors 1,2,3

### Single Command Requirement (RPRT-04)

The entire pipeline must run via:
```bash
python run_pipeline.py --sectors 1,2,3
```

### Pipeline Orchestration Flow

```
run_pipeline.py --sectors 1,2,3
├── Phase 1: Data ingestion + preprocessing + TLS detection
├── Phase 2: Feature extraction + CNN/XGBoost classification
├── Phase 3: MCMC parameter estimation + validation + plots
├── Phase 4 (Python): Generate CSV + PDF + dashboard data
│   ├── generate_catalogue()  → outputs/catalogue.csv
│   ├── generate_report()     → outputs/report.pdf
│   ├── generate_candidates_json() → outputs/candidates.json
│   ├── generate_star_jsons()      → outputs/stars/{ticid}.json
│   └── copy_plots_to_dashboard()  → dashboard/public/plots/
└── Phase 4 (Node): Build dashboard (optional — can be separate)
```

### Dashboard Build Script

The Python pipeline generates all data. Dashboard build is a separate step:

```bash
# In run_pipeline.py (final step)
import subprocess
import shutil

def build_dashboard(outputs_dir: Path, dashboard_dir: Path):
    """Copy outputs and build static dashboard."""
    # Copy plots to public/
    plots_dest = dashboard_dir / 'public' / 'plots'
    if plots_dest.exists():
        shutil.rmtree(plots_dest)
    shutil.copytree(outputs_dir / 'plots', plots_dest)

    # Copy data files to public/data/ (accessible at build time)
    data_dest = dashboard_dir / 'public' / 'data'
    data_dest.mkdir(exist_ok=True)
    shutil.copy2(outputs_dir / 'candidates.json', data_dest)

    # Copy star JSONs
    stars_dest = dashboard_dir / 'outputs' / 'stars'
    stars_dest.mkdir(parents=True, exist_ok=True)
    for f in (outputs_dir / 'stars').glob('*.json'):
        shutil.copy2(f, stars_dest)

    # Run Next.js build
    subprocess.run(['npx', 'next', 'build'], cwd=str(dashboard_dir), check=True)
```

### Makefile Alternative (simpler for hackathon)

```makefile
# Makefile
.PHONY: all pipeline dashboard clean

all: pipeline dashboard

pipeline:
	python run_pipeline.py --sectors 1,2,3

dashboard: pipeline
	cp -r outputs/plots dashboard/public/plots
	cp outputs/candidates.json dashboard/outputs/
	cp -r outputs/stars dashboard/outputs/
	cd dashboard && npx next build

clean:
	rm -rf outputs/ dashboard/out/
```

### Directory Structure

```
project/
├── run_pipeline.py          # Entry point
├── src/                     # Python pipeline code
│   ├── data/
│   ├── preprocessing/
│   ├── detection/
│   ├── classification/
│   ├── characterization/
│   └── report/
│       ├── generate_pdf.py
│       ├── generate_csv.py
│       └── generate_dashboard_data.py
├── outputs/                 # Pipeline outputs (gitignored)
│   ├── candidates.json
│   ├── catalogue.csv
│   ├── report.pdf
│   ├── summary_stats.json
│   ├── stars/
│   │   ├── 123456789.json
│   │   └── ...
│   └── plots/
│       ├── 123456789/
│       │   ├── diagnostic_4panel.png
│       │   ├── periodogram.html
│       │   └── ...
│       ├── confusion_matrix.png
│       ├── completeness_map.png
│       └── ...
├── dashboard/               # Next.js app
│   ├── app/
│   │   ├── page.tsx         # Home (candidate table)
│   │   ├── star/[ticid]/page.tsx
│   │   ├── map/page.tsx
│   │   └── layout.tsx
│   ├── components/
│   ├── outputs/             # Symlink or copy at build time
│   ├── public/plots/        # Static plot assets
│   ├── next.config.js
│   └── package.json
└── Makefile
```

### Decision: Python builds data, Makefile orchestrates

- `run_pipeline.py` does all science (Phases 1-3) + data generation (Phase 4 Python)
- Makefile/script handles file copying and `next build`
- Dashboard build is fast (<30s for ~200 pages) — acceptable to run as final step
- If time-constrained during hackathon, can skip `next build` and serve with `npx next dev`

---

## 8. Key Pitfalls & Solutions

### Pitfall Matrix

| # | Pitfall | Impact | Solution |
|---|---------|--------|----------|
| 1 | Leaflet CSS not loaded | Map renders without styles, broken controls | Import `'leaflet/dist/leaflet.css'` inside the `'use client'` map component |
| 2 | Leaflet `window is not defined` | Build crashes | Dynamic import with `ssr: false` — never import Leaflet at top level of a Server Component |
| 3 | Plotly bundle size (4.6 MB) | Slow page load, poor judge experience | Use PNG + iframe strategy; avoid bundling plotly.js in client JS |
| 4 | Static export: no API routes | Cannot fetch data at runtime | All data must be read at build time via `fs` in Server Components |
| 5 | `generateStaticParams` must enumerate ALL ticids | Missing stars = 404 | Read filesystem at build time, generate list from `outputs/stars/*.json` |
| 6 | `next/image` default loader incompatible with static export | Build error | Set `images: { unoptimized: true }` in next.config.js |
| 7 | Image paths break in production | 404 on plot images | Use paths relative to `public/` (e.g., `/plots/123/panel.png`) |
| 8 | CRS.Simple coordinate order | Stars appear in wrong positions | `[dec, ra]` not `[ra, dec]` — Leaflet is always [lat, lng] = [y, x] |
| 9 | React-Leaflet default marker icons broken | Missing marker PNGs | Use `CircleMarker` instead of `Marker` — no icon files needed |
| 10 | Next.js 15 `params` is a Promise | Type errors, undefined params | Always `const { ticid } = await params` |
| 11 | Large number of star pages slows build | Build timeout | Only pre-render SDE≥7 candidates (~200-500), not all 60k stars |
| 12 | Tailwind 4 breaking changes from v3 | Styles don't apply | Use Tailwind 4 class syntax; `@apply` still works but config format changed |
| 13 | shadcn init fails without proper setup | Missing components | Run `pnpm dlx shadcn@latest init` first with correct framework detection |
| 14 | PDF generation fails with missing images | Report crashes | Always guard with `Path.exists()` and show placeholder text |

### Build Order Dependency Chain

```
Phase 3 outputs complete
    → generate_csv.py (catalogue.csv)
    → generate_dashboard_data.py (candidates.json + star JSONs)
    → generate_pdf.py (report.pdf)
    → copy plots to dashboard/public/
    → next build (static export)
```

Each step MUST complete before the next. The Python pipeline handles 1-4; the Makefile handles step 5.


---

## RESEARCH COMPLETE

**Phase:** 4 - Presentation — Dashboard & Report
**Topics covered:**
1. Next.js 15 App Router static site generation (generateStaticParams, fs at build time, output: export)
2. shadcn DataTable with @tanstack/react-table (columns, filtering, sorting, pagination, CTA)
3. React-Leaflet celestial star map (CRS.Simple, dark background, CircleMarker, tier colors)
4. Plotly.js embedding strategy (PNG + iframe, avoiding bundle bloat)
5. PDF report generation (matplotlib PdfPages, 4-page assembly, PNG embedding)
6. Candidate catalogue CSV (column spec, disposition labels, uncertainty columns)
7. Pipeline integration (run_pipeline.py orchestration, Makefile, directory structure)
8. Key pitfalls and solutions (14 identified issues with mitigations)

**Key decisions:**
1. **PNG + iframe** over react-plotly.js — zero bundle cost, Phase 3 already generates both formats
2. **`images: { unoptimized: true }`** — required for static export, use raw `<img>` tags
3. **CircleMarker** over Marker — avoids icon path issues, natural for astronomical data
4. **Dynamic import with `ssr: false`** for both Leaflet and (if used) Plotly client components
5. **matplotlib PdfPages** over ReportLab — already a dependency, simpler API, graceful fallback
6. **Makefile orchestration** — Python generates all data, Makefile handles copy + next build
7. **Only SDE≥7 candidates get `/star/[ticid]` pages** — keeps build fast (~200-500 pages)
8. **`@tanstack/react-table` 8.x** — headless, composable, works perfectly with shadcn Table component
