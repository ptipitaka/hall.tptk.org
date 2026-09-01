"""Tests for annotate HTML report (transliteration via project converters)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from cs_roman_text import roman_to_thai  # noqa: E402
from generate_cs_roman_tex import note_to_thai  # noqa: E402
from paths import TMP_DIR  # noqa: E402
from report_annotate import AnnotateRow, classify_kind, default_output, render_html  # noqa: E402


class ReportAnnotateTests(unittest.TestCase):
    def test_patho_rule_id_without_patho_in_footnote(self) -> None:
        self.assertEqual(
            classify_kind("lābhimhīti – ม.พ.ป.", rule_id="roman-labhimhiti-patho"),
            "pāṭho",
        )

    def test_html_uses_note_to_thai_and_roman_to_thai(self) -> None:
        rows = [
            AnnotateRow(
                page=10,
                order=35,
                printed="tesaṃ yeva",
                footnote="tesaṃyeva niggahītasandhi – ม.พ.ป.",
                kind="niggahītasandhi",
                n=1,
            )
        ]
        doc = render_html(volume="01Vin01", rows=rows)
        self.assertIn(roman_to_thai("tesaṃ yeva"), doc)
        self.assertIn(note_to_thai("tesaṃyeva niggahītasandhi – ม.พ.ป."), doc)
        self.assertIn("tesaṃ yeva", doc)

    def test_default_output_is_under_repo_tmp(self) -> None:
        self.assertEqual(
            default_output("01Vin01"),
            TMP_DIR / "annotate_01Vin01.html",
        )


if __name__ == "__main__":
    unittest.main()
