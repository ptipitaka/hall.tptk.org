#!/usr/bin/env python3
"""Tests for peeling section ``Name nāma.`` labels from folded gāthā."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from cs_roman_text import is_section_nama_colophon  # noqa: E402
from fixup_glued_gatha_nama_colophons import unglue_nama_colophons  # noqa: E402


class SectionNamaColophonDetectTests(unittest.TestCase):
    def test_accepts_pabba_label(self) -> None:
        self.assertTrue(is_section_nama_colophon("Maddīpabbaṃ nāma."))
        self.assertTrue(is_section_nama_colophon("มทฺทีปพฺพํ นาม."))

    def test_accepts_kanda_label(self) -> None:
        self.assertTrue(is_section_nama_colophon("Dohaḷakaṇḍaṃ nāma."))

    def test_rejects_narrative_nama(self) -> None:
        self.assertFalse(is_section_nama_colophon("so hāro lakkhaṇo nāma."))
        self.assertFalse(
            is_section_nama_colophon("ayaṃ nayo aṅkuso nāma.")
        )

    def test_rejects_multi_sentence(self) -> None:
        self.assertFalse(
            is_section_nama_colophon(
                "Vessantarassa anumodi.{{sp1}} Maddīpabbaṃ nāma."
            )
        )


class UnglueNamaColophonTests(unittest.TestCase):
    def test_peels_trailing_bat(self) -> None:
        segs = [
            {
                "order": 1,
                "page": 363,
                "segment_type": "gatha",
                "source_layout": "mixed",
                "review_reasons": ["irregular_gatha_stanza"],
                "needs_review": True,
                "bats": [
                    {
                        "waks": [
                            {
                                "text": [
                                    {
                                        "script": "roman",
                                        "value": "Vessantarassa anumodi,",
                                    },
                                    {
                                        "script": "thai",
                                        "value": "เวสฺสนฺตรสฺส อนุโมทิ,",
                                    },
                                ]
                            },
                            {
                                "text": [
                                    {
                                        "script": "roman",
                                        "value": "puttake dānamuttamaṃ.",
                                    },
                                    {
                                        "script": "thai",
                                        "value": "ปุตฺตเก ทานมุตฺตมํ.",
                                    },
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
                                        "value": "Maddīpabbaṃ nāma.",
                                    },
                                    {
                                        "script": "thai",
                                        "value": "มทฺทีปพฺพํ นาม.",
                                    },
                                ]
                            }
                        ]
                    },
                ],
            }
        ]
        out, n = unglue_nama_colophons(segs)
        self.assertEqual(n, 1)
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0]["segment_type"], "gatha")
        self.assertEqual(len(out[0]["bats"]), 1)
        self.assertNotIn(
            "irregular_gatha_stanza", out[0].get("review_reasons") or []
        )
        self.assertEqual(out[0].get("source_layout"), "bat_line")
        self.assertEqual(out[1]["segment_type"], "prose")
        self.assertEqual(out[1].get("source_layout"), "center")
        self.assertEqual(out[1]["text"][0]["value"], "Maddīpabbaṃ nāma.")

    def test_converts_sole_colophon_gatha(self) -> None:
        segs = [
            {
                "order": 1,
                "page": 339,
                "segment_type": "gatha",
                "source_layout": "wak_line",
                "bats": [
                    {
                        "waks": [
                            {
                                "text": [
                                    {
                                        "script": "roman",
                                        "value": "Jūjakapabbaṃ nāma.",
                                    }
                                ]
                            }
                        ]
                    }
                ],
            }
        ]
        out, n = unglue_nama_colophons(segs)
        self.assertEqual(n, 1)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["segment_type"], "prose")
        self.assertEqual(out[0].get("source_layout"), "center")
        self.assertEqual(out[0]["text"][0]["value"], "Jūjakapabbaṃ nāma.")

    def test_leaves_real_verse_untouched(self) -> None:
        segs = [
            {
                "order": 1,
                "page": 1,
                "segment_type": "gatha",
                "bats": [
                    {
                        "waks": [
                            {
                                "text": [
                                    {
                                        "script": "roman",
                                        "value": "so hāro lakkhaṇo nāma.",
                                    }
                                ]
                            }
                        ]
                    }
                ],
            }
        ]
        out, n = unglue_nama_colophons(segs)
        self.assertEqual(n, 0)
        self.assertEqual(out[0]["segment_type"], "gatha")


if __name__ == "__main__":
    unittest.main()
