"""Load shared glyph / script JSON next to the package tree."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

# packages/pali_script/python/pali_script/data_loader.py → packages/pali_script/data
_DATA_DIR = Path(__file__).resolve().parents[2] / "data"


@lru_cache(maxsize=1)
def load_glyphs() -> dict[str, Any]:
    return json.loads((_DATA_DIR / "glyphs.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_scripts() -> dict[str, Any]:
    return json.loads((_DATA_DIR / "scripts.json").read_text(encoding="utf-8"))


def data_dir() -> Path:
    return _DATA_DIR
