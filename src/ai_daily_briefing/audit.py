"""Durable per-run audit records, separate from the confirmed delivery ledger."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path


class AuditLog:
    def __init__(self, path: str | Path):
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(target)
        self.connection.execute("""CREATE TABLE IF NOT EXISTS runs (
            run_id TEXT PRIMARY KEY, status TEXT NOT NULL, metrics_json TEXT NOT NULL,
            error TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")

    def __enter__(self) -> "AuditLog":
        return self

    def __exit__(self, *args: object) -> None:
        self.connection.close()

    def record_run(self, run_id: str, status: str, metrics: dict,
                   error: str | None = None) -> None:
        if not run_id or status not in {"dry-run", "failed", "sent", "no-news"}:
            raise ValueError("invalid run identity or status")
        if any(type(value) not in (int, float) or value < 0 for value in metrics.values()):
            raise ValueError("metrics must be nonnegative numbers")
        with self.connection:
            self.connection.execute("INSERT INTO runs(run_id, status, metrics_json, error) VALUES (?, ?, ?, ?)",
                                    (run_id, status, json.dumps(metrics, sort_keys=True), error))

    def get_run(self, run_id: str) -> dict | None:
        row = self.connection.execute("SELECT status, metrics_json, error, created_at FROM runs WHERE run_id = ?",
                                      (run_id,)).fetchone()
        return ({"run_id": run_id, "status": row[0], "metrics": json.loads(row[1]),
                 "error": row[2], "created_at": row[3]} if row else None)
