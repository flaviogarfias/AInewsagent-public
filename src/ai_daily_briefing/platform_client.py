"""Bind Composio Platform tool execution to a stable application user."""
from __future__ import annotations

from collections.abc import Callable
from urllib.parse import urlencode


class PlatformClient:
    def __init__(self, user_id: str, *, request: Callable[[str, dict | None], dict]):
        if not user_id or user_id.startswith("pg-test-"):
            raise ValueError("stable application user ID required")
        self.user_id = user_id
        self.request = request

    def execute(self, toolkit: str, slug: str, arguments: dict) -> dict:
        if toolkit not in {"gmail", "slack"} or not slug.startswith(toolkit.upper() + "_"):
            raise ValueError("tool slug and toolkit differ")
        path = "connected_accounts?" + urlencode({"limit": 100, "user_ids": self.user_id})
        accounts = []
        cursors = set()
        for _ in range(20):
            response = self.request(path, None)
            accounts.extend(item for item in response["items"] if
                            item.get("user_id") == self.user_id and
                            (item.get("toolkit") or {}).get("slug") == toolkit and
                            item.get("status") == "ACTIVE" and not item.get("is_disabled"))
            cursor = response.get("next_cursor")
            if not cursor:
                break
            if cursor in cursors:
                raise ValueError("repeated account pagination cursor")
            cursors.add(cursor)
            path = "connected_accounts?" + urlencode({"limit": 100, "user_ids": self.user_id,
                                                       "cursor": cursor})
        else:
            raise ValueError("connected account listing exceeded page limit")
        if len(accounts) != 1:
            raise ValueError("exactly one active connected account required")
        result = self.request("tools/execute/" + slug,
                              {"connected_account_id": accounts[0]["id"],
                               "user_id": self.user_id, "arguments": arguments})
        if not result.get("successful"):
            raise ValueError("connected account tool execution failed")
        return result


def verify_stable_connections(client: PlatformClient, sender: str,
                              channel_id: str, channel_name: str) -> dict[str, str]:
    """Read-only identity and channel preflight; never sends a message."""
    gmail = client.execute("gmail", "GMAIL_GET_PROFILE", {"user_id": "me"})
    if (gmail.get("data") or {}).get("emailAddress") != sender:
        raise ValueError("stable Gmail connection does not match configured sender")
    slack = client.execute("slack", "SLACK_RETRIEVE_CONVERSATION_INFORMATION",
                           {"channel": channel_id})
    data = slack.get("data") or {}
    target = data.get("channel") or {}
    if (not data.get("ok") or target.get("id") != channel_id or
            target.get("name") != channel_name or not target.get("is_member")):
        raise ValueError("stable Slack connection does not match configured channel")
    return {"gmail_log_id": gmail.get("log_id"), "slack_log_id": slack.get("log_id")}
