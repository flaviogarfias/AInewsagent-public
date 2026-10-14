"""Single canonical HTML report representation (PDF delivery is a later adapter)."""

from __future__ import annotations

from html import escape

_LIGHTS = {"green": ("Verde - muy valiosa", "#167c36"),
           "yellow": ("Amarillo - medianamente valiosa", "#8a5a00"),
           "red": ("Rojo - poco valiosa", "#a22a25")}


def source_line(item: dict) -> str:
    source = str(item.get("source", ""))
    published = str(item.get("published", ""))
    if item.get("feed_published") and item.get("kind") == "paper":
        return (f"Fuente: {source} — Fecha original de arXiv: {published}; "
                f"Fecha del feed: {item['feed_published']}")
    return f"Fuente: {source} — {published}"

def render_html(items: list[dict], timestamp: str) -> str:
    """Render untrusted candidate fields safely into an HTML email/report."""
    parts = ["<!doctype html><html lang=\"es\"><meta charset=\"utf-8\">",
             "<title>Resumen diario de IA</title><body>",
             "<h1>Lecturas de IA</h1>", f"<p>{escape(timestamp)}</p>"]
    for item in items:
        title = escape(str(item["title"]))
        url = escape(str(item["url"]), quote=True)
        light, color = _LIGHTS.get(item.get("traffic_light", "red"), _LIGHTS["red"])
        summary = escape(str(item.get("summary", "")))
        source_text = escape(source_line(item))
        kind = "Paper" if item["kind"] == "paper" else "Noticia"
        parts.extend([f"<section><h2>{kind}: {title}</h2>",
                      f'<p>Semáforo: <strong style="color:{color}">{light}</strong></p>', f"<p>{summary}</p>",
                      f"<p>{source_text}</p>",
                      f'<p><a href="{url}">Documento original</a></p></section>'])
    if not items:
        parts.append("<p>No hay candidatos nuevos verificables en esta ventana.</p>")
    parts.append("</body></html>")
    return "\n".join(parts)
