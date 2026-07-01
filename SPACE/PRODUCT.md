# Product

## Register

product

## Users

ISRO hackathon judges, astronomers, and mission planners triaging exoplanet candidates from TESS light curves. They work under time pressure during a 30-hour finale, scanning candidate tables, reviewing diagnostic plots, and making disposition calls. High data density and surgical precision matter — every pixel of a phase-folded light curve can hide an 84 ppm transit dip.

## Product Purpose

An interactive dashboard for an AI-enabled exoplanet detection pipeline. It surfaces candidate detections (4-class classification: planet, eclipsing binary, background blend, stellar variability), orbital parameter estimates, and calibrated confidence scores. Success = judges can navigate from candidate table → diagnostic plot → validation engine → star map in seconds, never losing context or confusing data.

## Brand Personality

**Raw. Mechanical. Precise.**

The interface projects a declassified aerospace blueprint — a military-grade telemetry terminal repurposed for astronomical discovery. No decoration, no hand-holding, no consumer UX tropes. Every element earns its place through information density or structural necessity. The visual language says "this was built for scientists, not optimized for conversion."

## Anti-references

- **SaaS dashboard templates** — soft shadows, rounded cards, gradient accents, "modern" spacing, stats cards with icons. The current design's amateurish AI-generation feel.
- **Glassmorphism / blur effects** — decorative, non-functional.
- **Conventional hero-metric layouts** — big number + small label + supporting stats. Anti-pattern for scientific tools.
- **Warm-tinted neutrals** — cream/sand/paper backgrounds. Wrong register entirely.
- **Generous padding and low information density** — judges need data, not breathing room.

## Design Principles

1. **Information density over decoration.** Every pixel serves data, not aesthetics. If removing it doesn't lose information, it doesn't belong.
2. **Mechanical precision, not organic comfort.** Rigid grids, visible compartmentalization, monospaced data, ASCII framing. The interface should feel like it was engineered, not designed.
3. **Raw functionalism.** No rounded corners, no shadows, no gradients. Sharp edges, solid borders, terminal typography. The tool disappears into the task.
4. **High signal, zero noise.** Color only where it carries meaning (disposition codes, confidence tiers, alerts). Everything else is white phosphor on dead CRT black.
5. **Accessible by design.** WCAG AA. High-contrast monochrome base with strategic red/green for status. Keyboard-navigable data tables. Screen-reader semantic DOM.

## Accessibility & Inclusion

- WCAG AA compliance (≥4.5:1 contrast for body text, ≥3:1 for large text)
- High-contrast dark substrate: white phosphor (#EAEAEA) on dead CRT black (#0A0A0A) — exceeds AA thresholds
- Keyboard navigation through all interactive elements (candidate table, filters, tabs, map)
- Semantic HTML: `<data>`, `<samp>`, `<kbd>`, `<output>`, `<dl>` for telemetry values
- Reduced motion: no decorative animations. State transitions are instant or ≤150ms
- Color is never the sole indicator — disposition always paired with text label
- Focus indicators visible and consistent
