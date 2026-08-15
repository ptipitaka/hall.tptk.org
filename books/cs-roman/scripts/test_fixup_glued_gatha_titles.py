#!/usr/bin/env python3
"""Tests for fixup_glued_gatha_titles."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from cs_roman_text import SECTION_RULE_FLAG  # noqa: E402
from fixup_glued_gatha_titles import unglue_gatha_titles  # noqa: E402


class UnglueGathaTitlesTests(unittest.TestCase):
    def test_splits_tassuddana_center_prose(self) -> None:
        segs = [
            {
                "order": 1,
                "page": 328,
                "segment_type": "prose",
                "source_layout": "center",
                "flags": [SECTION_RULE_FLAG],
                "text": [
                    {
                        "script": "roman",
                        "value": (
                            "Tassuddānaṃ Ubbhataṃ kathinaṃ tīṇi, "
                            "dhovanañca paṭiggaho.{{sp1}} Aññātakāni tīṇeva, "
                            "ubhinnaṃ dūtakena cāti."
                        ),
                    },
                    {
                        "script": "thai",
                        "value": (
                            "ตสฺสุทฺทานํ อุพฺภตํ กถินํ ตีณิ, "
                            "โธวนญฺจ ปฏิคฺคโห.{{sp1}} อญฺญาตกานิ ตีเณว, "
                            "อุภินฺนํ ทูตเกน จาติ."
                        ),
                    },
                ],
            }
        ]
        out, n = unglue_gatha_titles(segs)
        self.assertEqual(n, 1)
        self.assertEqual(len(out), 3)
        self.assertEqual(out[0]["segment_type"], "tassuddānaṃ")
        self.assertEqual(out[0]["order"], 1)
        self.assertEqual(out[0].get("source_layout"), "center")
        self.assertEqual(out[1]["segment_type"], "prose")
        self.assertEqual(out[2]["segment_type"], "prose")
        self.assertIn(SECTION_RULE_FLAG, out[2]["flags"])
        self.assertNotIn(SECTION_RULE_FLAG, out[1]["flags"])
        roman0 = out[0]["text"][0]["value"]
        self.assertEqual(roman0, "Tassuddānaṃ")
        self.assertIn("Ubbhataṃ", out[1]["text"][0]["value"])

    def test_ignores_niddesa_false_positive(self) -> None:
        segs = [
            {
                "order": 1,
                "page": 195,
                "segment_type": "prose",
                "source_layout": "center",
                "flags": [],
                "text": [
                    {
                        "script": "roman",
                        "value": (
                            "Pārāyanatthutigāthāniddesa imassa pārāyanassāti "
                            "tasmā imassa dhammapariyāyassa.{{sp1}} "
                            "Pārāyananteva adhivacanaṃ."
                        ),
                    }
                ],
            }
        ]
        out, n = unglue_gatha_titles(segs)
        self.assertEqual(n, 0)
        self.assertEqual(len(out), 1)


if __name__ == "__main__":
    unittest.main()
