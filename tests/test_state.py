import pytest

from ai_daily_briefing.state import DeliveryState


def test_pending_attempt_blocks_blind_retry_and_moves_to_sent_only_after_confirmation(tmp_path):
    path = tmp_path / "state.sqlite3"
    urls = ["https://example.org/paper", "https://example.org/news"]
    with DeliveryState(path) as state:
        state.begin_attempt(urls, "attempt-1")
        with pytest.raises(ValueError, match="pending"):
            state.begin_attempt(urls, "attempt-2")
        assert all(not state.is_sent(url) for url in urls)
        state.record_provider_acceptance(urls, "attempt-1", "gmail-123")
        with pytest.raises(ValueError, match="message ID"):
            state.confirm_delivery(urls, "attempt-1", "gmail-wrong")
        assert all(not state.is_sent(url) for url in urls)
    with DeliveryState(path) as state:
        assert state.pending_message_id(urls[0]) == "gmail-123"
        state.confirm_delivery(urls, "attempt-1", "gmail-123")
        assert all(state.message_id(url) == "gmail-123" for url in urls)
        with pytest.raises(ValueError, match="sent"):
            state.begin_attempt(urls, "attempt-3")


def test_failed_delivery_does_not_mark_items_sent(tmp_path):
    with DeliveryState(tmp_path / "state.sqlite3") as state:
        assert not state.is_sent("https://example.org/story")
        try:
            state.record_delivery(["https://example.org/story"], "")
        except ValueError:
            pass
        else:
            raise AssertionError("empty provider message ID accepted")
        assert not state.is_sent("https://example.org/story")
        state.record_delivery(["https://example.org/story"], "gmail-message-1")
        assert state.is_sent("https://example.org/story")
        assert state.message_id("https://example.org/story") == "gmail-message-1"
