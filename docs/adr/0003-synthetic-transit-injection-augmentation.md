# ADR-0003: 7× augmentation with synthetic transit injection

The training set is augmented at 7× — 1× original + 1× noise injection + 1× transit time jitter + 4× synthetic transit injection — rather than simpler 3× or 5× schemes.

**Why**: Real labeled catalogs (ExoFOP, Kepler) are heavily biased toward deeper, easier-to-detect transits. Earth-sized planets (50–200 ppm) are underrepresented because they are difficult to confirm. Synthetic injection creates batman-model transits at these shallow depths and injects them into real detrended TESS noise — the CNN learns from signals the labeled set cannot teach. The same synthetic injection pipeline produces a completeness map (recovery fraction vs. depth and period), which is a prize-winning differentiator. At ~85k–153k total samples, training completes in <3.5 hours on a T4 GPU.

**Rejected**: 3× augmentation (noise + jitter only) — insufficient to address the shallow-transit gap. 10× augmentation — diminishing returns, pushes training past 5 hours, and the additional samples are redundant variations.

**Status**: accepted
