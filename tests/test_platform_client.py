import pytest

from ai_daily_briefing.platform_client import PlatformClient, verify_stable_connections


def test_platform_client_routes_gmail_tool_to_stable_account_only():
    calls = []

    def request(path, payload=None):
        calls.append((path, payload))
        if path.startswith("connected_accounts?"):
            return {"items": [
                {"id": "ca_playground", "user_id": "pg-test-123", "status": "ACTIVE",
                 "toolkit": {"slug": "gmail"}},
                {"id": "ca_stable", "user_id": "briefing_owner_123", "status": "ACTIVE",
                 "is_disabled": False, "toolkit": {"slug": "gmail"}},
            ], "next_cursor": None}
        return {"successful": True, "data": {"emailAddress": "owner@example.org"},
                "log_id": "log_123"}

    client = PlatformClient("briefing_owner_123", request=request)
    result = client.execute("gmail", "GMAIL_GET_PROFILE", {"user_id": "me"})
    assert result["data"]["emailAddress"] == "owner@example.org"
    assert calls[-1] == ("tools/execute/GMAIL_GET_PROFILE", {
        "connected_account_id": "ca_stable", "user_id": "briefing_owner_123",
        "arguments": {"user_id": "me"}})


def test_platform_client_paginates_before_selecting_connection():
    calls = []

    def request(path, payload=None):
        calls.append(path)
        if path.startswith("connected_accounts?"):
            if "cursor=second" in path:
                return {"items": [{"id": "ca_real", "user_id": "owner_123",
                                   "status": "ACTIVE", "toolkit": {"slug": "slack"}}],
                        "next_cursor": None}
            return {"items": [], "next_cursor": "second"}
        return {"successful": True, "data": {"ok": True}}

    client = PlatformClient("owner_123", request=request)
    assert client.execute("slack", "SLACK_TEST_AUTH", {})["data"]["ok"]
    assert any("cursor=second" in path for path in calls)
    assert calls[-1] == "tools/execute/SLACK_TEST_AUTH"


def test_verify_stable_connections_checks_sender_and_channel_without_sending():
    called = []

    class FakeClient:
        def execute(self, toolkit, slug, arguments):
            called.append((toolkit, slug, arguments))
            if toolkit == "gmail":
                return {"successful": True, "data": {"emailAddress": "owner@example.org"},
                        "log_id": "log_gmail"}
            return {"successful": True, "data": {"ok": True, "channel": {
                "id": "C123", "name": "briefing-updates", "is_member": True}},
                "log_id": "log_slack"}

    result = verify_stable_connections(FakeClient(), "owner@example.org", "C123",
                                       "briefing-updates")
    assert result == {"gmail_log_id": "log_gmail", "slack_log_id": "log_slack"}
    assert called == [("gmail", "GMAIL_GET_PROFILE", {"user_id": "me"}),
                      ("slack", "SLACK_RETRIEVE_CONVERSATION_INFORMATION", {"channel": "C123"})]
