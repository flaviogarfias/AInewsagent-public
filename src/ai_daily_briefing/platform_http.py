"""Restricted Composio Platform HTTP client; never log authentication headers."""
from __future__ import annotations

import json
import re
from hashlib import md5
from collections.abc import Callable
from urllib.parse import urlsplit
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

BASE = "https://backend.composio.dev/api/v3.1/"
_PATH = re.compile(r"^(?:connected_accounts\?(?:[A-Za-z0-9_=&%.-]+)|tools/execute/(?:GMAIL|SLACK)_[A-Z0-9_]+|files/upload/request)$")


def _storage_url(url: str) -> bool:
    parts = urlsplit(url or "")
    host = parts.hostname or ""
    return (parts.scheme == "https" and
            (host.endswith(".amazonaws.com") or host.endswith(".r2.cloudflarestorage.com")) and
            not parts.username and not parts.password and parts.port in (None, 443))


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_DEFAULT_OPENER = build_opener(_NoRedirect).open


class PlatformHTTP:
    def __init__(self, key: str, *, opener: Callable = _DEFAULT_OPENER):
        if not key.startswith("ak_") or "=" in key or key != key.strip():
            raise ValueError("bare Composio project key required")
        self.key = key
        self.opener = opener

    def request(self, path: str, payload: dict | None) -> dict:
        if not _PATH.fullmatch(path):
            raise ValueError("unapproved Platform API path")
        headers = {"x-api-key": self.key, "Accept": "application/json"}
        if payload is not None:
            headers["Content-Type"] = "application/json"
        request = Request(BASE + path,
                          data=json.dumps(payload).encode() if payload is not None else None,
                          method="POST" if payload is not None else "GET", headers=headers)
        try:
            with self.opener(request, timeout=30) as response:
                content = response.read(20_000_001)
            if len(content) > 20_000_000:
                raise ValueError("oversized Platform response")
            data = json.loads(content)
            if not isinstance(data, dict):
                raise ValueError("unexpected Platform response")
            return data
        except (HTTPError, URLError, TimeoutError, ValueError) as error:
            raise OSError(f"Platform request failed ({type(error).__name__})") from None

    def put_pdf(self, url: str, data: bytes, mimetype: str) -> None:
        if not _storage_url(url):
            raise ValueError("unsafe storage URL")
        if not isinstance(data, bytes) or not data.startswith(b"%PDF") or mimetype != "application/pdf":
            raise ValueError("original PDF required")
        try:
            with self.opener(Request(url, data=data, method="PUT",
                                     headers={"Content-Type": mimetype}), timeout=30) as response:
                if response.status not in (200, 201, 204):
                    raise ValueError("storage rejected PDF")
                etag = response.headers.get("ETag", "").strip('"').lower()
                if etag and etag != md5(data).hexdigest():
                    raise ValueError("storage ETag differs")
        except (HTTPError, URLError, TimeoutError) as error:
            raise OSError(f"storage upload failed ({type(error).__name__})") from None

    def download(self, url: str) -> bytes:
        if not _storage_url(url):
            raise ValueError("unsafe storage URL")
        try:
            with self.opener(Request(url), timeout=30) as response:
                content = response.read(20_000_001)
        except (HTTPError, URLError, TimeoutError) as error:
            raise OSError(f"storage download failed ({type(error).__name__})") from None
        if len(content) > 20_000_000:
            raise ValueError("oversized storage download")
        return content
