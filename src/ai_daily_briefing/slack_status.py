"""Idempotent Slack operational status; uncertain posts remain pending."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from .platform_client import PlatformClient


def post_status_once(client: PlatformClient, channel_id: str, channel_name: str,
                     run_id: str, status: str, selected: int, source_errors: int,
                     workdir: str | Path) -> str:
    """Post one verified status per run; never blindly retry uncertain posts."""
    if status not in {"sent", "no-news", "failed"} or not run_id or selected < 0 or source_errors < 0:
        raise ValueError("invalid operational status")
    path = Path(workdir) / "slack-status.sqlite3"
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE IF NOT EXISTS posts (run_id TEXT PRIMARY KEY, status TEXT NOT NULL, ts TEXT)")
        if db.execute("SELECT 1 FROM posts WHERE run_id=?", (run_id,)).fetchone():
            raise ValueError("Slack status already attempted; reconcile before retry")
    info = client.execute("slack", "SLACK_RETRIEVE_CONVERSATION_INFORMATION",
                          {"channel": channel_id})
    data = info.get("data") or {}
    channel = data.get("channel") or {}
    if (not data.get("ok") or channel.get("id") != channel_id or
            channel.get("name") != channel_name or not channel.get("is_member")):
        raise ValueError("Slack channel identity mismatch")
    text = (f"Resumen IA | corrida {run_id} | estado: {status} | "
            f"seleccionados: {selected} | errores de fuente: {source_errors}")
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE IF NOT EXISTS posts (run_id TEXT PRIMARY KEY, status TEXT NOT NULL, ts TEXT)")
        try:
            with db:
                db.execute("INSERT INTO posts(run_id, status) VALUES (?, 'attempting')", (run_id,))
        except sqlite3.IntegrityError:
            raise ValueError("Slack status already attempted; reconcile before retry") from None
        sent = client.execute("slack", "SLACK_CHAT_POST_MESSAGE",
                              {"channel": channel_id, "text": text,
                               "mrkdwn": False, "unfurl_links": False, "unfurl_media": False})
        response = sent.get("data") or {}
        ts = response.get("ts")
        if not response.get("ok") or response.get("channel") != channel_id or not ts:
            raise ValueError("Slack post acceptance uncertain")
        history = client.execute("slack", "SLACK_FETCH_CONVERSATION_HISTORY",
                                 {"channel": channel_id, "limit": 100})
        observed = history.get("data") or {}
        if (not observed.get("ok") or not any(
                item.get("ts") == ts and item.get("text") == text
                for item in observed.get("messages") or [])):
            raise ValueError("Slack status readback uncertain")
        with db:
            db.execute("UPDATE posts SET status='verified', ts=? WHERE run_id=?", (ts, run_id))
        return ts
