"""4-page PDF report generator — Phase 4 presentation output.

Produces report.pdf from pre-rendered pipeline PNGs.
Always generates even with partial data (graceful fallback per D-11).
"""

import argparse
import logging
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from matplotlib.backends.backend_pdf import PdfPages

logger = logging.getLogger(__name__)

PAGE_SIZE = (8.5, 11)


def _text_block(fig, text_lines, y_start=10.0, fontsize=10, line_spacing=0.4):
    y = y_start
    for line in text_lines:
        fig.text(0.5, y / PAGE_SIZE[1], line, ha="center", va="top",
                 fontsize=fontsize, fontfamily="monospace", color="#333333")
        y -= line_spacing


def _image_or_placeholder(fig, path, rect, label="Not computed"):
    ax = fig.add_axes(rect)
    ax.axis("off")
    if path and Path(path).exists():
        img = mpimg.imread(str(path))
        ax.imshow(img)
        ax.set_title(Path(path).name, fontsize=8, fontfamily="monospace")
    else:
        ax.text(0.5, 0.5, label, ha="center", va="center",
                fontsize=12, color="#999999", fontfamily="monospace",
                transform=ax.transAxes)
        ax.set_title("", fontsize=8)


def _page_methodology(fig, outputs_dir: Path):
    fig.clf()
    fig.suptitle("1. Methodology", fontsize=14, fontweight="bold",
                 fontfamily="monospace", y=0.98)

    _image_or_placeholder(fig, outputs_dir / "plots" / "pipeline_flowchart.png",
                          [0.05, 0.45, 0.90, 0.48], "Flowchart not computed")
    _image_or_placeholder(fig, outputs_dir / "confusion_matrix.png",
                          [0.15, 0.05, 0.70, 0.38], "Confusion matrix not computed")

    _text_block(fig, [
        "Dual-View CNN (AstroNet) + XGBoost ensemble",
        "4-class: Planet Candidate / Eclipsing Binary / Background Blend / Stellar Variability",
        "TLS period search → feature extraction → ensemble classification → Bayesian validation",
    ], y_start=10.5, fontsize=8)


def _page_results(fig, outputs_dir: Path):
    fig.clf()
    fig.suptitle("2. Results", fontsize=14, fontweight="bold",
                 fontfamily="monospace", y=0.98)

    summary_path = outputs_dir / "catalogue" / "master_catalogue.parquet"
    if summary_path.exists():
        import pandas as pd
        df = pd.read_parquet(summary_path)
        n_total = len(df)
        n_gold = int((df.get("pc_confidence", 0) >= 0.90).sum()) if "pc_confidence" in df.columns else 0
        n_silver = int(((df.get("pc_confidence", 0) >= 0.70) & (df.get("pc_confidence", 0) < 0.90)).sum()) if "pc_confidence" in df.columns else 0
    else:
        n_total, n_gold, n_silver = 0, 0, 0

    _text_block(fig, [
        f"Total candidates (SDE >= 5): {n_total}",
        f"Gold tier (confidence >= 0.90): {n_gold}",
        f"Silver tier (confidence >= 0.70): {n_silver}",
    ], y_start=10.5, fontsize=10)

    _image_or_placeholder(fig, outputs_dir / "plots" / "best_planet_phase_folded.png",
                          [0.1, 0.15, 0.80, 0.65], "Best planet not computed")


def _page_validation(fig, outputs_dir: Path):
    fig.clf()
    fig.suptitle("3. Validation", fontsize=14, fontweight="bold",
                 fontfamily="monospace", y=0.98)

    _text_block(fig, [
        "Recovery tests against known exoplanets:",
        "WASP-121b (Sector 1) — hot Jupiter, 1.27 d period",
        "TOI-270 (Sector 3) — super-Earth system, 3.36 d period",
        "L 98-59 (Sector 2) — small planet system, 2.25 d period",
        "TOI-700 d — Earth-sized in habitable zone, 37.4 d period",
    ], y_start=10.5, fontsize=9)

    _image_or_placeholder(fig, outputs_dir / "plots" / "triceratops_fpp.png",
                          [0.05, 0.28, 0.42, 0.38], "TRICERATOPS not computed")
    _image_or_placeholder(fig, outputs_dir / "completeness" / "completeness_map.png",
                          [0.52, 0.28, 0.44, 0.38], "Completeness not computed")


def _page_uncertainties(fig, outputs_dir: Path):
    fig.clf()
    fig.suptitle("4. Uncertainties & Limitations", fontsize=14, fontweight="bold",
                 fontfamily="monospace", y=0.98)

    _text_block(fig, [
        "Assumptions:",
        "- Circular orbits assumed (e=0) for transit model fitting",
        "- Quadratic limb darkening from TICv8; uninformative priors on LD",
        "- Gaussian noise model; correlated (red) noise partially mitigated via GP detrending",
        "- Single-planet transits; multi-planet systems modelled individually",
        "",
        "Limitations:",
        "- 3-sector baseline limits detectable periods to ~20 d",
        "- T4 GPU memory constrained MCMC chains to 10,000 samples",
        "- Centroid analysis gated by TPF availability in MAST",
        "- Classification ECE target < 0.04; uncalibrated on very low SNR regimes",
    ], y_start=10.5, fontsize=8)

    _image_or_placeholder(fig, outputs_dir / "plots" / "best_planet_corner.png",
                          [0.1, 0.05, 0.80, 0.55], "Corner plot not computed")


def generate_report(outputs_dir: Path, output_path: Path) -> None:
    fig = plt.figure(figsize=PAGE_SIZE, dpi=150)

    with PdfPages(str(output_path)) as pdf:
        metadata = {
            "Title": "ISRO BAH 2026 PS-07: AI-Enabled Exoplanet Detection",
            "Author": "ISRO BAH Team",
        }
        try:
            pdf.infodict().update(metadata)
        except AttributeError:
            pass

        for page_fn in [_page_methodology, _page_results, _page_validation, _page_uncertainties]:
            page_fn(fig, outputs_dir)
            pdf.savefig(fig)

    plt.close(fig)
    logger.info("Wrote 4-page PDF report to %s", output_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate 4-page PDF report")
    parser.add_argument("--outputs-dir", type=Path, required=True)
    parser.add_argument("--output-path", type=Path, required=True)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    generate_report(args.outputs_dir, args.output_path)
