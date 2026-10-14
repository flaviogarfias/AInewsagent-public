"""PDF rendering from the same structured report items as HTML."""

from __future__ import annotations

from html import escape
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

from .report import source_line

_LABELS = {"green": "Verde - muy valiosa", "yellow": "Amarillo - medianamente valiosa",
           "red": "Rojo - poco valiosa"}


def write_pdf(items: list[dict], timestamp: str, output_path: str | Path) -> Path:
    """Render the identical chosen items/fields used by the canonical HTML renderer."""
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    title = ParagraphStyle("ReportTitle", parent=styles["Title"], fontSize=17, spaceAfter=12)
    body = ParagraphStyle("ReportBody", parent=styles["BodyText"], leading=15, spaceAfter=7,
                          wordWrap="CJK", alignment=TA_LEFT)
    small = ParagraphStyle("ReportLink", parent=body, fontSize=9, textColor=colors.HexColor("#155e91"))
    story = [Paragraph("Lecturas de IA", title), Paragraph(escape(timestamp), body)]
    if not items:
        story.append(Paragraph("No hay candidatos nuevos verificables en esta ventana.", body))
    for item in items:
        kind = "Paper" if item["kind"] == "paper" else "Noticia"
        url = escape(str(item["url"]), quote=True)
        story.extend([Spacer(1, 12), Paragraph(kind + ": " + escape(str(item["title"])), styles["Heading2"]),
                      Paragraph("Semáforo: " + _LABELS.get(item.get("traffic_light", "red"), _LABELS["red"]), body),
                      Paragraph(escape(str(item.get("summary", ""))), body),
                      Paragraph(escape(source_line(item)), body),
                      Paragraph(f'<link href="{url}">{url}</link>', small)])
    document = SimpleDocTemplate(str(target), pagesize=(595, 842), rightMargin=48, leftMargin=48,
                                 topMargin=48, bottomMargin=48)
    document.build(story)
    if not target.read_bytes().startswith(b"%PDF"):
        raise ValueError("PDF renderer did not produce a PDF")
    return target
