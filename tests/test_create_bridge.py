import os
from pathlib import Path

import pytest

from scripts.create_bridge import create_bridge


def test_bridge_is_local_exclusive_and_points_to_project(tmp_path):
    project = tmp_path / "project"
    (project / "scripts").mkdir(parents=True)
    (project / "scripts/scheduled_once.py").write_text("# fixture\n")
    target = tmp_path / "hermes" / "scripts" / "briefing.py"
    result = create_bridge(target, project)
    text = result.read_text()
    assert "scripts.scheduled_once import main" in text
    assert str(project) in text
    assert "config/briefing.json" in text
    assert result.stat().st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError):
        create_bridge(target, project)
    assert target.read_text() == text


def test_bridge_rejects_missing_project_entrypoint(tmp_path):
    target = tmp_path / "scripts" / "bridge.py"
    with pytest.raises(ValueError, match="scheduled_once"):
        create_bridge(target, tmp_path)
    assert not target.exists()
