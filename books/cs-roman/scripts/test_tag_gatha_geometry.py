"""Tests for geometry-based gāthā tagging."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from cs_roman_hanging import (  # noqa: E402
    _is_gatha_geometry_indent,
    _is_gatha_indent,
    _match_cached_line,
    normalize_match_text,
    page_body_lines,
)
from extract_cs_roman_pdf import (  # noqa: E402
    Segment,
    _looks_like_gatha_line,
    _looks_like_gatha_seed_line,
    detect_content_start,
    group_gatha_stanzas,
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
        self.assertFalse(gathas[0].needs_review)
        self.assertNotIn("irregular_gatha_stanza", gathas[0].review_reasons)

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


if __name__ == "__main__":
    unittest.main()
