from ai_daily_briefing.runtime import run_configured_dry_run
from ai_daily_briefing.audit import AuditLog
from ai_daily_briefing.state import DeliveryState
import pytest

def test_configured_runtime_uses_original_arxiv_date_to_exclude_old_paper(tmp_path):
    paper = {"kind": "paper", "title": "Language model inference method",
             "url": "https://arxiv.org/abs/2610.12582", "source": "arXiv cs.CL",
             "published": "2026-10-13T04:00:00Z",
             "abstract": "An inference method for language models with extensive technical baselines and comparisons."}
    seen = []
    result = run_configured_dry_run({"model": {"name": "qwen3:4b"}}, tmp_path,
                                     collect=lambda config: [paper],
                                     verify=lambda url: True,
                                     evaluate=lambda item: pytest.fail("old paper evaluated"),
                                     paper_date_lookup=lambda url: seen.append(url) or "2026-10-08T18:05:42Z",
                                     now="2026-10-13T09:30:00-06:00")
    assert result["status"] == "no-news" and result["items"] == []
    assert seen == [paper["url"]]

def test_default_runtime_batches_all_arxiv_dates(tmp_path, monkeypatch):
    import ai_daily_briefing.runtime as runtime_module
    base = {"kind": "paper", "source": "arXiv cs.CL", "published": "2026-10-13T04:00:00Z",
            "abstract": "An inference method for language models with extensive technical baselines and comparisons."}
    papers = [{**base, "title": f"Language model inference study {n}",
               "url": f"https://arxiv.org/abs/2610.{n:05d}"} for n in range(1, 8)]
    calls = []
    def dates(urls):
        calls.append(urls)
        return {url: "2026-10-12T18:05:42Z" if url.endswith("00007") else "2026-10-08T18:05:42Z"
                for url in urls}
    monkeypatch.setattr(runtime_module, "original_arxiv_dates", dates)
    result = run_configured_dry_run({"model": {"name": "qwen3:4b"}}, tmp_path,
                                     collect=lambda config: papers, verify=lambda url: True,
                                     evaluate=lambda item: {"criteria": {"novelty": False, "rigor": False,
                                         "ecosystem_relevance": False, "reproducibility": False},
                                         "summary": "Estudio de modelos."},
                                     now="2026-10-13T09:30:00-06:00")
    assert result["status"] == "dry-run" and result["items"][0]["url"] == papers[-1]["url"]
    assert calls == [[paper["url"] for paper in papers]]

def test_runtime_handles_more_than_one_hundred_arxiv_candidates(tmp_path, monkeypatch):
    import ai_daily_briefing.runtime as runtime_module
    from ai_daily_briefing.arxiv_dates import original_arxiv_dates
    from urllib.parse import parse_qs, urlsplit
    base = {"kind": "paper", "source": "arXiv", "published": "2026-10-13T04:00:00Z",
            "abstract": "An inference method for language models with extensive technical baselines and comparisons."}
    papers = [{**base, "title": f"Language model inference study {n}",
               "url": f"https://arxiv.org/abs/2610.{n:05d}"} for n in range(1, 102)]
    calls = []
    def fetch(url, limit):
        ids = parse_qs(urlsplit(url).query)["id_list"][0].split(",")
        calls.append(ids)
        entries = "".join(f"<entry><id>http://arxiv.org/abs/{identifier}v1</id>"
                          f"<published>{'2026-10-12' if identifier.endswith('00101') else '2026-10-08'}"
                          "T12:00:00Z</published></entry>" for identifier in ids)
        return f'<feed xmlns="http://www.w3.org/2005/Atom">{entries}</feed>'.encode(), "application/atom+xml"
    monkeypatch.setattr(runtime_module, "original_arxiv_dates",
                        lambda urls: original_arxiv_dates(urls, fetch=fetch))
    result = run_configured_dry_run({"model": {"name": "qwen3:4b"},
                                     "selection": {"max_evaluations_per_kind": 1}}, tmp_path,
                                     collect=lambda config: papers, verify=lambda url: True,
                                     evaluate=lambda item: {"criteria": {"novelty": False, "rigor": False,
                                         "ecosystem_relevance": False, "reproducibility": False},
                                         "summary": "Estudio de modelos."},
                                     now="2026-10-13T09:30:00-06:00")
    assert len(calls) == 2
    assert result["status"] == "dry-run" and result["source_errors"] == 0
    assert len(result["items"]) == 1 and result["items"][0]["url"] == papers[-1]["url"]

