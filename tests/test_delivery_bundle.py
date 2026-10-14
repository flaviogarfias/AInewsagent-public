import hashlib

import pytest

from ai_daily_briefing.artifacts import write_report_artifacts
from ai_daily_briefing.delivery_bundle import prepare_delivery_bundle, verify_delivery_bundle


def _artifacts(tmp_path):
    report = {"generated_at": "2026-10-03T07:00:00-06:00", "items": [
        {"kind": "paper", "title": "LLM infrastructure", "url": "https://example.org/paper",
         "summary": "Evidence-based evaluation.", "traffic_light": "yellow", "source": "arXiv",
         "published": "2026-10-03"}]}
    return write_report_artifacts(report, tmp_path)


def test_bundle_uses_existing_html_and_pdf_bytes_without_rerendering(tmp_path):
    paths = _artifacts(tmp_path)
    bundle = prepare_delivery_bundle(paths)
    assert bundle.html_body == paths["html"].read_text(encoding="utf-8")
    assert bundle.pdf_bytes == paths["pdf"].read_bytes()
    assert bundle.pdf_name == paths["pdf"].name
    assert bundle.html_sha256 == hashlib.sha256(paths["html"].read_bytes()).hexdigest()
    assert bundle.pdf_sha256 == hashlib.sha256(paths["pdf"].read_bytes()).hexdigest()
    verify_delivery_bundle(bundle, paths)


def test_bundle_rejects_changed_pdf_before_send(tmp_path):
    paths = _artifacts(tmp_path)
    bundle = prepare_delivery_bundle(paths)
    paths["pdf"].write_bytes(paths["pdf"].read_bytes() + b"changed")
    with pytest.raises(ValueError, match="PDF changed"):
        verify_delivery_bundle(bundle, paths)


def test_bundle_rejects_changed_html_before_send(tmp_path):
    paths = _artifacts(tmp_path)
    bundle = prepare_delivery_bundle(paths)
    paths["html"].write_text("<html>other report</html>")
    with pytest.raises(ValueError, match="HTML changed"):
        verify_delivery_bundle(bundle, paths)


def test_bundle_rejects_non_pdf_attachment(tmp_path):
    paths = _artifacts(tmp_path)
    paths["pdf"].write_bytes(b"not a PDF")
    with pytest.raises(ValueError, match="invalid PDF"):
        prepare_delivery_bundle(paths)
