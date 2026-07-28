"""Tests for Mātikā heading assignment + matika.json outline."""

from __future__ import annotations

import unittest

from assign_cs_roman_heading_levels import (
    MatikaEntry,
    assign_levels,
    classify_matika_title,
    compound_parts,
    match_entries_to_segments,
    normalize_title,
    split_outline_title,
)
from generate_cs_roman_tex import MatikaTocPlanner, matika_entry_toc_title, matika_toc_mark


def _heading(
    *,
    page: int,
    order: int,
    segment_type: str,
    roman: str,
    section_no: int | None = None,
) -> dict:
    seg: dict = {
        "page": page,
        "order": order,
        "segment_type": segment_type,
        "text": [
            {"script": "roman", "value": roman},
            {"script": "thai", "value": roman},
        ],
    }
    if section_no is not None:
        seg["section_no"] = section_no
    return seg


class SplitOutlineTitleTests(unittest.TestCase):
    def test_splits_number(self) -> None:
        no, title = split_outline_title("2.  Kosiyavagga")
        self.assertEqual(no, 2)
        self.assertEqual(title, "Kosiyavagga")

    def test_unnumbered(self) -> None:
        no, title = split_outline_title("Seyyasakabhikkhuvatthu")
        self.assertIsNone(no)
        self.assertEqual(title, "Seyyasakabhikkhuvatthu")


class CompoundPartsTests(unittest.TestCase):
    def test_splits_parent_and_child(self) -> None:
        seg = _heading(
            page=320,
            order=10,
            segment_type="chapter",
            roman="Kosiyavagga 5. Nisīdanasanthatasikkhāpada",
            section_no=2,
        )
        parent, child_no, child = compound_parts(seg)
        self.assertEqual(parent, "Kosiyavagga")
        self.assertEqual(child_no, 5)
        self.assertEqual(child, "Nisīdanasanthatasikkhāpada")


class ClassifyTests(unittest.TestCase):
    def test_vagga_is_h1(self) -> None:
        self.assertEqual(
            classify_matika_title("1. Cīvaravagga", has_page=False),
            "h1",
        )

    def test_sikkhapada_under_vagga_is_h2(self) -> None:
        self.assertEqual(
            classify_matika_title(
                "5. Nisīdanasanthatasikkhāpada",
                has_page=False,
                under_vagga=True,
            ),
            "h2",
        )

    def test_sikkhapada_under_kanda_is_h1(self) -> None:
        self.assertEqual(
            classify_matika_title(
                "1. Sukkavissaṭṭhisikkhāpada",
                has_page=False,
                under_vagga=False,
            ),
            "h1",
        )

    def test_subhead_under_vagga_is_h3(self) -> None:
        self.assertEqual(
            classify_matika_title(
                "Chabbaggiyabhikkhuvatthu",
                has_page=True,
                under_vagga=True,
            ),
            "h3",
        )

    def test_adhikaranasamatha_is_cha_peer_of_kanda(self) -> None:
        self.assertEqual(
            classify_matika_title("8. Adhikaraṇasamatha", has_page=False),
            "cha",
        )
        self.assertEqual(
            classify_matika_title("7. Sekhiyakaṇḍa", has_page=False),
            "cha",
        )

    def test_bhikkhunivibhanga_is_major_boo(self) -> None:
        self.assertEqual(
            classify_matika_title("Bhikkhunīvibhaṅga", has_page=False),
            "boo",
        )
        self.assertEqual(
            classify_matika_title("Bhikkhuvibhaṅga", has_page=False),
            "boo",
        )
        # Rule-internal analysis title stays a subhead, not the major part.
        self.assertEqual(
            classify_matika_title(
                "Sikkhāpadavibhaṅga",
                has_page=True,
                under_vagga=True,
            ),
            "h3",
        )


