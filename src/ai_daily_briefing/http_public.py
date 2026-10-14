"""Bounded public HTTP fetches with private-address and redirect guards."""

from __future__ import annotations

import ipaddress
import http.client
import socket
import ssl
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request

from .identity import canonical_url


class _PinnedConnection(http.client.HTTPConnection):
    def __init__(self, host: str, port: int, address: tuple, timeout: int):
        super().__init__(host, port, timeout=timeout)
        self.address = address

    def connect(self):
        family, socktype, proto, _, sockaddr = self.address
        raw = socket.socket(family, socktype, proto)
        try:
            raw.settimeout(self.timeout)
            raw.connect(sockaddr)
            if isinstance(self, _PinnedTLSConnection):
                self.sock = ssl.create_default_context().wrap_socket(raw, server_hostname=self.host)
            else:
                self.sock = raw
        except Exception:
            raw.close()
            raise


class _PinnedTLSConnection(_PinnedConnection):
    pass


class _PinnedResponse:
    def __init__(self, connection, response, url):
        self.connection, self.response, self.url = connection, response, url
        self.status, self.headers = response.status, response.headers

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.response.close()
        self.connection.close()

    def read(self, size):
        return self.response.read(size)

    def geturl(self):
        return self.url


def _open(request: Request, timeout: int, address: tuple):
    parts = urlsplit(request.full_url)
    port = parts.port or (443 if parts.scheme == "https" else 80)
    conn_type = _PinnedTLSConnection if parts.scheme == "https" else _PinnedConnection
    connection = conn_type(parts.hostname, port, address, timeout)
    path = parts.path or "/"
    if parts.query:
        path += "?" + parts.query
    try:
        connection.request("GET", path, headers=dict(request.header_items()))
        response = connection.getresponse()
        if response.status >= 300:
            error = HTTPError(request.full_url, response.status, response.reason, response.headers, None)
            response.close()
            connection.close()
            raise error
        return _PinnedResponse(connection, response, request.full_url)
    except Exception:
        connection.close()
        raise


def _resolve(host: str, port: int):
    return socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)


def public_get(url: str, limit: int = 1_000_000, resolver=_resolve,
               opener=_open) -> tuple[bytes, str]:
    """Reject non-public DNS answers and connect only to the validated IP."""
    original = canonical_url(url)
    from urllib.parse import urlsplit, urlunsplit
    parts = urlsplit(original)
    # Canonical identity drops trailing slashes; some origin servers require them.
    wire_url = (urlunsplit((parts.scheme, parts.netloc, parts.path + "/", parts.query, ""))
                if urlsplit(url).path.endswith("/") and not parts.path.endswith("/") else original)
    for attempt in range(2):
        current = urlsplit(wire_url)
        addresses = resolver(current.hostname, current.port or (443 if current.scheme == "https" else 80))
        if not addresses or any(not ipaddress.ip_address(address[4][0]).is_global for address in addresses):
            raise ValueError("source must resolve only to public addresses")
        request = Request(wire_url, headers={"User-Agent": "Mozilla/5.0 (AI briefing research)"})
        try:
            with opener(request, timeout=15, address=addresses[0]) as response:
                if 300 <= response.status < 400 or canonical_url(response.geturl()) != original:
                    raise ValueError("source redirect is not allowed")
                if response.status != 200:
                    raise ValueError("source returned non-200")
                data = response.read(limit + 1)
                if not data or len(data) > limit:
                    raise ValueError("empty or oversized source")
                return data, response.headers.get("Content-Type", "")
        except HTTPError as error:
            from urllib.parse import urljoin
            destination = urljoin(wire_url, error.headers.get("Location", ""))
            # Only permit a single same-origin trailing-slash canonicalization.
            if (attempt or error.code not in (301, 308) or
                    canonical_url(destination) != original or
                    urlsplit(destination).netloc != parts.netloc or
                    not urlsplit(destination).path.endswith("/")):
                if 300 <= error.code < 400:
                    raise ValueError("source redirect is not allowed") from error
                raise
            wire_url = destination
    raise ValueError("too many redirects")
