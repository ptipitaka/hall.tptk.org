"""Unit tests for CS Roman fake-bold helpers."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from cs_roman_bold import (  # noqa: E402
    BoldSpan,
    bold_ranges_from_geoms,
    bold_ranges_in_text,
    ranges_to_runs,
    substantial_bold_ranges,
    subtract_marker_ranges,
    unbold_ranges_in_runs,
)
from cs_roman_hanging import PageLine  # noqa: E402
from cs_roman_text import roman_to_thai, transliterate_runs  # noqa: E402


class BboxBoldBleedTests(unittest.TestCase):
    """Lemma bold must not paint the same word later in the segment."""

    def test_quoted_lemma_not_bolded(self) -> None:
        # Mirrors 01Vin01 §94: bold headword on line 1; plain repeat in quotes
        # on the following wrap line (measured PDF geometry).
        prepared = (
            "Bhūmaṭṭhaṃ nāma bhaṇḍaṃ bhūmiyaṃ nikkhittaṃ hoti nikhātaṃ "
            "paṭicchannaṃ. “Bhūmaṭṭhaṃ bhaṇḍaṃ avaharissāmī”ti theyyacitto"
        )
        lines = [
            PageLine(
                y0=373.23,
                x0=84.24,
                x1=425.0,
                y1=388.71,
                text="94. Bhūmaṭṭhaṃ nāma bhaṇḍaṃ bhūmiyaṃ nikkhittaṃ hoti nikhātaṃ",
            ),
            PageLine(
                y0=391.11,
                x0=62.64,
                x1=431.44,
                y1=406.59,
                text=(
                    "paṭicchannaṃ. “Bhūmaṭṭhaṃ bhaṇḍaṃ avaharissāmī”ti "
                    "theyyacitto dutiyaṃ"
                ),
            ),
        ]
        spans = [
            BoldSpan("Ayampī", (84.24, 93.58, 122.96, 105.58)),
            BoldSpan("Bhūmaṭṭhaṃ", (102.66, 376.12, 164.26, 388.12)),
        ]
        ranges = bold_ranges_from_geoms(prepared, spans, lines)
        self.assertEqual(ranges, [(0, len("Bhūmaṭṭhaṃ"))])
        # String-only path still bleeds — documents why geom matching exists.
        bled = bold_ranges_in_text(prepared, ["Bhūmaṭṭhaṃ"])
        self.assertEqual(len(bled), 2)

    def test_same_line_x_picks_correct_occurrence(self) -> None:
        prepared = "Foo bar Foo baz"
        lines = [
            PageLine(
                y0=100.0,
                x0=60.0,
                x1=300.0,
                y1=114.0,
                text="Foo bar Foo baz",
            )
        ]
        # Stroke over the second "Foo" (right half of the line).
        spans = [BoldSpan("Foo", (180.0, 101.0, 210.0, 113.0))]
        ranges = bold_ranges_from_geoms(prepared, spans, lines)
        second = prepared.index("Foo", 1)
        self.assertEqual(ranges, [(second, second + 3)])

    def test_multiline_sikkhapada_full_bold(self) -> None:
        """Tall multi-line stroke strings must bold the rule, not vanish.

        Regression: 02Vin02 §679 — texttrace emits near-full-line strokes whose
        bbox straddles wraps; requiring the match inside a *single* line window
        dropped all bold for the sikkhāpada.
        """
        prepared = (
            "“Yā pana bhikkhunī ussayavādikā vihareyya gahapatinā vā "
            "gahapatiputtena vā dāsena vā kammakārena{{n0}} vā antamaso "
            "samaṇaparibbājakenāpi, ayaṃ bhikkhunī paṭhamāpattikaṃ dhammaṃ "
            "āpannā nissāraṇīyaṃ saṃghādisesan”ti."
        )
        lines = [
            PageLine(
                y0=447.6,
                x0=84.2,
                x1=400.0,
                y1=463.0,
                text="679. “Yā pana bhikkhunī ussayavādikā vihareyya gahapatinā vā",
            ),
            PageLine(
                y0=464.2,
                x0=62.6,
                x1=404.0,
                y1=480.0,
                text="gahapatiputtena vā dāsena vā kammakārena1 vā antamaso",
            ),
            PageLine(
                y0=481.8,
                x0=62.6,
                x1=400.0,
                y1=497.0,
                text="samaṇaparibbājakenāpi, ayaṃ bhikkhunī paṭhamāpattikaṃ dhammaṃ",
            ),
            PageLine(
                y0=498.5,
                x0=62.6,
                x1=280.0,
                y1=514.0,
                text="āpannā nissāraṇīyaṃ saṃghādisesan”ti.",
            ),
        ]
        spans = [
            BoldSpan(
                "“Yā pana bhikkhunī ussayavādikā vihareyya gahapatinā vā "
                "gahapatiputtena vā dāsen",
                (62.6, 450.5, 399.0, 467.5),
            ),
            BoldSpan(
                "vā antamaso samaṇaparibbājakenāpi, ayaṃ bhikkhunī "
                "paṭhamāpattikaṃ dhammaṃ āpannā nissāraṇīyaṃ saṃghādisesan",
                (62.6, 468.0, 404.4, 485.0),
            ),
        ]
        ranges = bold_ranges_from_geoms(prepared, spans, lines)
        bold_chars = sum(b - a for a, b in ranges)
        # Most of the rule is bold; marker hole is fine.
        self.assertGreater(bold_chars / len(prepared), 0.75)
        self.assertTrue(any(a <= 0 < b or a <= 1 < b for a, b in ranges))

    def test_unrelated_page_span_ignored(self) -> None:
        prepared = "Bhūmaṭṭhaṃ nāma bhaṇḍaṃ."
        lines = [
            PageLine(
                y0=373.23,
                x0=84.24,
                x1=425.0,
                y1=388.71,
                text="94. Bhūmaṭṭhaṃ nāma bhaṇḍaṃ.",
            )
        ]
        spans = [BoldSpan("Ayampī", (84.24, 93.58, 122.96, 105.58))]
        self.assertEqual(bold_ranges_from_geoms(prepared, spans, lines), [])

    def test_two_lemmas_same_line_across_sp1(self) -> None:
        # 01Vin01 §99: both Nāvā and Nāvaṭṭhaṃ bold on one PDF line; quote plain.
        prepared = (
            "Nāvā nāma yāya tarati.{{sp1}} Nāvaṭṭhaṃ nāma bhaṇḍaṃ nāvāya "
            "nikkhittaṃ hoti. “Nāvaṭṭhaṃ bhaṇḍaṃ avaharissāmī”ti theyyacitto"
        )
        lines = [
            PageLine(
                y0=90.7,
                x0=84.2,
                x1=425.0,
                y1=106.2,
                text="99. Nāvā nāma yāya tarati. Nāvaṭṭhaṃ nāma bhaṇḍaṃ nāvāya",
            ),
            PageLine(
                y0=109.0,
                x0=62.6,
                x1=431.0,
                y1=124.5,
                text=(
                    "nikkhittaṃ hoti. “Nāvaṭṭhaṃ bhaṇḍaṃ avaharissāmī”ti "
                    "theyyacitto dutiyaṃ"
                ),
            ),
        ]
        spans = [
            BoldSpan("Nāvā", (102.7, 93.6, 128.2, 105.6)),
            BoldSpan("Nāvaṭṭhaṃ", (215.1, 93.6, 271.5, 105.6)),
        ]
        ranges = bold_ranges_from_geoms(prepared, spans, lines)
        bold_bits = [
            prepared[a:b]
            for a, b in ranges
        ]
        self.assertEqual(bold_bits, ["Nāvā", "Nāvaṭṭhaṃ"])
        # Quoted repeat stays plain.
        quoted_at = prepared.index("“Nāvaṭṭhaṃ") + 1
        self.assertFalse(any(a <= quoted_at < b for a, b in ranges))


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

    def test_thai_runs_strip_legacy_sp1(self) -> None:
        """Legacy ``{{sp1}}`` is stripped; must not become สฺปฺ/๑."""
        roman = "yācitabbā.{{sp1}} Dutiyampi"
        roman_runs = [
            {"value": "yācitabbā", "bold": True},
            {"value": ".{{sp1}} Dutiyampi", "bold": False},
        ]
        thai_runs = transliterate_runs(roman_runs)
        joined = "".join(r["value"] for r in thai_runs)
        self.assertEqual(joined, roman_to_thai(roman))
        self.assertNotIn("{{sp1}}", joined)
        self.assertNotIn("สฺปฺ", joined)
        self.assertIn("ยาจิตพฺพา. ทุติยมฺปิ", joined)
        self.assertNotIn("๑", "".join(r["value"] for r in thai_runs if r.get("bold")))


class UnboldRangesTests(unittest.TestCase):
    def test_clears_span_and_joins_adjacent_plain(self) -> None:
        text = "ayampi pārājiko hoti asaṃvāso”ti."
        runs = [
            {"value": "ayampi pārājiko hoti asaṃvāso”ti", "bold": True},
            {"value": ".", "bold": False},
        ]
        quote_end = text.index("”") + 1
        peeled = unbold_ranges_in_runs(runs, [(quote_end, len(text))])
        self.assertEqual(
            peeled,
            [
                {"value": "ayampi pārājiko hoti asaṃvāso”", "bold": True},
                {"value": "ti.", "bold": False},
            ],
        )

    def test_noop_when_already_plain(self) -> None:
        runs = [
            {"value": "asaṃvāso”", "bold": True},
            {"value": "ti.", "bold": False},
        ]
        self.assertIs(unbold_ranges_in_runs(runs, [(9, 12)]), runs)


if __name__ == "__main__":
    unittest.main()
