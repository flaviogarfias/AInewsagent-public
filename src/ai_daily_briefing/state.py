"""Persistent delivery ledger; discovery/dry runs never mutate sent state."""

from __future__ import annotations

import sqlite3
from pathlib import Path


class DeliveryState:
    def __init__(self, path: str | Path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.execute("CREATE TABLE IF NOT EXISTS sent (url TEXT PRIMARY KEY, message_id TEXT NOT NULL, sent_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
        self.connection.execute("CREATE TABLE IF NOT EXISTS pending (url TEXT PRIMARY KEY, attempt_id TEXT NOT NULL, message_id TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")

    def __enter__(self) -> "DeliveryState":
        return self

    def __exit__(self, *args: object) -> None:
        self.connection.close()

    def message_id(self, url: str) -> str | None:
        row = self.connection.execute("SELECT message_id FROM sent WHERE url = ?", (url,)).fetchone()
        return row[0] if row else None

    def is_sent(self, url: str) -> bool:
        return self.message_id(url) is not None

    def is_pending(self, url: str) -> bool:
        return self.connection.execute("SELECT 1 FROM pending WHERE url = ?", (url,)).fetchone() is not None

    def pending_message_id(self, url: str) -> str | None:
        row = self.connection.execute("SELECT message_id FROM pending WHERE url = ?", (url,)).fetchone()
        return row[0] if row else None

    def begin_attempt(self, urls: list[str], attempt_id: str) -> None:
        if not attempt_id.strip() or not urls or len(set(urls)) != len(urls) or any(not u for u in urls):
            raise ValueError("attempt ID and distinct URLs required")
        with self.connection:
            self.connection.execute("BEGIN IMMEDIATE")
            for url in urls:
                if self.is_sent(url):
                    raise ValueError("URL already sent")
                if self.connection.execute("SELECT 1 FROM pending WHERE url = ?", (url,)).fetchone():
                    raise ValueError("URL has pending delivery; reconcile before retry")
            self.connection.executemany("INSERT INTO pending(url, attempt_id) VALUES (?, ?)",
                                        [(url, attempt_id) for url in urls])

    def record_provider_acceptance(self, urls: list[str], attempt_id: str, message_id: str) -> None:
        if not message_id.strip() or not urls:
            raise ValueError("provider message ID and URLs required")
        with self.connection:
            self.connection.execute("BEGIN IMMEDIATE")
            for url in urls:
                row = self.connection.execute("SELECT attempt_id, message_id FROM pending WHERE url = ?", (url,)).fetchone()
                if not row or row[0] != attempt_id or (row[1] and row[1] != message_id):
                    raise ValueError("pending attempt mismatch")
            self.connection.executemany("UPDATE pending SET message_id = ? WHERE url = ?",
                                        [(message_id, url) for url in urls])

    def confirm_delivery(self, urls: list[str], attempt_id: str, message_id: str) -> None:
        if not message_id.strip() or not urls:
            raise ValueError("verified message ID and URLs required")
        with self.connection:
            self.connection.execute("BEGIN IMMEDIATE")
            for url in urls:
                row = self.connection.execute("SELECT attempt_id, message_id FROM pending WHERE url = ?", (url,)).fetchone()
                if not row or row != (attempt_id, message_id):
                    raise ValueError("pending message ID does not match verification")
            self.connection.executemany("INSERT INTO sent(url, message_id) VALUES (?, ?)",
                                        [(url, message_id) for url in urls])
            self.connection.executemany("DELETE FROM pending WHERE url = ?", [(url,) for url in urls])

    def record_delivery(self, urls: list[str], message_id: str) -> None:
        if not message_id.strip():
            raise ValueError("verified message ID required")
        if not urls or any(not url for url in urls):
            raise ValueError("at least one valid URL required")
        with self.connection:
            self.connection.executemany("INSERT OR IGNORE INTO sent(url, message_id) VALUES (?, ?)",
                                        [(url, message_id) for url in urls])