class MatchAndAssignTests(unittest.TestCase):
    def test_compound_matches_parent_and_child(self) -> None:
        segments = [
            _heading(
                page=320,
                order=50,
                segment_type="chapter",
                roman="Kosiyavagga 5. Nisīdanasanthatasikkhāpada",
                section_no=2,
            )
        ]
        entries = [
            MatikaEntry("Kosiyavagga", None, "h1", 18, section_no=2),
            MatikaEntry(
                "Nisīdanasanthatasikkhāpada", 320, "h2", 18, section_no=5
            ),
        ]
        entry_to_seg, unmatched, _ = match_entries_to_segments(entries, segments)
        self.assertEqual(entry_to_seg[0], 0)
        self.assertEqual(entry_to_seg[1], 0)
        self.assertEqual(unmatched, [])

    def test_fallback_does_not_put_unmatched_title_in_toc(self) -> None:
        data = {
            "schema_version": 1,
            "segments": [
                _heading(
                    page=132,
                    order=1,
                    segment_type="title",
                    roman="Idaṃ sabbamūlakaṃ",
                )
            ],
        }
        out, report, matika = assign_levels(data, entries=[])
        seg = out["segments"][0]
        self.assertEqual(seg.get("heading_kind"), "h2")
        self.assertFalse(seg.get("in_toc"))
        self.assertEqual(report["in_toc_count"], 0)
        self.assertEqual(matika["entries"], [])

    def test_assign_sets_deepest_kind_on_compound(self) -> None:
        data = {
            "schema_version": 1,
            "segments": [
                _heading(
                    page=320,
                    order=50,
                    segment_type="chapter",
                    roman="Kosiyavagga 5. Nisīdanasanthatasikkhāpada",
                    section_no=2,
                )
            ],
        }
        entries = [
            MatikaEntry("Kosiyavagga", None, "h1", 18, section_no=2),
            MatikaEntry(
                "Nisīdanasanthatasikkhāpada", 320, "h2", 18, section_no=5
            ),
        ]
        out, _report, matika = assign_levels(data, entries)
        seg = out["segments"][0]
        self.assertEqual(seg["heading_kind"], "h2")
        self.assertTrue(seg["in_toc"])
        self.assertEqual(matika["entries"][0]["matched_order"], 50)
        self.assertEqual(matika["entries"][0]["section_no"], 2)
        self.assertEqual(matika["entries"][0]["title"], "Kosiyavagga")
        self.assertEqual(matika["entries"][1]["matched_order"], 50)
        self.assertEqual(matika["entries"][1]["section_no"], 5)


