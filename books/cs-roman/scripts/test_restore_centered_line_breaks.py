"""Regression tests for centered-block manual line-break recovery.

The extractor collapses intra-block newlines to spaces (``_normalize_inline``),
so a centered block the source set as N independent centered lines — e.g. the
pātimokkha-uddesa formula ``Ime kho panāyasmanto … dhammā`` /
``uddesaṃ āgacchanti.`` — is stored as one joined string. These tests cover
``restore_centered_line_breaks`` (geometry-based recovery), ``{{br}}`` survival
through ``roman_to_thai``, and ``{{br}}`` → ``\\`` in the TeX emitter.
"""

from __future__ import annotations

import sys
import unittest
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import cs_roman_hanging as hanging  # noqa: E402
from cs_roman_hanging import (  # noqa: E402
    PageLine,
    restore_centered_line_breaks,
)
from cs_roman_text import (  # noqa: E402
    BR_MARKER,
    roman_to_thai,
)


@dataclass
class _Seg:
    page: int
    order: int
    item: int | None
    segment_type: str
    text: str
    pdf_page: int | None = None
    flags: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    symbol_notes: dict[str, str] = field(default_factory=dict)
    needs_review: bool = False
    review_reasons: list[str] = field(default_factory=list)
    source_layout: str | None = None
    bats: list[dict] | None = None
    hanging_lines: list[str] | None = None


def _make_doc(page_width: float = 499.0) -> Any:
    class _Page:
        rect = type("R", (), {"width": page_width})()

    class _Doc:
        page_count = 1

        def __getitem__(self, idx: int) -> object:
            return _Page()

    return _Doc()


# Measured 01Vin01 p.309 (Aniyata uddesa): two centered lines, each far
# narrower than the ~376bp measure, so the break before ``uddesaṃ`` is a
# typesetter's manual break, not a natural wrap.
_ANIYATA_LINE_1 = PageLine(
    y0=159.9, x0=141.4, x1=360.8, text="Ime kho panāyasmanto dve aniyatā dhammā"
)
_ANIYATA_LINE_2 = PageLine(
    y0=178.9, x0=197.5, x1=304.8, text=" uddesaṃ āgacchanti."
)
_ANIYATA_ROMAN = "Ime kho panāyasmanto dve aniyatā dhammā uddesaṃ āgacchanti."


