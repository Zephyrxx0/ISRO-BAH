# Domain Pitfalls: Exoplanet Detection Pipeline

**Domain:** AI-enabled exoplanet detection from TESS photometry (ISRO BAH 2026 PS-07)
**Researched:** 25 Jun 2026
**Confidence:** MEDIUM (MCMC and data-specific pitfalls need runtime validation)

## Critical Pitfalls

Mistakes that cause pipeline rewrites or complete failure to detect known planets.

### Pitfall 1: Over-Flattening the Light Curve
**What goes wrong:** Aggressive detrending (too-short window length in biweight or Savitzky-Golay) removes transit signals along with stellar variability. A 3-hour transit dip looks identical to short-timescale stellar noise when the detrending window is too tight.
**Why it happens:** Default window_length values in wotan (0.5 days) are tuned for long-period variability, not for preserving transit signals. Users apply detrending without understanding the timescale trade-off.
**Consequences:** Known planets (WASP-121b at 1.4% depth) may not be detected. False negative rate spikes. Invalidates the entire pipeline with no obvious error message — the transit simply disappears from the flattened light curve.
**Prevention:** Set `window_length` to ≥ 0.75 days (≥ 3× the longest expected transit duration of ~6 hours). Validate by injecting synthetic transits at known depths into test light curves and checking recovery rate > 95% after detrending.
**Detection:** If WASP-121b (TIC 22529346, Sector 7, 1.27-day period, ~1.4% depth) is not detected after preprocessing, detrending window is too short. Run the same pipeline on raw (non-detrended) data as a control — if the transit appears in raw but not detrended, over-flattening is confirmed.

