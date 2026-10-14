from pathlib import Path
from runpy import run_path

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "configure_project_key.py"


def test_project_key_setup_masks_output_and_never_overwrites(tmp_path, capsys):
    save_key = run_path(str(SCRIPT))["save_key"]
    path = tmp_path / ".env"
    save_key(path, "ak_test-only-value")
    assert path.read_text() == "COMPOSIO_PROJECT_API_KEY=ak_test-only-value\n"
    assert path.stat().st_mode & 0o777 == 0o600
    assert "ak_test-only-value" not in capsys.readouterr().out
    with pytest.raises(FileExistsError):
        save_key(path, "ak_replacement")
    assert path.read_text() == "COMPOSIO_PROJECT_API_KEY=ak_test-only-value\n"
    save_key(path, "ak_replacement", replace=True)
    assert path.read_text() == "COMPOSIO_PROJECT_API_KEY=ak_replacement\n"
    assert path.stat().st_mode & 0o777 == 0o600
    assert not list(tmp_path.glob(".env-new-*"))


def test_project_key_setup_rejects_multiline_or_empty(tmp_path):
    save_key = run_path(str(SCRIPT))["save_key"]
    path = tmp_path / ".env"
    for value in ("", "first\nsecond", "first\rsecond", "COMPOSIO_API_KEY=ak_fake", "ck_fake"):
        with pytest.raises(ValueError):
            save_key(path, value)
    assert not path.exists()
