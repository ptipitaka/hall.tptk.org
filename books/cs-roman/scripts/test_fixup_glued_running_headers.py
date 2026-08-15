"""Tests for glued running-header peel / fixup."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from fixup_glued_running_headers import repair_glued_running_headers  # noqa: E402


class FixupGluedRunningHeadersTests(unittest.TestCase):
    def test_peels_center_prose_and_fixes_false_item(self) -> None:
        segments = [
            {
                "page": 202,
                "order": 1,
                "segment_type": "prose",
                "item": 479,
                "text": [
                    {
                        "script": "roman",
                        "value": "So evaṃ samāhite citte āsavānaṃ",
                    }
                ],
            },
            {
                "page": 203,
                "order": 2,
                "segment_type": "prose",
                "item": 10,
                "source_layout": "center",
                "text": [
                    {
                        "script": "roman",
                        "value": (
                            "Subhasutta khayañāṇāya cittaṃ abhinīharati "
                            "abhininnāmeti, so idaṃ dukkhanti yathābhūtaṃ "
                            "pajānāti."
                        ),
                    }
                ],
            },
            {
                "page": 203,
                "order": 3,
                "segment_type": "prose",
                "item": 10,
                "text": [
                    {
                        "script": "roman",
                        "value": (
                            "Seyyathāpi māṇava pabbatasaṅkhepe udakarahado "
                            "accho vippasanno anāvilo."
                        ),
                    }
                ],
            },
        ]
        stats = repair_glued_running_headers(
            segments, {"10. Subhasutta", "Sīlakkhandhavaggapāḷi"}
        )
        self.assertEqual(stats["peeled"], 1)
        self.assertEqual(stats["cleared_center"], 1)
        self.assertGreaterEqual(stats["fixed_item"], 2)
        seg = segments[1]
        roman = seg["text"][0]["value"]
        self.assertTrue(roman.startswith("khayañāṇāya"), roman)
        self.assertNotIn("Subhasutta", roman)
        self.assertEqual(seg["item"], 479)
        self.assertNotIn("source_layout", seg)
        self.assertEqual(segments[2]["item"], 479)

    def test_residual_fixes_already_peeled_follower(self) -> None:
        segments = [
            {
                "page": 203,
                "order": 1,
                "segment_type": "prose",
                "item": 479,
                "text": [
                    {
                        "script": "roman",
                        "value": (
                            "khayañāṇāya cittaṃ abhinīharati abhininnāmeti, "
                            "so idaṃ dukkhanti yathābhūtaṃ pajānāti."
                        ),
                    }
                ],
            },
            {
                "page": 203,
                "order": 2,
                "segment_type": "prose",
                "item": 10,
                "text": [
                    {
                        "script": "roman",
                        "value": (
                            "Seyyathāpi māṇava pabbatasaṅkhepe udakarahado "
                            "accho vippasanno anāvilo."
                        ),
                    }
                ],
            },
        ]
        stats = repair_glued_running_headers(segments, {"10. Subhasutta"})
        self.assertEqual(stats["peeled"], 0)
        self.assertEqual(segments[1]["item"], 479)

    def test_peel_exposes_flush_continuation_candidate(self) -> None:
        """After peel, roman starts mid-sentence (lowercase) for page-start geom."""
        segments = [
            {
                "page": 202,
                "order": 1,
                "segment_type": "prose",
                "item": 479,
                "text": [
                    {
                        "script": "roman",
                        "value": "So evaṃ samāhite citte āsavānaṃ",
                    }
                ],
            },
            {
                "page": 203,
                "order": 2,
                "segment_type": "prose",
                "item": 10,
                "source_layout": "center",
                "text": [
                    {
                        "script": "roman",
                        "value": (
                            "Subhasutta khayañāṇāya cittaṃ abhinīharati "
                            "abhininnāmeti, so idaṃ dukkhanti yathābhūtaṃ "
                            "pajānāti."
                        ),
                    }
                ],
            },
        ]
        repair_glued_running_headers(segments, {"10. Subhasutta"})
        roman = segments[1]["text"][0]["value"]
        self.assertTrue(roman[0].islower(), roman)
        self.assertTrue(roman.startswith("khayañāṇāya"), roman)

    def test_skips_short_title_like_prose(self) -> None:
        segments = [
            {
                "page": 188,
                "order": 1,
                "segment_type": "prose",
                "text": [{"script": "roman", "value": "Subhasutta"}],
            }
        ]
        stats = repair_glued_running_headers(segments, {"10. Subhasutta"})
        self.assertEqual(stats["peeled"], 0)
        self.assertEqual(segments[0]["text"][0]["value"], "Subhasutta")

    def test_peels_folio_prefix_without_header_set(self) -> None:
        segments = [
            {
                "page": 13,
                "order": 1,
                "segment_type": "prose",
                "source_layout": "center",
                "text": [
                    {
                        "script": "roman",
                        "value": (
                            "Aṭṭhakanāgarasutta (52) Bhagavatā jānatā passatā "
                            "Arahatā Sammāsambuddhena ekadhammo akkhāto, "
                            "yattha bhikkhuno appamattassa ātāpino."
                        ),
                    }
                ],
            }
        ]
        stats = repair_glued_running_headers(segments, set())
        self.assertEqual(stats["peeled"], 1)
        self.assertEqual(stats["cleared_center"], 1)
        roman = segments[0]["text"][0]["value"]
        self.assertTrue(roman.startswith("Bhagavatā"), roman)
        self.assertNotIn("source_layout", segments[0])

    def test_drops_isolated_folio_title(self) -> None:
        segments = [
            {
                "page": 22,
                "order": 1,
                "segment_type": "title",
                "section_no": 4,
                "source_layout": "center",
                "text": [
                    {"script": "roman", "value": "Potaliyasutta"},
                ],
            },
            {
                "page": 27,
                "order": 2,
                "segment_type": "title",
                "heading_kind": "h2",
                "source_layout": "center",
                "text": [
                    {"script": "roman", "value": "Potaliyasutta (54)"},
                ],
            },
            {
                "page": 27,
                "order": 3,
                "segment_type": "prose",
                "item": 41,
                "text": [
                    {
                        "script": "roman",
                        "value": "Ime kho gahapati aṭṭha dhammā.",
                    }
                ],
            },
        ]
        stats = repair_glued_running_headers(
            segments, {"4. Potaliyasutta (54)"}
        )
        self.assertEqual(stats["dropped_titles"], 1)
        self.assertEqual(len(segments), 2)
        self.assertEqual(segments[0]["text"][0]["value"], "Potaliyasutta")
        self.assertEqual(segments[1]["segment_type"], "prose")

    def test_drops_continuation_samyutta_running_header_title(self) -> None:
        """Centered saṃyutta header before body (not child title) → drop."""
        segments = [
            {
                "page": 218,
                "order": 1,
                "segment_type": "title",
                "heading_kind": "cha",
                "source_layout": "center",
                "text": [
                    {"script": "roman", "value": "Vacchagottasaṃyutta"},
                ],
            },
            {
                "page": 218,
                "order": 2,
                "segment_type": "title",
                "heading_kind": "h2",
                "source_layout": "center",
                "text": [
                    {"script": "roman", "value": "Rūpaaññāṇasutta"},
                ],
            },
            {
                "page": 223,
                "order": 3,
                "segment_type": "title",
                "heading_kind": "h2",
                "source_layout": "center",
                "review_reasons": ["weak_heading_heuristic"],
                "text": [
                    {"script": "roman", "value": "Vacchagottasaṃyutta"},
                ],
            },
            {
                "page": 223,
                "order": 4,
                "segment_type": "prose",
                "text": [
                    {
                        "script": "roman",
                        "value": (
                            "Sāvatthinidānaṃ. Saṅkhāresu kho Vaccha "
                            "appaccakkhakammā -pa-."
                        ),
                    }
                ],
            },
        ]
        stats = repair_glued_running_headers(
            segments, {"12. Vacchagottasaṃyutta"}
        )
        self.assertGreaterEqual(stats["dropped_titles"], 1)
        romans = [
            s["text"][0]["value"]
            for s in segments
            if s.get("segment_type") == "title"
        ]
        self.assertEqual(romans.count("Vacchagottasaṃyutta"), 1)
        self.assertEqual(segments[0]["heading_kind"], "cha")
        self.assertEqual(segments[-1]["segment_type"], "prose")

    def test_keeps_samyutta_open_when_followed_by_child_title(self) -> None:
        segments = [
            {
                "page": 1,
                "order": 1,
                "segment_type": "title",
                "heading_kind": "h2",
                "source_layout": "center",
                "text": [{"script": "roman", "value": "Maggasaṃyutta"}],
            },
            {
                "page": 1,
                "order": 2,
                "segment_type": "title",
                "heading_kind": "cha",
                "source_layout": "center",
                "text": [{"script": "roman", "value": "Avijjāvagga"}],
            },
        ]
        stats = repair_glued_running_headers(
            segments, {"1. Maggasaṃyutta"}
        )
        self.assertEqual(stats["dropped_titles"], 0)
        self.assertEqual(len(segments), 2)

    def test_drops_repeated_gambhira_running_header(self) -> None:
        from fixup_glued_running_headers import (
            drop_continuation_gambhira_headers,
        )

        segments = [
            {
                "page": 1,
                "order": 1,
                "segment_type": "gambhīra",
                "heading_kind": "boo",
                "text": [
                    {
                        "script": "roman",
                        "value": "Saḷāyatanavaggasaṃyuttapāḷi",
                    },
                    {
                        "script": "thai",
                        "value": "สฬายตนวคฺคสํยุตฺตปาฬิ",
                    },
                ],
            },
            {
                "page": 2,
                "order": 2,
                "segment_type": "prose",
                "text": [{"script": "roman", "value": "Evaṃ me sutaṃ."}],
            },
            {
                "page": 3,
                "order": 3,
                "segment_type": "gambhīra",
                "heading_kind": "boo",
                "text": [
                    {
                        "script": "roman",
                        "value": "Saḷāyatanavaggasaṃyuttapāḷi",
                    },
                    {
                        "script": "thai",
                        "value": "สฬายตนวคฺคสํยุตฺตปาฬิ",
                    },
                ],
            },
            {
                "page": 3,
                "order": 4,
                "segment_type": "prose",
                "text": [{"script": "roman", "value": "Rūpā bhikkhave."}],
            },
            {
                "page": 50,
                "order": 5,
                "segment_type": "gambhīra",
                "heading_kind": "boo",
                "text": [
                    {
                        "script": "roman",
                        "value": "Khandhavaggasaṃyuttapāḷi",
                    },
                    {
                        "script": "thai",
                        "value": "ขนฺธวคฺคสํยุตฺตปาฬิ",
                    },
                ],
            },
        ]
        dropped = drop_continuation_gambhira_headers(segments)
        self.assertEqual(dropped, 1)
        gambhiras = [
            s for s in segments if s.get("segment_type") == "gambhīra"
        ]
        self.assertEqual(len(gambhiras), 2)
        self.assertEqual(
            gambhiras[0]["text"][1]["value"], "สฬายตนวคฺคสํยุตฺตปาฬิ"
        )
        self.assertEqual(
            gambhiras[1]["text"][1]["value"], "ขนฺธวคฺคสํยุตฺตปาฬิ"
        )


if __name__ == "__main__":
    unittest.main()