### Pitfall 2: Data Gap Interpolation Creating False Signals
**What goes wrong:** TESS has ~13-day data gaps per sector (spacecraft downlink). Interpolation across these gaps (linear, spline, or forward-fill) creates synthetic structure that TLS/BLS may falsely detect as a periodic signal.
**Why it happens:** Many data science tutorials teach "fill missing values" as a preprocessing step. Users apply this without understanding that transit search algorithms treat any structure as a candidate signal.
**Consequences:** False period detections at harmonics of the gap cadence. Phantom "transit" signals with periods that are artefacts of the interpolation. Inflates false positive rate by 5–10×.
**Prevention:** Mask (don't interpolate) all data gaps. TLS handles masked arrays natively. Set gap-edge points as unreliable (±0.5 days around each gap). Discard light curves with < 500 valid cadences.
**Detection:** Check periodogram for peaks at harmonics of ~13.7 days (the sector data gap cadence). If SDE > 7 peaks cluster around these harmonics, gap interpolation is the cause.

### Pitfall 3: Binary Classification Instead of 4-Class
**What goes wrong:** Building a binary "planet / not-planet" classifier. This fails to distinguish eclipsing binaries from planets, missing the primary false positive class that ISRO evaluators specifically care about.
**Why it happens:** Binary classification is simpler to implement. Many Kaggle datasets are binary. AstroNet's original paper was binary. Teams default to the simplest approach.
**Consequences:** Submission fails the classification requirement. EBs are labelled as "not-planet" but the pipeline cannot explain *why* — it just says "47% confidence, not a planet." ISRO judges will ask "is this an EB or a blend?" and the pipeline cannot answer.
**Prevention:** Implement the 4-class taxonomy from day 1: PLANET CANDIDATE, ECLIPSING BINARY, BACKGROUND BLEND, STELLAR VARIABILITY. Follow the taxonomy in CONTEXT.md and main.md Section 3.
**Detection:** If the classifier output has only 2 classes (or 4 classes but 2 are always 0% probability), you've built a binary classifier. The test is whether known EBs (TIC 349488688) get > 70% probability in the EB class.

### Pitfall 4: Uncalibrated Confidence Scores
**What goes wrong:** Reporting raw softmax probabilities as "confidence scores" without calibration. A raw softmax of 0.94 might only be correct 72% of the time — it's overconfident.
**Why it happens:** Softmax outputs are not calibrated probabilities. They tend to be overconfident, especially with deep neural networks. Most hackathon teams don't know about calibration, so they report raw softmax.
**Consequences:** Gold-tier candidates (confidence > 0.90) may include 28% false positives. Mission planners who trust the "94% confidence" label will waste follow-up resources on false positives. Undermines the entire point of confidence scoring.
**Prevention:** Apply temperature scaling on a held-out validation set. Report ECE (Expected Calibration Error). Target ECE < 0.04. The pipeline should output: "PC, confidence 0.94 (calibrated; 94% of predictions at this score are correct)."
**Detection:** Plot calibration curve (predicted probability vs. observed accuracy). If points deviate > 0.05 from the diagonal, calibration is poor. ECE > 0.10 means confidence scores are misleading.

### Pitfall 5: MCMC Non-Convergence
**What goes wrong:** emcee MCMC chains don't converge, producing unreliable posterior distributions. Reported "median ± 1σ" parameters are meaningless if the chains haven't mixed.
**Why it happens:** emcee needs proper initialization (near the true posterior mode), enough walkers (≥ 4× number of parameters), sufficient steps (≥ 50× autocorrelation time), and correct burn-in. Default settings often fail on transit data with multi-modal posteriors.
**Consequences:** Parameter uncertainties are wrong. "Period: 3.47 ± 0.001 days" might actually be "Period: 3.47 ± 0.5 days" — the pipeline is overconfident. Judges who understand Bayesian statistics will spot this immediately in corner plots.
**Prevention:** Initialize walkers from Nelder-Mead best-fit + small Gaussian ball. Run 32 walkers for ≥ 5000 steps. Discard first 1000 steps as burn-in. Check acceptance fraction (target 0.2–0.5). Check autocorrelation time (τ ≤ N_steps / 50). Run Gelman-Rubin diagnostic if time permits. Only report parameters if all convergence criteria pass; flag non-converged runs as "uncertain" in the catalogue.
**Detection:** Corner plots with "blobby" or multi-modal distributions. Acceptance fraction < 0.1 or > 0.8. Autocorrelation time > 500 steps. If chains look like random walks rather than stable distributions, MCMC has not converged.

## Moderate Pitfalls

### Pitfall 6: Excluding Saturated Stars Improperly
**What goes wrong:** Simply filtering Tmag < 6 removes ~1% of stars, but the boundary is soft — stars at Tmag 5.8–6.2 may show partial saturation artefacts that look like shallow transits.
**Prevention:** Use Tmag < 6 as a hard filter but also flag Tmag 6.0–6.5 stars as "CAUTION: near saturation limit" in the candidate catalogue. These candidates can be included but with a caveat.

### Pitfall 7: Single-Pass Transit Search Missing Multi-Planet Systems
**What goes wrong:** Running TLS once per star and taking the strongest peak. TOI-270 has 3 planets (3.36, 5.66, 11.38 days). The strongest transit may mask weaker ones.
**Prevention:** Implement iterative search: find signal 1 → mask its transits → run TLS again → find signal 2 → mask → run TLS again → find signal 3. Minimum 3 iterations per star. This adds ~50% to search time but is critical for multi-planet validation.

### Pitfall 8: Hard-Coded Limb Darkening Coefficients
**What goes wrong:** Using default limb darkening coefficients (u=[0.3, 0.1]) for all stars. Limb darkening varies with stellar temperature, surface gravity, and metallicity. Wrong coefficients produce systematic errors in transit depth (up to 5% for cool stars).
**Prevention:** Interpolate quadratic limb darkening coefficients from TICv8 using Claret & Bloemen (2011) tables. Per-star values. Computationally free (only 15 MCMC runs). Already decided in ADR-0011.

### Pitfall 9: Ignoring CROWDSAP During Classification
**What goes wrong:** High CROWDSAP (> 0.3) means > 30% of flux in the aperture comes from nearby stars — any "transit" could be a diluted background eclipsing binary. Classifying without using CROWDSAP misses the strongest blend indicator.
**Prevention:** Include CROWDSAP as a feature in XGBoost. Weight the blend classifier output by contamination ratio. Block PC classification if CROWDSAP > 0.5.

### Pitfall 10: Not Pre-Training Before the Hackathon
**What goes wrong:** Starting CNN training from scratch at Hour 0 of the hackathon. CNN training on Kepler DR24 (34k samples) takes 3–4 hours on T4. That's 10% of the total hackathon time burned before the model is even functional.
**Prevention:** Pre-train the CNN on Kepler DR24 data in the 7 days before the hackathon. Save weights. During hackathon: load pre-trained weights, fine-tune on TESS ExoFOP TOIs (10 epochs, ~2 hours). This is the explicit plan in the project strategy.

### Pitfall 11: SHAP on CNN Instead of XGBoost
**What goes wrong:** Trying to compute SHAP values for the CNN classifier. DeepExplainer on a CNN with 201-point inputs and 2.5M parameters is slow, memory-intensive, and produces 201-dimension feature importance maps that are hard to interpret.
**Prevention:** Run SHAP only on XGBoost. TreeExplainer is fast and produces per-feature importance for the 8 engineered features. These are physically meaningful (e.g., "odd/even depth difference was the strongest EB indicator"). Skip SHAP on CNN — it adds complexity without clarity.

## Minor Pitfalls

### Pitfall 12: Not Converting Transit Duration Units
**What goes wrong:** TLS reports duration in days. T₁₄ is conventionally reported in hours. Pipeline reports "Duration: 0.125 days" when judges expect "Duration: 3.0 hours."
**Prevention:** Multiply duration in days by 24 for reporting. Use hours consistently in the candidate catalogue, parameter table, and report.

### Pitfall 13: Failing to Handle Sector Boundaries
**What goes wrong:** Stars at sector boundaries have partial light curves (shorter effective observing window). Periods longer than the observation span are unreliable.
**Prevention:** Discard period candidates where `period > (observation_span / 2)`. Flag periods where `period > (observation_span / 3)` as "low confidence — limited phase coverage."

### Pitfall 14: Excessive Logging to MLflow During Bulk Processing
**What goes wrong:** Logging every TLS run (60k entries) to MLflow bloats the tracking database. MLflow UI becomes unresponsive.
**Prevention:** Log only aggregate metrics to MLflow (classification accuracy, ECE, parameter recovery rates). Log individual runs only for top 100 candidates. Use tqdm for progress tracking during bulk processing.

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Data Download | MAST rate-limiting or server overload during hackathon (many teams downloading simultaneously) | Pre-download Sector 1 data before hackathon. Have backup sectors (Sectors 2, 3) queued. |
| Preprocessing | biweight window_length too short for long-period planets | Test on TOI-270d (11.38-day period, ~3-hour transit). Set window_length = 0.75 days minimum. |
| TLS Period Search | GPU memory overflow when running TLS on all 60k LCs simultaneously | Batch processing: 1000 LCs per batch. Clear GPU memory between batches. |
| CNN Training | T4 GPU memory overflow with 7× augmentation (85k samples × 201 points) | Reduce batch size to 32. Use mixed-precision training (tf.keras.mixed_precision). |
| Feature Extraction | TPF download for centroid analysis times out on 500 targets | Pre-filter to top 200 by SDE. Use async HTTP with timeout=30s. Skip centroid analysis for targets where TPF download fails — flag as "centroid data unavailable." |
| XGBoost Training | Class imbalance leads to poor recall on Blend class (rarest class) | Use stratified k-fold. Monitor F1-macro (not accuracy). Apply scale_pos_weight if Blend class < 5% of samples. |
| Ensemble | CNN and XGBoost disagree strongly (probability gap > 0.3) | Flag as "ENSEMBLE DISAGREEMENT" in catalogue. Default to CNN for shape-driven cases, XGBoost for feature-driven cases. |
| MCMC | Convergence failure on low-SNR candidates | Skip MCMC if Nelder-Mead fit χ²/ν > 3. MCMC on noisy data won't converge. Report "parameters uncertain — insufficient SNR for MCMC." |
| Dashboard | Next.js build fails on large /outputs/ directory (> 500MB of plot files) | Compress PNGs (dpi=100 for dashboard). Use WebP for web display. Lazy-load HTML panels. |
| Report Generation | PDF exceeds 4-page limit with all candidate plots embedded | Reference plots by filename in report body. Only embed 2–3 best examples. Attach full plot directory as supplementary material. |

## Sources

- **Over-flattening:** main.md Section 6 (Preprocessing Pipeline), ADR-0010 (2-tier detrending)
- **Data gap masking:** main.md Section 6 Step 3, ADR-0013
- **Binary vs 4-class classification:** main.md Section 3 (Signal Classes), Section 9 (Classification Framework), ADR-0007
- **Confidence calibration:** main.md Section 11 (Uncertainty Estimation), CONTEXT.md (ECE, Temperature Scaling entries)
- **MCMC convergence:** Foreman-Mackey et al. (2013) emcee documentation, main.md Section 10 (Parameter Estimation)
- **Hackathon pitfalls:** main.md Section 24.5 (Hackathon FAQ), Section 18 (Implementation Timeline)
- **SHERLOCK benchmark:** Dévora-Pajares et al. (2024), MNRAS 532, 4752 — 98% TOI recovery
- **ExoMiner++ pitfalls:** Valizadegan et al. (2025), AJ 170.5 — multi-branch architecture training requirements

---

*Pitfall research for: ISRO BAH 2026 PS-07 — Exoplanet Detection Pipeline*
*Researched: 25 Jun 2026*
