"""Fail-closed daily dispatch guard; scheduler activation is a separate operation."""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .configuration import validate_delivery_targets
from .operational import run_once
from .schedule import in_dispatch_window


def run_scheduled(config: dict, workdir: str | Path, *, at: datetime | None = None,
                  execute=run_once) -> dict:
    """Only one attempt per local day, including failures needing reconciliation."""
    if config.get("delivery", {}).get("send_enabled") is not True:
        return {"status": "disabled"}
    schedule = config["schedule"]
    zone = ZoneInfo(schedule["timezone"])
    if at is None:
        at = datetime.now(zone)
    if not in_dispatch_window(schedule, at):
        return {"status": "outside-window"}
    errors = validate_delivery_targets(config["delivery"])
    if errors:
        raise ValueError("; ".join(errors))
    local_day = at.astimezone(zone).date().isoformat()
    directory = Path(workdir) / "scheduled-attempts"
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    marker = directory / f"{local_day}.json"
    try:
        fd = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return {"status": "already-attempted"}
    with os.fdopen(fd, "w", encoding="utf-8") as file:
        json.dump({"date": local_day, "status": "attempting"}, file)
        file.write("\n")
    result = execute(config, workdir, deliver=True)
    if result.get("status") not in {"sent", "no-news", "failed"} or not result.get("run_id"):
        raise ValueError("scheduled run returned an unverified state")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=directory,
                                         prefix=".result-", delete=False) as file:
            temporary = Path(file.name)
            json.dump({"date": local_day, "status": result["status"],
                       "run_id": result["run_id"]}, file)
            file.write("\n")
        os.replace(temporary, marker)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return result