class RestoreCenteredBreaksTests(unittest.TestCase):
    def test_splices_br_at_centered_line_boundary(self) -> None:
        seg = _Seg(
            page=1,
            order=1891,
            item=None,
            segment_type="prose",
            text=_ANIYATA_ROMAN,
            pdf_page=1,
            source_layout="center",
        )
        lines = [_ANIYATA_LINE_1, _ANIYATA_LINE_2]
        original = hanging.page_body_lines
        hanging.page_body_lines = lambda _page: lines  # type: ignore[assignment]
        try:
            stats = restore_centered_line_breaks(
                _make_doc(), [seg], content_start=1
            )
        finally:
            hanging.page_body_lines = original  # type: ignore[assignment]
        self.assertEqual(stats["centered_breaks_restored"], 1)
        self.assertEqual(
            seg.text,
            "Ime kho panāyasmanto dve aniyatā dhammā "
            + BR_MARKER
            + " uddesaṃ āgacchanti.",
        )

    def test_single_centered_line_gets_no_br(self) -> None:
        seg = _Seg(
            page=129,
            order=693,
            item=210,
            segment_type="prose",
            text="Baddhacakkaṃ.",
            pdf_page=129,
            source_layout="center",
        )
        lines = [PageLine(y0=173.0, x0=211.2, x1=291.1, text="Baddhacakkaṃ.")]
        original = hanging.page_body_lines
        hanging.page_body_lines = lambda _page: lines  # type: ignore[assignment]
        try:
            stats = restore_centered_line_breaks(
                _make_doc(), [seg], content_start=1
            )
        finally:
            hanging.page_body_lines = original  # type: ignore[assignment]
        self.assertEqual(stats["centered_breaks_restored"], 0)
        self.assertEqual(seg.text, "Baddhacakkaṃ.")

    def test_non_centered_segment_untouched(self) -> None:
        seg = _Seg(
            page=1,
            order=1891,
            item=443,
            segment_type="prose",
            text=_ANIYATA_ROMAN,
            pdf_page=1,
            source_layout=None,
        )
        original = hanging.page_body_lines
        hanging.page_body_lines = lambda _page: [_ANIYATA_LINE_1, _ANIYATA_LINE_2]
        try:
            stats = restore_centered_line_breaks(
                _make_doc(), [seg], content_start=1
            )
        finally:
            hanging.page_body_lines = original  # type: ignore[assignment]
        self.assertEqual(stats["centered_breaks_restored"], 0)
        self.assertEqual(seg.text, _ANIYATA_ROMAN)

    def test_reconstruction_mismatch_is_non_destructive(self) -> None:
        # The stored Roman does not match the join of the two centered lines
        # (extra trailing word), so the pass must leave the segment unchanged.
        seg = _Seg(
            page=1,
            order=1891,
            item=None,
            segment_type="prose",
            text=_ANIYATA_ROMAN + " extra",
            pdf_page=1,
            source_layout="center",
        )
        original = hanging.page_body_lines
        hanging.page_body_lines = lambda _page: [_ANIYATA_LINE_1, _ANIYATA_LINE_2]
        try:
            stats = restore_centered_line_breaks(
                _make_doc(), [seg], content_start=1
            )
        finally:
            hanging.page_body_lines = original  # type: ignore[assignment]
        self.assertEqual(stats["centered_breaks_restored"], 0)
        self.assertEqual(seg.text, _ANIYATA_ROMAN + " extra")

    def test_decorative_separator_line_not_absorbed(self) -> None:
        # The extractor groups a centered closer and the typesetter's ``_____``
        # section separator into one block (joined by ``_normalize_inline``).
        # The separator carries no letters, so it must not be treated as a
        # composing line — otherwise a ``{{br}}`` is spliced before it and
        # survives as a dangling trailing break once the decoration is stripped
        # downstream.
        seg = _Seg(
            page=25,
            order=76,
            item=None,
            segment_type="niṭṭhitaṃ",
            text="Sudinnabhāṇavāro niṭṭhito. _____",
            pdf_page=1,
            source_layout="center",
        )
        lines = [
            PageLine(
                y0=176.2,
                x0=184.3,
                x1=318.0,
                text="Sudinnabhāṇavāro niṭṭhito.",
            ),
            PageLine(y0=196.0, x0=234.4, x1=267.8, text="_____"),
            PageLine(
                y0=235.8,
                x0=214.3,
                x1=287.9,
                text="Makkaṭīvatthu",
            ),
        ]
        original = hanging.page_body_lines
        hanging.page_body_lines = lambda _page: lines  # type: ignore[assignment]
        try:
            stats = restore_centered_line_breaks(
                _make_doc(), [seg], content_start=1
            )
        finally:
            hanging.page_body_lines = original  # type: ignore[assignment]
        self.assertEqual(stats["centered_breaks_restored"], 0)
        self.assertNotIn(BR_MARKER, seg.text)

    def test_idempotent_skips_existing_br(self) -> None:
        seg = _Seg(
            page=1,
            order=1891,
            item=None,
            segment_type="prose",
            text="Ime kho panāyasmanto dve aniyatā dhammā "
            + BR_MARKER
            + " uddesaṃ āgacchanti.",
            pdf_page=1,
            source_layout="center",
        )
        original = hanging.page_body_lines
        hanging.page_body_lines = lambda _page: [_ANIYATA_LINE_1, _ANIYATA_LINE_2]
        try:
            stats = restore_centered_line_breaks(
                _make_doc(), [seg], content_start=1
            )
        finally:
            hanging.page_body_lines = original  # type: ignore[assignment]
        self.assertEqual(stats["centered_breaks_restored"], 0)
        self.assertEqual(stats["centered_breaks_existing"], 1)
        self.assertIn(BR_MARKER, seg.text)


class BrMarkerSurvivalTests(unittest.TestCase):
    def test_roman_to_thai_preserves_br(self) -> None:
        roman = "Ime kho panāyasmanto dve aniyatā dhammā " + BR_MARKER + " uddesaṃ āgacchanti."
        thai = roman_to_thai(roman)
        self.assertIn(BR_MARKER, thai)
        # The break sits between the two centered phrases, not inside a word.
        self.assertIn("ธมฺมา " + BR_MARKER + " อุทฺเทสํ", thai)

    def test_br_not_transliterated_to_letters(self) -> None:
        # ``{{br}}`` must pass through as the literal marker, never as บ/ร letters.
        thai = roman_to_thai("a " + BR_MARKER + " b")
        self.assertNotIn("บ", thai)
        self.assertNotIn("ร", thai)


class BrToTexTests(unittest.TestCase):
    def test_apply_notes_to_thai_converts_br_to_linebreak(self) -> None:
        from generate_cs_roman_tex import apply_notes_to_thai

        thai = roman_to_thai(
            "Ime kho panāyasmanto dve aniyatā dhammā "
            + BR_MARKER
            + " uddesaṃ āgacchanti."
        )
        tex, had_rule = apply_notes_to_thai(
            thai, notes=[], symbol_notes={}, apply_sentence_spacer=True
        )
        self.assertFalse(had_rule)
        self.assertIn("\\\\", tex)
        # The line break replaces the marker; the marker itself is gone.
        self.assertNotIn(BR_MARKER, tex)
        # Each centered phrase survives on its own side of the break.
        self.assertIn("ธมฺมา \\\\ อุทฺเทสํ", tex)


if __name__ == "__main__":
    unittest.main()
