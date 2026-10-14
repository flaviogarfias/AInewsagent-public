"""One-time, interactive local setup for a Composio project key.

Run in a real Terminal; never pass a key on the command line or in chat.
"""

from __future__ import annotations

import argparse
import getpass
import os
import tempfile
from pathlib import Path


def save_key(path: Path, key: str, *, replace: bool = False) -> None:
    if not key.startswith("ak_") or any(char.isspace() or char in "=\x00" for char in key):
        raise ValueError("Enter only the single project key, not NAME=key or a consumer key")
    path.parent.mkdir(parents=True, exist_ok=True)
    if replace:
        if not path.is_file() or path.is_symlink():
            raise ValueError("Only an existing regular .env may be replaced")
        fd, temporary = tempfile.mkstemp(prefix=".env-new-", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                stream.write(f"COMPOSIO_PROJECT_API_KEY={key}\n")
            os.chmod(temporary, 0o600)
            os.replace(temporary, path)
        finally:
            Path(temporary).unlink(missing_ok=True)
    else:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                stream.write(f"COMPOSIO_PROJECT_API_KEY={key}\n")
            os.chmod(path, 0o600)
        except BaseException:
            path.unlink(missing_ok=True)
            raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Save a project key without exposing it")
    parser.add_argument("--replace", action="store_true", help="atomically replace an existing local .env")
    args = parser.parse_args()
    env_file = Path(__file__).resolve().parents[1] / ".env"
    if env_file.exists() and not args.replace:
        raise SystemExit("The local .env already exists. Use --replace to replace it safely.")
    secret = getpass.getpass("Composio PROJECT API key (input hidden): ")
    try:
        save_key(env_file, secret, replace=args.replace)
    finally:
        del secret
    print("Saved local .env with owner-only permissions. Key not displayed.")