class MatikaTocPlannerTests(unittest.TestCase):
    def test_compound_emits_two_marks_at_one_segment(self) -> None:
        segments = [
            _heading(
                page=320,
                order=50,
                segment_type="chapter",
                roman="Kosiyavagga 5. Nisīdanasanthatasikkhāpada",
                section_no=2,
            )
        ]
        planner = MatikaTocPlanner(
            {
                "schema_version": 1,
                "entries": [
                    {
                        "title": "Kosiyavagga",
                        "section_no": 2,
                        "page": None,
                        "kind": "h1",
                        "matched_order": 50,
                    },
                    {
                        "title": "Nisīdanasanthatasikkhāpada",
                        "section_no": 5,
                        "page": 320,
                        "kind": "h2",
                        "matched_order": 50,
                    },
                ],
            },
            segments,
        )
        marks = planner.marks_for_segment(segments[0])
        self.assertEqual(len(marks), 2)
        self.assertIn("subsection", marks[0])
        self.assertIn("subsubsection", marks[1])
        self.assertIn("2. ", marks[0])
        self.assertIn("5. ", marks[1])
        joined = "\n".join(marks)
        self.assertNotIn("โกสิยวคฺค 5", joined)

    def test_page_anchor_for_unmatched_landmark(self) -> None:
        segments = [
            {
                "page": 151,
                "order": 1,
                "segment_type": "prose",
                "text": [{"script": "thai", "value": "เนื้อหา"}],
            }
        ]
        planner = MatikaTocPlanner(
            {
                "schema_version": 1,
                "entries": [
                    {
                        "title": "Seyyasakabhikkhuvatthu",
                        "page": 151,
                        "kind": "h2",
                        "matched_order": None,
                    }
                ],
            },
            segments,
        )
        marks = planner.marks_for_segment(segments[0])
        self.assertEqual(len(marks), 1)
        self.assertTrue(marks[0].startswith(r"\csromantocmark{subsubsection}"))

    def test_page_anchor_emits_on_first_visited_segment(self) -> None:
        """Continuation may be the first row on a folio; still emit landmark."""
        segments = [
            {
                "page": 3,
                "order": 10,
                "segment_type": "prose",
                "text": [{"script": "thai", "value": "ต้น"}],
            },
            {
                "page": 4,
                "order": 11,
                "segment_type": "prose_continuation",
                "text": [{"script": "thai", "value": "ต่อ"}],
            },
            {
                "page": 4,
                "order": 12,
                "segment_type": "prose",
                "text": [{"script": "thai", "value": "ถัดไป"}],
            },
        ]
        planner = MatikaTocPlanner(
            {
                "schema_version": 1,
                "entries": [
                    {
                        "title": "Kukkuṭacchāpakūpamākathā",
                        "page": 4,
                        "kind": "h2",
                        "matched_order": None,
                    }
                ],
            },
            segments,
        )
        self.assertEqual(planner.marks_for_segment(segments[0]), [])
        marks = planner.marks_for_segment(segments[1])
        self.assertEqual(len(marks), 1)
        self.assertIn("กุกฺกุฏจฺฉาปกูปมากถา", marks[0])
        self.assertEqual(planner.marks_for_segment(segments[2]), [])

    def test_outline_order_parents_before_page_landmarks(self) -> None:
        """Book/kaṇḍa marks precede page-1 landmarks that share the folio."""
        segments = [
            {
                "page": 1,
                "order": 1,
                "segment_type": "prose",
                "text": [{"script": "thai", "value": "ต้น"}],
            },
            {
                "page": 1,
                "order": 2,
                "segment_type": "gambhīra",
                "heading_kind": "boo",
                "text": [{"script": "roman", "value": "Pārājikapāḷi"}],
            },
            {
                "page": 1,
                "order": 4,
                "segment_type": "chapter",
                "heading_kind": "cha",
                "text": [{"script": "roman", "value": "Verañjakaṇḍa"}],
            },
        ]
        planner = MatikaTocPlanner(
            {
                "schema_version": 1,
                "entries": [
                    {
                        "title": "Pārājikapāḷi",
                        "page": None,
                        "kind": "boo",
                        "matched_order": 2,
                    },
                    {
                        "title": "Verañjakaṇḍa",
                        "page": None,
                        "kind": "cha",
                        "matched_order": 4,
                    },
                    {
                        "title": "Bhagavato paribhavakathā",
                        "page": 1,
                        "kind": "h2",
                        "matched_order": None,
                    },
                    {
                        "title": "Kukkuṭacchāpakūpamākathā",
                        "page": 4,
                        "kind": "h2",
                        "matched_order": None,
                    },
                ],
            },
            segments,
        )
        self.assertEqual(planner.marks_for_segment(segments[0]), [])
        marks2 = planner.marks_for_segment(segments[1])
        self.assertEqual(len(marks2), 1)
        self.assertIn("ปาราชิกปาฬิ", marks2[0])
        marks4 = planner.marks_for_segment(segments[2])
        self.assertEqual(len(marks4), 2)
        self.assertIn("เวรญฺชกณฺฑ", marks4[0])
        self.assertIn("ภควโต", marks4[1])

    def test_skips_past_matched_order_inversion(self) -> None:
        """Late outline row rematched to an early order must not stall TOC."""
        segments = [
            {
                "page": 1,
                "order": 4,
                "segment_type": "chapter",
                "text": [{"script": "thai", "value": "กัณฑ์"}],
            },
            {
                "page": 6,
                "order": 37,
                "segment_type": "chapter",
                "text": [{"script": "thai", "value": "สิกขาปท"}],
            },
            {
                "page": 51,
                "order": 100,
                "segment_type": "chapter",
                "text": [{"script": "thai", "value": "วรรคถัดไป"}],
            },
        ]
        planner = MatikaTocPlanner(
            {
                "schema_version": 1,
                "entries": [
                    {
                        "title": "Pācittiyakaṇḍa",
                        "page": None,
                        "kind": "cha",
                        "matched_order": 4,
                        "section_no": 5,
                    },
                    {
                        "title": "Omasavādasikkhāpada",
                        "page": 6,
                        "kind": "h2",
                        "matched_order": 37,
                        "section_no": 2,
                    },
                    {
                        "title": "Pācittiyapāḷi",
                        "page": None,
                        "kind": "boo",
                        "matched_order": 2,
                    },
                    {
                        "title": "Bhūtagāmavagga",
                        "page": None,
                        "kind": "h1",
                        "matched_order": 100,
                        "section_no": 2,
                    },
                ],
            },
            segments,
        )
        self.assertEqual(len(planner.marks_for_segment(segments[0])), 1)
        self.assertEqual(len(planner.marks_for_segment(segments[1])), 1)
        marks = planner.marks_for_segment(segments[2])
        self.assertEqual(len(marks), 1)
        self.assertIn("ภูตคามวคฺค", marks[0])

    def test_matika_toc_mark_levels(self) -> None:
        cmd = matika_toc_mark(
            {"title": "Cīvaravagga", "section_no": 1, "kind": "h1"}
        )
        self.assertIsNotNone(cmd)
        assert cmd is not None
        self.assertIn("{subsection}", cmd)
        self.assertIn("1. ", cmd)

    def test_matika_toc_mark_h3_is_paragraph(self) -> None:
        cmd = matika_toc_mark(
            {"title": "Paṭhamapaññatti", "page": 25, "kind": "h3"}
        )
        self.assertIsNotNone(cmd)
        assert cmd is not None
        self.assertIn("{paragraph}", cmd)

    def test_matika_entry_toc_title_prefixes_section_no(self) -> None:
        title = matika_entry_toc_title(
            {"title": "Kosiyavagga", "section_no": 2}
        )
        self.assertTrue(title.startswith("2. "))


class NormalizeTests(unittest.TestCase):
    def test_strips_leading_number(self) -> None:
        self.assertEqual(
            normalize_title("5. Nisīdanasanthatasikkhāpada"),
            "nisīdanasanthatasikkhāpada",
        )


if __name__ == "__main__":
    unittest.main()
