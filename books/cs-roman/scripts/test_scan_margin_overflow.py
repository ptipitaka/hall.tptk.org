"""Tests for scan_margin_overflow helpers."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from scan_margin_overflow import (  # noqa: E402
    PRINTING_GEOM,
    OverflowHit,
    display_char_count,
    format_report,
    text_block_right,
    words_from_glyphs,
)


def _hit(volume: str, page: int, text: str) -> OverflowHit:
    return OverflowHit(
        volume=volume,
        physical_page=page,
        y0=0.0,
        x1=0.0,
        text_right=0.0,
        overflow_pt=0.0,
        overflow_chars=0.0,
        text=text,
    )


class MarginOverflowHelperTests(unittest.TestCase):
    def test_display_char_count_skips_virama(self) -> None:
        # ส + ตฺ + ตา… — ฺ is nonspacing
        self.assertEqual(display_char_count("สตฺ"), 2)
        self.assertEqual(display_char_count("a"), 1)

    def test_printing_odd_even_text_right(self) -> None:
        page_w = 467.717
        odd = text_block_right(0, page_w, PRINTING_GEOM)
        even = text_block_right(1, page_w, PRINTING_GEOM)
        self.assertAlmostEqual(odd, 409.604, places=2)
        self.assertAlmostEqual(even, 394.607, places=2)
        self.assertGreater(odd, even)

    def test_format_report_orders_by_text_length_desc(self) -> None:
        report = format_report(
            "printing",
            [
                _hit("01Vin01", 10, "short"),
                _hit("02Vin02", 3, "muchlongerword"),
                _hit("01Vin01", 2, "medium"),
            ],
            ["01Vin01", "02Vin02"],
        )
        rows = [line for line in report.splitlines() if line.startswith("| ") and "volume" not in line]
        self.assertEqual(
            [r.split("|")[3].strip() for r in rows],
            ["muchlongerword", "medium", "short"],
        )

    def test_words_from_glyphs_splits_on_interword_gap(self) -> None:
        # Mimic 16An02 p.116: TeX word spaces ~6.4pt, no space glyphs;
        # footnote "1" sits ~1.7pt after the host word (must stay attached).
        chars = [
            ("ป", 0.0, 0.0, 5.0, 10.0),
            ("ร", 5.0, 0.0, 10.0, 10.0),
            ("ิ", 10.0, 0.0, 10.0, 10.0),  # Mn — attach
            ("เ", 16.4, 0.0, 20.0, 10.0),  # new word after 6.4pt gap
            ("ต", 20.0, 0.0, 25.0, 10.0),
            ("1", 26.7, 0.0, 30.0, 10.0),  # footnote — keep
        ]
        words = words_from_glyphs(chars)
        self.assertEqual([w.text for w in words], ["ปริ", "เต1"])
        self.assertAlmostEqual(words[1].x0, 16.4)
        self.assertAlmostEqual(words[1].x1, 30.0)

    def test_words_from_glyphs_splits_on_space_char(self) -> None:
        chars = [
            ("a", 0.0, 0.0, 5.0, 10.0),
            (" ", 5.0, 0.0, 8.0, 10.0),
            ("b", 8.0, 0.0, 13.0, 10.0),
        ]
        self.assertEqual([w.text for w in words_from_glyphs(chars)], ["a", "b"])


if __name__ == "__main__":
    unittest.main()
