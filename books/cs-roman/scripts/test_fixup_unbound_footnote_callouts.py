#!/usr/bin/env python3
"""Tests for unbound / collided footnote callout repair."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from extract_cs_roman_pdf import (  # noqa: E402
    Segment,
    group_gatha_stanzas,
    merge_note_carrying_units,
    remap_note_markers,
)
from fixup_unbound_footnote_callouts import (  # noqa: E402
    bind_literal_callouts_from_notes,
    fix_collided_note_indices,
    remap_collided_note_markers_in_texts,
    rebind_unbound_footnote_callouts,
)


def _wak(roman: str) -> dict:
    return {"text": [{"script": "roman", "value": roman}]}


class RemapNoteMarkersTests(unittest.TestCase):
    def test_offset(self) -> None:
        self.assertEqual(
            remap_note_markers("va{{n0}} and x{{n1}}.", 2),
            "va{{n2}} and x{{n3}}.",
        )

    def test_merge_two_lines_remaps_second(self) -> None:
        a = Segment(
            page=1,
            order=1,
            item=6,
            segment_type="gatha",
            text="Sirī tāta Alakkhī va{{n0}}, pucchitā etadabravuṃ.",
            notes=["Sirī ca tāta lakkhī ca (Syā, I)"],
        )
        b = Segment(
            page=1,
            order=2,
            item=6,
            segment_type="gatha",
            text="Uṭṭhāna{{n0}} vīriye pose, ramāhaṃ anusūyake.",
            notes=["Uṭṭhāne (Syā)"],
        )
        romans, notes, _sym, _flags = merge_note_carrying_units(
            [(a.text, a), (b.text, b)]
        )
        self.assertEqual(notes, ["Sirī ca tāta lakkhī ca (Syā, I)", "Uṭṭhāne (Syā)"])
        self.assertIn("va{{n0}}", romans[0])
        self.assertIn("Uṭṭhāna{{n1}}", romans[1])

    def test_fold_keeps_distinct_note_bodies(self) -> None:
        lines = [
            Segment(
                page=1,
                order=1,
                item=6,
                segment_type="gatha",
                text="Sirī tāta Alakkhī va{{n0}}, pucchitā etadabravuṃ.",
                notes=["Sirī ca tāta lakkhī ca (Syā, I)"],
            ),
            Segment(
                page=1,
                order=2,
                item=6,
                segment_type="gatha",
                text="Uṭṭhāna{{n0}} vīriye pose, ramāhaṃ anusūyake.",
                notes=["Uṭṭhāne (Syā)"],
            ),
        ]
        out = group_gatha_stanzas(lines)
        self.assertEqual(len(out), 1)
        g = out[0]
        self.assertEqual(
            g.notes,
            ["Sirī ca tāta lakkhī ca (Syā, I)", "Uṭṭhāne (Syā)"],
        )
        blob = " ".join(
            w["text"] for b in (g.bats or []) for w in b.get("waks") or []
        )
        self.assertIn("va{{n0}}", blob)
        self.assertIn("Uṭṭhāna{{n1}}", blob)


class CollidedMarkerFixupTests(unittest.TestCase):
    def test_remaps_duplicate_n0(self) -> None:
        texts = ["va{{n0}},", "Uṭṭhāna{{n0}} pose,"]
        notes = ["Sirī…", "Uṭṭhāne"]
        out = remap_collided_note_markers_in_texts(texts, notes)
        assert out is not None
        self.assertEqual(out[0], "va{{n0}},")
        self.assertEqual(out[1], "Uṭṭhāna{{n1}} pose,")

    def test_gatha_segment_collision(self) -> None:
        seg = {
            "segment_type": "gatha",
            "page": 1,
            "notes": ["Sirī ca tāta lakkhī ca (Syā, I)", "Uṭṭhāne (Syā)"],
            "bats": [
                {
                    "waks": [
                        _wak("Sirī tāta Alakkhī va{{n0}},"),
                        _wak("pucchitā etadabravuṃ."),
                    ]
                },
                {
                    "waks": [
                        _wak("Uṭṭhāna{{n0}} vīriye pose,"),
                        _wak("ramāhaṃ anusūyake."),
                    ]
                },
            ],
        }
        self.assertEqual(fix_collided_note_indices(seg), 1)
        left = seg["bats"][0]["waks"][0]["text"][0]["value"]
        right = seg["bats"][1]["waks"][0]["text"][0]["value"]
        self.assertIn("{{n0}}", left)
        self.assertIn("{{n1}}", right)


class LiteralBindTests(unittest.TestCase):
    def test_binds_ramati1(self) -> None:
        seg = {
            "segment_type": "gatha",
            "page": 2,
            "bats": [
                {
                    "waks": [
                        _wak("Usūyake duhadaye,"),
                        _wak("purise kammadussake."),
                    ]
                },
                {
                    "waks": [
                        _wak("Kāḷakaṇṇī mahārāja,"),
                        _wak("ramati1 cakkabhañjanī."),
                    ]
                },
            ],
        }
        available = {1: "Ramāti (Ka)"}
        n = bind_literal_callouts_from_notes(seg, available)
        self.assertEqual(n, 1)
        self.assertEqual(seg["notes"], ["Ramāti (Ka)"])
        wak = seg["bats"][1]["waks"][1]["text"][0]["value"]
        self.assertIn("ramati{{n0}}", wak)
        self.assertNotIn("ramati1", wak)
        self.assertEqual(available, {1: "Ramāti (Ka)"})

    def test_reuses_same_mark_across_segments(self) -> None:
        segs = [
            {
                "segment_type": "gatha",
                "page": 12,
                "bats": [{"waks": [_wak("Isippalobhane5 gaccha,")]}],
            },
            {
                "segment_type": "gatha",
                "page": 12,
                "bats": [{"waks": [_wak("Isippalobhane5 gaccha,")]}],
            },
        ]
        _c, lit = rebind_unbound_footnote_callouts(
            segs, pdf_notes_by_page={12: {5: "Isipalobhike (Sī)"}}
        )
        self.assertEqual(lit, 2)
        for seg in segs:
            self.assertIn("{{n0}}", seg["bats"][0]["waks"][0]["text"][0]["value"])
            self.assertEqual(seg["notes"], ["Isipalobhike (Sī)"])

    def test_split_glued_numbered_notes(self) -> None:
        from extract_cs_roman_pdf import split_glued_numbered_note_body

        parts = split_glued_numbered_note_body(
            2,
            "Dakkhitānaṃ (Syā, I) 3. Idaṃ padaṃ natthi (Sī-Syā-I-potthakesu.)",
        )
        self.assertEqual(
            parts,
            [
                (2, "Dakkhitānaṃ (Syā, I)"),
                (3, "Idaṃ padaṃ natthi (Sī-Syā-I-potthakesu.)"),
            ],
        )

    def test_rebind_combined(self) -> None:
        segs = [
            {
                "segment_type": "gatha",
                "page": 1,
                "notes": ["Sirī…", "Uṭṭhāne"],
                "bats": [
                    {
                        "waks": [
                            _wak("va{{n0}},"),
                            _wak("x."),
                        ]
                    },
                    {
                        "waks": [
                            _wak("Uṭṭhāna{{n0}} y,"),
                            _wak("z."),
                        ]
                    },
                ],
            },
            {
                "segment_type": "gatha",
                "page": 2,
                "bats": [
                    {
                        "waks": [
                            _wak("a,"),
                            _wak("ramati1 b."),
                        ]
                    }
                ],
            },
        ]
        c, lit = rebind_unbound_footnote_callouts(
            segs, pdf_notes_by_page={2: {1: "Ramāti (Ka)"}}
        )
        self.assertEqual(c, 1)
        self.assertEqual(lit, 1)
        self.assertIn("{{n1}}", segs[0]["bats"][1]["waks"][0]["text"][0]["value"])
        self.assertIn("{{n0}}", segs[1]["bats"][0]["waks"][1]["text"][0]["value"])


if __name__ == "__main__":
    unittest.main()
