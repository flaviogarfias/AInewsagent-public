"""Matching HTML/PDF artifacts from one report data structure."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .pdf_report import write_pdf
from .report import render_html


def write_report_artifacts(report: dict, output_dir: str | Path,
                           timezone: str = "America/Mexico_City") -> dict[str, Path]:
    """Render both formats once from the same selected items and CDMX timestamp."""
    local = datetime.fromisoformat(report["generated_at"].replace("Z", "+00:00"))
    if local.tzinfo is None:
        raise ValueError("generated_at must carry a timezone")
    local = local.astimezone(ZoneInfo(timezone))
    stamp = local.strftime("%Y-%m-%d-%H%M%S")
    label = local.strftime("%Y-%m-%d %H:%M %Z")
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    html_path = directory / f"reporte-{stamp}.html"
    pdf_path = directory / f"reporte-{stamp}.pdf"
    html_path.write_text(render_html(report["items"], label), encoding="utf-8")
    write_pdf(report["items"], label, pdf_path)
    return {"html": html_path, "pdf": pdf_path}
