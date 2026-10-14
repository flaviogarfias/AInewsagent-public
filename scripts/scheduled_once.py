"""Guarded scheduled entrypoint; creating a cron job is a separate decision."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ai_daily_briefing.configuration import validate_configuration
from ai_daily_briefing.operational import run_once
from ai_daily_briefing.scheduled import run_scheduled
from scripts.run_once import ROOT, _connect


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run only inside the daily dispatch window")
    parser.add_argument("config", type=Path)
    parser.add_argument("--workdir", type=Path, default=ROOT / "var")
    args = parser.parse_args(argv)
    config = json.loads(args.config.read_text(encoding="utf-8"))
    errors = validate_configuration(config)
    if errors:
        parser.error("; ".join(errors))
    result = run_scheduled(config, args.workdir,
                           execute=lambda settings, workdir, deliver:
                               run_once(settings, workdir, deliver=deliver,
                                        connect=lambda: _connect(settings)))
    payload = {"status": result["status"]}
    if "run_id" in result:
        payload.update(run_id=result["run_id"], selected=len(result["items"]),
                       source_errors=result["source_errors"],
                       delivery_message_id=result.get("delivery_message_id"))
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
