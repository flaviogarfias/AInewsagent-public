import pytest

from ai_daily_briefing.delivery_bundle import DeliveryBundle
from ai_daily_briefing.delivery_service import deliver_once
from ai_daily_briefing.state import DeliveryState


def _bundle():
    return DeliveryBundle("<!doctype html><p>Verified briefing</p>", b"%PDF-tested", "report.pdf", "unused", "unused")


def _observed(payload, message_id, *, body=None):
    return {"message_id": message_id, "label_ids": ["SENT"],
            "from_email": payload["from_email"], "recipient_email": payload["recipient_email"],
            "subject": payload["subject"], "html_body": payload["body"] if body is None else body,
            "pdf_name": payload["attachment"]["name"], "pdf_bytes": b"%PDF-tested"}


def test_deliver_once_marks_sent_only_after_exact_readback(tmp_path):
    calls = []
    url = "https://example.org/paper"
    with DeliveryState(tmp_path / "state.sqlite3") as state:
        def stage(name, data):
            calls.append("stage")
            assert data == b"%PDF-tested"
            return {"name": name, "mimetype": "application/pdf", "s3key": "stored-original"}

        def send(payload):
            calls.append("send")
            assert payload["attachment"]["s3key"] == "stored-original"
            assert "data" not in payload["attachment"]
            assert not state.is_sent(url)
            return "gmail-123"

        def fetch(message_id, payload):
            calls.append("readback")
            assert not state.is_sent(url)
            return _observed(payload, message_id)

        result = deliver_once(state, [url], _bundle(), "agent@example.org", "person@example.org",
                              "AI briefing", stage=stage, send=send, fetch=fetch)
        assert result == "gmail-123"
        assert state.message_id(url) == "gmail-123"
        assert calls == ["stage", "send", "readback"]
        with pytest.raises(ValueError, match="sent"):
            deliver_once(state, [url], _bundle(), "agent@example.org", "person@example.org",
                         "AI briefing", stage=stage, send=send, fetch=fetch)
        assert calls == ["stage", "send", "readback"]


def test_failed_readback_keeps_attempt_pending_and_blocks_retry(tmp_path):
    url = "https://example.org/news"
    with DeliveryState(tmp_path / "state.sqlite3") as state:
        stage = lambda name, data: {"name": name, "mimetype": "application/pdf", "s3key": "stored"}
        send = lambda payload: "gmail-123"
        fetch = lambda mid, payload: _observed(payload, mid, body="tampered")
        with pytest.raises(ValueError, match="HTML differs"):
            deliver_once(state, [url], _bundle(), "agent@example.org", "person@example.org",
                         "AI briefing", stage=stage, send=send, fetch=fetch)
        assert not state.is_sent(url)
        assert state.pending_message_id(url) == "gmail-123"
        with pytest.raises(ValueError, match="pending"):
            deliver_once(state, [url], _bundle(), "agent@example.org", "person@example.org",
                         "AI briefing", stage=stage, send=send, fetch=fetch)


def test_send_exception_never_marks_sent_and_blocks_blind_retry(tmp_path):
    url = "https://example.org/news"
    with DeliveryState(tmp_path / "state.sqlite3") as state:
        def uncertain_send(payload):
            raise TimeoutError("provider response lost")
        with pytest.raises(TimeoutError):
            deliver_once(state, [url], _bundle(), "agent@example.org", "person@example.org",
                         "AI briefing", stage=lambda n, d: {"name": n, "mimetype": "application/pdf", "s3key": "stored"},
                         send=uncertain_send, fetch=lambda mid, payload: {})
        assert not state.is_sent(url)
        with pytest.raises(ValueError, match="pending"):
            state.begin_attempt([url], "retry")
