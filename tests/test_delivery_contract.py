from hashlib import sha256

import pytest

from ai_daily_briefing.artifacts import write_report_artifacts
from ai_daily_briefing.delivery_bundle import prepare_delivery_bundle
from ai_daily_briefing.delivery_contract import build_email, verify_sent_email


def _bundle(tmp_path):
    paths = write_report_artifacts({"generated_at": "2026-10-03T07:00:00-06:00", "items": [
        {"kind": "news", "title": "LLM infrastructure", "url": "https://example.org/news",
         "summary": "Measured capacity increase.", "traffic_light": "yellow",
         "source": "Primary", "published": "2026-10-03"}]}, tmp_path)
    return prepare_delivery_bundle(paths)


def test_email_contract_uses_exact_artifact_bytes_and_explicit_destinations(tmp_path):
    bundle = _bundle(tmp_path)
    payload = build_email(bundle, sender="agent@example.org", recipient="person@example.org",
                          subject="AI briefing test")
    assert payload["from_email"] == "agent@example.org"
    assert payload["recipient_email"] == "person@example.org"
    assert payload["subject"] == "AI briefing test"
    assert payload["is_html"] is True
    assert payload["body"] == bundle.html_body
    assert payload["attachment"]["data"] == bundle.pdf_bytes
    assert payload["attachment"]["mimetype"] == "application/pdf"


def test_sent_email_must_match_exact_body_and_pdf_hash(tmp_path):
    bundle = _bundle(tmp_path)
    payload = build_email(bundle, "agent@example.org", "person@example.org", "AI briefing test")
    observed = {"message_id": "gmail-123", "label_ids": ["SENT"],
                "from_email": payload["from_email"], "recipient_email": payload["recipient_email"],
                "subject": payload["subject"], "html_body": payload["body"],
                "pdf_name": payload["attachment"]["name"],
                "pdf_bytes": payload["attachment"]["data"]}
    assert verify_sent_email(payload, observed) == "gmail-123"
    assert sha256(observed["pdf_bytes"]).hexdigest() == bundle.pdf_sha256
    with pytest.raises(ValueError, match="PDF differs"):
        verify_sent_email(payload, {**observed, "pdf_bytes": b"%PDF-other"})


def test_sent_email_allows_only_one_transport_appended_terminal_newline(tmp_path):
    bundle = _bundle(tmp_path)
    payload = build_email(bundle, "agent@example.org", "person@example.org", "AI briefing test")
    base = {"message_id": "gmail-123", "label_ids": ["SENT"],
            "from_email": payload["from_email"], "recipient_email": payload["recipient_email"],
            "subject": payload["subject"], "pdf_name": bundle.pdf_name,
            "pdf_bytes": bundle.pdf_bytes}
    assert verify_sent_email(payload, {**base, "html_body": payload["body"] + "\n"}) == "gmail-123"
    with pytest.raises(ValueError, match="HTML differs"):
        verify_sent_email(payload, {**base, "html_body": payload["body"] + "\n\n"})


def test_sent_label_alone_cannot_validate_delivery(tmp_path):
    bundle = _bundle(tmp_path)
    payload = build_email(bundle, "agent@example.org", "person@example.org", "AI briefing test")
    with pytest.raises(ValueError, match="HTML differs"):
        verify_sent_email(payload, {"message_id": "gmail-123", "label_ids": ["SENT"],
                                    "from_email": "agent@example.org", "recipient_email": "person@example.org",
                                    "subject": "AI briefing test", "html_body": "other",
                                    "pdf_name": bundle.pdf_name, "pdf_bytes": bundle.pdf_bytes})
