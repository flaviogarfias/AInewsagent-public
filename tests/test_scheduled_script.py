import json
from pathlib import Path

from scripts.scheduled_once import main


def test_scheduled_script_disabled_uses_no_network_or_audit(tmp_path, capsys):
    config = {"schedule": {"timezone": "America/Mexico_City", "time": "07:00",
                           "days": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]},
              "model": {"name": "qwen3-hermes:8b"},
              "feeds": [{"name": "Source", "kind": "news", "url": "https://example.org/rss"}],
              "delivery": {"send_enabled": False}}
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config))
    assert main([str(path), "--workdir", str(tmp_path)]) == 0
    assert json.loads(capsys.readouterr().out) == {"status": "disabled"}
    assert not (tmp_path / "audit.sqlite3").exists()
    assert not (tmp_path / "scheduled-attempts").exists()
