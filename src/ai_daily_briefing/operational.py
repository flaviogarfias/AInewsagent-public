"""Single-run control plane; scheduled and outbound use remain opt-in."""
from __future__ import annotations

from pathlib import Path
from collections.abc import Callable

from .cli import collect_configured_diagnostics
from .configuration import validate_delivery_targets
from .runtime import run_configured_dry_run
from .platform_delivery import deliver_with_stable_connections
from .slack_status import post_status_once


def run_once(config: dict, workdir: str | Path, *, deliver: bool = False,
             collect: Callable = collect_configured_diagnostics,
             evaluate: Callable | None = None, connect: Callable | None = None,
             notify: Callable = post_status_once, now: str | None = None) -> dict:
    """Run a dry-run, optionally deliver only with BOTH gates and healthy output."""
    if deliver and config.get("delivery", {}).get("send_enabled") is not True:
        raise ValueError("delivery disabled")
    if deliver:
        errors = validate_delivery_targets(config["delivery"])
        if errors:
            raise ValueError("; ".join(errors))
    kwargs = {"collect": collect, "now": now}
    if evaluate is not None:
        kwargs["evaluate"] = evaluate
    prepared = run_configured_dry_run(config, workdir, **kwargs)
    if not deliver:
        return prepared
    if connect is None:
        raise ValueError("stable Platform connection required")
    transport = connect()
    if prepared["status"] != "dry-run" or prepared["source_errors"]:
        notify(transport["client"], config["delivery"]["slack_channel_id"],
               transport["channel_name"], prepared["run_id"], "failed" if
               prepared["source_errors"] else prepared["status"],
               len(prepared["items"]), prepared["source_errors"], workdir)
        return prepared
    message_id = deliver_with_stable_connections(config, prepared, workdir,
                                                  **transport)
    notify(transport["client"], config["delivery"]["slack_channel_id"],
           transport["channel_name"], prepared["run_id"], "sent",
           len(prepared["items"]), prepared["source_errors"], workdir)
    return {**prepared, "delivery_message_id": message_id, "status": "sent"}