def test_legacy_paper_does_not_block_fresh_modern_paper(tmp_path, monkeypatch):
    import ai_daily_briefing.runtime as runtime_module
    from ai_daily_briefing.arxiv_dates import original_arxiv_dates
    base = {"kind": "paper", "source": "arXiv", "published": "2026-10-13T04:00:00Z",
            "abstract": "An inference method for language models with extensive technical baselines and comparisons."}
    papers = [{**base, "title": "Language model inference legacy",
               "url": "https://arxiv.org/abs/cs/9901001"},
              {**base, "title": "Language model inference modern",
               "url": "https://arxiv.org/abs/2610.12582"}]
    feed = b'''<feed xmlns="http://www.w3.org/2005/Atom">
    <entry><id>http://arxiv.org/abs/cs/9901001v1</id><published>1999-01-05T00:56:54Z</published></entry>
    <entry><id>http://arxiv.org/abs/2610.12582v1</id><published>2026-10-12T12:00:00Z</published></entry>
    </feed>'''
    monkeypatch.setattr(runtime_module, "original_arxiv_dates",
                        lambda urls: original_arxiv_dates(urls, fetch=lambda url, limit: (feed, "application/atom+xml")))
    result = run_configured_dry_run({"model": {"name": "qwen3:4b"}}, tmp_path,
                                     collect=lambda config: papers, verify=lambda url: True,
                                     evaluate=lambda item: {"criteria": {"novelty": False, "rigor": False,
                                         "ecosystem_relevance": False, "reproducibility": False},
                                         "summary": "Estudio de modelos."},
                                     now="2026-10-13T09:30:00-06:00")
    assert result["status"] == "dry-run" and result["source_errors"] == 0
    assert len(result["items"]) == 1 and result["items"][0]["url"] == papers[1]["url"]


def test_runtime_collects_then_prepares_without_delivery(tmp_path):
    config = {"model": {"name": "qwen3-hermes:8b"},
              "selection": {"window_hours": 48, "max_evaluations_per_kind": 1}}
    result = run_configured_dry_run(config, tmp_path, collect=lambda config: [],
                                    evaluate=lambda item: {}, verify=lambda url: False,
                                    now="2026-10-03T07:00:00-06:00")
    assert result["status"] == "no-news"
    with AuditLog(tmp_path / "audit.sqlite3") as audit:
        assert audit.get_run(result["run_id"])["metrics"]["candidates"] == 0


def test_runtime_diagnostic_collection_failure_never_reports_no_news(tmp_path):
    config = {"model": {"name": "qwen3-hermes:8b"}}
    result = run_configured_dry_run(config, tmp_path,
        collect=lambda config: {"candidates": [], "source_errors": 2,
                                "source_counts": {"Primary": 0, "Backup": 0}},
        evaluate=lambda item: {}, now="2026-10-03T07:00:00-06:00")
    assert result["status"] == "failed"
    with AuditLog(tmp_path / "audit.sqlite3") as audit:
        metrics = audit.get_run(result["run_id"])["metrics"]
        assert metrics["source_errors"] == 2
        assert metrics["source_count_Primary"] == 0


def test_collection_failure_is_audited_as_failed_without_delivery(tmp_path):
    def broken_collection(config):
        raise OSError("source unavailable")

    result = run_configured_dry_run({"schedule": {"timezone": "America/Mexico_City"}},
                                    tmp_path, collect=broken_collection,
                                    evaluate=lambda item: {}, now="2026-10-03T07:00:00-06:00")
    assert result["status"] == "failed"
    assert result["source_errors"] == 1
    assert result["items"] == []
    assert result["artifacts"] == {}
    with AuditLog(tmp_path / "audit.sqlite3") as audit:
        run = audit.get_run(result["run_id"])
        assert run["status"] == "failed"
        assert run["metrics"]["source_errors"] == 1
    with DeliveryState(tmp_path / "state.sqlite3") as state:
        assert state.connection.execute("SELECT COUNT(*) FROM sent").fetchone()[0] == 0
