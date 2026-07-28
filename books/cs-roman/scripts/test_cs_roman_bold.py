"""Unit tests for CS Roman fake-bold helpers."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from cs_roman_bold import (  # noqa: E402
    bold_ranges_in_text,
    ranges_to_runs,
    substantial_bold_ranges,
    subtract_marker_ranges,
)
from cs_roman_text import roman_to_thai, transliterate_runs  # noqa: E402


class SubstantialBoldRangesTests(unittest.TestCase):
    def test_keeps_full_line_closer_bold(self) -> None:
        text = "Pārājikakaṇḍaṃ niṭṭhitaṃ."
        ranges = bold_ranges_in_text(text, [text])
        self.assertEqual(substantial_bold_ranges(text, ranges), [(0, len(text))])

    def test_drops_lemma_bleed_on_plain_closer(self) -> None:
        text = "Vehāsakuṭisikkhāpadaṃ niṭṭhitaṃ aṭṭhamaṃ."
        ranges = bold_ranges_in_text(text, ["Vehāsakuṭi"])
        self.assertEqual(ranges, [(0, len("Vehāsakuṭi"))])
        self.assertEqual(substantial_bold_ranges(text, ranges), [])

    def test_ignores_note_markers_in_coverage(self) -> None:
        text = "Sammādiṭṭhisuttaṃ niṭṭhitaṃ navamaṃ{{n0}}."
        span = "Sammādiṭṭhisuttaṃ niṭṭhitaṃ navamaṃ."
        ranges = bold_ranges_in_text(text, [span])
        self.assertTrue(substantial_bold_ranges(text, ranges))


class MarkerBoldCollisionTests(unittest.TestCase):
    def test_digit_span_does_not_bold_inside_sp1(self) -> None:
        text = "yācitabbā.{{sp1}} Dutiyampi"
        self.assertEqual(bold_ranges_in_text(text, ["1"]), [])

    def test_lemma_bold_kept_beside_sp1(self) -> None:
        text = "Bhikkhū abhinetabbā.{{sp1}} Dutiyampi"
        ranges = bold_ranges_in_text(text, ["Bhikkhū abhinetabbā"])
        self.assertEqual(ranges, [(0, len("Bhikkhū abhinetabbā"))])

    def test_ranges_to_runs_strips_bold_inside_sp1(self) -> None:
        text = "yācitabbā.{{sp1}} Dutiyampi"
        sp1_one = text.index("{{sp1}}") + len("{{sp")
        runs = ranges_to_runs(text, [(sp1_one, sp1_one + 1)])
        self.assertIsNone(runs)

    def test_subtract_keeps_outside_marker(self) -> None:
        text = "Namo{{sp1}} tassa"
        ranges = subtract_marker_ranges(text, [(0, 4), (6, 7)])
        self.assertEqual(ranges, [(0, 4)])

    def test_thai_runs_keep_literal_sp1(self) -> None:
        """Regression: split ``{{sp`` / ``1`` / ``}}`` must not become สฺปฺ/๑."""
        roman = "yācitabbā.{{sp1}} Dutiyampi"
        roman_runs = [
            {"value": "yācitabbā", "bold": True},
            {"value": ".{{sp1}} Dutiyampi", "bold": False},
        ]
        thai_runs = transliterate_runs(roman_runs)
        joined = "".join(r["value"] for r in thai_runs)
        self.assertEqual(joined, roman_to_thai(roman))
        self.assertIn("{{sp1}}", joined)
        self.assertNotIn("สฺปฺ", joined)
        self.assertNotIn("๑", "".join(r["value"] for r in thai_runs if r.get("bold")))


if __name__ == "__main__":
    unittest.main()
