from hashlib import md5

import pytest

from ai_daily_briefing.composio_upload import stage_pdf


def test_stage_pdf_uses_original_bytes_and_digest():
    original = b"%PDF-1.4\noriginal bytes\n%%EOF"
    calls = []

    def post(payload):
        calls.append(("post", payload))
        return {"type": "new", "key": "gmail/files/report.pdf",
                "new_presigned_url": "https://s3.amazonaws.com/upload?signature=hidden"}

    def put(url, data, mimetype):
        calls.append(("put", data, mimetype))

    result = stage_pdf("report.pdf", original, request_upload=post, put_bytes=put)
    assert calls[0][1] == {"toolkit_slug": "gmail", "tool_slug": "GMAIL_SEND_EMAIL",
                           "filename": "report.pdf", "mimetype": "application/pdf",
                           "md5": md5(original).hexdigest()}
    assert calls[1] == ("put", original, "application/pdf")
    assert result == {"name": "report.pdf", "mimetype": "application/pdf",
                      "s3key": "gmail/files/report.pdf"}


def test_existing_identical_file_does_not_reupload():
    result = stage_pdf("report.pdf", b"%PDF-test", request_upload=lambda _: {
        "type": "existing", "key": "gmail/files/existing"},
        put_bytes=lambda *args: pytest.fail("should not upload"))
    assert result["s3key"] == "gmail/files/existing"


def test_stage_pdf_accepts_composio_r2_signed_host():
    uploaded = []
    stage_pdf("report.pdf", b"%PDF-real", request_upload=lambda _: {
        "type": "new", "key": "r2-key",
        "new_presigned_url": "https://temp.account.r2.cloudflarestorage.com/object?sig=hidden"},
        put_bytes=lambda url, data, mimetype: uploaded.append((data, mimetype)))
    assert uploaded == [(b"%PDF-real", "application/pdf")]


def test_stage_pdf_rejects_private_presigned_url():
    with pytest.raises(ValueError, match="upload URL"):
        stage_pdf("report.pdf", b"%PDF-test", request_upload=lambda _: {
            "type": "new", "key": "reference", "new_presigned_url": "http://127.0.0.1:8000/upload"},
            put_bytes=lambda *args: pytest.fail("unsafe upload"))


def test_stage_pdf_rejects_invalid_or_missing_reference():
    with pytest.raises(ValueError, match="PDF"):
        stage_pdf("report.pdf", b"not a PDF", request_upload=lambda _: {}, put_bytes=lambda *args: None)
    with pytest.raises(ValueError, match="reference"):
        stage_pdf("report.pdf", b"%PDF-test", request_upload=lambda _: {"type": "existing"},
                  put_bytes=lambda *args: None)
