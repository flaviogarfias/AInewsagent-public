from ai_daily_briefing.pdf_report import write_pdf


def test_pdf_contains_both_selected_titles_and_verified_urls(tmp_path):
    from pypdf import PdfReader
    items = [
        {"kind": "paper", "title": "LLM <agents>", "url": "https://arxiv.org/abs/2610.00049",
         "summary": "Método y resultados.", "traffic_light": "yellow", "source": "arXiv",
         "published": "2026-10-03"},
        {"kind": "news", "title": "Product update", "url": "https://example.org/launch",
         "summary": "Despliegue real.", "traffic_light": "green", "source": "Vendor",
         "published": "2026-10-03"},
    ]
    path = write_pdf(items, "2026-10-03 07:00 CST", tmp_path / "report.pdf")
    assert path.read_bytes().startswith(b"%PDF")
    text = "\n".join(page.extract_text() for page in PdfReader(path).pages)
    assert "LLM <agents>" in text
    assert "Product update" in text
    assert "https://arxiv.org/abs/2610.00049" in text
    assert "https://example.org/launch" in text

def test_pdf_distinguishes_arxiv_original_and_feed_dates(tmp_path):
    from pypdf import PdfReader
    item = {"kind": "paper", "title": "Model", "url": "https://arxiv.org/abs/2610.12582",
            "summary": "Estudio de modelos.", "traffic_light": "yellow", "source": "arXiv",
            "published": "2026-10-08T18:05:42Z", "feed_published": "2026-10-13T04:00:00Z"}
    path = write_pdf([item], "2026-10-13 09:30 CST", tmp_path / "report.pdf")
    text = "\n".join(page.extract_text() for page in PdfReader(path).pages)
    assert "Fecha original de arXiv: 2026-10-08T18:05:42Z" in text
    assert "Fecha del feed: 2026-10-13T04:00:00Z" in text
