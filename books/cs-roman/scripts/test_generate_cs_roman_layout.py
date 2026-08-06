"""Unit tests for cs-roman TeX layout emit helpers."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from paths import BOOKS, ensure_import_paths

ensure_import_paths()

from cs_roman_segments import DEFAULT_LAYOUT, save_document  # noqa: E402
from generate_cs_roman_tex import (  # noqa: E402
    PREAMBLE_WORD_SPACE,
    apply_notes_to_thai,
    build_body,
    escape_tex,
    format_gatha_group_inner,
    format_number,
    gatha_bat_tex,
    gatha_group_command,
    gatha_group_end_index,
    gatha_group_end_index_reading,
    gatha_left_column_bodies,
    gatha_measure_command,
    gatha_measure_group_command,
    gatha_set_left_command,
    gatha_stanza_commands,
    gatha_stanza_line_bodies,
    generate_reading_lines,
    generate_sync_lines,
    heading_command_with_recto_marks,
    is_prose_closer_command,
    is_section_closer,
    join_reading_flow_bodies,
    last_item_after_prose_closer_pair,
    layout_apply_command,
    note_to_thai,
    prose_with_closer_command,
    read_preamble_word_space,
    section_rule_commands,
    segment_command,
    split_recto_compound_title,
    toc_title_of,
    with_section_no,
    word_space_factor,
    wrap_word_space,
)


class GenerateCsRomanLayoutTests(unittest.TestCase):
    def test_en_dash_becomes_csromandash(self) -> None:
        """Sarabun en-dash is short; emit long discourse dash macro."""
        self.assertEqual(
            escape_tex("ภิกฺขู อามนฺเตสิ–"),
            r"ภิกฺขู อามนฺเตสิ\csromandash{}",
        )

    def test_horizontal_line_extension_becomes_csromandash(self) -> None:
        """PDF U+23AF has no Sarabun glyph; map like en-dash for legacy Thai."""
        self.assertEqual(
            escape_tex("ทิสฺสติ\u23af “เอวํ"),
            r"ทิสฺสติ\csromandash{} “เอวํ",
        )

    def test_preamble_word_space_from_tex_not_default_layout(self) -> None:
        """layout/DEFAULT absolute target scales against preamble.tex WordSpace."""
        self.assertEqual(PREAMBLE_WORD_SPACE, read_preamble_word_space())
        target = float(DEFAULT_LAYOUT["word_space"])
        self.assertEqual(
            word_space_factor(target),
            format_number(target / PREAMBLE_WORD_SPACE),
        )
        # Absolute target below the font-load baseline must still scale (overwrite).
        below = PREAMBLE_WORD_SPACE * 0.5
        self.assertEqual(
            word_space_factor(below),
            format_number(below / PREAMBLE_WORD_SPACE),
        )

    def test_layout_word_space_overwrites_drifted_preamble_baseline(self) -> None:
        """If preamble WordSpace ≠ DEFAULT, layout target still wins (spaceskip scale)."""
        import tempfile
        from pathlib import Path

        import generate_cs_roman_tex as gen

        with tempfile.TemporaryDirectory() as tmp:
            fake = Path(tmp) / "preamble.tex"
            fake.write_text(
                "\\babelfont{rm}[\n  WordSpace      = 1.6,\n]{Sarabun}\n",
                encoding="utf-8",
            )
            baseline = read_preamble_word_space(fake)
            self.assertEqual(baseline, 1.6)
            # Simulate generator math against that baseline (not DEFAULT_LAYOUT).
            target = float(DEFAULT_LAYOUT["word_space"])
            old = gen.PREAMBLE_WORD_SPACE
            try:
                gen.PREAMBLE_WORD_SPACE = baseline
                self.assertEqual(
                    gen.word_space_factor(target),
                    format_number(target / baseline),
                )
            finally:
                gen.PREAMBLE_WORD_SPACE = old

    def test_layout_apply_includes_all_keys(self) -> None:
        cmd = layout_apply_command(DEFAULT_LAYOUT)
        self.assertTrue(cmd.startswith(r"\csromanlayoutapply{"))
        ws_factor = word_space_factor(DEFAULT_LAYOUT["word_space"])
        # Absolute DEFAULT word_space → factor vs preamble; dimensions pass through.
        # Absolute DEFAULT word_space → factor vs preamble; dimensions pass through.
        self.assertIn(
            f"{{{ws_factor}}}{{1.5}}{{21.6pt}}{{5pt}}{{30pt}}{{65pt}}{{2.5em}}%",
            cmd,
        )

    def test_page_override_changes_every_slot(self) -> None:
        layout = {
            "word_space": 0.8,
            "line_space": 1.1,
            "par_indent": "18pt",
            "par_skip": "4pt",
            "gatha_stanza_skip": "4.5pt",
            "gatha_indent": "50pt",
            "emergency_stretch": "3em",
        }
        cmd = layout_apply_command(layout)
        ws_factor = word_space_factor(0.8)
        self.assertEqual(
            ws_factor, format_number(0.8 / PREAMBLE_WORD_SPACE)
        )
        self.assertIn(
            f"{{{ws_factor}}}{{1.1}}{{18pt}}{{4pt}}{{4.5pt}}{{50pt}}{{3em}}%",
            cmd,
        )

    def test_wrap_word_space_only_when_segment_differs(self) -> None:
        seg = {"page": 1, "order": 1}
        body = [r"\prose{ก}"]
        self.assertEqual(
            wrap_word_space(
                seg, body, page_word_space=1.0, segment_word_space=1.0
            ),
            body,
        )
        wrapped = wrap_word_space(
            seg, body, page_word_space=2.0, segment_word_space=0.8
        )
        ws_factor = word_space_factor(0.8)
        self.assertEqual(
            wrapped[0], rf"\csromanwordspacebegin{{{ws_factor}}}%"
        )
        self.assertEqual(wrapped[-1], r"\csromanwordspaceend")

    def test_generate_emits_volume_layout_only_for_sync(self) -> None:
        from generate_cs_roman_tex import generate

        volume_id = "_layout_test_vol"
        vol = BOOKS / "volumes" / volume_id
        data_path = vol / "data" / "segments.json"
        layout_path = vol / "data" / "layout.json"
        out_path = vol / "tex" / "body.generated.tex"
        try:
            data_path.parent.mkdir(parents=True, exist_ok=True)
            doc = {
                "schema_version": 1,
                "source": "books/cs-roman/source/01Vin01.pdf",
                "content_start_pdf_page": 24,
                "layout": {**DEFAULT_LAYOUT, "line_space": 1.2},
                "page_layout_reading_mode": {
                    "2": {
                        "line_space": 1.1,
                        "word_space": 3.0,
                    }
                },
                "segments": [
                    {
                        "page": 1,
                        "order": 1,
                        "segment_type": "prose",
                        "text": [{"script": "thai", "value": "หนึ่ง"}],
                    },
                    {
                        "page": 2,
                        "order": 2,
                        "segment_type": "prose",
                        "text": [{"script": "thai", "value": "สอง"}],
                    },
                ],
            }
            save_document(data_path, doc)
            written = generate(volume_id)
            text = written.read_text(encoding="utf-8")
            self.assertIn(r"\csromanlayoutapply{1}{1.2}{21.6pt}", text)
            self.assertIn(r"\csromanpage{2}", text)
            # Sync must not apply reading-mode page overrides.
            self.assertNotIn(r"\csromanlayoutapply{1.5}{1.1}", text)
            self.assertNotIn(r"\csromanreadingpagelayoutdef", text)
        finally:
            for path in (out_path, data_path, layout_path):
                if path.is_file():
                    path.unlink()
            for path in (data_path.parent, out_path.parent, vol):
                try:
                    path.rmdir()
                except OSError:
                    pass


class SectionNoGenerateTests(unittest.TestCase):
    def test_with_section_no_prefixes(self) -> None:
        self.assertEqual(
            with_section_no({"section_no": 1}, "ปาราชิกกณฺฑ"),
            "1. ปาราชิกกณฺฑ",
        )
        self.assertEqual(
            with_section_no({}, "ปาราชิกกณฺฑ"),
            "ปาราชิกกณฺฑ",
        )

    def test_split_recto_compound_title(self) -> None:
        self.assertEqual(
            split_recto_compound_title(
                r"1. \textbf{ปตฺตวคฺค 8. อฏฺฐมสิกฺขาปท}"
            ),
            ("1. ปตฺตวคฺค", "8. อฏฺฐมสิกฺขาปท"),
        )
        self.assertIsNone(split_recto_compound_title("1. ปตฺตวคฺค"))

    def test_heading_command_splits_compound_recto_marks(self) -> None:
        body = r"1. \textbf{ปตฺตวคฺค 8. อฏฺฐมสิกฺขาปท}"
        cmd = heading_command_with_recto_marks("2", body)
        self.assertIn(r"\csromanmarkh{1. ปตฺตวคฺค}", cmd)
        self.assertIn(r"\csromanmarkhii{8. อฏฺฐมสิกฺขาปท}", cmd)
        self.assertIn(rf"\csromanheadernomark{{2}}{{{body}}}", cmd)
        self.assertNotIn(r"\csromanheader{2}", cmd)

        plain = heading_command_with_recto_marks("2", "1. ปตฺตวคฺค")
        self.assertEqual(plain, r"\csromanheader{2}{1. ปตฺตวคฺค}")

    def test_segment_command_emits_numbered_heading(self) -> None:
        body = with_section_no({"section_no": 1}, "ปาราชิกกณฺฑ")
        cmd, _ = segment_command(
            "chapter",
            None,
            body,
            last_item=None,
            heading_kind="cha",
        )
        self.assertEqual(cmd, r"\chapterhead{1. ปาราชิกกณฺฑ}")

        cmd, _ = segment_command(
            "chapter",
            None,
            body,
            last_item=None,
            heading_kind="cha",
            chapter_page_start=True,
        )
        self.assertEqual(cmd, r"\chapterheadpage{1. ปาราชิกกณฺฑ}")

        h1_body = with_section_no(
            {"section_no": 1}, "ปฐมปาราชิก สุทินฺนภาณวาร"
        )
        cmd, _ = segment_command(
            "title",
            None,
            h1_body,
            last_item=None,
            heading_kind="h1",
        )
        self.assertEqual(
            cmd, r"\csromanheader{1}{1. ปฐมปาราชิก สุทินฺนภาณวาร}"
        )

    def test_paren_number_range_stays_unbroken(self) -> None:
        """``(12-13)`` stays one line; spaced ``(12- 13)`` is tightened."""
        tex, _ = apply_notes_to_thai(
            "อาปตฺติ ถุลฺลจฺจยสฺสาติ. (12-13)",
            notes=[],
            symbol_notes={},
        )
        self.assertIn(r"\mbox{(12-13)}", tex)
        spaced, _ = apply_notes_to_thai(
            "อาปตฺติ ถุลฺลจฺจยสฺสาติ. (12- 13)",
            notes=[],
            symbol_notes={},
        )
        self.assertIn(r"\mbox{(12-13)}", spaced)
        self.assertNotIn(r"\mbox{(12- 13)}", spaced)
        # Single paren numbers have no hyphen break point — leave alone.
        single, _ = apply_notes_to_thai(
            "อาปตฺติ ถุลฺลจฺจยสฺสาติ. (14)",
            notes=[],
            symbol_notes={},
        )
        self.assertIn("(14)", single)
        self.assertNotIn(r"\mbox{(14)}", single)
        self.assertEqual(escape_tex("(55-56)"), r"\mbox{(55-56)}")
        self.assertEqual(escape_tex("(15- 16)"), r"\mbox{(15-16)}")
        self.assertEqual(escape_tex("(27-  28)"), r"\mbox{(27-28)}")

    def test_symbol_mark_without_note_body(self) -> None:
        thai, _ = apply_notes_to_thai(
            "{{+}}เสยฺโย อโยคุโฬ ภุตฺโต,",
            notes=[],
            symbol_notes={},
        )
        self.assertIn(r"\csromansymbolmark{+}", thai)
        self.assertNotIn("missing", thai)
        self.assertNotIn(r"\csromansymbolfootnote", thai)

    def test_shared_plus_note_emits_footnote_once(self) -> None:
        """Two + callouts share one note: first foot-text, later mark only."""
        emitted: set[str] = set()
        note = {"+": "Khu 1. 57 piṭṭhe dhammapadepi."}
        first, _ = apply_notes_to_thai(
            "{{+}}กาสาวกณฺฐา พหโว,",
            notes=[],
            symbol_notes=note,
            emitted_symbol_notes=emitted,
        )
        second, _ = apply_notes_to_thai(
            "{{+}}เสยฺโย อโยคุโฬ ภุตฺโต,",
            notes=[],
            symbol_notes=note,
            emitted_symbol_notes=emitted,
        )
        self.assertIn(r"\csromansymbolfootnote{+}", first)
        self.assertIn(r"\csromansymbolmark{+}", second)
        self.assertNotIn(r"\csromansymbolfootnote", second)

    def test_bracket_symbol_note_emits_spaced_mark(self) -> None:
        """``{{[]}}`` → ``\\csromansymbolfootnote{[ ]}{…}`` (Syāma omission)."""
        thai, _ = apply_notes_to_thai(
            "[{{[]}}๒๑๙. ตีหา กาเรหิ",
            notes=[],
            symbol_notes={"[]": "Etthantare pāṭhā Syāmapotthake natthi."},
        )
        self.assertIn(r"\csromansymbolfootnote{[ ]}", thai)
        self.assertNotIn(r"\orphannote", thai)

    def test_note_to_thai_keeps_abbr_dot_word_space(self) -> None:
        """Catalog refs stay word-spaced; no sentence \\csromanspacer in notes."""
        thai = note_to_thai(
            "Imāni vatthūni Saṃ 1. 446 piṭṭhādīsupi āgatāni. So hoti."
        )
        self.assertIn("1. 446", thai)
        self.assertNotIn("{{sp1}}", thai)
        tex, _ = apply_notes_to_thai(
            "ปญฺห{{n0}}",
            notes=["Bhagavāti (Syā), Dī 1. 46, 109 piṭṭhesu."],
            symbol_notes={},
        )
        self.assertIn(r"\footnote{", tex)
        self.assertIn("1. 46", tex)
        self.assertNotIn(r"\csromanspacer", tex)

    def test_heading_drops_sp1_spacer(self) -> None:
        """Titles/chapters keep ``2. Name`` word-spaced — no \\csromanspacer."""
        tex, _ = apply_notes_to_thai(
            "จีวรวคฺค 2.{{sp1}} อุโทสิตสิกฺขาปท",
            notes=[],
            symbol_notes={},
            apply_sentence_spacer=False,
        )
        self.assertEqual(tex, "จีวรวคฺค 2. อุโทสิตสิกฺขาปท")
        self.assertNotIn(r"\csromanspacer", tex)

    def test_build_body_chapter_skips_sentence_spacer(self) -> None:
        seg = {
            "page": 297,
            "order": 1978,
            "segment_type": "chapter",
            "section_no": 1,
            "text": [
                {
                    "script": "roman",
                    "value": "Cīvaravagga 2.{{sp1}} Udositasikkhāpada",
                },
                {
                    "script": "thai",
                    "value": "จีวรวคฺค ๒.{{sp1}} อุโทสิตสิกฺขาปท",
                },
            ],
        }
        body, _ = build_body(seg)
        self.assertIn("2.", body)
        self.assertNotIn("๒", body)
        self.assertNotIn(r"\csromanspacer", body)
        self.assertIn("อุโทสิตสิกฺขาปท", body)

    def test_gatha_footnote_on_later_line(self) -> None:
        """Markers on a non-first บาท line must still resolve notes."""
        seg = {
            "page": 69,
            "order": 304,
            "segment_type": "gatha",
            "source_layout": "bat_line",
            "notes": ["Jantāgharena (Syā)"],
            "bats": [
                {
                    "waks": [
                        {
                            "text": [
                                {
                                    "script": "roman",
                                    "value": "Asambhinne Kusāpāto,",
                                },
                                {
                                    "script": "thai",
                                    "value": "อสมฺภินฺเน กุสาปาโต,",
                                },
                            ]
                        },
                        {
                            "text": [
                                {
                                    "script": "roman",
                                    "value": "jantaggena{{n0}} sahā dasa.",
                                },
                                {
                                    "script": "thai",
                                    "value": "ชนฺตคฺเคน{{n0}} สหา ทส.",
                                },
                            ]
                        },
                    ]
                }
            ],
        }
        cmds = gatha_stanza_commands(seg)
        joined = "\n".join(cmds)
        self.assertIn(r"\footnote{", joined)
        self.assertNotIn("missing note", joined)
        self.assertIn("ชนฺตาฆเรน", joined)  # Thai of Jantāgharena

    def test_gatha_stanza_optical_group(self) -> None:
        """Every บท emits \\csromangathagroup (optical block center)."""
        gatha = {
            "page": 150,
            "order": 830,
            "segment_type": "gatha",
            "source_layout": "bat_line",
            "bats": [
                {
                    "waks": [
                        {
                            "text": [
                                {
                                    "script": "thai",
                                    "value": "เมถุนาทินฺนาทานญฺจ,",
                                }
                            ]
                        },
                        {
                            "text": [
                                {
                                    "script": "thai",
                                    "value": "มนุสฺสวิคฺคหุตฺตริ.",
                                }
                            ]
                        },
                    ]
                },
                {
                    "waks": [
                        {
                            "text": [
                                {
                                    "script": "thai",
                                    "value": "ปาราชิกานิ จตฺตาริ,",
                                }
                            ]
                        },
                        {
                            "text": [
                                {
                                    "script": "thai",
                                    "value": "เฉชฺชวตฺถู อสํสยาติ.",
                                }
                            ]
                        },
                    ]
                },
            ],
        }
        cmds = gatha_stanza_commands(gatha)
        self.assertEqual(len(cmds), 1)
        self.assertTrue(cmds[0].startswith(r"\csromangathagroup{"))
        self.assertIn(r"\csromangathastanza{", cmds[0])
        self.assertIn(r" \\ ", cmds[0])
        self.assertIn(r"\csromangathabat{", cmds[0])
        self.assertIn("เมถุนาทินฺนาทานญฺจ,", cmds[0])
        self.assertIn("เฉชฺชวตฺถู อสํสยาติ.", cmds[0])

    def test_gatha_group_joins_consecutive_stanzas(self) -> None:
        """Consecutive บท → one group with one \\csromangathastanza per บท."""
        segs = [
            {
                "page": 10,
                "order": 1,
                "segment_type": "gatha",
                "source_layout": "bat_line",
                "bats": [
                    {
                        "waks": [
                            {"text": [{"script": "thai", "value": "อาอา,"}]},
                            {"text": [{"script": "thai", "value": "บีบี."}]},
                        ]
                    },
                    {
                        "waks": [
                            {"text": [{"script": "thai", "value": "ซีซี,"}]},
                            {"text": [{"script": "thai", "value": "ดีดี."}]},
                        ]
                    },
                ],
            },
            {
                "page": 10,
                "order": 2,
                "segment_type": "gatha",
                "source_layout": "bat_line",
                "bats": [
                    {
                        "waks": [
                            {"text": [{"script": "thai", "value": "อีอี,"}]},
                            {"text": [{"script": "thai", "value": "เอฟ."}]},
                        ]
                    },
                    {
                        "waks": [
                            {"text": [{"script": "thai", "value": "จีจี,"}]},
                            {"text": [{"script": "thai", "value": "เอช."}]},
                        ]
                    },
                ],
            },
            {
                "page": 10,
                "order": 3,
                "segment_type": "prose",
                "text": [{"script": "thai", "value": "ข้อความ"}],
            },
        ]
        self.assertEqual(gatha_group_end_index(segs, 0), 2)
        bodies = [
            gatha_stanza_line_bodies(segs[0]),
            gatha_stanza_line_bodies(segs[1]),
        ]
        inner = format_gatha_group_inner(bodies)
        self.assertEqual(inner.count(r"\csromangathastanza{"), 2)
        self.assertNotIn(r"\\[\gathastanzaskip]", inner)
        self.assertIn("อาอา,", inner)
        self.assertIn("เอช.", inner)
        self.assertIn(r"\csromangathabat{", inner)
        cmd = gatha_group_command(bodies)
        self.assertTrue(cmd.startswith(r"\csromangathagroup{"))
        lefts = [
            *gatha_left_column_bodies(segs[0]),
            *gatha_left_column_bodies(segs[1]),
        ]
        measure_lines = [
            *gatha_stanza_line_bodies(segs[0], for_measure=True),
            *gatha_stanza_line_bodies(segs[1], for_measure=True),
        ]
        measure = gatha_measure_group_command(lefts, measure_lines)
        self.assertTrue(measure.startswith(r"\csromangathameasuregroup{"))
        self.assertIn("อาอา,", measure)
        self.assertIn(r"\csromangathabat{", measure)
        setleft = gatha_set_left_command(lefts)
        self.assertTrue(setleft.startswith(r"\csromangathasetleft{"))
        self.assertEqual(lefts, ["อาอา,", "ซีซี,", "อีอี,", "จีจี,"])

    def test_gatha_bat_line_aligns_after_comma(self) -> None:
        """bat_line: right วรรค share a column from max left width (ฉ.284 sample)."""
        segs = [
            {
                "page": 284,
                "order": 1,
                "segment_type": "gatha",
                "source_layout": "bat_line",
                "bats": [
                    {
                        "waks": [
                            {
                                "text": [
                                    {
                                        "script": "thai",
                                        "value": "วิสฺสฏฺฐิ กายสํสคฺคํ,",
                                    }
                                ]
                            },
                            {
                                "text": [
                                    {
                                        "script": "thai",
                                        "value": "ทุฏฺฐุลฺลํ อตฺตกามญฺจ.",
                                    }
                                ]
                            },
                        ]
                    },
                    {
                        "waks": [
                            {
                                "text": [
                                    {
                                        "script": "thai",
                                        "value": "สญฺจริตฺตํ กุฏี เจว,",
                                    }
                                ]
                            },
                            {
                                "text": [
                                    {
                                        "script": "thai",
                                        "value": "วิหาโร จ อมูลกํ.",
                                    }
                                ]
                            },
                        ]
                    },
                ],
            },
            {
                "page": 284,
                "order": 2,
                "segment_type": "gatha",
                "source_layout": "bat_line",
                "bats": [
                    {
                        "waks": [
                            {
                                "text": [
                                    {
                                        "script": "thai",
                                        "value": "กิญฺจิเลสญฺจ เภโท จ,",
                                    }
                                ]
                            },
                            {
                                "text": [
                                    {
                                        "script": "thai",
                                        "value": "ตสฺเสว อนุวตฺตกา.",
                                    }
                                ]
                            },
                        ]
                    },
                    {
                        "waks": [
                            {
                                "text": [
                                    {
                                        "script": "thai",
                                        "value": "ทุพฺพจํ กุลทูสญฺจ,",
                                    }
                                ]
                            },
                            {
                                "text": [
                                    {
                                        "script": "thai",
                                        "value": "สํฆาทิเสสา เตรสาติ.",
                                    }
                                ]
                            },
                        ]
                    },
                ],
            },
        ]
        bodies = [gatha_stanza_line_bodies(s) for s in segs]
        self.assertEqual(len(bodies[0]), 2)
        self.assertEqual(
            bodies[0][0],
            gatha_bat_tex("วิสฺสฏฺฐิ กายสํสคฺคํ,", "ทุฏฺฐุลฺลํ อตฺตกามญฺจ."),
        )
        self.assertEqual(
            bodies[1][1],
            gatha_bat_tex("ทุพฺพจํ กุลทูสญฺจ,", "สํฆาทิเสสา เตรสาติ."),
        )
        lefts = [
            *gatha_left_column_bodies(segs[0]),
            *gatha_left_column_bodies(segs[1]),
        ]
        self.assertEqual(
            lefts,
            [
                "วิสฺสฏฺฐิ กายสํสคฺคํ,",
                "สญฺจริตฺตํ กุฏี เจว,",
                "กิญฺจิเลสญฺจ เภโท จ,",
                "ทุพฺพจํ กุลทูสญฺจ,",
            ],
        )
        # Sync emit: measuregroup + setleft + bat macros (no space-joined lines).
        doc = {"schema_version": 1, "segments": segs, "layout": DEFAULT_LAYOUT}
        lines, _ = generate_sync_lines(
            doc, [], "01Vin01", segs, DEFAULT_LAYOUT
        )
        tex = "\n".join(lines)
        self.assertIn(r"\csromangathameasuregroup{", tex)
        self.assertIn(r"\csromangathasetleft{", tex)
        self.assertIn(r"\csromangathabat{", tex)
        self.assertNotIn("กายสํสคฺคํ, ทุฏฺฐุลฺลํ", tex)

    def test_gatha_one_and_half_no_stanza_skip(self) -> None:
        """3 บาท (1 บทครึ่ง): full + half → one unbreakable stanza."""
        full = {
            "page": 185,
            "order": 1,
            "segment_type": "gatha",
            "source_layout": "bat_line",
            "bats": [
                {
                    "waks": [
                        {"text": [{"script": "thai", "value": "สญฺจิจฺจวธสปฺปาณํ,"}]},
                        {
                            "text": [
                                {
                                    "script": "thai",
                                    "value": "อุกฺโกฏํ ทุฏฺฐุลฺลฉาทนํ.",
                                }
                            ]
                        },
                    ]
                },
                {
                    "waks": [
                        {"text": [{"script": "thai", "value": "อูนวีสติ สตฺถญฺจ,"}]},
                        {
                            "text": [
                                {
                                    "script": "thai",
                                    "value": "สํวิธานํ อริฏฺฐกํ.",
                                }
                            ]
                        },
                    ]
                },
            ],
        }
        half = {
            "page": 185,
            "order": 2,
            "segment_type": "gatha",
            "source_layout": "bat_line",
            "bats": [
                {
                    "waks": [
                        {
                            "text": [
                                {
                                    "script": "thai",
                                    "value": "อุกฺขิตฺตํ กณฺฏกญฺเจว, ทส สิกฺขาปทา อิเมติ.",
                                }
                            ]
                        },
                    ]
                },
            ],
            "needs_review": True,
            "review_reasons": ["irregular_gatha_stanza"],
        }
        bodies = [
            gatha_stanza_line_bodies(full),
            gatha_stanza_line_bodies(half),
        ]
        self.assertEqual([len(b) for b in bodies], [2, 1])
        inner = format_gatha_group_inner(bodies)
        self.assertEqual(inner.count(r"\csromangathastanza{"), 1)
        self.assertIn(r" \\ ", inner)
        self.assertIn("สญฺจิจฺจวธสปฺปาณํ,", inner)
        self.assertIn("อุกฺขิตฺตํ กณฺฏกญฺเจว,", inner)

    def test_generate_page_shared_gatha_optical_center(self) -> None:
        """Two groups on one page: one measure, two groups; no fixed indent."""
        from generate_cs_roman_tex import generate

        volume_id = "_gatha_optical_vol"
        vol = BOOKS / "volumes" / volume_id
        data_path = vol / "data" / "segments.json"
        out_path = vol / "tex" / "body.generated.tex"
        try:
            data_path.parent.mkdir(parents=True, exist_ok=True)
            doc = {
                "schema_version": 1,
                "source": "books/cs-roman/source/01Vin01.pdf",
                "content_start_pdf_page": 24,
                "segments": [
                    {
                        "page": 150,
                        "order": 1,
                        "segment_type": "title",
                        "source_layout": "center",
                        "text": [
                            {"script": "roman", "value": "Tassuddānaṃ"},
                            {"script": "thai", "value": "ตสฺสุทฺทานํ"},
                        ],
                    },
                    {
                        "page": 150,
                        "order": 2,
                        "segment_type": "gatha",
                        "source_layout": "bat_line",
                        "bats": [
                            {
                                "waks": [
                                    {
                                        "text": [
                                            {
                                                "script": "thai",
                                                "value": "เมถุนาทินฺนาทานญฺจ,",
                                            }
                                        ]
                                    },
                                    {
                                        "text": [
                                            {
                                                "script": "thai",
                                                "value": "มนุสฺสวิคฺคหุตฺตริ.",
                                            }
                                        ]
                                    },
                                ]
                            },
                            {
                                "waks": [
                                    {
                                        "text": [
                                            {
                                                "script": "thai",
                                                "value": "ปาราชิกานิ จตฺตาริ,",
                                            }
                                        ]
                                    },
                                    {
                                        "text": [
                                            {
                                                "script": "thai",
                                                "value": "เฉชฺชวตฺถู อสํสยาติ.",
                                            }
                                        ]
                                    },
                                ]
                            },
                        ],
                    },
                    {
                        "page": 150,
                        "order": 3,
                        "segment_type": "prose",
                        "item": 344,
                        "text": [
                            {
                                "script": "thai",
                                "value": "ข้อความระหว่างกลุ่มคาถา",
                            }
                        ],
                    },
                    {
                        "page": 150,
                        "order": 4,
                        "segment_type": "gatha",
                        "source_layout": "bat_line",
                        "bats": [
                            {
                                "waks": [
                                    {
                                        "text": [
                                            {
                                                "script": "thai",
                                                "value": "สุสู ยถา,",
                                            }
                                        ]
                                    },
                                    {
                                        "text": [
                                            {
                                                "script": "thai",
                                                "value": "สกฺขรโธตปาณี.",
                                            }
                                        ]
                                    },
                                ]
                            },
                            {
                                "waks": [
                                    {
                                        "text": [
                                            {
                                                "script": "thai",
                                                "value": "ตาเสสสิ มํ,",
                                            }
                                        ]
                                    },
                                    {
                                        "text": [
                                            {
                                                "script": "thai",
                                                "value": "เสลมายาจมาโน.",
                                            }
                                        ]
                                    },
                                ]
                            },
                        ],
                    },
                ],
            }
            save_document(data_path, doc)
            generate(volume_id)
            tex = out_path.read_text(encoding="utf-8")
            self.assertIn(r"\csromancenter{ตสฺสุทฺทานํ}", tex)
            self.assertIn(r"\vspace{0.5\baselineskip}", tex)
            self.assertIn(r"\setlength{\csromangathapagewidth}{0pt}", tex)
            self.assertGreaterEqual(tex.count(r"\csromangathameasuregroup{"), 1)
            self.assertEqual(tex.count(r"\csromangathagroup{"), 2)
            self.assertIn(r"\csromangathabat{", tex)
            self.assertIn(r"\csromangathasetleft{", tex)
            self.assertIn("เมถุนาทินฺนาทานญฺจ,", tex)
            self.assertIn("สุสู ยถา,", tex)
            # Fixed-indent macros must not appear in generated body.
            self.assertNotIn(r"\gatha{", tex)
            self.assertNotIn(r"\gathaclose{", tex)
            # Measure lists lines from both groups (one measuregroup each).
            measure_blob = "\n".join(
                ln
                for ln in tex.splitlines()
                if ln.startswith(r"\csromangathameasuregroup{")
            )
            self.assertIn("เมถุนาทินฺนาทานญฺจ,", measure_blob)
            self.assertIn("เสลมายาจมาโน.", measure_blob)
        finally:
            if out_path.exists():
                out_path.unlink()
            if data_path.exists():
                data_path.unlink()
            layout_path = vol / "data" / "layout.json"
            if layout_path.exists():
                layout_path.unlink()
            for d in (vol / "tex", vol / "data", vol):
                if d.exists() and not any(d.iterdir()):
                    d.rmdir()

    def test_section_closer_band_for_flag_and_formulas(self) -> None:
        title_cmd, _ = segment_command(
            "title",
            None,
            "ปฐมปาราชิกํ สมตฺตํ.",
            last_item=None,
            section_rule=True,
        )
        self.assertEqual(title_cmd, r"\nitthitamruled{ปฐมปาราชิกํ สมตฺตํ.}")
        self.assertEqual(
            section_rule_commands(
                title_cmd, kind="title", section_rule=True
            ),
            [title_cmd],
        )
        # Long Anāpatti prose keeps body layout; rule is appended.
        prose_cmd, _ = segment_command(
            "prose",
            None,
            "อนาปตฺติ อตฺถปุเรกฺขารสฺส ธมฺมปุเรกฺขารสฺส "
            "อนุสาสนิปุเรกฺขารสฺส อุมฺมตฺตกสฺส อาทิกมฺมิกสฺสาติ.",
            last_item=None,
            section_rule=True,
        )
        self.assertTrue(prose_cmd.startswith(r"\prose{"))
        self.assertEqual(
            section_rule_commands(
                prose_cmd, kind="prose", section_rule=True
            ),
            [prose_cmd, r"\csromansectionrule"],
        )
        ruled, _ = segment_command(
            "niṭṭhitaṃ",
            None,
            "สุทินฺนภาณวาโร นิฏฺฐิโต.",
            last_item=None,
            section_rule=True,
        )
        self.assertEqual(
            section_rule_commands(
                ruled, kind="niṭṭhitaṃ", section_rule=True
            ),
            [r"\nitthitamruled{สุทินฺนภาณวาโร นิฏฺฐิโต.}"],
        )
        # Short samattaṃ mistagged as prose (+ spurious item) → closer band.
        catuttha, last = segment_command(
            "prose",
            232,
            "จตุตฺถปาราชิกํ สมตฺตํ.",
            last_item=231,
            section_rule=False,
        )
        self.assertEqual(catuttha, r"\nitthitam{จตุตฺถปาราชิกํ สมตฺตํ.}")
        self.assertEqual(last, 232)
        self.assertTrue(
            is_section_closer(
                "prose",
                "จตุตฺถปาราชิกํ สมตฺตํ.",
                section_rule=False,
                item=232,
            )
        )
        # Geometry center on plain prose → \csromancenter; keep item continuity.
        baddha, after_center = segment_command(
            "prose",
            210,
            "พทฺธจกฺกํ.",
            last_item=210,
            source_layout="center",
        )
        self.assertEqual(baddha, r"\csromancenter{พทฺธจกฺกํ.}")
        self.assertEqual(after_center, 210)
        # Without source_layout, middle line stays prose.
        evam, after_evam = segment_command(
            "prose",
            210,
            "เอวํ เอเกกํ มูลํ กาตุน พทฺธจกฺกํ ปริวตฺตกํ กตฺตพฺพํ.",
            last_item=after_center,
        )
        self.assertEqual(
            evam,
            r"\prose{เอวํ เอเกกํ มูลํ กาตุน พทฺธจกฺกํ ปริวตฺตกํ กตฺตพฺพํ.}",
        )
        self.assertEqual(after_evam, 210)
        # Sandwich-promoted center → \csromancenter (prose leading).
        evam_c, after_evam_c = segment_command(
            "prose",
            210,
            "เอวํ เอเกกํ มูลํ กาตุน พทฺธจกฺกํ ปริวตฺตกํ กตฺตพฺพํ.",
            last_item=after_center,
            source_layout="center",
        )
        self.assertEqual(
            evam_c,
            r"\csromancenter{เอวํ เอเกกํ มูลํ กาตุน พทฺธจกฺกํ ปริวตฺตกํ กตฺตพฺพํ.}",
        )
        self.assertEqual(after_evam_c, 210)
        # Bold title that is also centered keeps titlehead.
        bold_title, _ = segment_command(
            "title",
            None,
            r"\textbf{สนฺถตภาณวาร}",
            last_item=None,
            source_layout="center",
        )
        self.assertEqual(bold_title, r"\titlehead{\textbf{สนฺถตภาณวาร}}")
        # Plain title + center (e.g. Idaṃ sabbamūlakaṃ) → \csromancenter.
        sabba, _ = segment_command(
            "title",
            None,
            "อิทํ สพฺพมูลกํ",
            last_item=None,
            source_layout="center",
        )
        self.assertEqual(sabba, r"\csromancenter{อิทํ สพฺพมูลกํ}")
        # Numbered outline title + center keeps titlehead.
        numbered, _ = segment_command(
            "title",
            None,
            "2. ทุติยปาราชิก",
            last_item=None,
            source_layout="center",
            section_no=2,
        )
        self.assertEqual(numbered, r"\titlehead{2. ทุติยปาราชิก}")
        gambhira = r"\gambhira{ปาราชิกปาฬิ}"
        self.assertEqual(
            section_rule_commands(
                gambhira, kind="gambhīra", section_rule=True
            ),
            [gambhira],
        )

    def test_prose_with_closer_command_and_section_rule(self) -> None:
        cmd = prose_with_closer_command(
            "prose",
            "เนื้อหาก่อนปิด.",
            "ปฐมปาราชิกํ สมตฺตํ.",
            section_rule=True,
        )
        self.assertEqual(
            cmd,
            r"\prosewithcloserruled{เนื้อหาก่อนปิด.}{ปฐมปาราชิกํ สมตฺตํ.}",
        )
        self.assertTrue(is_prose_closer_command(cmd))
        self.assertEqual(
            section_rule_commands(cmd, kind="prose", section_rule=True),
            [cmd],
        )

    def test_reading_emit_pairs_prose_with_samatta_closer(self) -> None:
        segments = [
            {
                "page": 54,
                "order": 1,
                "segment_type": "prose",
                "text": [{"script": "thai", "value": "เนื้อหาก่อนปิด."}],
            },
            {
                "page": 54,
                "order": 2,
                "segment_type": "title",
                "text": [{"script": "thai", "value": "ปฐมปาราชิกํ สมตฺตํ."}],
                "flags": ["section_rule"],
            },
            {
                "page": 55,
                "order": 3,
                "segment_type": "title",
                "section_no": 2,
                "text": [{"script": "thai", "value": "ทุติยปาราชิก"}],
            },
        ]
        doc = {"schema_version": 1, "segments": segments, "layout": DEFAULT_LAYOUT}
        lines, _ = generate_reading_lines(
            doc,
            [],
            "01Vin01",
            segments,
            DEFAULT_LAYOUT,
        )
        body = "\n".join(lines)
        self.assertIn(r"\prosewithcloserruled{", body)
        self.assertIn("เนื้อหาก่อนปิด.", body)
        self.assertIn(r"{ปฐมปาราชิกํ สมตฺตํ.}", body)
        self.assertNotIn(r"\nitthitamruled{ปฐมปาราชิกํ สมตฺตํ.}", body)

    def test_last_item_after_proseitem_closer_pair(self) -> None:
        self.assertEqual(
            last_item_after_prose_closer_pair(
                "prose", 23, 22, closer_item=None
            ),
            23,
        )
        self.assertEqual(
            last_item_after_prose_closer_pair(
                "prose_continuation", None, 23, closer_item=None
            ),
            23,
        )

    def test_reading_proseitem_closer_keeps_last_item_for_next(self) -> None:
        segments = [
            {
                "page": 10,
                "order": 1,
                "item": 23,
                "segment_type": "prose",
                "text": [{"script": "thai", "value": "เนื้อหาก่อนปิด."}],
            },
            {
                "page": 10,
                "order": 2,
                "segment_type": "niṭṭhitaṃ",
                "text": [{"script": "thai", "value": "เวรญฺชภาณวาโร นิฏฺฐิโต."}],
            },
            {
                "page": 10,
                "order": 3,
                "item": 23,
                "segment_type": "prose",
                "text": [{"script": "thai", "value": "ย่อหน้าต่อภายใต้ข้อเดิม."}],
            },
        ]
        doc = {"schema_version": 1, "segments": segments, "layout": DEFAULT_LAYOUT}
        lines, _ = generate_reading_lines(
            doc, [], "01Vin01", segments, DEFAULT_LAYOUT
        )
        body = "\n".join(lines)
        self.assertIn(r"\proseitemwithcloser{23}{", body)
        self.assertIn(r"\prose{ย่อหน้าต่อภายใต้ข้อเดิม.}", body)
        self.assertNotIn(r"\proseitem{23}{ย่อหน้าต่อภายใต้ข้อเดิม.}", body)

    def test_sync_pairs_closer_once_with_symbol_note(self) -> None:
        segments = [
            {
                "page": 10,
                "order": 1,
                "segment_type": "prose",
                "text": [{"script": "thai", "value": "เนื้อหาก่อนปิด."}],
            },
            {
                "page": 10,
                "order": 2,
                "segment_type": "niṭṭhitaṃ",
                "text": [
                    {
                        "script": "thai",
                        "value": "เวรญฺชภาณวาโร{{*}} นิฏฺฐิโต.",
                    }
                ],
                "symbol_notes": {"*": "syā"},
            },
        ]
        doc = {"schema_version": 1, "segments": segments, "layout": DEFAULT_LAYOUT}
        lines, _ = generate_sync_lines(
            doc, [], "01Vin01", segments, DEFAULT_LAYOUT
        )
        body = "\n".join(lines)
        self.assertIn(r"\prosewithcloser{", body)
        self.assertIn(r"\csromansymbolfootnote{*}{", body)
        self.assertNotIn(r"\csromansymbolmark{*}", body)
        self.assertEqual(body.count(r"\csromansymbolfootnote{*}{"), 1)

    def test_sync_does_not_pair_centered_prose_with_closer(self) -> None:
        segments = [
            {
                "page": 10,
                "order": 1,
                "segment_type": "prose",
                "source_layout": "center",
                "text": [{"script": "thai", "value": "พทฺธจกฺกํ."}],
            },
            {
                "page": 10,
                "order": 2,
                "segment_type": "niṭṭhitaṃ",
                "text": [{"script": "thai", "value": "อิทํ สํขิตฺตํ นิฏฺฐิตํ."}],
            },
        ]
        doc = {"schema_version": 1, "segments": segments, "layout": DEFAULT_LAYOUT}
        lines, _ = generate_sync_lines(
            doc, [], "01Vin01", segments, DEFAULT_LAYOUT
        )
        body = "\n".join(lines)
        self.assertIn(r"\csromancenter{พทฺธจกฺกํ.}", body)
        self.assertIn(r"\nitthitam{อิทํ สํขิตฺตํ นิฏฺฐิตํ.}", body)
        self.assertNotIn(r"\prosewithcloser{", body)

    def test_toc_title_includes_section_no(self) -> None:
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
        self.assertEqual(toc_title_of(seg), "1. ปาราชิกกณฺฑ")

    def test_gatha_group_end_index_reading_spans_folios(self) -> None:
        segs = [
            {"page": 1, "order": 1, "segment_type": "gatha"},
            {"page": 2, "order": 2, "segment_type": "gatha_continuation"},
            {"page": 2, "order": 3, "segment_type": "prose"},
        ]
        self.assertEqual(gatha_group_end_index(segs, 0), 1)
        self.assertEqual(gatha_group_end_index_reading(segs, 0), 2)

    def test_join_reading_flow_bodies_marks_folio_changes(self) -> None:
        merged, marked = join_reading_flow_bodies(
            [(10, "ต้น"), (11, "ต่อ"), (11, "อีก")],
            last_folio_marked=None,
        )
        self.assertEqual(
            merged,
            r"\csromanfolio{10}ต้น \csromanfolio{11}ต่อ อีก",
        )
        self.assertEqual(marked, 11)

    def test_generate_reading_merges_continuation_without_page_break(self) -> None:
        from generate_cs_roman_tex import generate

        volume_id = "_reading_test_vol"
        vol = BOOKS / "volumes" / volume_id
        data_path = vol / "data" / "segments.json"
        layout_path = vol / "data" / "layout.json"
        sync_out = vol / "tex" / "body.generated.tex"
        reading_out = vol / "tex" / "body.reading.generated.tex"
        try:
            data_path.parent.mkdir(parents=True, exist_ok=True)
            doc = {
                "schema_version": 1,
                "source": "books/cs-roman/source/01Vin01.pdf",
                "content_start_pdf_page": 24,
                "layout": {**DEFAULT_LAYOUT},
                "page_layout_reading_mode": {
                    "100": {"line_space": 1.25},
                },
                "segments": [
                    {
                        "page": 1,
                        "order": 1,
                        "segment_type": "piṭaka",
                        "heading_kind": "nik",
                        "text": [{"script": "thai", "value": "วินยปิฏก"}],
                    },
                    {
                        "page": 1,
                        "order": 2,
                        "segment_type": "prose",
                        "item": 1,
                        "text": [{"script": "thai", "value": "ต้นย่อหน้า"}],
                    },
                    {
                        "page": 2,
                        "order": 3,
                        "segment_type": "prose_continuation",
                        "item": 1,
                        "text": [{"script": "thai", "value": "ต่อข้ามหน้า"}],
                    },
                    {
                        "page": 3,
                        "order": 4,
                        "segment_type": "chapter",
                        "heading_kind": "cha",
                        "text": [{"script": "thai", "value": "หัวข้อ"}],
                    },
                    {
                        "page": 3,
                        "order": 5,
                        "segment_type": "prose",
                        "item": 2,
                        "text": [{"script": "thai", "value": "ย่อหน้าใหม่"}],
                    },
                ],
            }
            save_document(data_path, doc)
            layout_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "source": doc["source"],
                        "content_start_pdf_page": 24,
                        "layout": {**DEFAULT_LAYOUT},
                        "page_layout_reading_mode": {
                            "100": {"line_space": 1.25},
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            sync_path = generate(volume_id, mode="sync")
            reading_path = generate(volume_id, mode="reading")
            self.assertEqual(sync_path, sync_out)
            self.assertEqual(reading_path, reading_out)

            sync_tex = sync_out.read_text(encoding="utf-8")
            reading_tex = reading_out.read_text(encoding="utf-8")

            self.assertIn(r"\csromanpage{2}", sync_tex)
            self.assertIn(r"\prosecont{ต่อข้ามหน้า}", sync_tex)
            self.assertNotIn(r"\csromanreadingpagelayoutdef", sync_tex)

            self.assertNotIn(r"\csromanpage", reading_tex)
            self.assertNotIn(r"\setcounter{page}", reading_tex)
            self.assertIn("% mode: reading", reading_tex)
            self.assertIn(r"\csromanreadingpagelayoutvolume{", reading_tex)
            self.assertIn(
                r"\csromanreadingpagelayoutdef{100}{1}{1.25}",
                reading_tex,
            )
            self.assertIn(r"\csromanreadingpagelayoutenable", reading_tex)
            self.assertNotIn(r"\csromanreadingpagelayoutdef", sync_tex)
            # Folio marks only on body — not on structural / TOC headings.
            self.assertNotIn(r"\pitaka{\csromanfolio", reading_tex)
            self.assertNotIn(r"\gambhira{\csromanfolio", reading_tex)
            self.assertNotIn(r"\chapterhead{\csromanfolio", reading_tex)
            self.assertNotIn(r"\chapterheadpage{\csromanfolio", reading_tex)
            self.assertNotIn(r"\chapterheadpageread{\csromanfolio", reading_tex)
            # cha on a new source folio → recto chapter open (plain, top pad).
            self.assertIn(r"\chapterheadpageread{หัวข้อ}", reading_tex)
            self.assertIn(r"\csromanfolio{1}", reading_tex)
            self.assertIn(r"\csromanfolio{2}", reading_tex)
            self.assertIn(r"\csromanfolio{3}", reading_tex)
            self.assertIn(
                r"\proseitem{1}{\csromanfolio{1}ต้นย่อหน้า \csromanfolio{2}ต่อข้ามหน้า}",
                reading_tex,
            )
            self.assertNotIn(r"\prosecont{", reading_tex)
            self.assertIn(
                r"\proseitem{2}{\csromanfolio{3}ย่อหน้าใหม่}",
                reading_tex,
            )
        finally:
            for path in (data_path, layout_path, sync_out, reading_out):
                if path.is_file():
                    path.unlink()
            for folder in (vol / "tex", vol / "data", vol):
                if folder.is_dir() and not any(folder.iterdir()):
                    folder.rmdir()

    def test_generate_reading_emits_page_toc_on_continuation(self) -> None:
        """Page-anchored Mātikā rows must survive reading-mode prose merges."""
        from generate_cs_roman_tex import generate

        volume_id = "_reading_toc_vol"
        vol = BOOKS / "volumes" / volume_id
        data_path = vol / "data" / "segments.json"
        layout_path = vol / "data" / "layout.json"
        matika_path = vol / "data" / "matika.json"
        reading_out = vol / "tex" / "body.reading.generated.tex"
        sync_out = vol / "tex" / "body.generated.tex"
        try:
            data_path.parent.mkdir(parents=True, exist_ok=True)
            doc = {
                "schema_version": 1,
                "source": "books/cs-roman/source/01Vin01.pdf",
                "content_start_pdf_page": 24,
                "layout": {**DEFAULT_LAYOUT},
                "page_layout_reading_mode": {},
                "segments": [
                    {
                        "page": 3,
                        "order": 16,
                        "segment_type": "prose",
                        "item": 9,
                        "text": [{"script": "thai", "value": "ต้นหน้าสาม"}],
                    },
                    {
                        "page": 4,
                        "order": 17,
                        "segment_type": "prose_continuation",
                        "item": 9,
                        "text": [{"script": "thai", "value": "ต่อหน้าสี่"}],
                    },
                    {
                        "page": 4,
                        "order": 18,
                        "segment_type": "prose",
                        "item": 10,
                        "text": [{"script": "thai", "value": "ย่อหน้าถัดไป"}],
                    },
                ],
            }
            save_document(data_path, doc)
            layout_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "source": doc["source"],
                        "content_start_pdf_page": 24,
                        "layout": {**DEFAULT_LAYOUT},
                        "page_layout_reading_mode": {},
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            matika_path.write_text(
                json.dumps(
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
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            reading_path = generate(volume_id, mode="reading")
            reading_tex = reading_path.read_text(encoding="utf-8")
            # Reading TOC page resolves via \pageref to the body dest (physical
            # sheet), not the source folio number in \csromantocmarkat.
            self.assertIn(
                r"\csromantocmarkref{subsection}{กุกฺกุฏจฺฉาปกูปมากถา}{mtk.0}",
                reading_tex,
            )
            self.assertNotIn(
                r"\csromantocmarkat{subsection}{กุกฺกุฏจฺฉาปกูปมากถา}",
                reading_tex,
            )
            # Mark must precede the merged paragraph that opens folio 4.
            mark_at = reading_tex.index("กุกฺกุฏจฺฉาปกูปมากถา")
            body_at = reading_tex.index(r"\csromanfolio{3}ต้นหน้าสาม")
            self.assertLess(mark_at, body_at)
        finally:
            for path in (
                data_path,
                layout_path,
                matika_path,
                reading_out,
                sync_out,
            ):
                if path.is_file():
                    path.unlink()
            for folder in (vol / "tex", vol / "data", vol):
                if folder.is_dir() and not any(folder.iterdir()):
                    folder.rmdir()

    def test_generate_reading_emits_clearpage_before_orders(self) -> None:
        from generate_cs_roman_tex import generate

        volume_id = "_reading_break_vol"
        vol = BOOKS / "volumes" / volume_id
        data_path = vol / "data" / "segments.json"
        layout_path = vol / "data" / "layout.json"
        sync_out = vol / "tex" / "body.generated.tex"
        reading_out = vol / "tex" / "body.reading.generated.tex"
        try:
            data_path.parent.mkdir(parents=True, exist_ok=True)
            doc = {
                "schema_version": 1,
                "source": "books/cs-roman/source/01Vin01.pdf",
                "content_start_pdf_page": 24,
                "layout": {**DEFAULT_LAYOUT},
                "page_layout_reading_mode": {},
                "page_breaks_reading_mode": {"before_orders": [4]},
                "segments": [
                    {
                        "page": 1,
                        "order": 1,
                        "segment_type": "piṭaka",
                        "heading_kind": "nik",
                        "text": [{"script": "thai", "value": "วินยปิฏก"}],
                    },
                    {
                        "page": 1,
                        "order": 2,
                        "segment_type": "prose",
                        "item": 1,
                        "text": [{"script": "thai", "value": "ย่อหน้าก่อน"}],
                    },
                    {
                        "page": 1,
                        "order": 3,
                        "segment_type": "niṭṭhitaṃ",
                        "text": [{"script": "thai", "value": "นิฏฺฐิโต."}],
                        "source_layout": "center",
                    },
                    {
                        "page": 2,
                        "order": 4,
                        "segment_type": "title",
                        "heading_kind": "h2",
                        "text": [
                            {
                                "script": "thai",
                                "value": "วินีตวตฺถุ-อุทฺทานคาถา",
                            }
                        ],
                        "source_layout": "center",
                    },
                    {
                        "page": 2,
                        "order": 5,
                        "segment_type": "prose",
                        "item": 2,
                        "text": [{"script": "thai", "value": "เนื้อหลังหัวข้อ"}],
                    },
                ],
            }
            save_document(data_path, doc)
            layout_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "source": doc["source"],
                        "content_start_pdf_page": 24,
                        "layout": {**DEFAULT_LAYOUT},
                        "page_layout_reading_mode": {},
                        "page_breaks_reading_mode": {"before_orders": [4]},
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            sync_path = generate(volume_id, mode="sync")
            reading_path = generate(volume_id, mode="reading")
            self.assertEqual(sync_path, sync_out)
            self.assertEqual(reading_path, reading_out)

            sync_tex = sync_out.read_text(encoding="utf-8")
            reading_tex = reading_out.read_text(encoding="utf-8")

            self.assertNotIn(r"\clearpage", sync_tex)
            clear_at = reading_tex.index(r"\clearpage")
            head_at = reading_tex.index(r"\csromanheader{2}{วินีตวตฺถุ-อุทฺทานคาถา}")
            self.assertLess(clear_at, head_at)
            # Only one forced break for this fixture.
            self.assertEqual(reading_tex.count(r"\clearpage"), 1)
        finally:
            for path in (data_path, layout_path, sync_out, reading_out):
                if path.is_file():
                    path.unlink()
            for folder in (vol / "tex", vol / "data", vol):
                if folder.is_dir() and not any(folder.iterdir()):
                    folder.rmdir()

    def test_generate_printing_matches_reading_flow_without_page_layout(self) -> None:
        """Printing reuses reading continuous flow but omits reading page map."""
        from generate_cs_roman_tex import generate

        geometry = (
            Path(__file__).resolve().parent.parent
            / "shared"
            / "style"
            / "pagegeometry-printing.tex"
        )
        geo = geometry.read_text(encoding="utf-8")
        self.assertIn(r"\setstocksize{230mm}{165mm}", geo)
        self.assertIn("0.937308", geo)
        self.assertIn(r"\setlrmarginsandblock{73.11bp}", geo)

        volume_id = "_printing_mode_vol"
        vol = BOOKS / "volumes" / volume_id
        data_path = vol / "data" / "segments.json"
        layout_path = vol / "data" / "layout.json"
        reading_out = vol / "tex" / "body.reading.generated.tex"
        printing_out = vol / "tex" / "body.printing.generated.tex"
        vol.mkdir(parents=True, exist_ok=True)
        (vol / "data").mkdir(exist_ok=True)
        (vol / "tex").mkdir(exist_ok=True)
        try:
            doc = {
                "schema_version": 1,
                "source": "books/cs-roman/source/_printing_mode_vol.pdf",
                "content_start_pdf_page": 24,
                "segments": [
                    {
                        "order": 1,
                        "page": 1,
                        "segment_type": "prose",
                        "item": 1,
                        "text": "pathamaṃ",
                        "text_thai": "ปฐมํ",
                    },
                    {
                        "order": 2,
                        "page": 2,
                        "segment_type": "prose_continuation",
                        "item": 1,
                        "text": "dutiyaṃ",
                        "text_thai": "ทุติยํ",
                    },
                ],
            }
            save_document(data_path, doc)
            layout_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "source": doc["source"],
                        "content_start_pdf_page": 24,
                        "layout": {**DEFAULT_LAYOUT},
                        "page_layout_reading_mode": {
                            "100": {"line_space": 1.25},
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            reading_path = generate(volume_id, mode="reading")
            printing_path = generate(volume_id, mode="printing")
            self.assertEqual(reading_path, reading_out)
            self.assertEqual(printing_path, printing_out)

            reading_tex = reading_out.read_text(encoding="utf-8")
            printing_tex = printing_out.read_text(encoding="utf-8")

            self.assertIn("% mode: printing", printing_tex)
            self.assertIn(r"\csromanfolio{1}", printing_tex)
            self.assertIn(r"\csromanfolio{2}", printing_tex)
            self.assertNotIn(r"\csromanpage", printing_tex)
            self.assertNotIn(r"\csromanreadingpagelayoutdef", printing_tex)
            self.assertNotIn(r"\csromanreadingpagelayoutenable", printing_tex)
            self.assertIn(r"\csromanreadingpagelayoutdef{100}", reading_tex)
            self.assertRegex(
                printing_tex,
                r"\\proseitem\{1\}\{\\csromanfolio\{1\}.+\s\\csromanfolio\{2\}.+\}",
            )
        finally:
            for path in (data_path, layout_path, reading_out, printing_out):
                if path.is_file():
                    path.unlink()
            for folder in (vol / "tex", vol / "data", vol):
                if folder.is_dir() and not any(folder.iterdir()):
                    folder.rmdir()


class RunningHeadGenerateTests(unittest.TestCase):
    """Running-head fields: piṭaka/nikāya injection + cha/h1 Mātikā setters."""

    def _suttanta_doc(self) -> tuple[dict, list[dict]]:
        segments = [
            {
                "page": 1,
                "order": 1,
                "segment_type": "title",
                "text": [{"script": "thai", "value": "ทีฆนิกาย"}],
            },
            {
                "page": 1,
                "order": 2,
                "segment_type": "gambhīra",
                "text": [{"script": "thai", "value": "สีลกฺขนฺธวคฺคปาฬิ"}],
            },
            {
                "page": 1,
                "order": 3,
                "segment_type": "chapter",
                "text": [{"script": "thai", "value": "พฺรหฺมชาลสุตฺต"}],
            },
        ]
        doc = {
            "schema_version": 1,
            "segments": segments,
            "layout": {**DEFAULT_LAYOUT},
            "page_layout_reading_mode": {},
        }
        return doc, segments

    def test_suttanta_injects_pitaka_and_nikaya_sync(self) -> None:
        doc, segments = self._suttanta_doc()
        lines, _ = generate_sync_lines(
            doc, [], "06Di01", segments, DEFAULT_LAYOUT
        )
        body = "\n".join(lines)
        self.assertIn(r"\setcsromanpitaka{สุตฺตนฺตปิฏก}", body)
        self.assertIn(r"\setcsromannikaya{ทีฆนิกาย}", body)

    def test_suttanta_injects_pitaka_and_nikaya_reading(self) -> None:
        doc, segments = self._suttanta_doc()
        lines, _ = generate_reading_lines(
            doc, [], "06Di01", segments, DEFAULT_LAYOUT, mode="reading"
        )
        body = "\n".join(lines)
        self.assertIn(r"\setcsromanpitaka{สุตฺตนฺตปิฏก}", body)
        self.assertIn(r"\setcsromannikaya{ทีฆนิกาย}", body)

    def test_vinaya_skips_injection_when_pitaka_present(self) -> None:
        segments = [
            {
                "page": 1,
                "order": 1,
                "segment_type": "piṭaka",
                "text": [{"script": "thai", "value": "วินยปิฏก"}],
            },
            {
                "page": 1,
                "order": 2,
                "segment_type": "gambhīra",
                "text": [{"script": "thai", "value": "ปาราชิกปาฬิ"}],
            },
        ]
        doc = {
            "schema_version": 1,
            "segments": segments,
            "layout": {**DEFAULT_LAYOUT},
            "page_layout_reading_mode": {},
        }
        lines, _ = generate_sync_lines(
            doc, [], "01Vin01", segments, DEFAULT_LAYOUT
        )
        body = "\n".join(lines)
        self.assertNotIn(r"\setcsromanpitaka{สุตฺตนฺตปิฏก}", body)
        self.assertNotIn(r"\setcsromannikaya{", body)
        self.assertIn(r"\pitaka{วินยปิฏก}", body)

    def _planner(self) -> tuple[object, list[dict]]:
        from generate_cs_roman_tex import MatikaTocPlanner

        segments = [
            {
                "page": 1,
                "order": 4,
                "segment_type": "chapter",
                "heading_kind": "cha",
                "text": [{"script": "thai", "value": "เวรญฺชกณฺฑ"}],
            },
            {
                "page": 1,
                "order": 5,
                "segment_type": "title",
                "heading_kind": "h1",
                "text": [{"script": "thai", "value": "ภควโต ปริภวกถา"}],
            },
            {
                "page": 3,
                "order": 41,
                "segment_type": "chapter",
                "heading_kind": "cha",
                "section_no": 1,
                "text": [{"script": "thai", "value": "ปาราชิกกณฺฑ"}],
            },
            {
                "page": 3,
                "order": 42,
                "segment_type": "title",
                "heading_kind": "h2",
                "section_no": 1,
                "text": [{"script": "thai", "value": "ปฐมปาราชิก"}],
            },
        ]
        matika = {
            "schema_version": 1,
            "entries": [
                {
                    "title": "Verañjakaṇḍa",
                    "page": None,
                    "kind": "cha",
                    "matched_order": 4,
                },
                {
                    "title": "Bhagavato paribhavakathā",
                    "page": 1,
                    "kind": "h1",
                    "matched_order": 5,
                },
                {
                    "title": "Pārājikakaṇḍa",
                    "page": None,
                    "kind": "cha",
                    "matched_order": 41,
                    "section_no": 1,
                },
                {
                    "title": "Paṭhamapārājika",
                    "page": None,
                    "kind": "h1",
                    "matched_order": 42,
                    "section_no": 1,
                },
            ],
        }
        planner = MatikaTocPlanner(matika, segments, mode="sync")
        return planner, segments

    def test_matika_emits_no_recto_head_setters(self) -> None:
        """Recto heads come from body marks; Mātikā only drives TOC."""
        planner, segments = self._planner()
        for seg in segments:
            self.assertEqual(planner.running_head_lines(seg), [])

    def test_append_toc_marks_skips_running_head_setters(self) -> None:
        from generate_cs_roman_tex import append_toc_marks

        planner, segments = self._planner()
        lines: list[str] = []
        append_toc_marks(lines, segments[2], planner=planner)
        joined = "\n".join(lines)
        self.assertNotIn(r"\setcsromanheadcha{", joined)
        self.assertNotIn(r"\setcsromanheadh{", joined)
        self.assertNotIn(r"\setcsromanheadhclear", joined)
        self.assertIn(r"\csromanmatikaanchor{", joined)


if __name__ == "__main__":
    unittest.main()
