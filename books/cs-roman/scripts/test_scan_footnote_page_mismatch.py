"""Tests for footnote-mismatch body callout detection (no PDF required)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from scan_footnote_page_mismatch import marks_in_body  # noqa: E402


def _row(text: str) -> dict:
    return {
        "text": text,
        "y0": 100.0,
        "y1": 112.0,
        "x0": 80.0,
        "size": 12.0,
        "spans": [],
    }


class BodyMarkTests(unittest.TestCase):
    def test_glued_letter_digit(self) -> None:
        self.assertEqual(marks_in_body([_row("สโมธานปริวาสํ1")]), [1])

    def test_callout_after_outline_paren(self) -> None:
        self.assertEqual(marks_in_body([_row("(8) 1")]), [1])

    def test_callout_after_empty_parens(self) -> None:
        self.assertEqual(marks_in_body([_row(") 1")]), [1])

    def test_outline_paren_alone_is_not_a_callout(self) -> None:
        self.assertEqual(marks_in_body([_row("(8)")]), [])
