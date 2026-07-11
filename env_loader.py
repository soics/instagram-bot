"""
Tiny .env loader so we don't need python-dotenv.
Reads KEY=VALUE lines from ~/instagrambot/.env and sets them in os.environ
IF they aren't already set. Existing env vars win (so systemd EnvironmentFile
overrides still work, and so does `export IG_PASSWORD=...` in the shell).

Usage:
    import env_loader
    # os.environ['IG_USERNAME'] and os.environ['IG_PASSWORD'] are now set
"""

import os
from pathlib import Path

ENV_FILE = Path(__file__).resolve().parent / ".env"


def _load(path: Path) -> None:
    if not path.exists():
        return
    try:
        with open(path, "r") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                # Only set if not already in environment
                os.environ.setdefault(key, value)
    except OSError as e:
        print(f"[env_loader] failed to read {path}: {e}")


_load(ENV_FILE)
