import pytest
from ai_daily_briefing.slack_status import post_status_once


class FakeClient:
    def __init__(self):
        self.calls = []
    def execute(self, toolkit, slug, args):
        self.calls.append((toolkit, slug, args))
        if slug == "SLACK_RETRIEVE_CONVERSATION_INFORMATION":
            return {"successful": True, "data": {"ok": True, "channel": {
                "id": "C123", "name": "briefing-updates", "is_member": True}}}
        if slug == "SLACK_CHAT_POST_MESSAGE":
            self.text = args["text"]
            return {"successful": True, "data": {"ok": True, "channel": "C123", "ts": "1234.5678"}}
        if slug == "SLACK_FETCH_CONVERSATION_HISTORY":
            return {"successful": True, "data": {"ok": True,
                "messages": [{"ts": "1234.5678", "text": self.text}]}}
        pytest.fail(f"unexpected slug {slug}")


def test_slack_operational_status_is_verified_once(tmp_path):
    client = FakeClient()
    result = post_status_once(client, "C123", "briefing-updates", "run-1",
                              "no-news", 0, 0, tmp_path)
    assert result == "1234.5678"
    assert [slug for _, slug, _ in client.calls] == [
        "SLACK_RETRIEVE_CONVERSATION_INFORMATION", "SLACK_CHAT_POST_MESSAGE",
        "SLACK_FETCH_CONVERSATION_HISTORY"]
    with pytest.raises(ValueError, match="already attempted"):
        post_status_once(client, "C123", "briefing-updates", "run-1", "no-news", 0, 0, tmp_path)
    assert len(client.calls) == 3


def test_slack_uncertain_send_is_not_retried(tmp_path):
    class Uncertain(FakeClient):
        def execute(self, toolkit, slug, args):
            if slug == "SLACK_CHAT_POST_MESSAGE":
                raise OSError("network response lost")
            return super().execute(toolkit, slug, args)
    client = Uncertain()
    with pytest.raises(OSError):
        post_status_once(client, "C123", "briefing-updates", "run-2", "failed", 0, 1, tmp_path)
    with pytest.raises(ValueError, match="already attempted"):
        post_status_once(client, "C123", "briefing-updates", "run-2", "failed", 0, 1, tmp_path)
