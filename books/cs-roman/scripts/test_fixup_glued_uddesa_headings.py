"""Tests for peeling glued pātimokkha uddesa headings in segment JSON."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from fixup_glued_uddesa_headings import unglue_uddesa_headings  # noqa: E402


class UnglueUddesaHeadingsTests(unittest.TestCase):
    def test_peels_prose_item_into_chapter_and_body(self) -> None:
        segments = [
            {
                "page": 294,
                "order": 1,
                "segment_type": "prose",
                "item": 1,
                "text": [
                    {
                        "script": "roman",
                        "value": (
                            "Cīvaravagga 1.{{sp1}} Paṭhamakathinasikkhāpada "
                            "Ime kho panāyasmanto tiṃsa nissaggiyā pācittiyā "
                            "dhammā uddesaṃ āgacchanti."
                        ),
                    },
                    {
                        "script": "thai",
                        "value": (
                            "จีวรวคฺค ๑.{{sp1}} ปฐมกถินสิกฺขาปท อิเม โข "
                            "ปนายสฺมนฺโต ติํส นิสฺสคฺคิยา ปาจิตฺติยา ธมฺมา "
                            "อุทฺเทสํ อาคจฺฉนฺติ."
                        ),
                    },
                ],
                "source_layout": "center",
            },
            {
                "page": 294,
                "order": 2,
                "segment_type": "prose",
                "item": 459,
                "text": [
                    {"script": "roman", "value": "Tena samayena…"},
                    {"script": "thai", "value": "เตน สมเยน…"},
                ],
            },
        ]
        fixed = unglue_uddesa_headings(segments)
        self.assertEqual(fixed, 1)
        self.assertEqual(len(segments), 3)
        head, uddesa, body = segments
        self.assertEqual(head["order"], 1)
        self.assertEqual(uddesa["order"], 2)
        self.assertEqual(body["order"], 3)
        self.assertEqual(head["segment_type"], "chapter")
        self.assertEqual(head["section_no"], 1)
        self.assertNotIn("item", head)
        self.assertEqual(head["heading_kind"], "h1")
        self.assertTrue(head["in_toc"])
        roman = next(t["value"] for t in head["text"] if t["script"] == "roman")
        self.assertEqual(roman, "Cīvaravagga 1. Paṭhamakathinasikkhāpada")
        self.assertNotIn("{{sp1}}", roman)
        self.assertEqual(uddesa["segment_type"], "prose")
        self.assertNotIn("item", uddesa)
        uddesa_roman = next(
            t["value"] for t in uddesa["text"] if t["script"] == "roman"
        )
        self.assertTrue(uddesa_roman.startswith("Ime kho"))
        self.assertEqual(body["item"], 459)

    def test_peels_already_typed_chapter_keeps_heading_kind(self) -> None:
        segments = [
            {
                "page": 468,
                "order": 1,
                "segment_type": "chapter",
                "text": [
                    {
                        "script": "roman",
                        "value": (
                            "Parimaṇḍalavagga Ime kho panāyyāyo sekhiyā "
                            "dhammā uddesaṃ āgacchanti."
                        ),
                    }
                ],
                "heading_kind": "h1",
                "in_toc": True,
                "source_layout": "center",
            }
        ]
        fixed = unglue_uddesa_headings(segments)
        self.assertEqual(fixed, 1)
        self.assertEqual(len(segments), 2)
        self.assertEqual(segments[0]["heading_kind"], "h1")
        self.assertTrue(segments[0]["in_toc"])
        roman = next(
            t["value"] for t in segments[0]["text"] if t["script"] == "roman"
        )
        self.assertEqual(roman, "Parimaṇḍalavagga")


if __name__ == "__main__":
    unittest.main()
