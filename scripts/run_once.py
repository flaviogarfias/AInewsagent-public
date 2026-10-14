"""One-shot briefing entrypoint: default no-send; outbound requires two gates.

No cron or automatic notifications are installed by this script.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from ai_daily_briefing.configuration import validate_configuration
from ai_daily_briefing.operational import run_once
from ai_daily_briefing.platform_client import PlatformClient
from ai_daily_briefing.platform_http import PlatformHTTP

ROOT = Path(__file__).resolve().parents[1]


def _project_key() -> str:
    lines = (ROOT / ".env").read_text().splitlines()
    keys = [line.partition("=")[2].strip() for line in lines
            if line.startswith("COMPOSIO_PROJECT_API_KEY=")]
    if len(keys) != 1 or not keys[0].startswith("ak_") or "=" in keys[0]:
        raise ValueError("one bare local Composio project key is required")
    return keys[0]


def _connect(config: dict) -> dict:
    user_id = (ROOT / "var/composio-owner-user-id.txt").read_text().strip()
    http = PlatformHTTP(_project_key())
    client = PlatformClient(user_id, request=http.request)
    date = datetime.now(ZoneInfo(config["schedule"]["timezone"])).strftime("%Y-%m-%d")
    return {"client": client, "channel_name": config["delivery"]["slack_channel_name"],
            "request_upload": lambda payload: http.request("files/upload/request", payload),
            "put_bytes": http.put_pdf, "download": http.download,
            "subject": f"Resumen diario de IA — {date}"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run one audited AI briefing; no send by default")
    parser.add_argument("config", type=Path)
    parser.add_argument("--workdir", type=Path, default=ROOT / "var")
    parser.add_argument("--deliver", action="store_true", help="send only if config also enables delivery")
    args = parser.parse_args(argv)
    config = json.loads(args.config.read_text(encoding="utf-8"))
    errors = validate_configuration(config)
    if errors:
        parser.error("; ".join(errors))
    if args.deliver and config["delivery"].get("send_enabled") is not True:
        raise ValueError("delivery disabled")
    result = run_once(config, args.workdir, deliver=args.deliver,
                      connect=lambda: _connect(config))
    print(json.dumps({"run_id": result["run_id"], "status": result["status"],
                      "selected": len(result["items"]),
                      "source_errors": result["source_errors"],
                      "artifacts": {name: str(path) for name, path in result["artifacts"].items()},
                      "delivery_message_id": result.get("delivery_message_id")},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
