"""Conservative extraction of substantive article text from public HTML."""

from __future__ import annotations

from html.parser import HTMLParser
from .http_public import public_get


class _ArticleParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.hidden = 0
        self.chunks: list[str] = []
        self.tags: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append(tag)
        if tag in {"article", "main"}:
            self.depth += 1
        if tag in {"script", "style", "nav", "footer", "aside", "form", "svg"}:
            self.hidden += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"article", "main"} and self.depth:
            self.depth -= 1
        if tag in {"script", "style", "nav", "footer", "aside", "form", "svg"} and self.hidden:
            self.hidden -= 1
        if tag in {"p", "h1", "h2", "h3", "li", "div"} and self.depth and not self.hidden:
            self.chunks.append("\n")
        if self.tags:
            self.tags.pop()

    def handle_data(self, data: str) -> None:
        if self.depth and not self.hidden:
            value = " ".join(data.split())
            if value:
                self.chunks.append(value + " ")


def extract_article_text(data: bytes, limit: int = 12000) -> str:
    """Return bounded article/main text or empty when the page has no article."""
    parser = _ArticleParser()
    parser.feed(data.decode("utf-8", errors="replace"))
    text = "\n".join(line.strip() for line in "".join(parser.chunks).splitlines() if line.strip())
    return text[:limit] if len(text) >= 80 else ""


def fetch_article_text(url: str) -> str:
    """Fetch a public HTML article; caller must first restrict trusted source URLs."""
    content, content_type = public_get(url, limit=1_000_000)
    if "text/html" not in content_type.lower():
        return ""
    return extract_article_text(content)
