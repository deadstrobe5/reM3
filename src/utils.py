"""Common utility functions for the reMarkable sync tool."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional


def ensure_directory(path: Path) -> None:
    """Create directory and all parent directories if they don't exist."""
    path.mkdir(parents=True, exist_ok=True)


def read_json(path: Path) -> Optional[dict]:
    """Read and parse a JSON file, returning None on error."""
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def sanitize_name(name: str) -> str:
    """Sanitize a name for use as a filesystem path component."""
    name = (name or "").strip()
    for ch, repl in [("/", "-"), ("\\", "-"), (":", " -")]:
        name = name.replace(ch, repl)
    return name[:200] if len(name) > 200 else name


def choose_unique_path(base_path: Path) -> Path:
    """Find a unique path by appending (1), (2), etc. if the path exists."""
    if not base_path.exists() and not base_path.is_symlink():
        return base_path
    stem = base_path.stem
    suffix = base_path.suffix
    parent = base_path.parent
    i = 1
    while True:
        candidate = parent / f"{stem} ({i}){suffix}"
        if not candidate.exists() and not candidate.is_symlink():
            return candidate
        i += 1
