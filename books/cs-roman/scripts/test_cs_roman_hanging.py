"""Unit tests for CS Roman hanging-paragraph detection."""

from __future__ import annotations

import sys
import unittest
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from cs_roman_hanging import (  # noqa: E402
    HangingGroup,
    PageLine,
    _is_body_flush,
    _is_center_line,
    _is_first_indent,
    _is_gatha_indent,
    _is_hang_indent,
    _is_short_center_sandwich_text,
    _match_after_leading_tokens,
    _match_cached_line,
    merge_hanging_into_segments,
    normalize_match_text,
    segment_roman_text,
    tag_center_layout_by_geometry,
    tag_center_layout_by_sandwich,
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


class NormalizeMatchTests(unittest.TestCase):
    def test_strips_item_prefix(self) -> None:
        self.assertEqual(
            normalize_match_text("338. Paṭiggaṇhāti vīmaṃsati."),
            normalize_match_text("Paṭiggaṇhāti vīmaṃsati."),
        )


class MergeHangingTests(unittest.TestCase):
    def test_merges_head_and_children(self) -> None:
        segs: list[Any] = [
            _Seg(216, 1, 338, "prose", "Paṭiggaṇhāti vīmaṃsati paccāharati, āpatti saṃghādisesassa.", pdf_page=239),
            _Seg(216, 2, 338, "prose", "Paṭiggaṇhāti vīmaṃsati na paccāharati, āpatti thullaccayassa.", pdf_page=239),
            _Seg(216, 3, 338, "prose", "Paṭiggaṇhāti na vīmaṃsati paccāharati, āpatti thullaccayassa.", pdf_page=239),
            _Seg(216, 4, 338, "prose", "Puriso sambahule bhikkhū āṇāpeti …", pdf_page=239),
        ]
        groups = [
            HangingGroup(
                pdf_page=239,
                head="338. Paṭiggaṇhāti vīmaṃsati paccāharati, āpatti saṃghādisesassa.",
                lines=(
                    "Paṭiggaṇhāti vīmaṃsati na paccāharati, āpatti thullaccayassa.",
                    "Paṭiggaṇhāti na vīmaṃsati paccāharati, āpatti thullaccayassa.",
                ),
            )
        ]
        n = merge_hanging_into_segments(segs, groups)
        self.assertEqual(n, 1)
        self.assertEqual(len(segs), 2)
        self.assertEqual(segs[0].source_layout, "hanging")
        self.assertEqual(len(segs[0].hanging_lines or []), 2)
        self.assertEqual(segs[1].text.startswith("Puriso"), True)


class IndentBandTests(unittest.TestCase):
    def test_flush_and_indent_bands(self) -> None:
        self.assertTrue(_is_body_flush(62.6))
        self.assertFalse(_is_body_flush(84.2))
        self.assertTrue(_is_first_indent(84.2))
        self.assertFalse(_is_first_indent(62.6))
        self.assertTrue(_is_gatha_indent(119.3))  # dialogue * line (p.223)
        self.assertTrue(_is_gatha_indent(127.4))
        self.assertTrue(_is_gatha_indent(149.0))
        self.assertFalse(_is_gatha_indent(105.8))
        self.assertFalse(_is_gatha_indent(116.0))  # hang upper edge
        self.assertFalse(_is_gatha_indent(187.0))
        # Numbered KN/SN bat bodies sit just below the old 100pt hang floor.
        self.assertTrue(_is_hang_indent(97.2))  # 23Khu06 p.1
        self.assertTrue(_is_hang_indent(103.0))
        self.assertTrue(_is_hang_indent(105.8))
        self.assertFalse(_is_hang_indent(96.0))
        self.assertFalse(_is_hang_indent(84.2))

    def test_normalize_strips_markers(self) -> None:
        self.assertEqual(
            normalize_match_text("vadati{{n0}} viññāpeti"),
            normalize_match_text("vadati viññāpeti"),
        )

    def test_normalize_strips_glued_footnote_digits(self) -> None:
        """PDF 'Videsso1' must match segment 'Videsso{{n0}}' for gāthā geometry."""
        self.assertEqual(
            normalize_match_text("Videsso{{n0}} hoti atiyācanāya."),
            normalize_match_text("Videsso1 hoti atiyācanāya."),
        )
        self.assertEqual(
            normalize_match_text("Videsso{{n0}} hoti atiyācanāya."),
            "Videsso hoti atiyācanāya.",
        )


class CenterLineTests(unittest.TestCase):
    def test_short_centered_label(self) -> None:
        # Measured 01Vin01 p.129: Baddhacakkaṃ. / Idaṃ saṃkhittaṃ.
        line = PageLine(y0=173.0, x0=211.2, x1=291.1, text="Baddhacakkaṃ.")
        self.assertTrue(_is_center_line(line, 499.0))
        line2 = PageLine(y0=228.7, x0=205.9, x1=296.4, text="Idaṃ saṃkhittaṃ.")
        self.assertTrue(_is_center_line(line2, 499.0))

    def test_full_width_first_indent_is_not_center(self) -> None:
        # Evaṃ ekekaṃ… on the same page — first indent, wide line.
        line = PageLine(
            y0=200.8,
            x0=84.2,
            x1=430.3,
            text="Evaṃ ekekaṃ mūlaṃ kātuna baddhacakkaṃ parivattakaṃ kattabbaṃ.",
        )
        self.assertFalse(_is_center_line(line, 499.0))

    def test_tag_center_on_json_segments(self) -> None:
        class _Page:
            rect = type("R", (), {"width": 499.0})()

        class _Doc:
            page_count = 1

            def __getitem__(self, idx: int) -> object:
                return _Page()

        segs = [
            {
                "page": 1,
                "order": 693,
                "item": 210,
                "segment_type": "prose",
                "text": [{"script": "roman", "value": "Baddhacakkaṃ."}],
            },
            {
                "page": 1,
                "order": 694,
                "item": 210,
                "segment_type": "prose",
                "text": [
                    {
                        "script": "roman",
                        "value": (
                            "Evaṃ ekekaṃ mūlaṃ kātuna baddhacakkaṃ "
                            "parivattakaṃ kattabbaṃ."
                        ),
                    }
                ],
            },
        ]

        import cs_roman_hanging as hanging

        lines = [
            PageLine(y0=173.0, x0=211.2, x1=291.1, text="Baddhacakkaṃ."),
            PageLine(
                y0=200.8,
                x0=84.2,
                x1=430.3,
                text=(
                    "Evaṃ ekekaṃ mūlaṃ kātuna baddhacakkaṃ "
                    "parivattakaṃ kattabbaṃ."
                ),
            ),
        ]
        original = hanging.page_body_lines
        hanging.page_body_lines = lambda _page: lines  # type: ignore[assignment]
        try:
            stats = tag_center_layout_by_geometry(
                _Doc(), segs, content_start=1
            )
        finally:
            hanging.page_body_lines = original  # type: ignore[assignment]
        self.assertEqual(stats["tagged_center"], 1)
        self.assertEqual(stats["tagged_center_sandwich"], 0)
        self.assertEqual(segs[0].get("source_layout"), "center")
        self.assertIsNone(segs[1].get("source_layout"))

    def test_short_text_is_sandwich_eligible(self) -> None:
        self.assertTrue(
            _is_short_center_sandwich_text(
                "Evaṃ ekekaṃ mūlaṃ kātuna baddhacakkaṃ "
                "parivattakaṃ kattabbaṃ."
            )
        )
        # Long body between centers must not promote.
        long = (
            "Tīhākārehi -pa-. Sattahākārehi paṭhamañca jhānaṃ "
            "dutiyañca jhānaṃ tatiyañca jhānaṃ catutthañca jhānaṃ "
            "ākāsānañcāyatanañca viññāṇañcāyatanañca "
            "ākiñcaññāyatanañca nevasaññānāsaññāyatanañca "
            "saññāvedayitanirodhañca samāpajjiṃ."
        )
        self.assertFalse(_is_short_center_sandwich_text(long))

    def test_sandwich_promotes_short_middle(self) -> None:
        # 01Vin01 p.129: Baddhacakkaṃ. / Evaṃ… / Idaṃ saṃkhittaṃ.
        segs = [
            {
                "page": 129,
                "order": 693,
                "item": 210,
                "segment_type": "prose",
                "source_layout": "center",
                "text": [{"script": "roman", "value": "Baddhacakkaṃ."}],
            },
            {
                "page": 129,
                "order": 694,
                "item": 210,
                "segment_type": "prose",
                "text": [
                    {
                        "script": "roman",
                        "value": (
                            "Evaṃ ekekaṃ mūlaṃ kātuna baddhacakkaṃ "
                            "parivattakaṃ kattabbaṃ."
                        ),
                    }
                ],
            },
            {
                "page": 129,
                "order": 695,
                "item": 210,
                "segment_type": "prose",
                "source_layout": "center",
                "text": [{"script": "roman", "value": "Idaṃ saṃkhittaṃ."}],
            },
        ]
        stats = tag_center_layout_by_sandwich(segs)
        self.assertEqual(stats["tagged_center_sandwich"], 1)
        self.assertEqual(segs[1].get("source_layout"), "center")

    def test_sandwich_skips_long_middle(self) -> None:
        segs = [
            {
                "page": 132,
                "order": 714,
                "segment_type": "title",
                "source_layout": "center",
                "text": [{"script": "roman", "value": "Idaṃ sabbamūlakaṃ"}],
            },
            {
                "page": 132,
                "order": 715,
                "item": 214,
                "segment_type": "prose",
                "text": [
                    {
                        "script": "roman",
                        "value": (
                            "Tīhākārehi -pa-.{{sp1}} Sattahākārehi "
                            "paṭhamañca jhānaṃ dutiyañca jhānaṃ "
                            "tatiyañca jhānaṃ catutthañca jhānaṃ "
                            "ākāsānañcāyatanañca viññāṇañcāyatanañca "
                            "ākiñcaññāyatanañca "
                            "nevasaññānāsaññāyatanañca "
                            "saññāvedayitanirodhañca samāpajjiṃ."
                        ),
                    }
                ],
            },
            {
                "page": 132,
                "order": 716,
                "segment_type": "niṭṭhitaṃ",
                "source_layout": "center",
                "text": [
                    {"script": "roman", "value": "Sabbamūlakaṃ niṭṭhitaṃ."}
                ],
            },
        ]
        stats = tag_center_layout_by_sandwich(segs)
        self.assertEqual(stats["tagged_center_sandwich"], 0)
        self.assertIsNone(segs[1].get("source_layout"))


class ReclassifyByIndentTests(unittest.TestCase):
    def test_indented_match_is_first_indent(self) -> None:
        lines = [PageLine(y0=90.0, x0=84.2, text="vadati viññāpeti -pa-")]
        matched = _match_cached_line(lines, "vadati viññāpeti -pa-")
        self.assertIsNotNone(matched)
        assert matched is not None
        self.assertTrue(_is_first_indent(matched.x0))

    def test_flush_match_stays_continuation_logic(self) -> None:
        lines = [PageLine(y0=90.0, x0=62.6, text="vadati viññāpeti -pa-")]
        matched = _match_cached_line(lines, "vadati viññāpeti -pa- yadi")
        self.assertIsNotNone(matched)
        assert matched is not None
        self.assertTrue(_is_body_flush(matched.x0))
        self.assertFalse(_is_first_indent(matched.x0))

    def test_json_upgrade_path_detects_flush(self) -> None:
        seg = {
            "page": 30,
            "order": 98,
            "item": 46,
            "segment_type": "prose",
            "text": [
                {"script": "roman", "value": "vadati viññāpeti -pa-"},
                {"script": "thai", "value": "วทติ วิญฺญาเปติ ฯเปฯ"},
            ],
        }
        self.assertTrue(segment_roman_text(seg).startswith("vadati"))
        lines = [PageLine(y0=90.0, x0=62.6, text="vadati viññāpeti -pa-")]
        matched = _match_cached_line(lines, segment_roman_text(seg))
        self.assertIsNotNone(matched)
        assert matched is not None
        self.assertTrue(_is_body_flush(matched.x0))

    def test_match_after_hyphen_repair_leading_token(self) -> None:
        """PDF keeps pariyāyena; segment starts at asubhakathaṃ after repair."""
        lines = [
            PageLine(
                y0=90.0,
                x0=62.6,
                text="pariyāyena asubhakathaṃ katheti, asubhāya vaṇṇaṃ",
            )
        ]
        seg_text = "asubhakathaṃ katheti, asubhāya vaṇṇaṃ bhāsati"
        matched = _match_cached_line(lines, seg_text)
        self.assertIsNotNone(matched)
        assert matched is not None
        self.assertTrue(_is_body_flush(matched.x0))
        self.assertTrue(
            _match_after_leading_tokens(
                normalize_match_text(lines[0].text),
                normalize_match_text(seg_text),
                normalize_match_text(seg_text)[:28],
            )
        )

    def test_midline_pot_ma_gyi_does_not_steal_indent_head(self) -> None:
        """01Vin01 p.36: ``. . Bhikkhu…`` flush must not beat indented head."""
        lines = [
            PageLine(
                y0=126.0,
                x0=62.6,
                text=(
                    "pārājikassa. . Bhikkhupaccatthikā manussitthiṃ "
                    "bhikkhussa santike ānetvā"
                ),
            ),
            PageLine(
                y0=179.0,
                x0=62.6,
                text=(
                    "pārājikassa. . Bhikkhupaccatthikā manussitthiṃ "
                    "bhikkhussa santike ānetvā"
                ),
            ),
            PageLine(
                y0=238.0,
                x0=84.2,
                text="Bhikkhupaccatthikā manussitthiṃ bhikkhussa santike ānetvā",
            ),
        ]
        needle = (
            "Bhikkhupaccatthikā manussitthiṃ bhikkhussa santike ānetvā "
            "passāvamaggena. Mukhena aṅgajātaṃ abhinisīdenti"
        )
        matched = _match_cached_line(lines, needle)
        self.assertIsNotNone(matched)
        assert matched is not None
        self.assertTrue(_is_first_indent(matched.x0))
        self.assertEqual(matched.y0, 238.0)

    def test_shared_prefix_prefers_longest_common(self) -> None:
        """01Vin01 p.157: …khaṇḍacakkaṃ… must not steal …baddhacakkaṃ."""
        lines = [
            PageLine(
                y0=100.0,
                x0=108.06,
                x1=394.3,
                text="Vatthuvisārakassa ekamūlakassa khaṇḍacakkaṃ niṭṭhitaṃ.",
            ),
            PageLine(
                y0=400.0,
                x0=131.46,
                x1=370.84,
                text="Vatthuvisārakassa ekamūlakassa baddhacakkaṃ.",
            ),
            PageLine(
                y0=420.0,
                x0=200.88,
                x1=301.44,
                text="Mūlaṃ saṃkhittaṃ.",
            ),
        ]
        matched = _match_cached_line(
            lines, "Vatthuvisārakassa ekamūlakassa baddhacakkaṃ."
        )
        self.assertIsNotNone(matched)
        assert matched is not None
        self.assertEqual(
            matched.text, "Vatthuvisārakassa ekamūlakassa baddhacakkaṃ."
        )
        self.assertTrue(_is_center_line(matched, 499.0))
        # Sibling closer still resolves to its own (earlier) line.
        closer = _match_cached_line(
            lines,
            "Vatthuvisārakassa ekamūlakassa khaṇḍacakkaṃ niṭṭhitaṃ.",
        )
        self.assertIsNotNone(closer)
        assert closer is not None
        self.assertIn("khaṇḍacakkaṃ", closer.text)

    def test_shared_prefix_center_tag_uses_correct_line(self) -> None:
        """Geometry center must use baddha line, not the earlier khaṇḍa line."""

        class _Page:
            rect = type("R", (), {"width": 499.0})()

        class _Doc:
            page_count = 1

            def __getitem__(self, idx: int) -> object:
                return _Page()

        segs = [
            {
                "page": 1,
                "order": 722,
                "segment_type": "niṭṭhitaṃ",
                "text": [
                    {
                        "script": "roman",
                        "value": (
                            "Vatthuvisārakassa ekamūlakassa "
                            "khaṇḍacakkaṃ niṭṭhitaṃ."
                        ),
                    }
                ],
            },
            {
                "page": 1,
                "order": 726,
                "item": 216,
                "segment_type": "prose",
                "text": [
                    {
                        "script": "roman",
                        "value": (
                            "Vatthuvisārakassa ekamūlakassa baddhacakkaṃ."
                        ),
                    }
                ],
            },
            {
                "page": 1,
                "order": 727,
                "item": 216,
                "segment_type": "prose",
                "text": [{"script": "roman", "value": "Mūlaṃ saṃkhittaṃ."}],
            },
        ]
        lines = [
            PageLine(
                y0=100.0,
                x0=108.06,
                x1=394.3,
                text=(
                    "Vatthuvisārakassa ekamūlakassa "
                    "khaṇḍacakkaṃ niṭṭhitaṃ."
                ),
            ),
            PageLine(
                y0=400.0,
                x0=131.46,
                x1=370.84,
                text="Vatthuvisārakassa ekamūlakassa baddhacakkaṃ.",
            ),
            PageLine(
                y0=420.0,
                x0=200.88,
                x1=301.44,
                text="Mūlaṃ saṃkhittaṃ.",
            ),
        ]
        import cs_roman_hanging as hanging

        original = hanging.page_body_lines
        hanging.page_body_lines = lambda _page: lines  # type: ignore[assignment]
        try:
            stats = tag_center_layout_by_geometry(
                _Doc(), segs, content_start=1
            )
        finally:
            hanging.page_body_lines = original  # type: ignore[assignment]
        self.assertGreaterEqual(stats["tagged_center"], 2)
        self.assertEqual(segs[1].get("source_layout"), "center")
        self.assertEqual(segs[2].get("source_layout"), "center")


if __name__ == "__main__":
    unittest.main()
