"""Tests for solid mid-word hyphen fixup on segment documents."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from fixup_solid_midword_hyphens import strip_document_midword_hyphens  # noqa: E402
from cs_roman_text import roman_value_from_text_field  # noqa: E402


class FixupSolidMidwordHyphensTests(unittest.TestCase):
    def test_strips_body_keeps_pa_and_notes(self) -> None:
        doc = {
            "schema_version": 1,
            "segments": [
                {
                    "order": 1,
                    "segment_type": "prose",
                    "page": 1,
                    "text": [
                        {"script": "roman", "value": "na-upanissaye -pa- hoti."},
                        {"script": "thai", "value": "น-อุปนิสฺสเย ฯเปฯ โหติ."},
                    ],
                    "notes": ["na-ārammaṇe"],
                    "symbol_notes": {"*": "avitakka-avicāro"},
                }
            ],
        }
        fixed = strip_document_midword_hyphens(doc)
        self.assertGreater(fixed, 0)
        seg = doc["segments"][0]
        roman = roman_value_from_text_field(seg["text"])
        self.assertEqual(roman, "naupanissaye -pa- hoti.")
        self.assertIn("-pa-", roman)
        self.assertNotIn("na-upa", roman)
        # Notes keep hyphens for generate-time morpheme splits.
        self.assertEqual(seg["notes"], ["na-ārammaṇe"])
        self.assertEqual(seg["symbol_notes"]["*"], "avitakka-avicāro")
        thai = next(
            e["value"] for e in seg["text"] if e["script"] == "thai"
        )
        self.assertEqual(thai, "นอุปนิสฺสเย ฯเปฯ โหติ.")
        self.assertNotIn("-", thai.replace("ฯเปฯ", ""))


if __name__ == "__main__":
    unittest.main()
