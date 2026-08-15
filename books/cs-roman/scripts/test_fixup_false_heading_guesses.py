"""Tests for demoting speech-intro / weak-uncentered false headings."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from extract_cs_roman_pdf import (  # noqa: E402
    Segment,
    _classify_heading,
    demote_false_heading_guesses,
    ends_with_speech_intro_dash,
)
from fixup_false_heading_guesses import fix_segment  # noqa: E402


class SpeechIntroDashTests(unittest.TestCase):
    def test_en_em_dash_detected(self) -> None:
        self.assertTrue(
            ends_with_speech_intro_dash(
                "Atha kho āvuso Assaji bhikkhu imaṃ dhammapariyāyaṃ abhāsi–"
            )
        )
        self.assertTrue(
            ends_with_speech_intro_dash("Te tumhe imāya gāthāya paṭicodetha—")
        )
        self.assertFalse(ends_with_speech_intro_dash("Abhiññātānaṃ pabbajjā"))
        self.assertFalse(ends_with_speech_intro_dash("pabbaj-"))

    def test_classify_rejects_speech_intro_dash(self) -> None:
        kind, reasons = _classify_heading(
            "Atha kho āvuso Assaji bhikkhu imaṃ dhammapariyāyaṃ abhāsi–"
        )
        self.assertIsNone(kind)
        self.assertEqual(reasons, [])

        kind2, _ = _classify_heading("Te tumhe imāya gāthāya paṭicodetha–")
        self.assertIsNone(kind2)

    def test_classify_keeps_centered_style_short_title(self) -> None:
        kind, reasons = _classify_heading("Abhiññātānaṃ pabbajjā")
        self.assertEqual(kind, "title")
        self.assertEqual(reasons, ["weak_heading_heuristic"])

    def test_classify_keeps_structural_chapter(self) -> None:
        kind, reasons = _classify_heading("Cīvaravagga")
        self.assertEqual(kind, "chapter")
        self.assertEqual(reasons, [])


class DemoteFalseHeadingGuessesTests(unittest.TestCase):
    def test_demotes_dash_intro(self) -> None:
        segs = [
            Segment(
                page=53,
                order=1,
                item=None,
                segment_type="title",
                text="Atha kho āvuso Assaji bhikkhu imaṃ dhammapariyāyaṃ abhāsi–",
                review_reasons=["weak_heading_heuristic"],
                needs_review=True,
            )
        ]
        stats = demote_false_heading_guesses(segs)
        self.assertEqual(stats["demoted_speech_intro_dash"], 1)
        self.assertEqual(segs[0].segment_type, "prose")
        self.assertEqual(segs[0].review_reasons, [])
        self.assertFalse(segs[0].needs_review)

    def test_demotes_weak_without_center(self) -> None:
        segs = [
            Segment(
                page=9,
                order=1,
                item=None,
                segment_type="title",
                text="Aññātāro bhavissantī”ti.]",
                review_reasons=["weak_heading_heuristic"],
                needs_review=True,
            )
        ]
        stats = demote_false_heading_guesses(segs)
        self.assertEqual(stats["demoted_weak_uncentered"], 1)
        self.assertEqual(segs[0].segment_type, "prose")

    def test_keeps_weak_when_centered(self) -> None:
        segs = [
            Segment(
                page=54,
                order=1,
                item=None,
                segment_type="title",
                text="Abhiññātānaṃ pabbajjā",
                source_layout="center",
                review_reasons=["weak_heading_heuristic"],
                needs_review=True,
            )
        ]
        stats = demote_false_heading_guesses(segs)
        self.assertEqual(stats["demoted_speech_intro_dash"], 0)
        self.assertEqual(stats["demoted_weak_uncentered"], 0)
        self.assertEqual(segs[0].segment_type, "title")


class FixupFalseHeadingGuessesTests(unittest.TestCase):
    def test_fixup_clears_heading_meta(self) -> None:
        seg = {
            "segment_type": "title",
            "heading_kind": "h2",
            "in_toc": False,
            "needs_review": True,
            "review_reasons": [
                "weak_heading_heuristic",
                "heading_level_unmatched_matika",
            ],
            "text": [
                {
                    "script": "roman",
                    "value": "Te tumhe imāya gāthāya paṭicodetha–",
                },
                {
                    "script": "thai",
                    "value": "เต ตุเมฺห อิมาย คาถาย ปฏิโจเทถ–",
                },
            ],
        }
        self.assertTrue(fix_segment(seg))
        self.assertEqual(seg["segment_type"], "prose")
        self.assertNotIn("heading_kind", seg)
        self.assertNotIn("review_reasons", seg)
        self.assertNotIn("needs_review", seg)


if __name__ == "__main__":
    unittest.main()
