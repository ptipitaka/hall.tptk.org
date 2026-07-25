"""Unit tests for cs-roman page-break word repair."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from extract_cs_roman_pdf import (  # noqa: E402
    _paragraph_seems_complete,
    _repair_mid_word_split,
)


class RepairMidWordSplitTests(unittest.TestCase):
    def test_no_hyphen_keeps_separate_words(self) -> None:
        prev, nxt = _repair_mid_word_split(
            "… sāmantā hasamānā ṭhitā",
            "hoti. So bhikkhu …",
        )
        self.assertEqual(prev, "… sāmantā hasamānā ṭhitā")
        self.assertEqual(nxt, "hoti. So bhikkhu …")

    def test_hyphen_joins_leading_word(self) -> None:
        prev, nxt = _repair_mid_word_split(
            "agārasmā anagāriyaṃ pabbaj-",
            "jāya. Evaṃ …",
        )
        self.assertEqual(prev, "agārasmā anagāriyaṃ pabbajjāya")
        self.assertEqual(nxt, ". Evaṃ …")

    def test_soft_hyphen_joins_leading_word(self) -> None:
        prev, nxt = _repair_mid_word_split(
            "pabbaj\u00ad",
            "jāya.",
        )
        self.assertEqual(prev, "pabbajjāya")
        self.assertEqual(nxt, ".")


class ParagraphCompleteTests(unittest.TestCase):
    def test_period_then_paren_ref_is_complete(self) -> None:
        self.assertTrue(
            _paragraph_seems_complete(
                "Anāpatti bhikkhu pārājikassa, āpatti thullaccayassati. (14-15)"
            )
        )

    def test_ti_then_paren_ref_is_complete(self) -> None:
        self.assertTrue(
            _paragraph_seems_complete("Anāpatti bhikkhu asañciccāti. (16)")
        )

    def test_thai_digits_paren_ref_is_complete(self) -> None:
        self.assertTrue(
            _paragraph_seems_complete("อนาปตฺติ ภิกฺขุ อสญฺจิจฺจาติ. (๑๔-๑๕)")
        )

    def test_mid_sentence_not_complete(self) -> None:
        self.assertFalse(
            _paragraph_seems_complete("Tena kho pana samayena Āḷavakā bhikkhū")
        )


if __name__ == "__main__":
    unittest.main()
