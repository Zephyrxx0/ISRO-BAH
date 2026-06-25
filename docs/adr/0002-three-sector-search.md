# ADR-0002: Three-sector search over single-sector

The pipeline processes TESS Sectors 1, 2, and 3 (~60,000 stars) rather than the default single sector (~20,000 stars).

**Why**: A single 27-day sector captures at most 2 transits for planets with P ≈ 13 days — long-period planets are effectively invisible. Three sectors extend the detectable period range and provide cross-sector validation that the pipeline generalizes. With 7 days available (not 30 hours), the additional download and processing time is absorbed by overnight runs. Sector 1 provides gold-standard validation targets (WASP-121b, TOI-270). Sector 2 adds L 98-59 overlap. Sector 3 confirms robustness across TESS camera rotations.

**Rejected**: Single-sector only — simplifies the pipeline but caps the maximum detectable period, reduces the candidate catalogue size, and removes the cross-sector consistency demonstration that differentiates the submission.

**Status**: accepted
