"""Translate Gmail tool responses into the exact-byte delivery contract."""

from __future__ import annotations

from base64 import urlsafe_b64decode
from email.utils import parseaddr
from typing import Callable
from urllib.parse import urlsplit


def _storage_url(url: str) -> bool:
    parts = urlsplit(url or "")
    host = parts.hostname or ""
    return (parts.scheme == "https" and
            (host.endswith(".amazonaws.com") or host.endswith(".r2.cloudflarestorage.com")) and
            not parts.username and not parts.password and parts.port in (None, 443))


def _html_part(part: dict) -> str | None:
    if part.get("mimeType", "").lower() == "text/html":
        data = (part.get("body") or {}).get("data")
        if not isinstance(data, str):
            return None
        return urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode("utf-8")
    for child in part.get("parts") or []:
        found = _html_part(child)
        if found is not None:
            return found
    return None


class ComposioTransport:
    def __init__(self, *, execute: Callable[[str, dict], dict],
                 download: Callable[[str], bytes]):
        self.execute = execute
        self.download = download

    def _run(self, slug: str, args: dict) -> dict:
        response = self.execute(slug, args)
        if not response.get("successful") or not isinstance(response.get("data"), dict):
            raise ValueError(f"Composio {slug} did not succeed")
        return response["data"]

    def send(self, payload: dict) -> str:
        """Send via an explicitly selected authenticated connection."""
        attachment = payload.get("attachment") or {}
        if (not attachment.get("s3key") or attachment.get("mimetype") != "application/pdf" or
                "data" in attachment):
            raise ValueError("Gmail requires staged PDF reference, not bytes")
        fields = ("from_email", "recipient_email", "subject", "body", "is_html", "attachment")
        args = {key: payload[key] for key in fields}
        args["user_id"] = "me"
        response = self._run("GMAIL_SEND_EMAIL", args)
        message_id = response.get("id") or response.get("messageId") or response.get("message_id")
        if not isinstance(message_id, str) or not message_id.strip():
            raise ValueError("Gmail message ID missing from send response")
        return message_id

    def fetch(self, message_id: str, expected: dict) -> dict:
        """Read one Sent message and its PDF; do not infer receipt by addressee."""
        item = self._run("GMAIL_FETCH_MESSAGE_BY_MESSAGE_ID",
                         {"message_id": message_id, "format": "full", "user_id": "me"})
        if item.get("messageId") != message_id:
            raise ValueError("Gmail readback message ID differs")
        attachments = [a for a in item.get("attachmentList") or []
                       if a.get("filename") == expected["attachment"]["name"]]
        if len(attachments) != 1 or not attachments[0].get("attachmentId"):
            raise ValueError("expected PDF attachment not found exactly once")
        filename = attachments[0]["filename"]
        result = self._run("GMAIL_GET_ATTACHMENT",
                           {"message_id": message_id, "attachment_id": attachments[0]["attachmentId"],
                            "file_name": filename, "user_id": "me"})
        file = result.get("file") or {}
        url = file.get("s3url")
        if file.get("name") != filename or not _storage_url(url):
            raise ValueError("unsafe or mismatched attachment download")
        data = self.download(url)
        if not isinstance(data, bytes) or not data.startswith(b"%PDF"):
            raise ValueError("downloaded attachment is not a PDF")
        headers = {h.get("name", "").lower(): h.get("value", "")
                   for h in (item.get("payload") or {}).get("headers") or []}
        html = _html_part(item.get("payload") or {})
        return {"message_id": message_id, "label_ids": item.get("labelIds") or [],
                "from_email": parseaddr(headers.get("from", ""))[1],
                "recipient_email": parseaddr(headers.get("to", ""))[1],
                "subject": headers.get("subject"), "html_body": html,
                "pdf_name": filename, "pdf_bytes": data}
