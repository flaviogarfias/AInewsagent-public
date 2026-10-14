"""Fail-closed delivery transaction around an injected provider transport."""

from __future__ import annotations

from typing import Callable
from uuid import uuid4

from .delivery_bundle import DeliveryBundle
from .delivery_contract import build_email, verify_sent_email
from .state import DeliveryState


def deliver_once(state: DeliveryState, urls: list[str], bundle: DeliveryBundle,
                 sender: str, recipient: str, subject: str, *,
                 stage: Callable[[str, bytes], dict],
                 send: Callable[[dict], str],
                 fetch: Callable[[str, dict], dict]) -> str:
    """Send once; uncertainty leaves durable pending records for reconciliation.

    Fetch must retrieve the exact sent message and original attachment bytes, not
    a provider success flag. No automatic retry is permitted after uncertainty.
    """
    if not urls or len(set(urls)) != len(urls) or any(not url for url in urls):
        raise ValueError("distinct content URLs required")
    for url in urls:
        if state.is_sent(url):
            raise ValueError("URL already sent")
        if state.is_pending(url):
            raise ValueError("URL has pending delivery; reconcile before retry")
    expected = build_email(bundle, sender, recipient, subject)
    staged = stage(bundle.pdf_name, bundle.pdf_bytes)
    if (not isinstance(staged, dict) or staged.get("name") != bundle.pdf_name or
            staged.get("mimetype") != "application/pdf" or not staged.get("s3key")):
        raise ValueError("PDF staging returned invalid file reference")
    attempt_id = uuid4().hex
    state.begin_attempt(urls, attempt_id)
    outgoing = {**expected, "attachment": staged}
    message_id = send(outgoing)
    if not isinstance(message_id, str) or not message_id.strip():
        raise ValueError("provider message ID missing; delivery is uncertain")
    state.record_provider_acceptance(urls, attempt_id, message_id)
    observed = fetch(message_id, expected)
    confirmed_id = verify_sent_email(expected, observed)
    if confirmed_id != message_id:
        raise ValueError("readback message ID differs from provider response")
    state.confirm_delivery(urls, attempt_id, confirmed_id)
    return confirmed_id
