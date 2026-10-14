"""Prepare (but do not schedule) a private Hermes no-agent bridge."""
from __future__ import annotations

import argparse
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def create_bridge(target: Path, project_root: Path = ROOT) -> Path:
    """Write a local bridge once; never overwrite an existing scheduler script."""
    project_root = project_root.resolve(strict=True)
    if not (project_root / "scripts/scheduled_once.py").is_file():
        raise ValueError("project root lacks scheduled_once.py")
    target = target.expanduser().absolute()
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    source = ("\"\"\"Private Hermes dispatch bridge, generated locally.\"\"\"\n"
              "from pathlib import Path\nimport sys\n"
              f"ROOT = Path({str(project_root)!r})\n"
              "sys.path.insert(0, str(ROOT))\n"
              "sys.path.insert(0, str(ROOT / 'src'))\n"
              "from scripts.scheduled_once import main\n"
              "if __name__ == '__main__':\n"
              "    raise SystemExit(main([str(ROOT / 'config/briefing.json'), "
              "'--workdir', str(ROOT / 'var')]))\n")
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        stream.write(source)
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a private Hermes cron bridge (no job created)")
    parser.add_argument("output", type=Path, help="path under the active HERMES_HOME/scripts directory")
    args = parser.parse_args()
    path = create_bridge(args.output)
    print(f"Bridge prepared: {path}; no job created, no email sent")


if __name__ == "__main__":
    main()
