"""Runtime configuration. Everything that varies between installs comes from the environment."""
from __future__ import annotations

import os
from pathlib import Path

VERSION = "0.1.0"


def _path(name: str, default: str) -> Path:
    return Path(os.environ.get(name, default)).expanduser().resolve()


DATA_DIR = _path("ZOCALO_DATA_DIR", "./data")
DATASETS_DIR_DEFAULT = _path("ZOCALO_DATASETS_DIR", "./datasets")
DOCS_DIR = _path("ZOCALO_DOCS_DIR", str(Path(__file__).resolve().parents[2] / "docs"))
IN_DOCKER = os.environ.get("ZOCALO_IN_DOCKER") == "1"
# Where the datasets folder lives on the host, shown in Settings when running in Docker.
DATASETS_HOST = os.environ.get("ZOCALO_DATASETS_HOST", "")
# "none": no login (personal use on your own machine). "accounts": user accounts with passwords.
AUTH_DEFAULT = os.environ.get("ZOCALO_AUTH", "accounts").strip().lower()
WEB_DIR = Path(__file__).resolve().parent / "web"

DATA_DIR.mkdir(parents=True, exist_ok=True)
