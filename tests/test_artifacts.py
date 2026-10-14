from ai_daily_briefing.artifacts import write_report_artifacts


def test_writes_matching_html_pdf_with_cdmx_filename(tmp_path):
    from pypdf import PdfReader
    report = {"generated_at": "2026-10-03T07:00:00-06:00", "items": [
        {"kind": "paper", "title": "AI infrastructure", "url": "https://example.org/paper",
         "summary": "Texto original verificado.", "traffic_light": "yellow", "source": "arXiv",
         "published": "2026-10-03"}]}
    paths = write_report_artifacts(report, tmp_path)
    assert paths["html"].name == "reporte-2026-10-03-070000.html"
    assert paths["pdf"].name == "reporte-2026-10-03-070000.pdf"
    assert "https://example.org/paper" in paths["html"].read_text()
    text = PdfReader(paths["pdf"]).pages[0].extract_text()
    assert "https://example.org/paper" in text
    assert "Texto original verificado." in text
