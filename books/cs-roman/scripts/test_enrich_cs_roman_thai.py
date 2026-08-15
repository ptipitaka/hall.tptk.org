"""Tests for enrich_cs_roman_thai (section_rule flag preservation)."""

from __future__ import annotations

import unittest

from enrich_cs_roman_thai import enrich_document
from cs_roman_text import SECTION_RULE_FLAG


class EnrichSectionRuleTests(unittest.TestCase):
    def test_force_preserves_existing_section_rule_flag(self) -> None:
        """After extract, _____ is already stripped into the flag — keep it."""
        doc = {
            "segments": [
                {
                    "page": 112,
                    "order": 573,
                    "segment_type": "title",
                    "flags": [SECTION_RULE_FLAG],
                    "text": [
                        {"script": "roman", "value": "Tatiyapārājikaṃ samattaṃ."},
                        {"script": "thai", "value": "ตติยปาราชิกํ สมตฺตํ."},
                    ],
                }
            ]
        }
        out, _, _ = enrich_document(doc, force=True)
        seg = out["segments"][0]
        self.assertIn(SECTION_RULE_FLAG, seg.get("flags") or [])
        roman = next(e["value"] for e in seg["text"] if e["script"] == "roman")
        self.assertNotIn("_____", roman)

    def test_trailing_underscores_still_set_flag(self) -> None:
        doc = {
            "segments": [
                {
                    "page": 1,
                    "order": 1,
                    "segment_type": "niṭṭhitaṃ",
                    "text": "Sudinnabhāṇavāro niṭṭhito. _____",
                }
            ]
        }
        out, _, _ = enrich_document(doc, force=True)
        seg = out["segments"][0]
        self.assertIn(SECTION_RULE_FLAG, seg.get("flags") or [])

    def test_normalizes_pot_ma_gyi_inside_bats_waks(self) -> None:
        """Nested gāthā wak text must get the same spacing contract."""
        from cs_roman_text import SP1_MARKER

        doc = {
            "segments": [
                {
                    "page": 1,
                    "order": 1,
                    "segment_type": "gatha",
                    "bats": [
                        {
                            "waks": [
                                {
                                    "text": [
                                        {
                                            "script": "roman",
                                            "value": (
                                                f"bhajethāti.{SP1_MARKER}"
                                                f"{SP1_MARKER}Chaṭṭhaṃ."
                                            ),
                                        },
                                        {
                                            "script": "thai",
                                            "value": (
                                                f"ภเชถาติ.{SP1_MARKER}"
                                                f"{SP1_MARKER}ฉฏฺฐํ."
                                            ),
                                        },
                                    ]
                                }
                            ]
                        }
                    ],
                }
            ]
        }
        out, _, _ = enrich_document(doc, force=False)
        wak = out["segments"][0]["bats"][0]["waks"][0]["text"]
        roman = next(e["value"] for e in wak if e["script"] == "roman")
        thai = next(e["value"] for e in wak if e["script"] == "thai")
        self.assertNotIn(SP1_MARKER + SP1_MARKER, roman)
        self.assertNotIn(SP1_MARKER + SP1_MARKER, thai)
        self.assertIn(f".{SP1_MARKER} Chaṭṭhaṃ.", roman)
        self.assertIn(f".{SP1_MARKER} ฉฏฺฐํ.", thai)


if __name__ == "__main__":
    unittest.main()
