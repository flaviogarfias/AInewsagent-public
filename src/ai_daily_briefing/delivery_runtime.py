"""Explicitly gated transition from prepared report to verified delivery.

Not imported or called by the read-only CLI or scheduler.
"""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from .delivery_bundle import prepare_delivery_bundle, verify_delivery_bundle
from .delivery_service import deliver_once
from .state import DeliveryState


def deliver_prepared(config: dict, prepared: dict, workdir: str | Path, *,
                     stage: Callable[[str, bytes], dict], send: Callable[[dict], str],
                     fetch: Callable[[str, dict], dict], subject: str = "") -> str:
    """Deliver a healthy prepared report once, with no implied retries."""
    delivery = config["delivery"]
    if delivery.get("send_enabled") is not True:
        raise ValueError("delivery disabled")
    if prepared.get("status") != "dry-run" or prepared.get("source_errors") != 0:
        raise ValueError("only a healthy prepared report may be delivered")
    items = prepared.get("items") or []
    if not 1 <= len(items) <= 2 or len(set(i.get("kind") for i in items)) != len(items):
        raise ValueError("expected at most one paper and one news item")
    if not subject.strip():
        raise ValueError("explicit delivery subject required")
    bundle = prepare_delivery_bundle(prepared["artifacts"])
    verify_delivery_bundle(bundle, prepared["artifacts"])
    with DeliveryState(Path(workdir) / "state.sqlite3") as state:
        return deliver_once(state, [item["url"] for item in items], bundle,
                            delivery["sender"], delivery["recipient"], subject,
                            stage=stage, send=send, fetch=fetch)
