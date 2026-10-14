from base64 import urlsafe_b64encode

import pytest

from ai_daily_briefing.composio_transport import ComposioTransport


def _enc(value):
    return urlsafe_b64encode(value.encode()).decode().rstrip("=")


def test_send_explicit_contract_and_extracts_provider_id():
    calls = []

    def execute(slug, args):
        calls.append((slug, args))
        return {"successful": True, "data": {"id": "gmail-123"}}

    client = ComposioTransport(execute=execute, download=lambda url: b"")
    payload = {"from_email": "agent@example.org", "recipient_email": "person@example.org",
               "subject": "Briefing", "body": "<b>Test</b>", "is_html": True,
               "attachment": {"name": "report.pdf", "mimetype": "application/pdf", "s3key": "stored"}}
    assert client.send(payload) == "gmail-123"
    assert calls == [("GMAIL_SEND_EMAIL", {**payload, "user_id": "me"})]


def test_fetch_reconstructs_html_headers_and_original_attachment_bytes():
    calls = []
    pdf = b"%PDF-exact-original"

    def execute(slug, args):
        calls.append((slug, args))
        if slug == "GMAIL_FETCH_MESSAGE_BY_MESSAGE_ID":
            return {"successful": True, "data": {
                "messageId": "gmail-123", "labelIds": ["SENT"],
                "payload": {"headers": [
                    {"name": "From", "value": "Agent <agent@example.org>"},
                    {"name": "To", "value": "person@example.org"},
                    {"name": "Subject", "value": "Briefing"}],
                    "parts": [{"mimeType": "multipart/alternative", "parts": [
                        {"mimeType": "text/html", "body": {"data": _enc("<b>Test</b>")}}]}]},
                "attachmentList": [{"attachmentId": "attachment-1", "filename": "report.pdf"}]}}
        return {"successful": True, "data": {"file": {
            "name": "report.pdf", "s3url": "https://temp.account.r2.cloudflarestorage.com/file?token=hidden"}}}

    client = ComposioTransport(execute=execute, download=lambda url: pdf)
    expected = {"attachment": {"name": "report.pdf"}}
    observed = client.fetch("gmail-123", expected)
    assert observed == {"message_id": "gmail-123", "label_ids": ["SENT"],
                        "from_email": "agent@example.org", "recipient_email": "person@example.org",
                        "subject": "Briefing", "html_body": "<b>Test</b>",
                        "pdf_name": "report.pdf", "pdf_bytes": pdf}
    assert calls[0] == ("GMAIL_FETCH_MESSAGE_BY_MESSAGE_ID",
                        {"message_id": "gmail-123", "format": "full", "user_id": "me"})
    assert calls[1] == ("GMAIL_GET_ATTACHMENT", {"message_id": "gmail-123",
                      "attachment_id": "attachment-1", "file_name": "report.pdf", "user_id": "me"})


def test_fetch_refuses_wrong_or_unsafe_attachment():
    client = ComposioTransport(execute=lambda slug, args: {"successful": True, "data": {
        "messageId": "gmail-123", "labelIds": ["SENT"], "payload": {"headers": [],
        "parts": [{"mimeType": "text/html", "body": {"data": _enc("<b>Test</b>")}}]},
        "attachmentList": []}}, download=lambda url: b"unexpected")
    with pytest.raises(ValueError, match="attachment"):
        client.fetch("gmail-123", {"attachment": {"name": "report.pdf"}})
