"""Completeness map visualization — 2D heatmap of recovery fraction.

Reads pre-computed recovery grid and renders:
- PNG: matplotlib heatmap (150 dpi, 10×8 inch)
- HTML: interactive Plotly heatmap with hover

Annotates Earth-analog (84 ppm) and Super-Earth (250 ppm) depth thresholds.
"""

import logging
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import plotly.graph_objects as go

from src.characterization.utils import ensure_directories

logger = logging.getLogger(__name__)

PNG_DPI = 150


def generate_completeness_visualization(
    grid_path: str = "data/completeness/recovery_grid.npz",
    output_dir: str = "outputs/completeness",
) -> tuple[str, str]:
    """Generate PNG and Plotly HTML completeness map.

    Returns (png_path, html_path).
    """
    ensure_directories()
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Load pre-computed grid
    data = np.load(grid_path)
    recovery_map = data["recovery_map"]
    depths_ppm = data["depths_ppm"]
    periods = data["periods"]

    png_path = _plot_completeness_png(recovery_map, depths_ppm, periods, output_dir)
    html_path = _plot_completeness_html(recovery_map, depths_ppm, periods, output_dir)

    return png_path, html_path


def _plot_completeness_png(recovery_map: np.ndarray, depths_ppm: np.ndarray,
                           periods: np.ndarray, output_dir: str) -> str:
    """Generate matplotlib PNG heatmap."""
    fig, ax = plt.subplots(figsize=(10, 8))

    im = ax.pcolormesh(
        periods, depths_ppm, recovery_map,
        cmap="RdYlGn", vmin=0, vmax=1, shading="auto",
    )
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Orbital Period (days)", fontsize=12)
    ax.set_ylabel("Transit Depth (ppm)", fontsize=12)
    ax.set_title("Pipeline Completeness Map — Recovery Fraction", fontsize=14)

    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label("Recovery Fraction", fontsize=11)

    # Annotate key depth thresholds
    ax.axhline(84, color="white", linestyle="--", alpha=0.8, linewidth=1.5, label="Earth-analog (84 ppm)")
    ax.axhline(250, color="cyan", linestyle="--", alpha=0.8, linewidth=1.5, label="Super-Earth (~250 ppm)")
    ax.legend(loc="upper left", fontsize=10)

    out_path = Path(output_dir) / "completeness_map.png"
    fig.savefig(out_path, dpi=PNG_DPI, bbox_inches="tight")
    plt.close(fig)
    logger.info("Completeness PNG saved: %s", out_path)
    return str(out_path)


def _plot_completeness_html(recovery_map: np.ndarray, depths_ppm: np.ndarray,
                            periods: np.ndarray, output_dir: str) -> str:
    """Generate interactive Plotly HTML heatmap."""
    fig = go.Figure(data=go.Heatmap(
        z=recovery_map,
        x=np.log10(periods),
        y=np.log10(depths_ppm),
        colorscale="RdYlGn",
        zmin=0, zmax=1,
        colorbar=dict(title="Recovery Fraction"),
        hovertemplate=(
            "Period: %{customdata[0]:.2f} d<br>"
            "Depth: %{customdata[1]:.0f} ppm<br>"
            "Recovery: %{z:.2f}<extra></extra>"
        ),
        customdata=np.dstack(np.meshgrid(periods, depths_ppm)),
    ))

    # Add threshold lines
    fig.add_hline(y=np.log10(84), line=dict(color="white", dash="dash", width=2),
                  annotation_text="Earth-analog (84 ppm)")
    fig.add_hline(y=np.log10(250), line=dict(color="cyan", dash="dash", width=2),
                  annotation_text="Super-Earth (250 ppm)")

    fig.update_layout(
        title="Pipeline Completeness Map",
        xaxis_title="log₁₀(Period / days)",
        yaxis_title="log₁₀(Depth / ppm)",
        height=600, width=800,
    )

    out_path = Path(output_dir) / "completeness_map.html"
    fig.write_html(str(out_path))
    logger.info("Completeness HTML saved: %s", out_path)
    return str(out_path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    generate_completeness_visualization()
