import pytest

from ai_daily_briefing.delivery_runtime import deliver_prepared
from ai_daily_briefing.state import DeliveryState


def _prepared(tmp_path):
    html = tmp_path / "report.html"
    pdf = tmp_path / "report.pdf"
    html.write_text("<!doctype html><p>AI briefing</p>")
    pdf.write_bytes(b"%PDF-tested")
    return {"status": "dry-run", "source_errors": 0,
            "artifacts": {"html": html, "pdf": pdf},
            "items": [{"kind": "paper", "url": "https://example.org/paper"}]}


def test_delivery_runtime_blocks_all_outbound_calls_when_disabled(tmp_path):
    calls = []
    result = _prepared(tmp_path)
    config = {"delivery": {"send_enabled": False, "sender": "agent@example.org",
                           "recipient": "person@example.org"}}
    with pytest.raises(ValueError, match="disabled"):
        deliver_prepared(config, result, tmp_path,
                         stage=lambda *a: calls.append("stage"),
                         send=lambda *a: calls.append("send"),
                         fetch=lambda *a: calls.append("fetch"))
    assert calls == []
    with DeliveryState(tmp_path / "state.sqlite3") as state:
        assert not state.is_pending(result["items"][0]["url"])


def test_delivery_runtime_uses_original_artifacts_once_and_suppresses_repeat(tmp_path):
    result = _prepared(tmp_path)
    calls = []
    config = {"delivery": {"send_enabled": True, "sender": "agent@example.org",
                           "recipient": "person@example.org"}}

    def stage(name, data):
        calls.append("stage")
        assert data == b"%PDF-tested"
        return {"name": name, "mimetype": "application/pdf", "s3key": "stored"}

    def send(payload):
        calls.append("send")
        assert payload["body"] == "<!doctype html><p>AI briefing</p>"
        return "gmail-123"

    def fetch(message_id, payload):
        calls.append("fetch")
        return {"message_id": message_id, "label_ids": ["SENT"],
                "from_email": payload["from_email"],
                "recipient_email": payload["recipient_email"],
                "subject": payload["subject"], "html_body": payload["body"],
                "pdf_name": payload["attachment"]["name"],
                "pdf_bytes": b"%PDF-tested"}

    assert deliver_prepared(config, result, tmp_path, stage=stage, send=send,
                            fetch=fetch, subject="AI briefing") == "gmail-123"
    assert calls == ["stage", "send", "fetch"]
    with DeliveryState(tmp_path / "state.sqlite3") as state:
        assert state.message_id("https://example.org/paper") == "gmail-123"
    with pytest.raises(ValueError, match="sent"):
        deliver_prepared(config, result, tmp_path, stage=stage, send=send,
                         fetch=fetch, subject="AI briefing")
    assert calls == ["stage", "send", "fetch"]


def test_delivery_runtime_refuses_partial_collection_even_with_items(tmp_path):
    result = _prepared(tmp_path)
    result["source_errors"] = 1
    calls = []
    config = {"delivery": {"send_enabled": True, "sender": "agent@example.org",
                           "recipient": "person@example.org"}}
    with pytest.raises(ValueError, match="healthy"):
        deliver_prepared(config, result, tmp_path, stage=lambda *a: calls.append("stage"),
                         send=lambda *a: calls.append("send"),
                         fetch=lambda *a: calls.append("fetch"), subject="AI briefing")
    assert calls == []
