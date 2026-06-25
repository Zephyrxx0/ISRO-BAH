# Exoplanet Detection Pipeline

An end-to-end ML pipeline that ingests TESS satellite photometry and outputs classified exoplanet candidates with orbital parameters and calibrated confidence scores.

## Language

### Observational Data

**Light Curve (LC)**:
A time series of stellar brightness (flux) measured by TESS at a fixed cadence, typically 2-minute sampling over ~27 days per sector.
_Avoid_: Time series, photometric series

**Cadence**:
The fixed time interval between consecutive flux measurements. TESS 2-min cadence ("short cadence") is the primary data mode for this project.
_Avoid_: Sample rate, frame rate

**Sector**:
One ~27-day continuous observing window of TESS covering a specific region of the sky. The satellite observes 26 sectors total.
_Avoid_: Field, pointing

**TIC (TESS Input Catalog)**:
The master catalog of ~1.7 billion stellar objects with parameters (Teff, logg, Rs, Ms, TESS magnitude, CROWDSAP) used to select targets and provide stellar context.
_Avoid_: Stellar catalog

**Target Pixel File (TPF)**:
Pixel-level cutout image data around a target star, used for centroid analysis to detect background blends.
_Avoid_: Postage stamp, pixel cutout

### Signals

**Transit**:
A periodic, brief dip in a star's light curve caused by a planet crossing in front of (transiting) the stellar disk, blocking a fraction of the star's light.

**Transit Depth (δ)**:
The fractional drop in flux during a transit, expressed in ppm (parts per million) or as a fraction. Equal to (Rp/Rs)² for a central transit. Earth around Sun-like star ≈ 84 ppm (0.008%).
_Avoid_: Dip depth, occultation depth

**Transit Duration (T₁₄)**:
The total time from first to fourth contact of a transit — ingress start to egress end. Typically reported in hours.
_Avoid_: Transit length, event duration

**Orbital Period (P)**:
The time between successive transits, equal to the planet's orbital period. Measured in days.
_Avoid_: Periodicity

**Phase Folding**:
Collapsing a time-series light curve onto a single orbital cycle by wrapping time modulo the orbital period, stacking all transits to improve signal-to-noise.
_Avoid_: Epoch folding, period folding

**Periodogram**:
A power spectrum over trial periods showing detection strength — the output of a period-search algorithm (BLS or TLS). The peak period is the best-fit orbital period.
_Avoid_: Power spectrum, frequency plot

**Secondary Eclipse**:
A smaller dip at orbital phase 0.5 when the planet passes behind the star — present in eclipsing binaries (both stars are luminous) but negligible or absent in planet transits. A key EB discriminator.
_Avoid_: Secondary transit, occultation

**Odd/Even Depth Difference**:
The difference between transit depths measured in odd- and even-numbered transits. Eclipsing binaries show alternating depths (primary vs. secondary star eclipses); planet transits show equal depths.
_Avoid_: Depth alternation, transit-to-transit variation

**V-Shape Metric**:
The ratio of ingress+egress duration to total transit duration. V-shaped (high ratio) suggests a grazing eclipsing binary; flat-bottomed (low ratio) suggests a planet.
_Avoid_: Transit shape parameter

### Signal Classes

**Planet Candidate (PC)**:
A transit-like signal consistent with a planet orbiting the target star. Characterized by small depth (<~3%), flat bottom, equal odd/even depths, stable centroid, no secondary eclipse.

**Eclipsing Binary (EB)**:
A binary star system where one star eclipses the other. Characterized by deep primary eclipse, detectable secondary eclipse at phase 0.5, odd/even depth mismatch, possibly V-shaped profile.

**Background Blend (Blend)**:
A false positive where an eclipsing binary in a nearby background star is diluted by the target star's flux, mimicking a shallow planet transit. Detected via centroid shift during transit events and low CROWDSAP.
_Avoid_: Blended eclipsing binary, diluted EB

**False Positive (FP)**:
Any non-planet signal. Includes EBs, blends, stellar variability, and instrumental artefacts. Used as the umbrella term for "not a planet."

**Stellar Variability (Other/FP)**:
Quasi-periodic or irregular flux modulation caused by star spots, pulsations, or flares. Not caused by a transiting body.
_Avoid_: Stellar activity, rotational modulation

**Instrumental / Systematic**:
Flux artefacts caused by spacecraft behaviour (momentum dumps, Earth/Moon scattered light, detector noise) rather than astrophysical sources. Handled as a preprocessing gate via TESS quality flags, not as a classifier class.

**TOI (TESS Object of Interest)**:
A TESS detection vetted by the community and assigned a disposition label (PC, FP, EB, etc.) on ExoFOP-TESS. Used as ground-truth labels for training and validation.

**Disposition**:
The final label assigned to a signal by the pipeline: PLANET CANDIDATE, ECLIPSING BINARY, BACKGROUND BLEND, STELLAR VARIABILITY, or SUB-THRESHOLD. Replaces raw classifier output with a human-readable verdict.
_Avoid_: Final class, output label

