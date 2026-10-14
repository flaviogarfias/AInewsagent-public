import json
from pathlib import Path
import pytest

from scripts.run_once import main


def test_run_once_script_refuses_outbound_flag_when_config_disabled(tmp_path):
    config = {"schedule": {"timezone": "America/Mexico_City", "time": "07:00",
                           "days": ["monday"]}, "model": {"name": "qwen3-hermes:8b"},
              "feeds": [{"name": "Source", "kind": "news", "url": "https://example.org/rss"}],
              "delivery": {"send_enabled": False}}
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config))
    with pytest.raises(ValueError, match="disabled"):
        main([str(path), "--deliver", "--workdir", str(tmp_path)])
    assert not (tmp_path / "audit.sqlite3").exists()
