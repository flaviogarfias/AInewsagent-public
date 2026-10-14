"""Provider-neutral contract for exact email body and PDF verification."""

from __future__ import annotations

from hashlib import sha256

from .delivery_bundle import DeliveryBundle


def build_email(bundle: DeliveryBundle, sender: str, recipient: str, subject: str) -> dict:
    """Describe one email from already-rendered bytes; perform no send."""
    if not sender or not recipient or not subject.strip():
        raise ValueError("sender, recipient and subject are required")
    return {"from_email": sender, "recipient_email": recipient, "subject": subject,
            "body": bundle.html_body, "is_html": True,
            "attachment": {"name": bundle.pdf_name, "mimetype": "application/pdf",
                           "data": bundle.pdf_bytes}}


def verify_sent_email(expected: dict, observed: dict) -> str:
    """Validate sender-side Sent copy; recipient arrival is a separate check."""
    message_id = observed.get("message_id", "")
    if not isinstance(message_id, str) or not message_id.strip() or "SENT" not in observed.get("label_ids", []):
        raise ValueError("Gmail Sent copy not confirmed")
    for field in ("from_email", "recipient_email", "subject"):
        if observed.get(field) != expected[field]:
            raise ValueError(f"{field} differs from prepared email")
    # Composio/Gmail appends exactly one terminal LF to HTML MIME bodies.
    # Preserve all other bytes; do not normalize arbitrary whitespace or markup.
    actual_html = observed.get("html_body")
    if actual_html not in (expected["body"], expected["body"] + "\n"):
        raise ValueError("HTML differs from prepared email")
    attachment = expected["attachment"]
    if observed.get("pdf_name") != attachment["name"] or not isinstance(observed.get("pdf_bytes"), bytes):
        raise ValueError("PDF differs from prepared email")
    if sha256(observed["pdf_bytes"]).digest() != sha256(attachment["data"]).digest():
        raise ValueError("PDF differs from prepared email")
    return message_id
