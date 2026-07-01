"""Phase 4 presentation output generators.

CSV catalogue, 4-page PDF report, and dashboard JSON data files.
"""

from .generate_csv import generate_catalogue
from .generate_pdf import generate_report
from .generate_dashboard_data import generate_candidates_json, generate_star_jsons

__all__ = [
    "generate_catalogue",
    "generate_report",
    "generate_candidates_json",
    "generate_star_jsons",
]
