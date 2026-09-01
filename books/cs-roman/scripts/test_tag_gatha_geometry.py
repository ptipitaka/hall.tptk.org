"""Tests for geometry-based gāthā tagging."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from cs_roman_hanging import (  # noqa: E402
    _is_first_indent,
    _is_gatha_geometry_indent,
    _is_gatha_indent,
    _match_cached_line,
    normalize_match_text,
    page_body_lines,
)
from extract_cs_roman_pdf import (  # noqa: E402
    Segment,
    _looks_like_bat_gatha_line,
    _looks_like_gatha_line,
    _looks_like_gatha_seed_line,
    detect_content_start,
    expand_glued_gatha_printed_lines,
    group_gatha_stanzas,
    split_glued_gatha_printed_line_tail,
    tag_gatha_by_geometry,
)


class ThreeBatOneAndHalfTests(unittest.TestCase):
    def test_three_bat_lines_merge_into_one_segment(self) -> None:
        """3 printed bat-lines → one บทครึ่ง segment (3 bats), not irregular half."""
        lines = [
            Segment(
                page=8,
                order=1,
                item=None,
                segment_type="gatha",
                text="Manāpameva bhāseyya, nā’manāpaṃ kudācanaṃ.",
            ),
            Segment(
                page=8,
                order=2,
                item=None,
                segment_type="gatha",
                text="Manāpaṃ bhāsamānassa, garuṃ bhāraṃ udabbahi.",
            ),
            Segment(
                page=8,
                order=3,
                item=None,
                segment_type="gatha",
                text="Dhanañca naṃ alābhesi, tena ca’ttamano ahūti.",
            ),
        ]
        grouped = group_gatha_stanzas(lines)
        gathas = [s for s in grouped if s.segment_type == "gatha"]
        self.assertEqual(len(gathas), 1)
        self.assertEqual(len(gathas[0].bats or []), 3)
        self.assertEqual(gathas[0].source_layout, "bat_line")
        self.assertFalse(gathas[0].needs_review)
        self.assertNotIn("irregular_gatha_stanza", gathas[0].review_reasons)

    def test_section_rule_tail_does_not_block_bat_split(self) -> None:
        """Trailing ``_____`` glued by extract must not leave the last บาท unsplit."""
        from cs_roman_text import SECTION_RULE_FLAG

        lines = [
            Segment(
                page=340,
                order=1,
                item=None,
                segment_type="gatha",
                text="Vesālī Vajji Nāḷandā, Bhāradvāja Soṇo ca Ghosito.",
            ),
            Segment(
                page=340,
                order=2,
                item=None,
                segment_type="gatha",
                text="Hāliddiko Nakulapitā, Lohicco Verahaccānīti. _____",
            ),
        ]
        grouped = group_gatha_stanzas(lines)
        gathas = [s for s in grouped if s.segment_type == "gatha"]
        self.assertEqual(len(gathas), 1)
        bats = gathas[0].bats or []
        self.assertEqual([len(b.get("waks") or []) for b in bats], [2, 2])
        self.assertEqual(gathas[0].source_layout, "bat_line")
        self.assertNotIn("irregular_gatha_stanza", gathas[0].review_reasons)
        self.assertIn(SECTION_RULE_FLAG, gathas[0].flags)
        # No leftover ``_____`` gatha segment.
        self.assertFalse(
            any(
                (s.bats or [{}])[0].get("waks", [{}])[0].get("text") == "_____"
                for s in gathas
                if s.bats
            )
        )
        right = bats[1]["waks"][1]["text"]
        self.assertEqual(right, "Lohicco Verahaccānīti.")
        self.assertNotIn("_____", right)


class MixedBatAndLongSingleTests(unittest.TestCase):
    def test_long_single_lines_use_mixed_layout(self) -> None:
        """04Vin04 p.103: one bat pair + two long stop lines → mixed."""
        from extract_cs_roman_pdf import gatha_layout_fix_target
        from generate_cs_roman_tex import gatha_stanza_line_bodies

        lines = [
            Segment(
                page=103,
                order=1,
                item=None,
                segment_type="gatha",
                text="Pārivāsikesu tayo, catu mānattacārike.",
            ),
            Segment(
                page=103,
                order=2,
                item=None,
                segment_type="gatha",
                text="Na samenti ratticchedesu mānattesu ca devasi.",
            ),
            Segment(
                page=103,
                order=3,
                item=None,
                segment_type="gatha",
                text="Dve kammā sadisā sesā tayo kammā samāsamāti.",
            ),
        ]
        grouped = group_gatha_stanzas(lines)
        gathas = [s for s in grouped if s.segment_type == "gatha"]
        self.assertEqual(len(gathas), 1)
        g = gathas[0]
        self.assertEqual(g.source_layout, "mixed")
        self.assertEqual(len(g.bats or []), 2)
        self.assertEqual(g.bats[0]["waks"][0]["text"], "Pārivāsikesu tayo,")
        self.assertEqual(
            g.bats[1]["waks"][0]["text"],
            "Na samenti ratticchedesu mānattesu ca devasi.",
        )
        self.assertIn("mixed_gatha_layout", g.review_reasons)
        self.assertFalse(g.needs_review)

        folded = {
            "segment_type": "gatha",
            "source_layout": "wak_line",
            "bats": [
                {
                    "waks": [
                        {
                            "text": [
                                {"script": "roman", "value": "Pārivāsikesu tayo,"},
                                {"script": "thai", "value": "ปาริวาสิเกสุ ตโย,"},
                            ]
                        },
                        {
                            "text": [
                                {
                                    "script": "roman",
                                    "value": "catu mānattacārike.",
                                },
                                {
                                    "script": "thai",
                                    "value": "จตุ มานตฺตจาริเก.",
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
                                    "value": "Na samenti ratticchedesu{{n0}} mānattesu ca devasi.",
                                },
                                {
                                    "script": "thai",
                                    "value": "น สเมนฺติ รตฺติจฺเฉเทสุ{{n0}} มานตฺเตสุ จ เทวสิ.",
                                },
                            ]
                        },
                        {
                            "text": [
                                {
                                    "script": "roman",
                                    "value": "Dve kammā sadisā sesā tayo kammā samāsamāti{{n0}}.",
                                },
                                {
                                    "script": "thai",
                                    "value": "เทฺว กมฺมา สทิสา เสสา ตโย กมฺมา สมาสมาติ{{n0}}.",
                                },
                            ]
                        },
                    ]
                },
            ],
        }
        self.assertEqual(gatha_layout_fix_target(folded), "mixed")
        folded["source_layout"] = "mixed"
        bodies = gatha_stanza_line_bodies(folded)
        self.assertEqual(len(bodies), 3)
        self.assertTrue(bodies[0].startswith(r"\csromangathabat{"))
        self.assertIn("ปาริวาสิเกสุ ตโย,", bodies[0])
        self.assertIn("จตุ มานตฺตจาริเก.", bodies[0])
        self.assertNotIn(r"\csromangathabat", bodies[1])
        self.assertNotIn(r"\csromangathabat", bodies[2])
        self.assertIn("น สเมนฺติ", bodies[1])
        self.assertIn("เทฺว กมฺมา", bodies[2])

        pure_bat = {
            "segment_type": "gatha",
            "source_layout": "bat_line",
            "bats": [
                {
                    "waks": [
                        {"text": [{"script": "roman", "value": "Mūlāya mānattārahā,"}]},
                        {
                            "text": [
                                {
                                    "script": "roman",
                                    "value": "tathā mānattacāritā.",
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
                                    "script": "roman",
                                    "value": "Abbhānārahe nayo cāpi,",
                                }
                            ]
                        },
                        {
                            "text": [
                                {
                                    "script": "roman",
                                    "value": "sambhedam nayato puna.",
                                }
                            ]
                        },
                    ]
                },
            ],
        }
        self.assertIsNone(gatha_layout_fix_target(pure_bat))


class Vin03Item39FoldTests(unittest.TestCase):
    def test_printed_bat_lines_split_instead_of_one_wak(self) -> None:
        """03Vin03 item 39: ``A, B.`` lines become bat columns, not one วรรค."""
        from generate_cs_roman_tex import gatha_stanza_line_bodies

        lines = [
            Segment(
                page=33,
                order=1,
                item=39,
                segment_type="gatha",
                text="Nerañjarāyaṃ Bhagavā, Uruvelakassapaṃ jaṭilaṃ avoca.",
            ),
            Segment(
                page=33,
                order=2,
                item=None,
                segment_type="gatha",
                text="Sace te Kassapa agaru, viharemu ajjaṇho aggisālamhīti.",
            ),
            Segment(
                page=33,
                order=3,
                item=None,
                segment_type="gatha",
                text="Na kho me mahāsamaṇa garu,",
            ),
            Segment(
                page=33,
                order=4,
                item=None,
                segment_type="gatha",
                text="Phāsukāmova taṃ nivāremi.",
            ),
            Segment(
                page=33,
                order=5,
                item=None,
                segment_type="gatha",
                text="Abhīto pāvisi bhayamatīto.",
            ),
            Segment(
                page=33,
                order=6,
                item=None,
                segment_type="gatha",
                text="Disvā isiṃ paviṭṭhaṃ, ahināgo dummano padhūpāyi.",
            ),
            Segment(
                page=33,
                order=7,
                item=None,
                segment_type="gatha",
                text="Sumanamanaso adhimano, manussanāgopi tattha padhūpāyi.",
            ),
        ]
        grouped = group_gatha_stanzas(lines)
        gathas = [s for s in grouped if s.segment_type == "gatha"]
        self.assertGreaterEqual(len(gathas), 2)
        first = gathas[0]
        self.assertEqual(first.source_layout, "bat_line")
        self.assertEqual(first.bats[0]["waks"][0]["text"], "Nerañjarāyaṃ Bhagavā,")
        self.assertEqual(
            first.bats[0]["waks"][1]["text"],
            "Uruvelakassapaṃ jaṭilaṃ avoca.",
        )

        disva_seg = None
        disva_bat = None
        for g in gathas:
            for bat in g.bats or []:
                waks = bat.get("waks") or []
                left = (waks[0].get("text") if waks else "") or ""
                if str(left).startswith("Disvā isiṃ"):
                    disva_seg = g
                    disva_bat = bat
                    break
            if disva_bat is not None:
                break
        self.assertIsNotNone(disva_seg)
        self.assertIsNotNone(disva_bat)
        assert disva_seg is not None
        assert disva_bat is not None
        self.assertEqual(disva_seg.source_layout, "bat_line")
        waks = disva_bat["waks"]
        self.assertEqual(waks[0]["text"], "Disvā isiṃ paviṭṭhaṃ,")
        self.assertEqual(waks[1]["text"], "ahināgo dummano padhūpāyi.")

        folded = {
            "segment_type": "gatha",
            "source_layout": "bat_line",
            "bats": [
                {
                    "waks": [
                        {
                            "text": [
                                {
                                    "script": "roman",
                                    "value": "Disvā isiṃ paviṭṭhaṃ,",
                                },
                                {"script": "thai", "value": "ทิสฺวา อิสิํ ปวิฏฺฐํ,"},
                            ]
                        },
                        {
                            "text": [
                                {
                                    "script": "roman",
                                    "value": "ahināgo dummano padhūpāyi.",
                                },
                                {
                                    "script": "thai",
                                    "value": "อหินาโค ทุมฺมโน ปธูปายิ.",
                                },
                            ]
                        },
                    ]
                }
            ],
        }
        bodies = gatha_stanza_line_bodies(folded)
        self.assertEqual(len(bodies), 1)
        self.assertTrue(bodies[0].startswith(r"\csromangathabat{"))
        self.assertIn("ทิสฺวา อิสิํ ปวิฏฺฐํ,", bodies[0])
        self.assertIn("อหินาโค ทุมฺมโน ปธูปายิ.", bodies[0])


_PDF = (
    Path(__file__).resolve().parents[1]
    / "volumes"
    / "01Vin01"
    / "source"
    / "01Vin01.pdf"
)
_PDF_02 = (
    Path(__file__).resolve().parents[1]
    / "volumes"
    / "02Vin02"
    / "source"
    / "02Vin02.pdf"
)
_PDF_03 = (
    Path(__file__).resolve().parents[1]
    / "source"
    / "03Vin03.pdf"
)
if not _PDF_03.is_file():
    _PDF_03 = (
        Path(__file__).resolve().parents[1]
        / "volumes"
        / "03Vin03"
        / "source"
        / "03Vin03.pdf"
    )


class GathaIndentBandTests(unittest.TestCase):
    def test_bands(self) -> None:
        self.assertTrue(_is_gatha_indent(119.3))  # dialogue * (p.223)
        self.assertTrue(_is_gatha_indent(127.4))
        self.assertTrue(_is_gatha_indent(138.7))
        self.assertTrue(_is_gatha_indent(149.0))
        self.assertFalse(_is_gatha_indent(105.8))  # hang
        self.assertFalse(_is_gatha_indent(116.0))  # hang upper edge
        self.assertFalse(_is_gatha_indent(84.2))  # first indent
        self.assertFalse(_is_gatha_indent(62.6))  # flush
        self.assertFalse(_is_gatha_indent(187.0))  # centered title

    def test_geometry_indent_includes_hang_band_verse(self) -> None:
        """Embedded bat lines near hang (Manāpameva ~98–108) are taggable."""
        self.assertTrue(_is_gatha_geometry_indent(98.3))
        self.assertTrue(_is_gatha_geometry_indent(108.0))
        self.assertTrue(_is_gatha_geometry_indent(119.3))
        self.assertFalse(_is_gatha_geometry_indent(84.2))
        self.assertFalse(_is_gatha_geometry_indent(62.6))
        self.assertFalse(_is_gatha_geometry_indent(96.0))


class NormalizeApparatusTests(unittest.TestCase):
    def test_strips_star_prefix_for_match(self) -> None:
        seg = "{{*}}\u201cA\u00f1\u00f1\u0101th\u0101 santamatt\u0101na\u1e43, a\u00f1\u00f1ath\u0101 yo pavedaye."
        pdf = "* \u201cA\u00f1\u00f1\u0101th\u0101 santamatt\u0101na\u1e43, a\u00f1\u00f1ath\u0101 yo pavedaye."
        self.assertEqual(normalize_match_text(seg), normalize_match_text(pdf))


class VerseShapeTests(unittest.TestCase):
    def test_bat_line_is_seed(self) -> None:
        self.assertTrue(
            _looks_like_gatha_seed_line(
                "{{*}}\u201cA\u00f1\u00f1\u0101th\u0101 santamatt\u0101na\u1e43, a\u00f1\u00f1ath\u0101 yo pavedaye."
            )
        )
        self.assertTrue(
            _looks_like_gatha_seed_line(
                "Nikacca kitavasseva, bhutta\u1e43 theyyena tassa ta\u1e43."
            )
        )

    def test_bat_line_requires_comma_and_stop(self) -> None:
        """Each bat-line บาท is ``วรรค, วรรค.`` — both marks required."""
        from extract_cs_roman_pdf import _looks_like_bat_gatha_line

        self.assertTrue(
            _looks_like_bat_gatha_line(
                "Manāpameva bhāseyya, nā’manāpaṃ kudācanaṃ."
            )
        )
        self.assertTrue(
            _looks_like_bat_gatha_line(
                "Dhanañca naṃ alābhesi, tena ca’ttamano ahūti."
            )
        )
        # period only — not a full บาท line
        self.assertFalse(
            _looks_like_bat_gatha_line("Tadāpi me bhikkhave amanāpā khuṃsanā.")
        )
        # comma only — wak_line first half, not bat_line
        self.assertFalse(_looks_like_bat_gatha_line("Dārudakā mattikā dve tiṇāni,"))

    def test_wak_comma_is_seed(self) -> None:
        self.assertTrue(
            _looks_like_gatha_seed_line("D\u0101rudak\u0101 mattik\u0101 dve ti\u1e47\u0101ni,")
        )

    def test_prose_not_seed(self) -> None:
        self.assertFalse(
            _looks_like_gatha_seed_line(
                "Atha kho Bhagav\u0101 Vaggumud\u0101t\u012briye bhikkh\u016b anekapariy\u0101yena"
            )
        )
        # Closers / short sentences are not seeds; geometry blocks false runs.
        self.assertFalse(
            _looks_like_gatha_seed_line("Santhatabh\u0101\u1e47av\u0101ro ni\u1e6d\u1e6dhito.")
        )
        # wak second half is allowed as a continuation shape
        self.assertTrue(
            _looks_like_gatha_line("Sa\u1e43ghassa satta avah\u0101si seyya\u1e43.")
        )
        self.assertTrue(
            _looks_like_gatha_line(
                "Ettheva te mano na ramittha (Kassapāti Bhagavā,)"
            )
        )


@unittest.skipUnless(_PDF.is_file(), "01Vin01.pdf not available")
class Page222EmbeddedWakTests(unittest.TestCase):
    def test_footnote_digit_line_joins_gatha_run(self) -> None:
        """Videsso1 (PDF) / Videsso{{n0}} must stay inside the wak_line stanza."""
        try:
            import fitz
        except ImportError:
            self.skipTest("pymupdf not installed")

        doc = fitz.open(_PDF)
        cs = detect_content_start(doc)
        assert cs is not None
        pdf_page = cs + 222 - 1
        lines = page_body_lines(doc[pdf_page - 1])
        verse_lines = [ln for ln in lines if _is_gatha_indent(ln.x0)]
        self.assertGreaterEqual(len(verse_lines), 4)

        segs = []
        for i, ln in enumerate(verse_lines[:4]):
            text = ln.text
            # Mimic attach_notes: glued PDF digit → {{n0}} marker.
            text = text.replace("* ", "{{*}}").replace("+ ", "{{+}}")
            text = text.replace("Videsso1", "Videsso{{n0}}")
            segs.append(
                Segment(
                    page=222,
                    order=i + 1,
                    item=344,
                    segment_type="prose",
                    text=text,
                    pdf_page=pdf_page,
                    notes=(["Desso (Sī)"] if "{{n0}}" in text else []),
                    flags=(["star"] if "{{*}}" in text else []),
                )
            )
        segs.append(
            Segment(
                page=222,
                order=5,
                item=344,
                segment_type="prose",
                text="Tesaṃ hi nāma bhikkhave tiracchānagatānaṃ",
                pdf_page=pdf_page,
            )
        )

        self.assertIsNotNone(
            _match_cached_line(lines, "Videsso{{n0}} hoti atiyācanāya.")
        )
        n = tag_gatha_by_geometry(doc, segs, content_start=cs)
        self.assertEqual(n, 4)
        self.assertTrue(all(s.segment_type == "gatha" for s in segs[:4]))
        self.assertTrue(all(s.item is None for s in segs[:4]))
        self.assertEqual(segs[4].segment_type, "prose")

        grouped = group_gatha_stanzas(segs)
        gathas = [s for s in grouped if s.segment_type == "gatha"]
        self.assertEqual(len(gathas), 1)
        self.assertEqual(gathas[0].source_layout, "wak_line")


@unittest.skipUnless(_PDF.is_file(), "01Vin01.pdf not available")
class Page116GeometryTagTests(unittest.TestCase):
    def test_embedded_bat_lines_become_gatha_stanzas(self) -> None:
        try:
            import fitz
        except ImportError:
            self.skipTest("pymupdf not installed")

        doc = fitz.open(_PDF)
        cs = detect_content_start(doc)
        assert cs is not None
        pdf_page = cs + 116 - 1
        lines = page_body_lines(doc[pdf_page - 1])
        verse_lines = [ln for ln in lines if _is_gatha_indent(ln.x0)]
        self.assertGreaterEqual(len(verse_lines), 6)

        # Simulate extracted printed-line prose segments (as merge_blocks leaves them).
        segs = [
            Segment(
                page=116,
                order=i + 1,
                item=195,
                segment_type="prose",
                text=ln.text.replace("* ", "{{*}}").replace("+ ", "{{+}}"),
                pdf_page=pdf_page,
                flags=(
                    ["star"]
                    if ln.text.lstrip().startswith("*")
                    else (["plus"] if ln.text.lstrip().startswith("+") else [])
                ),
            )
            for i, ln in enumerate(verse_lines[:6])
        ]
        # Trailing prose at first-indent must not be absorbed.
        segs.append(
            Segment(
                page=116,
                order=7,
                item=195,
                segment_type="prose",
                text="Atha kho Bhagavā Vaggumudātīriye bhikkhū anekapariyāyena",
                pdf_page=pdf_page,
            )
        )

        n = tag_gatha_by_geometry(doc, segs, content_start=cs)
        self.assertEqual(n, 6)
        self.assertTrue(all(s.segment_type == "gatha" for s in segs[:6]))
        self.assertTrue(all(s.item is None for s in segs[:6]))
        self.assertEqual(segs[6].segment_type, "prose")

        grouped = group_gatha_stanzas(segs)
        gathas = [s for s in grouped if s.segment_type == "gatha"]
        self.assertEqual(len(gathas), 3)
        self.assertTrue(all(s.source_layout == "bat_line" for s in gathas))
        self.assertEqual(segs[6].segment_type, "prose")

        # Matching still works with {{*}} vs PDF *
        m = _match_cached_line(lines, segs[0].text)
        self.assertIsNotNone(m)
        assert m is not None
        self.assertTrue(_is_gatha_indent(m.x0))


@unittest.skipUnless(_PDF_02.is_file(), "02Vin02.pdf not available")
class Page8HangBandEmbeddedGathaTests(unittest.TestCase):
    def test_manapameva_three_bats_tagged_and_grouped(self) -> None:
        """Hang-band 1 บทครึ่ง (x0~98–108) must tag as gatha, not stay prose."""
        try:
            import fitz
        except ImportError:
            self.skipTest("pymupdf not installed")

        doc = fitz.open(_PDF_02)
        cs = detect_content_start(doc)
        assert cs is not None
        pdf_page = cs + 8 - 1
        lines = page_body_lines(doc[pdf_page - 1])
        bat_lines = [
            ln
            for ln in lines
            if _is_gatha_geometry_indent(ln.x0)
            and (
                "Manāpameva" in ln.text
                or "Manāpaṃ bhāsamānassa" in ln.text
                or "Dhanañca naṃ" in ln.text
            )
        ]
        self.assertEqual(len(bat_lines), 3)
        self.assertTrue(all(_is_gatha_geometry_indent(ln.x0) for ln in bat_lines))
        self.assertFalse(_is_gatha_indent(bat_lines[0].x0))

        segs = [
            Segment(
                page=8,
                order=i + 1,
                item=13,
                segment_type="prose",
                text=ln.text.replace("* ", "{{*}}").replace("+ ", "{{+}}"),
                pdf_page=pdf_page,
                flags=(["star"] if ln.text.lstrip().startswith("*") else []),
            )
            for i, ln in enumerate(bat_lines)
        ]
        segs.append(
            Segment(
                page=8,
                order=4,
                item=13,
                segment_type="prose",
                text="Tadāpi me bhikkhave amanāpā khuṃsanā vambhanā",
                pdf_page=pdf_page,
            )
        )

        n = tag_gatha_by_geometry(doc, segs, content_start=cs)
        self.assertEqual(n, 3)
        self.assertTrue(all(s.segment_type == "gatha" for s in segs[:3]))
        self.assertEqual(segs[3].segment_type, "prose")

        grouped = group_gatha_stanzas(segs)
        gathas = [s for s in grouped if s.segment_type == "gatha"]
        self.assertEqual(len(gathas), 1)
        self.assertEqual(len(gathas[0].bats or []), 3)


@unittest.skipUnless(_PDF_02.is_file(), "02Vin02.pdf not available")
class Page77HangBandEmbeddedWakTests(unittest.TestCase):
    def test_adhicetaso_wak_lines_tagged_and_grouped(self) -> None:
        """Hang-band wak_line udāna (x0~98–108) must tag as gatha, not prose."""
        try:
            import fitz
        except ImportError:
            self.skipTest("pymupdf not installed")

        doc = fitz.open(_PDF_02)
        cs = detect_content_start(doc)
        assert cs is not None
        pdf_page = cs + 77 - 1
        lines = page_body_lines(doc[pdf_page - 1])
        wak_lines = [
            ln
            for ln in lines
            if _is_gatha_geometry_indent(ln.x0)
            and any(
                key in ln.text
                for key in (
                    "Adhicetaso",
                    "Munino monapathesu",
                    "Sok",
                    "Upasanthassa",
                )
            )
        ]
        self.assertEqual(len(wak_lines), 4)
        self.assertTrue(all(_is_gatha_geometry_indent(ln.x0) for ln in wak_lines))
        self.assertFalse(_is_gatha_indent(wak_lines[0].x0))
        seed = wak_lines[0].text.replace("* ", "{{*}}")
        self.assertTrue(_looks_like_gatha_seed_line(seed))
        self.assertFalse(_looks_like_bat_gatha_line(seed))

        segs = [
            Segment(
                page=77,
                order=i + 1,
                item=None,
                segment_type="prose",
                text=ln.text.replace("* ", "{{*}}").replace("+ ", "{{+}}"),
                pdf_page=pdf_page,
                flags=(["star"] if ln.text.lstrip().startswith("*") else []),
            )
            for i, ln in enumerate(wak_lines)
        ]
        segs.append(
            Segment(
                page=77,
                order=5,
                item=None,
                segment_type="prose",
                text="Bhikkhuniyo evamāhaṃsu “nanu avocumhā na dāni ajja ovādo",
                pdf_page=pdf_page,
            )
        )

        n = tag_gatha_by_geometry(doc, segs, content_start=cs)
        self.assertEqual(n, 4)
        self.assertTrue(all(s.segment_type == "gatha" for s in segs[:4]))
        self.assertEqual(segs[4].segment_type, "prose")

        grouped = group_gatha_stanzas(segs)
        gathas = [s for s in grouped if s.segment_type == "gatha"]
        self.assertEqual(len(gathas), 1)
        self.assertEqual(gathas[0].source_layout, "wak_line")
        self.assertEqual(len(gathas[0].bats or []), 2)


class GluedGathaBatLineExpandTests(unittest.TestCase):
    def test_expand_helpers_split_and_leave_plain_bat(self) -> None:
        glued = (
            "Appaṭivedhā Asallakkhaṇā, Anupalakkhaṇena Appaccupalakkhaṇā."
            "{{sp1}} Asamapekkhaṇā Appaccupekkhaṇā Appaccakkhakammanti."
        )
        peeled = split_glued_gatha_printed_line_tail(glued)
        self.assertIsNotNone(peeled)
        assert peeled is not None
        self.assertEqual(
            peeled[0],
            "Appaṭivedhā Asallakkhaṇā, Anupalakkhaṇena Appaccupalakkhaṇā.",
        )
        self.assertTrue(peeled[1].startswith("Asamapekkhaṇā"))
        self.assertEqual(
            expand_glued_gatha_printed_lines(
                "Aññāṇā Adassanā ceva, Anabhisamayā Ananubodhā."
            ),
            ["Aññāṇā Adassanā ceva, Anabhisamayā Ananubodhā."],
        )

    def test_yamaka_two_clause_line_not_expanded(self) -> None:
        """35Abhi07 p.76: Yamaka ``X. Y`` is one printed line, not glued verse."""
        line = "Sotaṃ sotindriyaṃ. Indriyā cakkhundriyaṃ -pa-."
        self.assertIsNone(split_glued_gatha_printed_line_tail(line))
        self.assertEqual(expand_glued_gatha_printed_lines(line), [line])
        dotted = "Sotaṃ sotindriyaṃ.  . Indriyā cakkhundriyaṃ -pa-."
        self.assertEqual(len(expand_glued_gatha_printed_lines(dotted)), 1)

    def test_space_only_bat_plus_next_line_still_expands(self) -> None:
        glued = (
            "Appaṭivedhā Asallakkhaṇā, Anupalakkhaṇena Appaccupalakkhaṇā. "
            "Asamapekkhaṇā Appaccupekkhaṇā Appaccakkhakammanti."
        )
        peeled = split_glued_gatha_printed_line_tail(glued)
        self.assertIsNotNone(peeled)
        assert peeled is not None
        self.assertTrue(peeled[1].startswith("Asamapekkhaṇā"))

    def test_vacchagotta_glued_second_line_folds_cleanly(self) -> None:
        """13Sam02 Vacchagotta uddāna: block-joined lines 2+3 must not merge."""
        lines = [
            Segment(
                page=223,
                order=1,
                item=None,
                segment_type="gatha",
                text="Aññāṇā Adassanā ceva, Anabhisamayā Ananubodhā.",
            ),
            Segment(
                page=223,
                order=2,
                item=None,
                segment_type="gatha",
                text=(
                    "Appaṭivedhā Asallakkhaṇā, Anupalakkhaṇena Appaccupalakkhaṇā."
                    "{{sp1}} Asamapekkhaṇā Appaccupekkhaṇā Appaccakkhakammanti."
                ),
            ),
        ]
        grouped = group_gatha_stanzas(lines)
        gathas = [s for s in grouped if s.segment_type.startswith("gatha")]
        flat: list[str] = []
        for g in gathas:
            for bat in g.bats or []:
                for wak in bat.get("waks") or []:
                    flat.append(str(wak.get("text") or ""))
        self.assertEqual(flat[0], "Aññāṇā Adassanā ceva,")
        self.assertEqual(flat[1], "Anabhisamayā Ananubodhā.")
        self.assertEqual(flat[2], "Appaṭivedhā Asallakkhaṇā,")
        self.assertEqual(flat[3], "Anupalakkhaṇena Appaccupalakkhaṇā.")
        self.assertEqual(
            flat[4],
            "Asamapekkhaṇā Appaccupekkhaṇā Appaccakkhakammanti.",
        )
        # Right วรรค of bat 2 must not retain the third printed line.
        self.assertNotIn("Asamapekkhaṇā", flat[3])


@unittest.skipUnless(_PDF_03.is_file(), "03Vin03.pdf not available")
class Vin03Item55FirstIndentQuoteTests(unittest.TestCase):
    def test_quoted_first_indent_verse_tags_as_gatha(self) -> None:
        """03Vin03 p.46 item 55: first-indent quoted bats must not stay prose."""
        try:
            import fitz
        except ImportError:
            self.skipTest("pymupdf not installed")

        doc = fitz.open(_PDF_03)
        cs = detect_content_start(doc)
        assert cs is not None
        pdf_page = cs + 46 - 1
        lines = page_body_lines(doc[pdf_page - 1])
        verse_lines = []
        seen_kimeva = False
        for ln in lines:
            if "Kimeva" in ln.text:
                seen_kimeva = True
            if not seen_kimeva:
                continue
            if not _is_first_indent(ln.x0):
                break
            verse_lines.append(ln)
        self.assertGreaterEqual(len(verse_lines), 4)
        self.assertTrue(_is_first_indent(verse_lines[0].x0))

        segs = [
            Segment(
                page=46,
                order=i + 1,
                item=55,
                segment_type="prose",
                text=ln.text.replace("* ", "{{*}}").replace("+ ", "{{+}}"),
                pdf_page=pdf_page,
            )
            for i, ln in enumerate(verse_lines)
        ]
        segs.append(
            Segment(
                page=47,
                order=len(segs) + 1,
                item=56,
                segment_type="prose",
                text="Atha kho āyasmā Uruvelakassapo uṭṭhāyāsanā ekaṃsaṃ uttarāsaṅgaṃ karitvā",
                pdf_page=pdf_page + 1,
            )
        )

        n = tag_gatha_by_geometry(doc, segs, content_start=cs)
        self.assertGreaterEqual(n, 4)
        self.assertEqual(segs[0].segment_type, "gatha")
        self.assertEqual(segs[0].item, 55)
        self.assertTrue(all(s.segment_type == "gatha" for s in segs[:-1]))
        self.assertEqual(segs[-1].segment_type, "prose")

        grouped = group_gatha_stanzas(segs)
        gathas = [s for s in grouped if s.segment_type == "gatha"]
        self.assertGreaterEqual(len(gathas), 1)
        first = gathas[0]
        self.assertEqual(first.source_layout, "bat_line")
        left = first.bats[0]["waks"][0]["text"]
        self.assertIn("Kimeva", str(left))
        self.assertTrue(str(left).rstrip().endswith(","))


if __name__ == "__main__":
    unittest.main()