### Detection Metrics

**Signal Detection Efficiency (SDE)**:
The statistical significance of a BLS/TLS periodogram peak: (peak_power − mean_power) / std_power. SDE > 7 is conventionally a significant detection. SDE between 5 and 7 is a sub-threshold candidate.
_Avoid_: Detection significance, peak significance

**Signal-to-Noise Ratio (SNR)**:
The ratio of transit depth to the photometric noise floor, scaled by the square root of the number of in-transit data points. Per-event SNR measures single-transit detectability.
_Avoid_: Detection SNR, event significance

**Combined Differential Photometric Precision (CDPP)**:
The empirical photometric noise floor of a light curve at a specified timescale (typically 1 hour). Sets the minimum detectable transit depth.
_Avoid_: RMS noise, photometric precision

### Classification Metrics

**Confidence Score**:
The temperature-scaled softmax probability of the predicted class from the full ensemble (0.6 × CNN + 0.4 × XGBoost), calibrated such that a score of 0.90 means the prediction is correct ~90% of the time.
_Avoid_: Classifier probability, raw softmax

**Confidence Tier**:
A colour-coded triage band based on classifier confidence: Gold (> 0.90), Silver (0.70–0.90), Bronze (< 0.70). Used for mission planner prioritisation.
_Avoid_: Confidence level, probability band

**Expected Calibration Error (ECE)**:
The weighted average difference between predicted confidence and observed accuracy across confidence bins. Target: ECE < 0.04 (well-calibrated).
_Avoid_: Calibration error

**Temperature Scaling**:
A post-hoc calibration method that divides logits by a learned temperature parameter T (T > 1 softens probabilities) to align predicted confidence with empirical accuracy on a held-out validation set.
_Avoid_: Platt scaling, probability calibration

**False Positive Probability (FPP)**:
The Bayesian posterior probability that a signal is not a planet, computed by TRICERATOPS+ using stellar parameters, contrast curves, and population priors. FPP < 1.5% qualifies as a Validated Planet.
_Avoid_: FPP score, vetting probability

**Nearby False Positive Probability (NFPP)**:
The component of FPP attributable to a resolved nearby star. NFPP < 0.1% is required alongside FPP < 1.5% for planet validation.
_Avoid_: Contamination probability

**Completeness Map**:
A plot of signal recovery fraction as a function of transit depth and orbital period, generated by injecting synthetic transits at known parameters and measuring detection rate. Characterizes what the pipeline can and cannot find.
_Avoid_: Sensitivity map, recovery fraction

### Stellar and Pipeline Parameters

**CROWDSAP / Contamination Ratio**:
The fraction of flux in the photometric aperture contributed by nearby stars (from TICv8). Contamination > 0.3 indicates significant blending risk; < 0.5 blocks PC classification.
_Avoid_: Dilution factor, blend ratio

**Centroid Shift**:
The spatial offset of the flux-weighted pixel centroid during transit vs. out of transit, measured from TPF data. A non-zero shift (> 3σ) indicates the transit originates from a background star — a blend.
_Avoid_: Pixel offset, positional shift

**Limb Darkening**:
The optical effect where a star's disk appears dimmer near the edge, affecting the transit light curve shape. Parameterized with quadratic coefficients per star, interpolated from TICv8 using Claret & Bloemen (2011) tables.
_Avoid_: Stellar dimming, edge darkening

**Detrending**:
Removing long-term stellar variability and instrumental trends from the light curve before transit search, while preserving transit shapes. Performed in two tiers: biweight (Wotan) for all light curves, Gaussian Process (celerite2 Matérn-3/2) for top candidates.
_Avoid_: Flattening, baseline removal

**Posterior Distribution**:
The probability distribution of a transit parameter (P, δ, T₁₄, Rp/Rs, inclination) after MCMC sampling, given the observed data. Summarized as median ± 1σ (16th/84th percentile credible intervals).
_Avoid_: Parameter distribution, MCMC output

### Training Strategy

**Pre-training**:
Training the CNN on the Kepler DR24 labeled dataset (34,032 TCEs) to learn transit morphology before fine-tuning on TESS-specific data. Provides a strong shape prior and more training samples.
_Avoid_: Base training, initial training

**Fine-tuning**:
Continuing CNN training on TESS TOI labels after Kepler pre-training, adapting the model to TESS-specific noise, cadence, and systematics. The final model.
_Avoid_: Transfer learning, adaptation training

**Synthetic Transit Injection**:
Generating batman-model transits at known depths (50–200 ppm) and injecting them into real detrended TESS noise to create labeled training samples for shallow transits that are underrepresented in real catalogs. Powers the completeness map.
_Avoid_: Signal injection, artificial transits

**Ensemble**:
The weighted combination (0.6 × CNN + 0.4 × XGBoost) of the deep learning and gradient-boosted tree classifiers. Produces the final 4-class softmax probabilities.
_Avoid_: Voting classifier, model combination
