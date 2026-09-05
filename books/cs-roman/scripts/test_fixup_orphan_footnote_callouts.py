"""Tests for rebinding orphan numbered footnotes to spaced callouts."""

from __future__ import annotations

import unittest

from fixup_orphan_footnote_callouts import rebind_orphan_footnote_callouts


class RebindOrphanFootnoteTests(unittest.TestCase):
    def test_binds_spaced_callout_and_drops_orphan(self) -> None:
        segments = [
            {
                "page": 75,
                "order": 1,
                "segment_type": "prose_continuation",
                "item": 149,
                "text": [
                    {
                        "script": "roman",
                        "value": (
                            "dve dhammā paccāsīsitabbā 1 "
                            "uposathapucchakañca,"
                        ),
                    },
                    {
                        "script": "thai",
                        "value": (
                            "เทฺว ธมฺมา ปจฺจาสีสิตพฺพา 1 "
                            "อุโปสถปุจฺฉกญฺจ,"
                        ),
                    },
                ],
            },
            {
                "page": 75,
                "order": 2,
                "segment_type": "note",
                "item": 1,
                "text": [
                    {
                        "script": "roman",
                        "value": "Paccāsiṃ sitabbā (Itipi)",
                    },
                    {
                        "script": "thai",
                        "value": "ปจฺจาสิํ สิตพฺพา (อิติปิ)",
                    },
                ],
                "needs_review": True,
                "review_reasons": ["orphan_note"],
            },
        ]
        fixed = rebind_orphan_footnote_callouts(segments)
        self.assertEqual(fixed, 1)
        self.assertEqual(len(segments), 1)
        body = segments[0]
        roman = body["text"][0]["value"]
        thai = body["text"][1]["value"]
        self.assertIn("paccāsīsitabbā{{n0}}", roman)
        self.assertNotIn(" 1 ", roman)
        self.assertIn("{{n0}}", thai)
        self.assertEqual(body["notes"], ["Paccāsiṃ sitabbā (Itipi)"])
        self.assertEqual(body["order"], 1)

    def test_skips_spaced_outline_number(self) -> None:
        segments = [
            {
                "page": 10,
                "order": 1,
                "segment_type": "chapter",
                "text": [
                    {
                        "script": "roman",
                        "value": "Cīvaravagga 1. Paṭhamakathinasikkhāpada",
                    }
                ],
            },
            {
                "page": 10,
                "order": 2,
                "segment_type": "note",
                "item": 1,
                "text": [{"script": "roman", "value": "Variant (Itipi)"}],
                "needs_review": True,
                "review_reasons": ["orphan_note"],
            },
        ]
        fixed = rebind_orphan_footnote_callouts(segments)
        self.assertEqual(fixed, 0)
        self.assertEqual(len(segments), 2)

    def test_binds_inline_plus_orphan(self) -> None:
        segments = [
            {
                "page": 274,
                "order": 1,
                "segment_type": "prose",
                "text": [
                    {
                        "script": "roman",
                        "value": "Te + evarūpaṃ anācāraṃ ācaranti.",
                    }
                ],
                "symbol_notes": {"*": "Idaṃ vatthu Vi 4. 22."},
            },
            {
                "page": 274,
                "order": 2,
                "segment_type": "note",
                "flags": ["plus"],
                "text": [
                    {"script": "roman", "value": "Vi 4. 284 piṭṭhādīsupi."}
                ],
                "needs_review": True,
                "review_reasons": ["orphan_note"],
            },
        ]
        fixed = rebind_orphan_footnote_callouts(segments)
        self.assertEqual(fixed, 1)
        self.assertEqual(len(segments), 1)
        roman = segments[0]["text"][0]["value"]
        self.assertIn("Te{{+}}evarūpaṃ", roman.replace(" ", ""))
        self.assertEqual(
            segments[0]["symbol_notes"]["+"], "Vi 4. 284 piṭṭhādīsupi."
        )

    def test_binds_bracket_orphan(self) -> None:
        segments = [
            {
                "page": 134,
                "order": 1,
                "segment_type": "prose",
                "text": [
                    {
                        "script": "roman",
                        "value": "[ 219. Tīhā kārehi dutiyañca jhānaṃ",
                    }
                ],
            },
            {
                "page": 134,
                "order": 2,
                "segment_type": "note",
                "text": [
                    {
                        "script": "roman",
                        "value": "[  ] Etthantare pāṭhā Syāmapotthake natthi.",
                    }
                ],
                "needs_review": True,
                "review_reasons": ["orphan_note"],
            },
        ]
        fixed = rebind_orphan_footnote_callouts(segments)
        self.assertEqual(fixed, 1)
        self.assertEqual(len(segments), 1)
        self.assertTrue(
            segments[0]["text"][0]["value"].startswith("[{{[]}}")
        )
        self.assertEqual(
            segments[0]["symbol_notes"]["[]"],
            "Etthantare pāṭhā Syāmapotthake natthi.",
        )

    def test_binds_glued_star_after_dash(self) -> None:
        segments = [
            {
                "page": 492,
                "order": 1,
                "segment_type": "prose",
                "item": 447,
                "text": [
                    {
                        "script": "roman",
                        "value": "Bhagavā bhikkhū āmantesi– *cattārome bhikkhave",
                    }
                ],
            },
            {
                "page": 492,
                "order": 2,
                "segment_type": "note",
                "flags": ["star"],
                "text": [{"script": "roman", "value": "Aṃ 1. 362 piṭṭhepi."}],
                "needs_review": True,
                "review_reasons": ["orphan_note"],
            },
        ]
        fixed = rebind_orphan_footnote_callouts(segments)
        self.assertEqual(fixed, 1)
        self.assertEqual(len(segments), 1)
        roman = segments[0]["text"][0]["value"]
        self.assertIn("{{*}}", roman)
        self.assertEqual(
            segments[0]["symbol_notes"]["*"], "Aṃ 1. 362 piṭṭhepi."
        )

    def test_attaches_leftover_page_note_without_callout(self) -> None:
        segments = [
            {
                "page": 177,
                "order": 1,
                "segment_type": "prose",
                "item": 183,
                "text": [
                    {
                        "script": "roman",
                        "value": "Idha pana bhikkhave bhikkhu sambahulā.",
                    }
                ],
            },
            {
                "page": 177,
                "order": 2,
                "segment_type": "note",
                "item": 10,
                "text": [
                    {
                        "script": "roman",
                        "value": "Mūlāyavisuddhinavaka (Sī, Syā)",
                    }
                ],
                "needs_review": True,
                "review_reasons": ["orphan_note"],
            },
        ]
        fixed = rebind_orphan_footnote_callouts(segments)
        self.assertEqual(fixed, 1)
        self.assertEqual(len(segments), 1)
        roman = segments[0]["text"][0]["value"]
        self.assertTrue(roman.endswith("{{n0}}"))
        self.assertEqual(
            segments[0]["notes"],
            ["Mūlāyavisuddhinavaka (Sī, Syā)"],
        )

    def test_repairs_folio_stolen_paren_onto_numbered_callout(self) -> None:
        """``({{()}}150)`` + literal ``(te)2`` → folio restored, ``{{n0}}`` bound."""
        segments = [
            {
                "page": 86,
                "order": 1,
                "segment_type": "prose_continuation",
                "item": 161,
                "text": [
                    {
                        "script": "roman",
                        "value": "So bhikkhu abhiramatīti{{n0}}. ({{()}}150)",
                    },
                    {
                        "script": "thai",
                        "value": "โส ภิกฺขุ อภิรมตีติ{{n0}}. ({{()}}150)",
                    },
                ],
                "notes": ["Abhiramīti (Sī, Syā)"],
                "symbol_notes": {
                    "()": "(?) Evamuparipi īdisesu ṭhānesu.",
                },
            },
            {
                "page": 86,
                "order": 2,
                "segment_type": "prose",
                "item": 162,
                "text": [
                    {
                        "script": "roman",
                        "value": 'bhāsatī”ti (te)2 anekākāravokāraṃ.',
                    },
                    {
                        "script": "thai",
                        "value": "ภาสตี”ติ (เต)2 อเนกาการโวการํ.",
                    },
                ],
                "symbol_notes": {
                    "*": "Idaṃ vatthu Saṃ 3. 278 piṭṭhepi āgataṃ.",
                },
            },
        ]
        fixed = rebind_orphan_footnote_callouts(segments)
        self.assertGreaterEqual(fixed, 1)
        cont, prose = segments[0], segments[1]
        self.assertIn("(150)", cont["text"][0]["value"])
        self.assertNotIn("{{()}}", cont["text"][0]["value"])
        self.assertNotIn("()", cont.get("symbol_notes") or {})
        self.assertIn("(te){{n0}}", prose["text"][0]["value"])
        self.assertNotIn("(te)2", prose["text"][0]["value"])
        self.assertEqual(
            prose["notes"],
            ["( ) (?) Evamuparipi īdisesu ṭhānesu."],
        )


if __name__ == "__main__":
    unittest.main()
