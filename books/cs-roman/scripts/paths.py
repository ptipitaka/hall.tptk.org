"""Canonical paths for the self-contained books/cs-roman tree."""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
BOOKS = SCRIPTS_DIR.parent
REPO = BOOKS.parents[1]  # hall.tptk.org
SOURCE_DIR = BOOKS / "source"
OUTPUT_DIR = BOOKS / "output"
VOLUMES_DIR = BOOKS / "volumes"
PALI_SCRIPT_PYTHON = REPO / "packages" / "pali_script" / "python"


def ensure_import_paths() -> None:
    """Put local scripts + pali_script on sys.path."""
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    if PALI_SCRIPT_PYTHON.is_dir() and str(PALI_SCRIPT_PYTHON) not in sys.path:
        sys.path.insert(0, str(PALI_SCRIPT_PYTHON))


def repo_relative(path: Path) -> str:
    """Return a forward-slash path relative to the repo when possible."""
    resolved = path.resolve()
    try:
        return resolved.relative_to(REPO.resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()
