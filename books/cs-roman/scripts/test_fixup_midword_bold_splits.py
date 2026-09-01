"""Tests for mid-token bold-split fixup on segment documents."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from cs_roman_text import roman_to_thai  # noqa: E402
from fixup_midword_bold_splits import (  # noqa: E402
    snap_document_midword_bold_splits,
)


class FixupMidwordBoldSplitsTests(unittest.TestCase):
    def test_closes_peyya_leftover_and_rederives_thai(self) -> None:
        roman = (
            "“Yo pana bhikkhu agilāno visibbanāpekkho jotiṃ "
            "samādaheyya vā samādahāpeyya vā aññatra "
            "tathārūpappaccayā pācittiyan”ti."
        )
        doc = {
            "schema_version": 1,
            "segments": [
                {
                    "page": 153,
                    "order": 1147,
                    "segment_type": "prose",
                    "text": [
                        {
                            "script": "roman",
                            "value": roman,
                            "runs": [
                                {"value": "“", "bold": False},
                                {
                                    "value": (
                                        "Yo pana bhikkhu agilāno "
                                        "visibbanāpekkho jotiṃ "
                                        "samādaheyya vā"
                                    ),
                                    "bold": True,
                                },
                                {"value": " ", "bold": False},
                                {"value": "samādahāpeyy", "bold": True},
                                {
                                    "value": (
                                        "a vā aññatra tathārūpappaccayā "
                                        "pācittiyan”ti."
                                    ),
                                    "bold": False,
                                },
                            ],
                        },
                        {
                            "script": "thai",
                            "value": roman_to_thai(roman),
                            "runs": [
                                {"value": "“", "bold": False},
                                {"value": "โย", "bold": True},
                                {"value": " ", "bold": False},
                                {
                                    "value": roman_to_thai("samādahāpeyy"),
                                    "bold": True,
                                },
                                {
                                    "value": roman_to_thai(
                                        "a vā aññatra tathārūpappaccayā "
                                        "pācittiyan”ti."
                                    ),
                                    "bold": False,
                                },
                            ],
                        },
                    ],
                }
            ],
        }
        fixed = snap_document_midword_bold_splits(doc)
        self.assertEqual(fixed, 1)
        roman_entry = doc["segments"][0]["text"][0]
        self.assertEqual(
            [r for r in roman_entry["runs"] if r["bold"]][-1]["value"],
            "samādahāpeyya",
        )
        thai_entry = doc["segments"][0]["text"][1]
        bold_thai = "".join(
            r["value"] for r in thai_entry["runs"] if r["bold"]
        )
        self.assertIn(roman_to_thai("samādahāpeyya"), bold_thai)
        self.assertNotIn("เปยฺยฺ", bold_thai)
        self.assertEqual(snap_document_midword_bold_splits(doc), 0)


if __name__ == "__main__":
    unittest.main()
