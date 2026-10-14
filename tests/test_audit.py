from ai_daily_briefing.audit import AuditLog


def test_audit_records_success_and_failure_without_marking_delivery(tmp_path):
    with AuditLog(tmp_path / "audit.sqlite3") as audit:
        audit.record_run("run-1", "dry-run", {"public_calls": 4, "candidates": 12,
                                              "selected": 2, "elapsed_ms": 1800})
        audit.record_run("run-2", "failed", {"public_calls": 2, "candidates": 0,
                                             "selected": 0, "elapsed_ms": 200}, error="source timeout")
        success = audit.get_run("run-1")
        failure = audit.get_run("run-2")
        assert success["status"] == "dry-run"
        assert success["metrics"]["selected"] == 2
        assert failure["error"] == "source timeout"
        assert failure["metrics"]["public_calls"] == 2
