"""Configured no-send runtime: collection, selection, artifacts and audit."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from time import monotonic
from uuid import uuid4
from zoneinfo import ZoneInfo

from .audit import AuditLog
from .arxiv_dates import original_arxiv_dates

from .article_text import fetch_article_text
from .cli import collect_configured_diagnostics
from .dry_run import run_dry_run
from .evaluator import evaluate_with_ollama
from .verification import verify_source


def run_configured_dry_run(config: dict, workdir: str | Path, collect=collect_configured_diagnostics,
                           evaluate=None, verify=verify_source,
                           fetch_text=fetch_article_text, now: str | None = None,
                           paper_date_lookup=None) -> dict:
    """Execute bounded read-only research; returns report paths and audit ID."""
    if now is None:
        now = datetime.now(ZoneInfo(config["schedule"]["timezone"])).isoformat()
    if evaluate is None:
        model = config["model"]
        evaluate = lambda item: evaluate_with_ollama(item, model["name"],
                                                       model.get("base_url", "http://127.0.0.1:11434"))
    started = monotonic()
    try:
        collected = collect(config)
    except (OSError, ValueError) as error:
        run_id = uuid4().hex
        with AuditLog(Path(workdir) / "audit.sqlite3") as audit:
            audit.record_run(run_id, "failed", {"candidates": 0, "selected": 0,
                                                 "source_errors": 1,
                                                 "elapsed_ms": int((monotonic() - started) * 1000)},
                             error=type(error).__name__)
        return {"run_id": run_id, "status": "failed", "artifacts": {},
                "source_errors": 1, "items": []}
    candidates = collected["candidates"] if isinstance(collected, dict) else collected
    collection_errors = collected.get("source_errors", 0) if isinstance(collected, dict) else 0
    source_counts = collected.get("source_counts", {}) if isinstance(collected, dict) else {}
    selection = config.get("selection", {})
    return run_dry_run(candidates, now, workdir, evaluate=evaluate, verify=verify,
                       fetch_text=fetch_text, collection_errors=collection_errors,
                       source_counts=source_counts,
                       window_hours=selection.get("window_hours", 48),
                       max_evaluations_per_kind=selection.get("max_evaluations_per_kind", 6),
                       paper_date_lookup=paper_date_lookup,
                       paper_dates_lookup=(original_arxiv_dates if paper_date_lookup is None else None))
