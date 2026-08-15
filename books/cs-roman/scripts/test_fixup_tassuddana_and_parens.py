#!/usr/bin/env python3
"""Tests for peeling expansion parentheticals glued after verse/prose."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from fixup_glued_parentheticals import unglue_parentheticals  # noqa: E402
from fixup_tassuddana_labels import retag_tassuddana_labels  # noqa: E402


class UnglueParentheticalTests(unittest.TestCase):
    def test_peels_paren_from_last_gatha_wak(self) -> None:
        paren = (
            "(Appamādavaggo Bojjhaṅgasaṃyuttassa "
            "bojjhaṅgavasena vitthāretabbo.)"
        )
        segs = [
            {
                "order": 1,
                "page": 119,
                "segment_type": "gatha",
                "source_layout": "bat_line",
                "review_reasons": ["irregular_gatha_stanza"],
                "needs_review": True,
                "bats": [
                    {
                        "waks": [
                            {
                                "text": [
                                    {
                                        "script": "roman",
                                        "value": "Tathāgataṃ Padaṃ Kūṭaṃ,",
                                    }
                                ]
                            },
                            {
                                "text": [
                                    {
                                        "script": "roman",
                                        "value": "Mūlaṃ Sārena Vassikaṃ.",
                                    }
                                ]
                            },
                        ]
                    },
                    {
                        "waks": [
                            {
                                "text": [
                                    {
                                        "script": "roman",
                                        "value": (
                                            "Rājā Candimasūriyā ca, "
                                            "Vatthena dasamaṃ padanti. "
                                            + paren
                                        ),
                                    }
                                ]
                            },
                        ]
                    },
                ],
            }
        ]
        out, n = unglue_parentheticals(segs)
        self.assertEqual(n, 1)
        self.assertEqual(len(out), 2)
        last_wak = out[0]["bats"][-1]["waks"][-1]["text"][0]["value"]
        self.assertEqual(
            last_wak,
            "Rājā Candimasūriyā ca, Vatthena dasamaṃ padanti.",
        )
        self.assertNotIn("irregular_gatha_stanza", out[0].get("review_reasons") or [])
        self.assertEqual(out[1]["segment_type"], "prose")
        self.assertEqual(out[1]["source_layout"], "center")
        self.assertEqual(out[1]["text"][0]["value"], paren)


class RetagTassuddanaTests(unittest.TestCase):
    def test_retags_title_to_tassuddana(self) -> None:
        segs = [
            {
                "order": 1,
                "page": 1,
                "segment_type": "title",
                "heading_kind": "h1",
                "in_toc": True,
                "text": [
                    {"script": "roman", "value": "Tassuddānaṃ"},
                    {"script": "thai", "value": "ตสฺสุทฺทานํ"},
                ],
            }
        ]
        out, n = retag_tassuddana_labels(segs)
        self.assertEqual(n, 1)
        self.assertEqual(out[0]["segment_type"], "tassuddānaṃ")
        self.assertEqual(out[0]["source_layout"], "center")
        self.assertNotIn("heading_kind", out[0])
        self.assertNotIn("in_toc", out[0])


if __name__ == "__main__":
    unittest.main()
