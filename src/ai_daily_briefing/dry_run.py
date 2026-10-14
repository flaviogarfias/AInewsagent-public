"""Read-only delivery rehearsal with durable audit and optional HTML/PDF artifacts."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from time import monotonic
from uuid import uuid4

from .artifacts import write_report_artifacts
from .audit import AuditLog
from .pipeline import prepare_briefing
from .state import DeliveryState


def run_dry_run(candidates: list[dict], now: str, workdir: str | Path,
                evaluate: Callable[[dict], dict], verify: Callable[[str], bool],
                fetch_text: Callable[[str], str] | None = None,
                max_evaluations_per_kind: int = 6,
                window_hours: int = 48,
                collection_errors: int = 0,
                source_counts: dict[str, int] | None = None,
                paper_date_lookup: Callable[[str], str | None] | None = None,
                paper_dates_lookup: Callable[[list[str]], dict[str, str]] | None = None) -> dict:
    """Never send or advance delivered-state; retain status for zero-news/failure."""
    root = Path(workdir)
    root.mkdir(parents=True, exist_ok=True)
    run_id = uuid4().hex
    started = monotonic()
    with AuditLog(root / "audit.sqlite3") as audit:
        try:
            with DeliveryState(root / "state.sqlite3") as state:
                report = prepare_briefing(candidates, state, now, evaluate, verify,
                                          fetch_text=fetch_text,
                                          paper_date_lookup=paper_date_lookup,
                                          paper_dates_lookup=paper_dates_lookup,
                                          window_hours=window_hours,
                                          max_evaluations_per_kind=max_evaluations_per_kind)
            artifacts = (write_report_artifacts(report, root / "artifacts" / run_id)
                         if report["items"] else {})
            total_errors = report["source_errors"] + collection_errors
            status = ("failed" if total_errors else
                      "dry-run" if report["items"] else "no-news")
            metrics = {"candidates": len(candidates), "selected": len(report["items"]),
                       "source_errors": total_errors,
                       "elapsed_ms": int((monotonic() - started) * 1000)}
            metrics.update({f"source_count_{name}": count for name, count in (source_counts or {}).items()})
            audit.record_run(run_id, status, metrics)
            return {"run_id": run_id, "status": status, "artifacts": artifacts,
                    "source_errors": total_errors, "items": report["items"]}
        except Exception as error:
            audit.record_run(run_id, "failed", {"candidates": len(candidates), "selected": 0,
                                                "elapsed_ms": int((monotonic() - started) * 1000)},
                             error=type(error).__name__)
            raise
