"""Shared validation primitives for repository checks."""

from __future__ import annotations

from pathlib import Path


def require_paths(paths: list[Path]) -> list[str]:
    return [str(path) for path in paths if not path.exists()]
