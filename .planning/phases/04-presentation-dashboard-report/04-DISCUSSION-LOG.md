# Phase 4: Presentation — Dashboard & Report - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-28
**Phase:** 4-Presentation — Dashboard & Report
**Areas discussed:** Dashboard layout & routing, Data pipeline to dashboard, PDF report generation, Celestial map & diagnostics

---

## Dashboard Layout & Routing

| Option | Description | Selected |
|--------|-------------|----------|
| Multi-route | / → table, /star/[ticid] → diagnostics, /map → celestial. Deep-linkable. Standard App Router. | ✓ |
| Single-page tabs | Everything on / with tabbed panels. More state management. | |
| Dashboard shell + sections | Single /dashboard route with scrollable sections. Simpler, less interactive. | |

| Option | Description | Selected |
|--------|-------------|----------|
| Top navbar + breadcrumbs | Horizontal nav + breadcrumb trail. shadcn/ui compatible. | ✓ |
| Sidebar navigation | Persistent left sidebar. Admin-panel feel. | |
| Minimal back links | No global nav, just back links. Minimalist. | |

| Option | Description | Selected |
|--------|-------------|----------|
| Summary stats + filters + table | Stat cards, filter bar, sortable table. Judge-facing context. | ✓ |
| Just filterable table | No summary. Clean, data-dense. | |
| Table + hero section | Hero banner + table. Narrative approach. | |

| Option | Description | Selected |
|--------|-------------|----------|
| Show available data + note | Graceful degradation. Note explains missing diagnostics. | ✓ |
| Two page variants | Full vs Summary layouts by tier. | |
| Only render Gold-tier pages | No pages for non-Gold stars. | |

---

## Data Pipeline to Dashboard

| Option | Description | Selected |
|--------|-------------|----------|
| Static generation (SSG) | `next build` reads /outputs/ at build. Fast, zero server. | ✓ |
| Server-side (SSR) | API routes read files at request time. Needs Node server. | |
| Hybrid static + client fetch | Static shell, client fetches JSON. Simplest build. | |

| Option | Description | Selected |
|--------|-------------|----------|
| Single candidates.json + per-star | Master table JSON + individual star files. Clean separation. | ✓ |
| Single master catalogue | One large file. Simple but heavy. | |
| Only per-star files | Scan filesystem for table. Complex. | |

| Option | Description | Selected |
|--------|-------------|----------|
| SDE≥7 candidates only | ~200-500 pre-rendered pages. Aligns with gating. | ✓ |
| All SDE≥5 candidates | ~2000+ pages. Longer build. | |
| Gold and Silver tier only | Confidence >0.70. Fewest pages. | |

| Option | Description | Selected |
|--------|-------------|----------|
| Copy to /public at build | Build script copies before next build. Safe, standard. | ✓ |
| Symlink /outputs into /public | No copy. Can break on some platforms. | |
| Python writes directly to /public | Pipeline targets Next.js dir. Coupling concern. | |

---

## PDF Report Generation

| Option | Description | Selected |
|--------|-------------|----------|
| Python pipeline | run_pipeline.py generates PDF as final step. All data in memory. | ✓ |
| Next.js server-side | puppeteer renders report HTML to PDF. More layout flexibility. | |
| Both | Python for data, Next.js for layout. Most complex. | |

| Option | Description | Selected |
|--------|-------------|----------|
| Matplotlib PDF + PyPDF2 | Native vector graphics. No new dependencies beyond PyPDF2. | ✓ |
| ReportLab | Professional but heavier learning curve. Charts as PNG. | |
| WeasyPrint + HTML/CSS | CSS layout. Requires system deps (Cairo, Pango). | |

| Option | Description | Selected |
|--------|-------------|----------|
| End of run_pipeline.py, reuse PNGs | PDF reads existing Phase 3 PNGs. Fast, consistent with dashboard. | ✓ |
| Inline generation during pipeline | Re-render charts at higher DPI. Duplicates logic. | |
| Separate report script | Clean separation but extra command. | |

| Option | Description | Selected |
|--------|-------------|----------|
| Graceful fallback with notes | Placeholder + explanation for missing data. Report always generates. | ✓ |
| Fail fast | Require all outputs. Risk no report at all. | |
| Conditional sections | Dynamic layout based on available data. | |

---

## Celestial Map & Diagnostics

| Option | Description | Selected |
|--------|-------------|----------|
| Equirectangular RA/Dec scatter | RA as lon, Dec as lat. Dark background. Simple, astronomy-standard. | ✓ |
| AladinLite tiles | Real sky imagery overlay. More impressive, heavier dependency. | |
| Plotly.js scatter | No projection concerns. Less map-like feel. | |

| Option | Description | Selected |
|--------|-------------|----------|
| Color-coded circles + tooltips + click | Gold/Silver/Bronze by tier, scaled by SDE. Click navigates to star. | ✓ |
| Cluster markers by sector | Clustered by sector, zoom to expand. | |
| Minimal dots + info panel | Small dots, click opens side panel. No navigation away. | |

| Option | Description | Selected |
|--------|-------------|----------|
| Plotly HTML + PNG fallback | Interactive by default, static PNG fallback. Best of both. | ✓ |
| Static PNGs only | Simple, fast, guaranteed. Less impressive. | |
| Plotly HTML only | No fallback. Fragile for judging. | |

| Option | Description | Selected |
|--------|-------------|----------|
| Parameter card + corner plot + disposition | Full dossier: params, 4-panel, corner, TRICERATOPS+, badge. | ✓ |
| Just 4-panel + classification bar | Minimal, plots speak. Parameters collapsible. | |
| Everything scrollable | Full scroll page. Comprehensive but could overwhelm. | |

---

## Agent's Discretion

No areas deferred to agent — all gray areas were discussed and decided by the user.

## Deferred Ideas

None — discussion stayed within phase scope.
