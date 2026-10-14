import pytest
from ai_daily_briefing.platform_delivery import deliver_with_stable_connections
from ai_daily_briefing.state import DeliveryState


def test_platform_delivery_disabled_never_touches_connections_or_upload(tmp_path):
    prepared = {"status": "dry-run", "items": [], "artifacts": {}}
    with pytest.raises(ValueError, match="disabled"):
        deliver_with_stable_connections(
            {"delivery": {"send_enabled": False}}, prepared, tmp_path,
            client=None, channel_name="briefing-updates", subject="AI briefing",
            request_upload=lambda *a: pytest.fail("uploaded"),
            put_bytes=lambda *a: pytest.fail("uploaded"),
            download=lambda *a: pytest.fail("downloaded"))


def test_platform_delivery_wires_stable_account_and_confirms_original_pdf(tmp_path):
    from base64 import urlsafe_b64encode
    html = tmp_path / "report.html"
    pdf = tmp_path / "report.pdf"
    html.write_text("<!doctype html><p>AI briefing</p>")
    pdf.write_bytes(b"%PDF-real-original")
    prepared = {"status": "dry-run", "source_errors": 0,
                "items": [{"kind": "news", "url": "https://example.org/story"}],
                "artifacts": {"html": html, "pdf": pdf}}
    config = {"delivery": {"send_enabled": True, "sender": "agent@example.org",
                           "recipient": "person@example.org", "slack_channel_id": "C0123"}}
    slugs = []
    class Client:
        def execute(self, toolkit, slug, args):
            slugs.append((toolkit, slug))
            if slug == "GMAIL_GET_PROFILE":
                return {"successful": True, "data": {"emailAddress": "agent@example.org"}}
            if slug == "SLACK_RETRIEVE_CONVERSATION_INFORMATION":
                return {"successful": True, "data": {"ok": True, "channel": {
                    "id": "C0123", "name": "briefing-updates", "is_member": True}}}
            if slug == "GMAIL_SEND_EMAIL":
                assert args["attachment"]["s3key"] == "stored"
                return {"successful": True, "data": {"id": "gmail-123"}}
            if slug == "GMAIL_FETCH_MESSAGE_BY_MESSAGE_ID":
                return {"successful": True, "data": {"messageId": "gmail-123", "labelIds": ["SENT"],
                    "attachmentList": [{"filename": "report.pdf", "attachmentId": "att-1"}],
                    "payload": {"headers": [
                        {"name": "From", "value": "agent@example.org"},
                        {"name": "To", "value": "person@example.org"},
                        {"name": "Subject", "value": "AI briefing"}],
                        "parts": [{"mimeType": "text/html", "body": {"data":
                            urlsafe_b64encode(html.read_bytes()).decode()}}]}}}
            if slug == "GMAIL_GET_ATTACHMENT":
                return {"successful": True, "data": {"file": {"name": "report.pdf",
                    "s3url": "https://bucket.r2.cloudflarestorage.com/attachment"}}}
            pytest.fail(f"Unexpected tool: {slug}")
    message_id = deliver_with_stable_connections(config, prepared, tmp_path,
        client=Client(), channel_name="briefing-updates", subject="AI briefing",
        request_upload=lambda _: {"type": "existing", "key": "stored"},
        put_bytes=lambda *a: pytest.fail("existing file re-uploaded"),
        download=lambda url: pdf.read_bytes())
    assert message_id == "gmail-123"
    assert slugs[:2] == [("gmail", "GMAIL_GET_PROFILE"),
                         ("slack", "SLACK_RETRIEVE_CONVERSATION_INFORMATION")]
    assert ("gmail", "GMAIL_SEND_EMAIL") in slugs
    with DeliveryState(tmp_path / "state.sqlite3") as state:
        assert state.message_id("https://example.org/story") == message_id


def test_platform_delivery_requires_matching_stable_identities_before_upload(tmp_path):
    class Client:
        def execute(self, toolkit, slug, arguments):
            if toolkit == "gmail":
                return {"data": {"emailAddress": "someone-else@example.org"}}
            pytest.fail("Slack preflight reached after Gmail mismatch")
    config = {"delivery": {"send_enabled": True, "sender": "agent@example.org",
                           "recipient": "person@example.org", "slack_channel_id": "C0123"}}
    with pytest.raises(ValueError, match="Gmail connection"):
        deliver_with_stable_connections(config, {"status": "dry-run", "source_errors": 0},
            tmp_path, client=Client(), channel_name="briefing-updates", subject="AI briefing",
            request_upload=lambda *a: pytest.fail("uploaded"),
            put_bytes=lambda *a: pytest.fail("uploaded"),
            download=lambda *a: pytest.fail("downloaded"))
    with DeliveryState(tmp_path / "state.sqlite3") as state:
        assert state.connection.execute("SELECT COUNT(*) FROM sent").fetchone()[0] == 0
