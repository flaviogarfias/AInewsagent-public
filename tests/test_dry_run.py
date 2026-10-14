from ai_daily_briefing.dry_run import run_dry_run
from ai_daily_briefing.audit import AuditLog
from ai_daily_briefing.state import DeliveryState
import pytest


def test_dry_run_without_date_lookup_fails_closed_for_arxiv(tmp_path):
    paper = {"kind": "paper", "title": "Language model inference method",
             "url": "https://arxiv.org/abs/2610.12582", "source": "arXiv cs.CL",
             "published": "2026-10-13T04:00:00Z",
             "abstract": "An inference method for language models with extensive technical baselines and comparisons."}
    result = run_dry_run([paper], "2026-10-13T09:30:00-06:00", tmp_path,
                         evaluate=lambda item: pytest.fail("unverified paper evaluated"),
                         verify=lambda url: True)
    assert result["status"] == "failed"
    assert result["source_errors"] == 1
    assert result["items"] == []


def test_unusable_teaser_article_fails_run_despite_other_news(tmp_path):
    teaser = {"kind": "news", "title": "GPU acceleration with AI agents",
              "url": "https://example.org/teaser", "source": "Vendor",
              "published": "2026-10-13T21:33:21Z",
              "abstract": "Enterprise data processing with agentic AI requires substantial resources "
                          "and increasingly complex workloads, with GPU acceleration..."}
    healthy = {"kind": "news", "title": "LLM inference infrastructure launch",
               "url": "https://example.org/healthy", "source": "Vendor",
               "published": "2026-10-13T21:33:21Z",
               "abstract": "A new language model inference system has reached production customers "
                           "with documented throughput and latency improvements."}
    result = run_dry_run([teaser, healthy], "2026-10-13T17:39:00-06:00", tmp_path,
        evaluate=lambda item: {"criteria": {"economic_impact": False, "deployment": True,
                         "competitive_disruption": False, "source_verifiability": True},
                         "summary": "Se describe un despliegue de infraestructura de inferencia."},
        verify=lambda url: True, fetch_text=lambda url: "")
    assert len(result["items"]) == 1
    assert result["items"][0]["url"] == healthy["url"]
    assert result["source_errors"] == 1
    assert result["status"] == "failed"


def test_dry_run_no_news_records_audit_without_generating_email(tmp_path):
    result = run_dry_run([], "2026-10-03T07:00:00-06:00", tmp_path,
                         evaluate=lambda item: {}, verify=lambda url: False)
    assert result["status"] == "no-news"
    assert result["source_errors"] == 0
    assert result["artifacts"] == {}
    with AuditLog(tmp_path / "audit.sqlite3") as audit:
        assert audit.get_run(result["run_id"])["metrics"]["selected"] == 0
    with DeliveryState(tmp_path / "state.sqlite3") as state:
        assert state.connection.execute("SELECT COUNT(*) FROM sent").fetchone()[0] == 0


def test_collection_error_with_no_candidates_is_failed_and_audited(tmp_path):
    result = run_dry_run([], "2026-10-03T07:00:00-06:00", tmp_path,
                         evaluate=lambda item: {}, verify=lambda url: False,
                         collection_errors=1, source_counts={"Broken RSS": 0})
    assert result["status"] == "failed"
    with AuditLog(tmp_path / "audit.sqlite3") as audit:
        metrics = audit.get_run(result["run_id"])["metrics"]
        assert metrics["source_errors"] == 1
        assert metrics["source_count_Broken RSS"] == 0


def test_dry_run_respects_configured_time_window(tmp_path):
    item = {"kind": "paper", "title": "LLM inference", "url": "https://example.org/paper",
            "published": "2026-10-01T07:00:00Z", "source": "arXiv",
            "abstract": "A lengthy technical study of LLM inference with benchmarks and direct comparisons against deployed baselines."}
    result = run_dry_run([item], "2026-10-03T07:00:00-06:00", tmp_path,
                         evaluate=lambda item: {}, verify=lambda url: True, window_hours=24)
    assert result["status"] == "no-news"


def test_dry_run_marks_all_source_failures_as_failed_not_no_news(tmp_path):
    item = {"kind": "news", "title": "LLM rollout", "url": "https://example.org/news",
            "published": "2026-10-03T01:00:00Z", "source": "Vendor", "abstract": "Detailed LLM rollout measurements and real deployment to paying customers in production."}
    result = run_dry_run([item], "2026-10-03T07:00:00-06:00", tmp_path,
                         evaluate=lambda item: {}, verify=lambda url: False)
    assert result["status"] == "failed"
    with AuditLog(tmp_path / "audit.sqlite3") as audit:
        assert audit.get_run(result["run_id"])["metrics"]["source_errors"] == 1


def test_selected_items_with_collection_errors_are_failed_not_ready(tmp_path):
    item = {"kind": "paper", "title": "LLM inference systems", "url": "https://example.org/paper",
            "published": "2026-10-03T01:00:00Z", "source": "arXiv",
            "abstract": "A detailed evaluation of LLM inference systems with reproducible comparisons and explicit serving benchmarks."}
    result = run_dry_run([item], "2026-10-03T07:00:00-06:00", tmp_path,
                         evaluate=lambda item: {"criteria": {"novelty": True,
                             "rigor": True, "ecosystem_relevance": True,
                             "reproducibility": True}, "summary": "Evaluación de inferencia."},
                         verify=lambda url: True, collection_errors=1)
    assert len(result["items"]) == 1
    assert result["source_errors"] == 1
    assert result["status"] == "failed"


def test_evaluator_exception_never_persists_exception_message(tmp_path):
    item = {"kind": "paper", "title": "LLM inference systems", "url": "https://example.org/paper",
            "published": "2026-10-03T01:00:00Z", "source": "arXiv",
            "abstract": "A detailed evaluation of LLM inference systems with reproducible comparisons and explicit serving benchmarks."}
    def fail(_item):
        raise OSError("private-key-should-not-be-recorded")
    with pytest.raises(OSError):
        run_dry_run([item], "2026-10-03T07:00:00-06:00", tmp_path,
                    evaluate=fail, verify=lambda url: True)
    with AuditLog(tmp_path / "audit.sqlite3") as audit:
        rows = audit.connection.execute("SELECT status, error FROM runs").fetchall()
    assert rows == [("failed", "OSError")]
