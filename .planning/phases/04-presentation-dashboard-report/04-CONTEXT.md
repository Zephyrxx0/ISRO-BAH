# Phase 4: Presentation — Dashboard & Report - Context

**Gathered:** 2026-06-28
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase delivers the judge-facing outputs of the entire pipeline: an interactive Next.js read-only dashboard (candidate table, per-star diagnostics, celestial star map), a candidate catalogue CSV, and a 4-page PDF report. All data consumed from pre-rendered `/outputs/` — no live Python backend. The dashboard is a static site generated at build time after the Python pipeline completes.
</domain>

<decisions>
## Implementation Decisions

### Dashboard Layout & Routing
- **D-01:** Multi-route architecture: `/` (candidate table home), `/star/[ticid]` (per-star diagnostics), `/map` (celestial star map). Standard Next.js App Router pattern. Deep-linkable star pages.
- **D-02:** Top navbar + breadcrumbs navigation. Navbar links: Candidates, Star Map, About. Breadcrumb trail on star detail pages (Home > TIC 12345678).
- **D-03:** Home page includes summary stat cards (Total candidates, Gold tier count, Planets confirmed, Avg SDE) above a filter bar (by tier, classification, period range) and a sortable candidate table.
- **D-04:** Non-Gold / non-diagnostic star detail pages show whatever data is available plus a note: "Full diagnostics available for SDE≥7 Gold-tier candidates only." Graceful degradation — no broken pages.

### Data Pipeline to Dashboard
- **D-05:** Static Site Generation (SSG) at build time. Python pipeline runs first, produces all outputs in `/outputs/`. Then `next build` reads outputs via `generateStaticParams` + `fs`, pre-renders all pages as static HTML.
- **D-06:** Data format: single `/outputs/candidates.json` (powers the filterable table — TIC ID, period, depth, SDE, classification, tier, etc.) + per-star `/outputs/stars/{ticid}.json` (full diagnostics for detail pages).
- **D-07:** Only SDE≥7 candidates get pre-rendered `/star/[ticid]` pages (~200-500 stars). Other stars exist only in the table with a note.
- **D-08:** Diagnostic images (PNGs, Plotly HTML) are copied from `/outputs/plots/` to `/public/plots/` before `next build`. Served as static assets.

### PDF Report Generation
- **D-09:** Python pipeline generates the 4-page PDF as the final step of `run_pipeline.py`. Matplotlib PDF backend + PyPDF2 for page assembly.
- **D-10:** Reuses existing PNGs from Phase 3 outputs (confusion matrix, corner plots, completeness map) — no re-rendering.
- **D-11:** Graceful fallback for missing/partial results: if TRICERATOPS+ didn't run, show "FPP/NFPP not computed." Missing charts get a placeholder with explanation. Report always generates.

### Celestial Map & Diagnostics
- **D-12:** Leaflet.js with equirectangular RA/Dec scatter plot on dark background. RA mapped to longitude (0-360°), Dec mapped to latitude (-90° to +90°). No external sky tile dependency.
- **D-13:** Gold-tier markers = gold circles, Silver = silver, Bronze = bronze. Marker radius scaled by SDE. Hover tooltip shows TIC ID, period, depth, classification. Click marker navigates to `/star/[ticid]`. Filter checkboxes to toggle tiers.
- **D-14:** Star detail pages embed Plotly HTML (interactive) with PNG fallback. Judges can zoom/hover/toggle traces; PNG guarantees rendering if Plotly fails.
- **D-15:** Star detail page layout: parameter card (period, depth, duration, SDE, SNR, Rp/Rs, inclination with uncertainties) → 4-panel diagnostics → MCMC corner plot (if available) → TRICERATOPS+ FPP/NFPP → disposition badge.

### the agent's Discretion
*(No areas deferred to agent — all gray areas were discussed and decided.)*
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Architecture & Stack
- `.planning/ROADMAP.md` §Phase 4 — Success criteria, dependencies, requirements mapping (DASH-01 through RPRT-04)
- `.planning/PROJECT.md` — Stack decisions (Next.js 15, shadcn/ui, Tailwind 4, Plotly.js, Leaflet.js), ADR-0010 (read-only dashboard), storage decisions
- `.planning/REQUIREMENTS.md` — DASH-01 to DASH-04 (dashboard), RPRT-01 to RPRT-04 (report/deliverables)
- `AGENTS.md` — Full stack reference, key decisions summary

### ADRs
- `docs/adr/0001-dual-view-cnn-architecture.md` — CNN architecture context
- `docs/adr/0002-three-sector-search.md` — 3-sector scope context
- `docs/adr/0003-synthetic-transit-injection-augmentation.md` — Augmentation context
- `docs/adr/0004-kepler-pretrain-tess-finetune.md` — Training strategy context

### Phase 3 Outputs (upstream dependency)
- Phase 3 produces diagnostic PNGs, Plotly HTML, corner plots, completeness map, candidate CSV, and TRICERATOPS+ results in `/outputs/` — all consumed by Phase 4.

### No Additional Specs
No SPEC.md, no prior CONTEXT.md files exist. Requirements and decisions are fully captured in this document and the referenced files above.
</canonical_refs>

<code_context>
## Existing Code Insights

**No code exists yet in this repository.** The repo is currently planning-only. All architecture lives in `.planning/` and `docs/adr/`.

### Stack Reference (from AGENTS.md)
- **Framework:** Next.js 15 (App Router)
- **UI:** shadcn/ui, Tailwind 4
- **Visualization:** Plotly.js (interactive charts), Leaflet.js (celestial map)
- **Data:** `.npz` per light curve + Parquet master catalogue (Python side)
- **Dashboard data:** JSON from `/outputs/` consumed at build time

### Integration Points
- Dashboard reads pre-rendered files from `/outputs/` directory (produced by Phase 3)
- Build process: Python pipeline completes → copy images to `/public/` → `next build` → static export
- Single command: `python run_pipeline.py --sectors 1,2,3` produces all outputs including PDF
</code_context>

<specifics>
## Specific Ideas

No specific UI mockups or references mentioned. Standard approaches apply:
- shadcn/ui Table component with column sorting and filter dropdowns
- Leaflet.js with React-Leaflet wrapper for map integration
- react-plotly.js for Plotly HTML embedding
- Next.js `generateStaticParams` reading filesystem at build time
</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.
</deferred>

---

*Phase: 4-Presentation — Dashboard & Report*
*Context gathered: 2026-06-28*
