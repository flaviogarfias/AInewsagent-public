import io
import json
import pytest
from urllib.error import HTTPError

from ai_daily_briefing.platform_http import PlatformHTTP


class Reply:
    status = 200
    headers = {"ETag": '"irrelevant"'}
    def __init__(self, body): self.body = body
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self, limit): return self.body


def test_platform_http_uses_project_key_only_on_platform_origin():
    requests = []
    def opener(request, timeout):
        requests.append(request)
        return Reply(json.dumps({"items": []}).encode())
    http = PlatformHTTP("ak_test", opener=opener)
    assert http.request("connected_accounts?limit=100", None) == {"items": []}
    assert requests[0].get_header("X-api-key") == "ak_test"
    assert requests[0].full_url == "https://backend.composio.dev/api/v3.1/connected_accounts?limit=100"
    with pytest.raises(ValueError):
        http.request("https://elsewhere.example/secret", None)
    with pytest.raises(ValueError):
        http.request("../other", None)
    assert len(requests) == 1


def test_platform_storage_rejects_untrusted_hosts_before_network():
    http = PlatformHTTP("ak_test", opener=lambda *args, **kwargs: pytest.fail("network called"))
    with pytest.raises(ValueError, match="storage"):
        http.put_pdf("https://evil.example/upload", b"%PDF-data", "application/pdf")
    with pytest.raises(ValueError, match="storage"):
        http.download("https://evil.example/download")


def test_platform_storage_upload_and_download_omit_project_key():
    from hashlib import md5
    calls = []
    payload = b"%PDF-data"
    class StorageReply(Reply):
        headers = {"ETag": '"' + md5(payload).hexdigest() + '"'}
    def opener(request, timeout):
        calls.append(request)
        return StorageReply(b"" if request.get_method() == "PUT" else payload)
    http = PlatformHTTP("ak_test", opener=opener)
    url = "https://bucket.r2.cloudflarestorage.com/example"
    http.put_pdf(url, payload, "application/pdf")
    assert http.download(url) == payload
    assert [r.get_method() for r in calls] == ["PUT", "GET"]
    assert all(r.get_header("X-api-key") is None for r in calls)


def test_platform_http_sanitizes_provider_errors():
    def fail(request, timeout):
        raise HTTPError("https://backend.composio.dev/ak_test", 401, "ak_test", {}, io.BytesIO(b"ak_test"))
    http = PlatformHTTP("ak_test", opener=fail)
    with pytest.raises(OSError) as error:
        http.request("connected_accounts?limit=100", None)
    assert "ak_test" not in str(error.value)
