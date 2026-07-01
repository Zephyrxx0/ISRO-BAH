export default function AboutPage() {
  return (
    <div className="w-full max-w-3xl mx-auto py-12 px-6 space-y-6">
      <div className="border border-[var(--border-color)] bg-[var(--surface)] p-6">
        <h1 className="font-sans font-black text-2xl text-[var(--fg)] tracking-tighter mb-4">
          ABOUT THIS PIPELINE
        </h1>

        <div className="space-y-3 font-mono text-xs text-[var(--fg-dim)] leading-relaxed">
          <p>
            AI-Enabled Exoplanet Detection Pipeline — ISRO BAH 2026 PS-07.
            Built for the Bharatiya Antariksh Hackathon 2026 Grand Finale
            (6–7 August 2026). Team of 3–4.
          </p>

          <p>
            The pipeline ingests TESS 2-minute cadence photometry from 3 sectors
            (~60,000 stars), runs TLS period search for transit signals, extracts
            engineered features, and classifies candidates using a Dual-View CNN
            + XGBoost ensemble into 4 astrophysical classes: planet candidate,
            eclipsing binary, background blend, and stellar variability.
          </p>

          <p>
            Top Gold-tier candidates undergo Bayesian validation via TRICERATOPS+
            MCMC and SHERLOCK cross-sector recovery. Parameter estimation uses
            batman transit models with per-star limb darkening from TICv8,
            sampled via emcee MCMC.
          </p>
        </div>
      </div>

      <div className="border border-[var(--border-color)] bg-[var(--surface)] p-6">
        <h2 className="font-sans font-black text-lg text-[var(--fg)] tracking-tighter mb-3">
          TECHNICAL STACK
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2 font-mono text-[10px] text-[var(--fg-dim)] tracking-widest">
          {[
            "TLS PERIOD SEARCH",
            "DUAL-VIEW CNN (ASTRONET)",
            "XGBOOST ENSEMBLE",
            "BATMAN TRANSIT MODEL",
            "EMCEE MCMC SAMPLER",
            "TRICERATOPS+ VALIDATION",
            "SHERLOCK RECOVERY",
            "NEXT.JS DASHBOARD",
            "TENSORFLOW 2.21",
            "SCIKIT-LEARN 1.7",
            "LIGHTKURVE / ASTROPY",
            "MATPLOTLIB / PLOTLY",
          ].map((item) => (
            <div key={item} className="border border-[var(--border-color)] px-3 py-2">
              {item}
            </div>
          ))}
        </div>
      </div>

      <div className="border border-[var(--border-color)] bg-[var(--surface)] p-6">
        <h2 className="font-sans font-black text-lg text-[var(--fg)] tracking-tighter mb-3">
          VALIDATION TARGETS
        </h2>
        <div className="space-y-1 font-mono text-[10px] text-[var(--fg-dim)] tracking-widest">
          <div>WASP-121b — SECTOR 1 — HOT JUPITER, 1.27 D</div>
          <div>TOI-270 — SECTOR 3 — SUPER-EARTH SYSTEM, 3.36 D</div>
          <div>L 98-59 — SECTOR 2 — SMALL PLANET SYSTEM, 2.25 D</div>
          <div>TOI-700 D — SECTOR 1 — EARTH-SIZED, HABITABLE ZONE, 37.4 D</div>
        </div>
      </div>
    </div>
  );
}
