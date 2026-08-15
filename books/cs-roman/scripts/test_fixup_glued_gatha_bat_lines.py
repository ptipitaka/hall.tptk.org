#!/usr/bin/env python3
"""Tests for fixup_glued_gatha_bat_lines."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from fixup_glued_gatha_bat_lines import (  # noqa: E402
    gatha_has_glued_printed_lines,
    gatha_has_unsplit_bat_wak,
    unglue_gatha_bat_lines,
)
from cs_roman_text import SECTION_RULE_FLAG, roman_value_from_text_field  # noqa: E402


def _wak(roman: str, thai: str = "") -> dict:
    text = [{"script": "roman", "value": roman}]
    if thai:
        text.append({"script": "thai", "value": thai})
    return {"text": text}


class UnglueGathaBatLinesTests(unittest.TestCase):
    def test_detects_glued_right_wak(self) -> None:
        seg = {
            "segment_type": "gatha",
            "source_layout": "bat_line",
            "bats": [
                {
                    "waks": [
                        _wak("Aññāṇā Adassanā ceva,"),
                        _wak("Anabhisamayā Ananubodhā."),
                    ]
                },
                {
                    "waks": [
                        _wak("Appaṭivedhā Asallakkhaṇā,"),
                        _wak(
                            "Anupalakkhaṇena Appaccupalakkhaṇā.{{sp1}} "
                            "Asamapekkhaṇā Appaccupekkhaṇā Appaccakkhakammanti."
                        ),
                    ]
                },
            ],
        }
        self.assertTrue(gatha_has_glued_printed_lines(seg))

    def test_unglues_vacchagotta_shape(self) -> None:
        segs = [
            {
                "order": 1,
                "page": 223,
                "segment_type": "gatha",
                "source_layout": "bat_line",
                "bats": [
                    {
                        "waks": [
                            _wak(
                                "Aññāṇā Adassanā ceva,",
                                "อญฺญาณา อทสฺสนา เจว,",
                            ),
                            _wak(
                                "Anabhisamayā Ananubodhā.",
                                "อนภิสมยา อนนุโพธา.",
                            ),
                        ]
                    },
                    {
                        "waks": [
                            _wak(
                                "Appaṭivedhā Asallakkhaṇā,",
                                "อปฺปฏิเวธา อสลฺลกฺขณา,",
                            ),
                            _wak(
                                "Anupalakkhaṇena Appaccupalakkhaṇā.{{sp1}} "
                                "Asamapekkhaṇā Appaccupekkhaṇā "
                                "Appaccakkhakammanti.",
                                "อนุปลกฺขเณน อปฺปจฺจุปลกฺขณา.{{sp1}} "
                                "อสมเปกฺขณา อปฺปจฺจุเปกฺขณา "
                                "อปฺปจฺจกฺขกมฺมนฺติ.",
                            ),
                        ]
                    },
                ],
            }
        ]
        out, n = unglue_gatha_bat_lines(segs)
        self.assertEqual(n, 1)
        gathas = [s for s in out if s.get("segment_type", "").startswith("gatha")]
        flat: list[str] = []
        for g in gathas:
            for bat in g.get("bats") or []:
                for wak in bat.get("waks") or []:
                    flat.append(roman_value_from_text_field(wak.get("text")))
        self.assertEqual(flat[2], "Appaṭivedhā Asallakkhaṇā,")
        self.assertEqual(flat[3], "Anupalakkhaṇena Appaccupalakkhaṇā.")
        self.assertTrue(any(t.startswith("Asamapekkhaṇā") for t in flat))
        self.assertNotIn("Asamapekkhaṇā", flat[3])

    def test_ignores_clean_bat_line(self) -> None:
        segs = [
            {
                "order": 1,
                "page": 1,
                "segment_type": "gatha",
                "source_layout": "bat_line",
                "bats": [
                    {
                        "waks": [
                            _wak("Aññāṇā Adassanā ceva,"),
                            _wak("Anabhisamayā Ananubodhā."),
                        ]
                    }
                ],
            }
        ]
        out, n = unglue_gatha_bat_lines(segs)
        self.assertEqual(n, 0)
        self.assertEqual(len(out), 1)

    def test_refolds_unsplit_bat_after_section_rule(self) -> None:
        """13Sam02 p.340: last บาท stayed one วรรค after ``_____`` was flagged."""
        segs = [
            {
                "order": 2167,
                "page": 340,
                "segment_type": "gatha",
                "source_layout": "bat_line",
                "flags": [SECTION_RULE_FLAG],
                "needs_review": True,
                "review_reasons": ["irregular_gatha_stanza"],
                "bats": [
                    {
                        "waks": [
                            _wak(
                                "Vesālī Vajji Nāḷandā,",
                                "เวสาลี วชฺชิ นาฬนฺทา,",
                            ),
                            _wak(
                                "Bhāradvāja Soṇo ca Ghosito.",
                                "ภารทฺวาช โสโณ จ โฆสิโต.",
                            ),
                        ]
                    },
                    {
                        "waks": [
                            _wak(
                                "Hāliddiko Nakulapitā, Lohicco Verahaccānīti.",
                                "หาลิทฺทิโก นกุลปิตา, โลหิจฺโจ เวรหจฺจานีติ.",
                            ),
                        ]
                    },
                ],
            }
        ]
        self.assertTrue(gatha_has_unsplit_bat_wak(segs[0]))
        out, n = unglue_gatha_bat_lines(segs)
        self.assertEqual(n, 1)
        self.assertEqual(len(out), 1)
        bats = out[0]["bats"]
        self.assertEqual([len(b["waks"]) for b in bats], [2, 2])
        self.assertEqual(out[0].get("source_layout"), "bat_line")
        self.assertNotIn("irregular_gatha_stanza", out[0].get("review_reasons") or [])
        self.assertIn(SECTION_RULE_FLAG, out[0].get("flags") or [])
        self.assertEqual(
            roman_value_from_text_field(bats[1]["waks"][0]["text"]),
            "Hāliddiko Nakulapitā,",
        )
        self.assertEqual(
            roman_value_from_text_field(bats[1]["waks"][1]["text"]),
            "Lohicco Verahaccānīti.",
        )

    def test_does_not_refold_mixed_trailing_bat_line(self) -> None:
        """05Vin05 p.257: mixed บท with a last 1-wak ``A, B.`` printed line."""
        segs = [
            {
                "order": 1941,
                "page": 257,
                "item": 336,
                "segment_type": "gatha",
                "source_layout": "mixed",
                "review_reasons": ["mixed_gatha_layout"],
                "bats": [
                    {
                        "waks": [
                            _wak("Sabbānipetāni viyākarohi,"),
                            _wak("Handa vākyaṃ suṇoma te."),
                        ]
                    },
                    {
                        "waks": [
                            _wak("Ekatiṃsā ye garukā, aṭṭhettha anavasesā."),
                            _wak(
                                "Ye garukā te duṭṭhullā, "
                                "ye duṭṭhullā sā sīlavipatti."
                            ),
                        ]
                    },
                    {
                        "waks": [
                            _wak(
                                "Pārājikaṃ saṃghādiseso, "
                                "“sīlavipattī”ti vuccati."
                            ),
                        ]
                    },
                ],
            }
        ]
        self.assertFalse(gatha_has_unsplit_bat_wak(segs[0]))
        out, n = unglue_gatha_bat_lines(segs)
        self.assertEqual(n, 0)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["source_layout"], "mixed")
        self.assertEqual([len(b["waks"]) for b in out[0]["bats"]], [2, 2, 1])
        self.assertEqual(
            roman_value_from_text_field(out[0]["bats"][2]["waks"][0]["text"]),
            "Pārājikaṃ saṃghādiseso, “sīlavipattī”ti vuccati.",
        )

    def test_does_not_unglue_yamaka_wak_line(self) -> None:
        """35Abhi07 p.76: Yamaka ``X. Y`` is one printed line, not PDF glue."""
        segs = [
            {
                "order": 544,
                "page": 76,
                "item": 5,
                "segment_type": "gatha",
                "source_layout": "wak_line",
                "review_reasons": ["irregular_gatha_stanza"],
                "bats": [
                    {
                        "waks": [
                            _wak("Sotaṃ sotindriyaṃ. Indriyā cakkhundriyaṃ -pa-."),
                            _wak("Sotaṃ sotindriyaṃ."),
                        ]
                    },
                    {"waks": [_wak(". Indriyā aññātāvindriyaṃ.")]},
                ],
            }
        ]
        self.assertFalse(gatha_has_glued_printed_lines(segs[0]))
        out, n = unglue_gatha_bat_lines(segs)
        self.assertEqual(n, 0)
        self.assertEqual(len(out), 1)
        self.assertEqual(
            roman_value_from_text_field(out[0]["bats"][0]["waks"][0]["text"]),
            "Sotaṃ sotindriyaṃ. Indriyā cakkhundriyaṃ -pa-.",
        )


if __name__ == "__main__":
    unittest.main()