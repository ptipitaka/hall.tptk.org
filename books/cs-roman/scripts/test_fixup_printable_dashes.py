"""Tests for U+23AF → en-dash fixup on stored segment JSON."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from cs_roman_text import EN_DASH, HORIZONTAL_LINE_EXTENSION  # noqa: E402
from fixup_printable_dashes import fix_document_printable_dashes  # noqa: E402


class FixupPrintableDashesTests(unittest.TestCase):
    def test_replaces_in_text_notes_and_symbol_notes(self) -> None:
        doc = {
            "schema_version": 1,
            "segments": [
                {
                    "page": 1,
                    "order": 1,
                    "segment_type": "prose",
                    "text": [
                        {
                            "script": "roman",
                            "value": f"udāhareyya{HORIZONTAL_LINE_EXTENSION}",
                        },
                        {
                            "script": "thai",
                            "value": f"อุทาหเรยฺย{HORIZONTAL_LINE_EXTENSION}",
                        },
                    ],
                    "notes": [
                        f"pāṭho dissati{HORIZONTAL_LINE_EXTENSION} “Evaṃ"
                    ],
                    "symbol_notes": {
                        "*": f"katthaci{HORIZONTAL_LINE_EXTENSION} natthi"
                    },
                }
            ],
        }
        n = fix_document_printable_dashes(doc)
        self.assertEqual(n, 4)
        seg = doc["segments"][0]
        self.assertEqual(
            seg["text"][0]["value"],
            f"udāhareyya{EN_DASH}",
        )
        self.assertEqual(
            seg["text"][1]["value"],
            f"อุทาหเรยฺย{EN_DASH}",
        )
        self.assertEqual(
            seg["notes"][0],
            f"pāṭho dissati{EN_DASH} “Evaṃ",
        )
        self.assertEqual(
            seg["symbol_notes"]["*"],
            f"katthaci{EN_DASH} natthi",
        )
        self.assertNotIn(HORIZONTAL_LINE_EXTENSION, str(doc))

    def test_noop_when_absent(self) -> None:
        doc = {
            "segments": [
                {
                    "segment_type": "prose",
                    "text": [{"script": "roman", "value": "sādhu"}],
                }
            ]
        }
        self.assertEqual(fix_document_printable_dashes(doc), 0)


if __name__ == "__main__":
    unittest.main()
