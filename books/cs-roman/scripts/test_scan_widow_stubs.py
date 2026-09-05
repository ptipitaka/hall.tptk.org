"""Tests for widow-stub heading heuristics (no PDF required)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from scan_orphan_headings import norm_key  # noqa: E402
from scan_widow_stubs import Line, looks_like_heading  # noqa: E402


def _line(text: str, *, w: float = 89.0) -> Line:
    return Line(text=text, y0=86.3, x0=80.0, w=w, size=12.0)


class WidowHeadingTests(unittest.TestCase):
    def test_numbered_title_is_heading(self) -> None:
        self.assertTrue(looks_like_heading(_line("5. ตีหิ", w=80)))

    def test_heading_kind_title_is_heading(self) -> None:
        title = "ธมฺมกมฺมทฺวาทสก"
        keys = {norm_key(title)}
        self.assertTrue(looks_like_heading(_line(title), keys))
        self.assertFalse(looks_like_heading(_line(title), set()))

    def test_prose_fragment_is_not_heading(self) -> None:
        self.assertFalse(looks_like_heading(_line("อยํอิมสฺมิํอตฺเถ"), set()))
