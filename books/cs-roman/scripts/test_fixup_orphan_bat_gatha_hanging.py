"""Tests for numbered hanging / orphan → gāthā promotion."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from fixup_orphan_bat_gatha_hanging import fix_segments  # noqa: E402
from generate_cs_roman_tex import gatha_stanza_line_bodies  # noqa: E402


def _text(roman: str, thai: str = "") -> list[dict]:
    out = [{"script": "roman", "value": roman}]
    if thai:
        out.append({"script": "thai", "value": thai})
    return out


def _wak(roman: str, thai: str = "") -> dict:
    return {"text": _text(roman, thai)}


class NumberedHangingToGathaTests(unittest.TestCase):
    def test_promotes_hanging_bat_pair(self) -> None:
        segs = [
            {
                "order": 1,
                "segment_type": "prose",
                "item": 1,
                "source_layout": "hanging",
                "text": _text(
                    "Vessantaraṃ taṃ pucchāmi, sakuṇa bhaddamatthu te.",
                    "เวสฺสนฺตรํ ตํ ปุจฺฉามิ, สกุณ ภทฺทมตฺถุ เต.",
                ),
                "hanging_lines": [
                    _text(
                        "Rajjaṃ kāretukāmena, kiṃ su kiccaṃ kataṃ varaṃ.",
                        "รชฺชํ กาเรตุกาเมน, กิํ สุ กิจฺจํ กตํ วรํ.",
                    )
                ],
            }
        ]
        out, n = fix_segments(segs)
        self.assertEqual(n, 1)
        self.assertEqual(len(out), 1)
        g = out[0]
        self.assertEqual(g["segment_type"], "gatha")
        self.assertEqual(g["source_layout"], "bat_line")
        self.assertEqual(g["item"], 1)
        self.assertEqual(len(g["bats"]), 2)
        self.assertNotIn("hanging_lines", g)
        bodies = gatha_stanza_line_bodies(g)
        self.assertEqual(len(bodies), 2)
        self.assertTrue(bodies[0].startswith(r"\csromangathaitembat{1}"))
        self.assertTrue(bodies[1].startswith(r"\csromangathacontbat{"))

    def test_merges_prose_plus_orphan_one_bat(self) -> None:
        segs = [
            {
                "order": 1,
                "segment_type": "prose",
                "item": 1,
                "text": _text(
                    "Vessantaraṃ taṃ pucchāmi, sakuṇa bhaddamatthu te.",
                    "เวสฺสนฺตรํ ตํ ปุจฺฉามิ, สกุณ ภทฺทมตฺถุ เต.",
                ),
            },
            {
                "order": 2,
                "segment_type": "gatha",
                "source_layout": "bat_line",
                "bats": [
                    {
                        "waks": [
                            _wak("Rajjaṃ kāretukāmena,", "รชฺชํ กาเรตุกาเมน,"),
                            _wak(
                                "kiṃ su kiccaṃ kataṃ varaṃ.",
                                "กิํ สุ กิจฺจํ กตํ วรํ.",
                            ),
                        ]
                    }
                ],
                "needs_review": True,
                "review_reasons": ["irregular_gatha_stanza"],
            },
        ]
        out, n = fix_segments(segs)
        self.assertEqual(n, 1)
        g = out[0]
        self.assertEqual(g["segment_type"], "gatha")
        self.assertEqual(g["item"], 1)
        self.assertEqual(len(g["bats"]), 2)

    def test_merges_after_nama_colophon_peel(self) -> None:
        """23Khu06 §2266: prose bat head + clean 1-bat after ``nāma.`` peel."""
        segs = [
            {
                "order": 1,
                "page": 363,
                "segment_type": "prose",
                "item": 2266,
                "text": _text(
                    "Iti Maddī varārohā, rājaputtī yasassinī.",
                    "อิติ มทฺที วราโรหา, ราชปุตฺตี ยสสฺสินี.",
                ),
            },
            {
                "order": 2,
                "page": 363,
                "segment_type": "gatha",
                "source_layout": "bat_line",
                "item": None,
                "bats": [
                    {
                        "waks": [
                            _wak(
                                "Vessantarassa anumodi,",
                                "เวสฺสนฺตรสฺส อนุโมทิ,",
                            ),
                            _wak(
                                "puttake dānamuttamaṃ.",
                                "ปุตฺตเก ทานมุตฺตมํ.",
                            ),
                        ]
                    }
                ],
            },
            {
                "order": 3,
                "page": 363,
                "segment_type": "prose",
                "source_layout": "center",
                "text": _text("Maddīpabbaṃ nāma.", "มทฺทีปพฺพํ นาม."),
            },
        ]
        out, n = fix_segments(segs)
        self.assertEqual(n, 1)
        self.assertEqual(len(out), 2)
        g = out[0]
        self.assertEqual(g["segment_type"], "gatha")
        self.assertEqual(g["item"], 2266)
        self.assertEqual(g["source_layout"], "bat_line")
        self.assertEqual(len(g["bats"]), 2)
        bodies = gatha_stanza_line_bodies(g)
        self.assertEqual(len(bodies), 2)
        self.assertTrue(bodies[0].startswith(r"\csromangathaitembat{2266}"))
        self.assertTrue(bodies[1].startswith(r"\csromangathacontbat{"))
        self.assertEqual(out[1].get("source_layout"), "center")

    def test_does_not_merge_kammavaca_with_following_one_bat(self) -> None:
        """04Vin04 p.226: ñatti close is prose, not a บาท head."""
        segs = [
            {
                "order": 1,
                "page": 226,
                "segment_type": "prose",
                "item": 234,
                "text": _text(
                    "Sammato saṃghena itthannāmo bhikkhu salākaggāhāpako, "
                    "khamati saṃghassa, tasmā tuṇhī, evametaṃ dhārayāmī”ti.",
                    "สมฺมโต สงฺเฆน อิตฺถนฺนาโม ภิกฺขุ สลากคฺคาหาปโก, "
                    "ขมติ สงฺฆสฺส, ตสฺมา ตุณฺหี, เอวเมตํ ธารยามี”ติ.",
                ),
            },
            {
                "order": 2,
                "page": 226,
                "segment_type": "gatha",
                "source_layout": "bat_line",
                "item": 234,
                "needs_review": True,
                "review_reasons": ["irregular_gatha_stanza"],
                "bats": [
                    {
                        "waks": [
                            _wak("Kena vūpasantaṃ,", "เกน วูปสนฺตํ,"),
                            _wak(
                                "sammukhāvinayena ca yebhuyyasikāya ca.",
                                "สมฺมุขาวินเยน จ เยภุยฺยสิกาย จ.",
                            ),
                        ]
                    }
                ],
            },
        ]
        out, n = fix_segments(segs)
        self.assertEqual(n, 0)
        self.assertEqual(out[0]["segment_type"], "prose")
        self.assertEqual(out[1]["segment_type"], "gatha")
        self.assertEqual(len(out), 2)

    def test_keeps_true_hanging_prose(self) -> None:
        segs = [
            {
                "order": 1,
                "segment_type": "prose",
                "item": 338,
                "source_layout": "hanging",
                "text": _text(
                    "Tena kho pana samayena bhagavā sāvatthiyaṃ viharati jetavane "
                    "anāthapiṇḍikassa ārāme tatra kho bhagavā."
                ),
                "hanging_lines": [
                    _text(
                        "Bhikkhū āmantesi bhikkhavo ti bhadante ti te bhikkhū "
                        "bhagavato paccassosuṃ bhagavā etadavoca."
                    )
                ],
            }
        ]
        out, n = fix_segments(segs)
        self.assertEqual(n, 0)
        self.assertEqual(out[0]["source_layout"], "hanging")


if __name__ == "__main__":
    unittest.main()
