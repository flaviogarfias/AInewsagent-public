"""Create/reuse one stable local Composio user and connect Gmail + Slack.

No email or Slack message is sent. Links are user-facing OAuth entry points.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from uuid import uuid4

from composio import Composio

ROOT = Path(__file__).resolve().parents[1]
IDENTITY_PATH = ROOT / "var/composio-owner-user-id.txt"
REQUIRED = ("gmail", "slack")


def project_key() -> str:
    lines = (ROOT / ".env").read_text().splitlines()
    matches = [line.partition("=")[2].strip() for line in lines
               if line.startswith("COMPOSIO_PROJECT_API_KEY=")]
    if len(matches) != 1 or not matches[0].startswith("ak_") or "=" in matches[0]:
        raise ValueError("exactly one valid project key must exist in the ignored .env file")
    return matches[0]


def stable_user_id() -> str:
    IDENTITY_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not IDENTITY_PATH.exists():
        value = "briefing_owner_" + uuid4().hex
        fd = os.open(IDENTITY_PATH, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(value + "\n")
    value = IDENTITY_PATH.read_text().strip()
    if not value.startswith("briefing_owner_") or len(value) != len("briefing_owner_") + 32:
        raise ValueError("invalid stable owner ID; do not silently replace it")
    return value


def main() -> None:
    config = json.loads((ROOT / "config/briefing.json").read_text())
    if config["delivery"]["send_enabled"]:
        raise ValueError("disable recurring sending before connection setup")
    key = project_key()
    user_id = stable_user_id()
    client = Composio(api_key=key)
    session = client.create(user_id=user_id, toolkits=list(REQUIRED), manage_connections=False)
    toolkits = session.toolkits()
    status = {item.slug: bool(item.connection and item.connection.is_active)
              for item in toolkits.items if item.slug in REQUIRED}
    print(json.dumps({"user_id": user_id,
                      "connected": status}, ensure_ascii=False))
    for slug in REQUIRED:
        if status.get(slug):
            print(json.dumps({"toolkit": slug, "state": "already_connected"}))
            continue
        request = session.authorize(slug)
        url = request.redirect_url
        if not url.startswith("https://connect.composio.dev/"):
            raise ValueError("unexpected Connect Link host")
        print(json.dumps({"toolkit": slug, "state": "awaiting_user_oauth",
                          "connect_link": url}, ensure_ascii=False))


if __name__ == "__main__":
    main()
