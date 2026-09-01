"""Unit tests for cs-roman segments schema v1 normalize/validate."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from cs_roman_segments import (  # noqa: E402
    doc_comment_encoding_errors,
    DEFAULT_LAYOUT,
    SCHEMA_VERSION,
    compact_segment,
    doc_layout,
    doc_page_layout_reading,
    doc_reading_break_before_orders,
    effective_layout,
    effective_word_space,
    layout_path_for,
    load_document,
    migrate_segment_word_space,
    normalize_content,
    normalize_document,
    normalize_layout,
    save_document,
    seg_word_space,
    validate_document,
)


class CsRomanSegmentsTests(unittest.TestCase):
    def test_compact_omits_empty_and_unused(self) -> None:
        seg = {
            "page": 1,
            "order": 1,
            "item": None,
            "segment_type": "prose",
            "text": [
                {"script": "roman", "value": "Hello", "runs": [{"value": "Hello", "bold": False}]},
                {"script": "thai", "value": "เฮลโล", "runs": [{"value": "เฮลโล", "bold": False}]},
            ],
            "pdf_page": 24,
            "flags": [],
            "notes": [],
            "symbol_notes": {},
            "needs_review": False,
            "review_reasons": [],
            "in_toc": False,
        }
        out = compact_segment(seg)
        self.assertNotIn("item", out)
        self.assertNotIn("pdf_page", out)
        self.assertNotIn("flags", out)
        self.assertNotIn("notes", out)
        self.assertNotIn("needs_review", out)
        self.assertNotIn("in_toc", out)
        for entry in out["text"]:
            self.assertNotIn("runs", entry)

    def test_compact_keeps_bold_runs_and_gatha_without_ids(self) -> None:
        seg = {
            "page": 2,
            "order": 5,
            "segment_type": "gatha",
            "source_layout": "bat_line",
            "bats": [
                {
                    "bat": 1,
                    "waks": [
                        {
                            "wak": 1,
                            "role": "sadap",
                            "text": [
                                {
                                    "script": "thai",
                                    "value": "ก",
                                    "runs": [{"value": "ก", "bold": True}],
                                }
                            ],
                        }
                    ],
                }
            ],
            "flags": [],
            "notes": [],
            "symbol_notes": {},
            "needs_review": False,
            "review_reasons": [],
        }
        out = compact_segment(seg)
        self.assertEqual(out["bats"][0]["waks"][0]["text"][0]["runs"][0]["bold"], True)
        self.assertNotIn("bat", out["bats"][0])
        self.assertNotIn("wak", out["bats"][0]["waks"][0])
        self.assertNotIn("role", out["bats"][0]["waks"][0])

    def test_compact_keeps_section_no(self) -> None:
        seg = {
            "page": 13,
            "order": 41,
            "segment_type": "chapter",
            "heading_kind": "cha",
            "section_no": 1,
            "in_toc": True,
            "text": [
                {"script": "roman", "value": "Pārājikakaṇḍa"},
                {"script": "thai", "value": "ปาราชิกกณฺฑ"},
            ],
        }
        out = compact_segment(seg)
        self.assertEqual(out["section_no"], 1)
        self.assertEqual(out["heading_kind"], "cha")
        self.assertTrue(out["in_toc"])
        self.assertNotIn("item", out)

        bare = compact_segment({**seg, "section_no": None})
        self.assertNotIn("section_no", bare)

    def test_compact_drops_segment_word_space(self) -> None:
        seg = {
            "page": 3,
            "order": 2,
            "segment_type": "prose",
            "item": 10,
            "text": [{"script": "thai", "value": "ตตฺร เจ"}],
            "word_space": 1.2,
            "flags": [],
            "notes": [],
        }
        out = compact_segment(seg)
        self.assertNotIn("word_space", out)

    def test_migrate_drops_segment_word_space_and_page_layout(self) -> None:
        doc = {
            "page_layout": {"3": {"line_space": 1.1}},
            "segments": [
                {"page": 3, "order": 10, "segment_type": "prose"},
                {
                    "page": 3,
                    "order": 11,
                    "segment_type": "prose",
                    "word_space": 1.2,
                },
            ],
        }
        migrated = migrate_segment_word_space(doc)
        self.assertNotIn("word_space", migrated["segments"][1])
        self.assertNotIn("page_layout", migrated)

    def test_validate_rejects_segment_word_space(self) -> None:
        base = {
            "schema_version": SCHEMA_VERSION,
            "source": "books/cs-roman/source/01Vin01.pdf",
            "content_start_pdf_page": 24,
            "segments": [
                {
                    "page": 1,
                    "order": 1,
                    "segment_type": "prose",
                    "text": [{"script": "thai", "value": "ก"}],
                    "word_space": 1.5,
                }
            ],
        }
        errors = validate_document(base)
        self.assertTrue(any("word_space" in e for e in errors))

    def test_validate_rejects_removed_page_layout(self) -> None:
        base = {
            "schema_version": SCHEMA_VERSION,
            "source": "books/cs-roman/source/01Vin01.pdf",
            "content_start_pdf_page": 24,
            "layout": dict(DEFAULT_LAYOUT),
            "segments": [],
            "page_layout": {"3": {"line_space": 1.1}},
        }
        errors = validate_document(base)
        self.assertTrue(any("page_layout: removed" in e for e in errors))

    def test_normalize_document_schema(self) -> None:
        doc = normalize_document(
            {
                "source": "books/cs-roman/source/01Vin01.pdf",
                "text_format": "legacy prose",
                "heading_assignment": {"matika_entries": 1},
                "content_start_pdf_page": 24,
                "segments": [
                    {
                        "page": 1,
                        "order": 1,
                        "segment_type": "title",
                        "text": [{"script": "thai", "value": "หัวข้อ"}],
                        "heading_kind": "h1",
                        "in_toc": True,
                        "flags": [],
                        "notes": [],
                        "symbol_notes": {},
                        "needs_review": False,
                        "review_reasons": [],
                    }
                ],
            }
        )
        self.assertEqual(doc["schema_version"], SCHEMA_VERSION)
        self.assertNotIn("text_format", doc)
        self.assertNotIn("heading_assignment", doc)
        self.assertEqual(doc["layout"], DEFAULT_LAYOUT)
        self.assertNotIn("page_layout", doc)
        errors = validate_document(doc)
        self.assertEqual(errors, [])
        content = normalize_content(doc)
        self.assertEqual(set(content), {"schema_version", "segments"})
        layout = normalize_layout(doc)
        self.assertNotIn("segments", layout)
        self.assertIn("layout", layout)

    def test_normalize_fills_layout_and_keeps_reading_overrides(self) -> None:
        doc = normalize_document(
            {
                "source": "books/cs-roman/source/01Vin01.pdf",
                "content_start_pdf_page": 24,
                "layout": {"line_space": 1.15, "word_space": 2.0},
                "page_layout": {
                    "10": {"line_space": 1.1},
                },
                "page_layout_reading_mode": {
                    "100": {
                        "line_space": 1.1,
                        "word_space": 1.5,
                        "par_indent": "20pt",
                        "par_skip": "5pt",
                        "gatha_stanza_skip": "5pt",
                        "gatha_indent": "60pt",
                        "emergency_stretch": "2em",
                    },
                    "bad": {"line_space": 1.0},
                    "0": {"line_space": 1.0},
                },
                "segments": [
                    {"page": 10, "order": 1, "segment_type": "prose"},
                ],
            }
        )
        self.assertEqual(doc["layout"]["line_space"], 1.15)
        self.assertEqual(doc["layout"]["word_space"], 2.0)
        self.assertEqual(doc["layout"]["par_skip"], DEFAULT_LAYOUT["par_skip"])
        self.assertEqual(set(doc["layout"]), set(DEFAULT_LAYOUT))
        self.assertNotIn("page_layout", doc)
        self.assertEqual(list(doc["page_layout_reading_mode"]), ["100"])
        self.assertEqual(
            doc["page_layout_reading_mode"]["100"]["gatha_indent"], "60pt"
        )
        self.assertEqual(validate_document(doc), [])

    def test_validate_layout_rejects_unknown_and_bad_values(self) -> None:
        base = {
            "schema_version": SCHEMA_VERSION,
            "source": "books/cs-roman/source/01Vin01.pdf",
            "content_start_pdf_page": 24,
            "layout": dict(DEFAULT_LAYOUT),
            "segments": [],
        }
        self.assertEqual(validate_document(base), [])
        bad_key = {
            **base,
            "layout": {**DEFAULT_LAYOUT, "font_scale": 1.1},
        }
        self.assertTrue(any("unknown" in e for e in validate_document(bad_key)))
        bad_dim = {
            **base,
            "page_layout_reading_mode": {"3": {"par_skip": "wide"}},
        }
        self.assertTrue(any("par_skip" in e for e in validate_document(bad_dim)))
        bad_mult = {
            **base,
            "page_layout_reading_mode": {"3": {"line_space": 0}},
        }
        self.assertTrue(any("line_space" in e for e in validate_document(bad_mult)))

    def test_effective_layout_reading_precedence_all_keys(self) -> None:
        page_patch = {
            "word_space": 1.0,
            "line_space": 1.1,
            "par_indent": "18pt",
            "par_skip": "4pt",
            "gatha_stanza_skip": "4.5pt",
            "gatha_indent": "50pt",
            "emergency_stretch": "3em",
        }
        doc = {
            "layout": {**DEFAULT_LAYOUT, "word_space": 2.0, "line_space": 1.2},
            "page_layout_reading_mode": {"5": page_patch},
            "segments": [
                {"page": 5, "order": 1, "segment_type": "prose"},
            ],
        }
        self.assertEqual(doc_layout(doc)["word_space"], 2.0)
        # Sync ignores reading map.
        self.assertEqual(effective_layout(doc, 5)["word_space"], 2.0)
        eff = effective_layout(doc, 5, reading=True)
        expected = {**DEFAULT_LAYOUT, **page_patch}
        self.assertEqual(eff, expected)
        self.assertEqual(
            effective_layout(doc, 6, reading=True)["word_space"], 2.0
        )
        self.assertIsNone(seg_word_space(doc, doc["segments"][0]))
        self.assertEqual(
            effective_word_space(doc, doc["segments"][0], page=5),
            2.0,
        )

    def test_normalize_keeps_empty_page_layout_reading_mode(self) -> None:
        doc = normalize_layout(
            {
                "source": "books/cs-roman/source/01Vin01.pdf",
                "content_start_pdf_page": 24,
                "layout": dict(DEFAULT_LAYOUT),
                "page_layout_reading_mode": {},
            }
        )
        self.assertEqual(doc["page_layout_reading_mode"], {})
        filled = normalize_layout(
            {
                "source": "books/cs-roman/source/01Vin01.pdf",
                "content_start_pdf_page": 24,
                "layout": dict(DEFAULT_LAYOUT),
                "page_layout_reading_mode": {
                    "100": {"line_space": 1.2},
                    "bad": {"line_space": 1.0},
                },
            }
        )
        self.assertEqual(list(filled["page_layout_reading_mode"]), ["100"])
        self.assertEqual(
            filled["page_layout_reading_mode"]["100"]["line_space"], 1.2
        )

    def test_validate_page_layout_reading_mode_rejects_segments(self) -> None:
        base = {
            "schema_version": SCHEMA_VERSION,
            "source": "books/cs-roman/source/01Vin01.pdf",
            "content_start_pdf_page": 24,
            "layout": dict(DEFAULT_LAYOUT),
            "segments": [],
            "page_layout_reading_mode": {
                "10": {"line_space": 1.2, "segments": {"1": {"word_space": 1.0}}},
            },
        }
        errors = validate_document(base)
        self.assertTrue(any("page_layout_reading_mode.10.segments" in e for e in errors))
        ok = {
            **base,
            "page_layout_reading_mode": {"10": {"line_space": 1.2}},
        }
        self.assertEqual(validate_document(ok), [])

    def test_normalize_and_validate_page_breaks_reading_mode(self) -> None:
        layout = normalize_layout(
            {
                "source": "books/cs-roman/source/01Vin01.pdf",
                "content_start_pdf_page": 24,
                "layout": dict(DEFAULT_LAYOUT),
                "page_breaks_reading_mode": {
                    "before_orders": [483, 10, 483, 0, "x"],
                },
            }
        )
        self.assertEqual(
            layout["page_breaks_reading_mode"]["before_orders"],
            [10, 483],
        )
        self.assertEqual(
            doc_reading_break_before_orders(layout),
            {10, 483},
        )
        self.assertEqual(doc_reading_break_before_orders({}), set())

        base = {
            "schema_version": SCHEMA_VERSION,
            "source": "books/cs-roman/source/01Vin01.pdf",
            "content_start_pdf_page": 24,
            "layout": dict(DEFAULT_LAYOUT),
            "segments": [],
            "page_breaks_reading_mode": {"before_orders": [483]},
        }
        self.assertEqual(validate_document(base), [])
        bad = {**base, "page_breaks_reading_mode": {"before_orders": ["nope"]}}
        self.assertTrue(
            any("before_orders[0]" in e for e in validate_document(bad))
        )
        bad_key = {
            **base,
            "page_breaks_reading_mode": {"before_orders": [1], "after": []},
        }
        self.assertTrue(
            any("unknown key" in e for e in validate_document(bad_key))
        )

    def test_effective_layout_reading_uses_reading_map_not_sync(self) -> None:
        doc = {
            "layout": dict(DEFAULT_LAYOUT),
            "page_layout": {"5": {"line_space": 1.1}},
            "page_layout_reading_mode": {"5": {"line_space": 1.25}},
            "segments": [],
        }
        # Sync: volume only (legacy page_layout ignored).
        self.assertEqual(
            effective_layout(doc, 5)["line_space"], DEFAULT_LAYOUT["line_space"]
        )
        self.assertEqual(
            effective_layout(doc, 5, reading=True)["line_space"], 1.25
        )
        self.assertEqual(
            effective_layout(doc, 6, reading=True)["line_space"],
            DEFAULT_LAYOUT["line_space"],
        )
        self.assertEqual(list(doc_page_layout_reading(doc)), [5])

    def test_normalize_preserves_layout_doc_comments(self) -> None:
        layout = normalize_layout(
            {
                "source": "books/cs-roman/source/01Vin01.pdf",
                "content_start_pdf_page": 24,
                "layout": dict(DEFAULT_LAYOUT),
                "//": ["overview"],
                "//layout": "volume defaults",
                "//page_layout_reading_mode": ["reading pages"],
            }
        )
        self.assertEqual(layout["//"], ["overview"])
        self.assertEqual(layout["//layout"], "volume defaults")
        self.assertLess(list(layout).index("//"), list(layout).index("source"))
        self.assertLess(list(layout).index("//layout"), list(layout).index("layout"))

    def test_doc_comment_encoding_rejects_mojibake(self) -> None:
        # UTF-8 Thai misread as windows-874 leaves EURO / C1 controls.
        bad = {
            "//": ["layout.json \u0e40\u0e19\u20ac\u0e40\u0e18\u0099"],
            "//layout": ["word_space = " + ("x" * 900)],
        }
        errs = doc_comment_encoding_errors(bad)
        self.assertTrue(any("mojibake" in e for e in errs), errs)
        self.assertTrue(any("suspiciously long" in e for e in errs), errs)
        self.assertEqual(
            doc_comment_encoding_errors(
                {"//": ["layout.json — ปรับจังหวะการพิมพ์"]}
            ),
            [],
        )

    def test_01vin01_layout_doc_comments_are_readable_thai(self) -> None:
        root = Path(__file__).resolve().parents[1]
        path = root / "volumes" / "01Vin01" / "data" / "layout.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(doc_comment_encoding_errors(data), [])
        overview = " ".join(data["//"])
        self.assertIn("ปรับจังหวะ", overview)
        self.assertIn("บังคับขึ้นหน้า", overview)

    def test_rewrite_layout_origin_comments_points_at_git_copy(self) -> None:
        from cs_roman_segments import rewrite_layout_origin_comments

        data = {
            "source": "books/cs-roman/source/01Vin01.pdf",
            "//": [
                "layout.json — ปรับจังหวะการพิมพ์ / บังคับขึ้นหน้า (ไม่ใช่เนื้อหา)",
                "ไฟล์ต้นทาง (แก้ที่นี่): books/cs-roman/output/01Vin01.layout.json",
                "sync คัดลอกมาที่ volumes/01Vin01/data/layout.json",
                "รายละเอียดเต็ม: books/cs-roman/SCHEMA.md",
            ],
        }
        updated = rewrite_layout_origin_comments(data)
        overview = "\n".join(updated["//"])
        self.assertIn("volumes/01Vin01/data/layout.json", overview)
        self.assertNotIn("แก้ที่นี่): books/cs-roman/output/", overview)
        self.assertIn("SCHEMA.md", overview)

    def test_split_roundtrip_files(self) -> None:
        doc = {
            "schema_version": SCHEMA_VERSION,
            "source": "books/cs-roman/source/01Vin01.pdf",
            "content_start_pdf_page": 24,
            "layout": {**DEFAULT_LAYOUT, "word_space": 3.5},
            "page_layout_reading_mode": {
                "100": {"line_space": 1.2},
            },
            "segments": [
                {"page": 322, "order": 2159, "segment_type": "prose"},
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            segments_path = root / "01Vin01.segments.json"
            save_document(segments_path, doc)
            layout_path = layout_path_for(segments_path)
            self.assertTrue(layout_path.is_file())
            content = load_document(segments_path)
            self.assertEqual(content["layout"]["word_space"], 3.5)
            self.assertEqual(
                content["page_layout_reading_mode"]["100"]["line_space"],
                1.2,
            )
            self.assertNotIn("page_layout", content)
            self.assertEqual(validate_document(content), [])
            raw_content = segments_path.read_text(encoding="utf-8")
            self.assertNotIn('"layout"', raw_content)
            self.assertIn('"segments"', raw_content)
            raw_layout = layout_path.read_text(encoding="utf-8")
            self.assertIn('"layout"', raw_layout)
            self.assertNotIn('"segments": [', raw_layout)


if __name__ == "__main__":
    unittest.main()
