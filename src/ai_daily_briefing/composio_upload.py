"""Stage original PDF bytes for a Composio Gmail attachment, without sending."""

from __future__ import annotations

from hashlib import md5
from pathlib import PurePath
from typing import Callable
from urllib.parse import urlsplit


def stage_pdf(filename: str, pdf_bytes: bytes, *,
              request_upload: Callable[[dict], dict],
              put_bytes: Callable[[str, bytes, str], None]) -> dict:
    """Return FileUploadable metadata after an exact-byte upload (or dedup)."""
    if not isinstance(pdf_bytes, bytes) or not pdf_bytes.startswith(b"%PDF"):
        raise ValueError("PDF bytes are required")
    if not filename or PurePath(filename).name != filename or not filename.endswith(".pdf"):
        raise ValueError("PDF filename must be a plain .pdf name")
    mimetype = "application/pdf"
    response = request_upload({"toolkit_slug": "gmail", "tool_slug": "GMAIL_SEND_EMAIL",
                               "filename": filename, "mimetype": mimetype,
                               "md5": md5(pdf_bytes).hexdigest()})
    key = response.get("key")
    if not isinstance(key, str) or not key:
        raise ValueError("Composio file reference missing")
    kind = response.get("type")
    if kind == "new":
        url = response.get("new_presigned_url") or response.get("newPresignedUrl")
        parts = urlsplit(url or "")
        host = parts.hostname or ""
        allowed_storage = (host.endswith(".amazonaws.com") or
                           host.endswith(".r2.cloudflarestorage.com"))
        if (parts.scheme != "https" or not allowed_storage or
                parts.username or parts.password or parts.port not in (None, 443)):
            raise ValueError("unsafe upload URL")
        put_bytes(url, pdf_bytes, mimetype)
    elif kind != "existing":
        raise ValueError("unrecognized Composio file upload status")
    return {"name": filename, "mimetype": mimetype, "s3key": key}
