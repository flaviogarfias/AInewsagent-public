from ai_daily_briefing.verification import verify_source


class Response:
    status = 200
    def __init__(self, url):
        self.url = url
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return None
    def geturl(self):
        return self.url
    def read(self, size):
        return b"Source content with evidence"


def test_verify_source_requires_valid_original_response():
    assert verify_source("https://example.org/a", opener=lambda request, timeout: Response(request.full_url))
    assert not verify_source("https://example.org/a", opener=lambda request, timeout: Response("https://other.org/landing"))
    assert not verify_source("file:///etc/passwd", opener=lambda request, timeout: Response("file:///etc/passwd"))
