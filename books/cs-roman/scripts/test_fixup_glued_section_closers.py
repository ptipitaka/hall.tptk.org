#!/usr/bin/env python3
"""Tests for peeling section closers glued after a verse/prose stop."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from fixup_glued_section_closers import unglue_section_closers  # noqa: E402


class UnglueGathaCloserTests(unittest.TestCase):
    def test_peels_samatto_from_last_wak(self) -> None:
        segs = [
            {
                "order": 1,
                "page": 43,
                "segment_type": "gatha",
                "source_layout": "bat_line",
                "bats": [
                    {
                        "waks": [
                            {
                                "text": [
                                    {
                                        "script": "roman",
                                        "value": "Attadīpā Paṭipadā,",
                                    },
                                    {
                                        "script": "thai",
                                        "value": "อตฺตทีปา ปฏิปทา,",
                                    },
                                ]
                            },
                            {
                                "text": [
                                    {
                                        "script": "roman",
                                        "value": "dve ca honti Aniccatā.",
                                    },
                                    {
                                        "script": "thai",
                                        "value": "เทฺว จ โหนฺติ อนิจฺจตา.",
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
                                        "value": "Samanupassanā Khandhā,",
                                    },
                                    {
                                        "script": "thai",
                                        "value": "สมนุปสฺสนา ขนฺธา,",
                                    },
                                ]
                            },
                            {
                                "text": [
                                    {
                                        "script": "roman",
                                        "value": (
                                            "dve Soṇā dve Nandikkhayena cāti."
                                            "{{sp1}} Mūlapaṇṇāsako samatto."
                                        ),
                                    },
                                    {
                                        "script": "thai",
                                        "value": (
                                            "เทฺว โสณา เทฺว นนฺทิกฺขเยน จาติ."
                                            "{{sp1}} มูลปณฺณาสโก สมตฺโต."
                                        ),
                                    },
                                ]
                            },
                        ]
                    },
                ],
            }
        ]
        out, n = unglue_section_closers(segs)
        self.assertEqual(n, 1)
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0]["segment_type"], "gatha")
        last_wak = out[0]["bats"][-1]["waks"][-1]["text"]
        thai = next(t["value"] for t in last_wak if t["script"] == "thai")
        roman = next(t["value"] for t in last_wak if t["script"] == "roman")
        self.assertEqual(thai, "เทฺว โสณา เทฺว นนฺทิกฺขเยน จาติ.")
        self.assertEqual(roman, "dve Soṇā dve Nandikkhayena cāti.")
        self.assertNotIn("สมตฺโต", thai)
        self.assertEqual(out[1]["segment_type"], "niṭṭhitaṃ")
        closer_thai = next(
            t["value"] for t in out[1]["text"] if t["script"] == "thai"
        )
        self.assertEqual(closer_thai, "มูลปณฺณาสโก สมตฺโต.")

    def test_peels_prose_samatto_trailer(self) -> None:
        segs = [
            {
                "order": 1,
                "page": 1,
                "segment_type": "prose",
                "text": [
                    {
                        "script": "thai",
                        "value": (
                            "นาปรํ อิตฺถตฺตายาติ ปชานาตีติ.{{sp1}} "
                            "สฏฺฐิเปยฺยาโล สมตฺโต."
                        ),
                    }
                ],
            }
        ]
        out, n = unglue_section_closers(segs)
        self.assertEqual(n, 1)
        self.assertEqual(out[0]["segment_type"], "prose")
        self.assertEqual(
            out[0]["text"][0]["value"],
            "นาปรํ อิตฺถตฺตายาติ ปชานาตีติ.",
        )
        self.assertEqual(out[1]["segment_type"], "niṭṭhitaṃ")


class UnglueSikkhapadaOrdinalCloserTests(unittest.TestCase):
    def test_peels_parenthetical_sikkhapada_ordinal_from_prose(self) -> None:
        segs = [
            {
                "order": 1,
                "page": 262,
                "segment_type": "prose",
                "item": 408,
                "text": [
                    {
                        "script": "roman",
                        "value": (
                            "Anāpatti tathāsaññī codeti vā codāpeti vā "
                            "ummattakassa ādikammikassāti. (Aññābhāgiya) "
                            "kiñcilesasikkhāpadaṃ niṭṭhitaṃ navamaṃ."
                        ),
                    },
                    {
                        "script": "thai",
                        "value": (
                            "อนาปตฺติ ตถาสญฺญี โจเทติ วา โจทาเปติ วา "
                            "อุมฺมตฺตกสฺส อาทิกมฺมิกสฺสาติ. (อญฺญาภาคิย) "
                            "กิญฺจิเลสสิกฺขาปทํ นิฏฺฐิตํ นวมํ."
                        ),
                    },
                ],
            }
        ]
        out, n = unglue_section_closers(segs)
        self.assertEqual(n, 1)
        self.assertEqual(out[0]["segment_type"], "prose")
        self.assertEqual(out[0]["item"], 408)
        roman = next(
            t["value"] for t in out[0]["text"] if t["script"] == "roman"
        )
        thai = next(
            t["value"] for t in out[0]["text"] if t["script"] == "thai"
        )
        self.assertEqual(
            roman,
            "Anāpatti tathāsaññī codeti vā codāpeti vā ummattakassa "
            "ādikammikassāti.",
        )
        self.assertEqual(
            thai,
            "อนาปตฺติ ตถาสญฺญี โจเทติ วา โจทาเปติ วา อุมฺมตฺตกสฺส "
            "อาทิกมฺมิกสฺสาติ.",
        )
        self.assertEqual(out[1]["segment_type"], "niṭṭhitaṃ")
        closer_roman = next(
            t["value"] for t in out[1]["text"] if t["script"] == "roman"
        )
        closer_thai = next(
            t["value"] for t in out[1]["text"] if t["script"] == "thai"
        )
        self.assertEqual(
            closer_roman,
            "(Aññābhāgiya) kiñcilesasikkhāpadaṃ niṭṭhitaṃ navamaṃ.",
        )
        self.assertEqual(
            closer_thai,
            "(อญฺญาภาคิย) กิญฺจิเลสสิกฺขาปทํ นิฏฺฐิตํ นวมํ.",
        )


if __name__ == "__main__":
    unittest.main()
