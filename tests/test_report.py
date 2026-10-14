from ai_daily_briefing.report import render_html


def test_report_escapes_untrusted_feed_text_and_keeps_original_link():
    html = render_html([{"kind": "paper", "title": "<script>alert(1)</script>",
                         "url": "https://arxiv.org/abs/2510.12345", "summary": "Method & baseline",
                         "traffic_light": "yellow", "source": "arXiv", "published": "2026-10-03"}],
                       "2026-10-03 07:00 CST")
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert 'href="https://arxiv.org/abs/2510.12345"' in html
    assert "Method &amp; baseline" in html
    assert "Amarillo" in html
    assert "Semáforo: yellow" not in html

def test_arxiv_report_distinguishes_original_and_feed_dates():
    html = render_html([{"kind": "paper", "title": "Model", "url": "https://arxiv.org/abs/2610.12582",
                         "summary": "Estudio de modelos.", "traffic_light": "yellow", "source": "arXiv",
                         "published": "2026-10-08T18:05:42Z",
                         "feed_published": "Tue, 13 Oct 2026 00:00:00 -0400"}],
                       "2026-10-13 09:30 CST")
    assert "Fecha original de arXiv: 2026-10-08T18:05:42Z" in html
    assert "Fecha del feed: Tue, 13 Oct 2026 00:00:00 -0400" in html
