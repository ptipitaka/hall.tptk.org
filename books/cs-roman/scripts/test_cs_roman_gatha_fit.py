#!/usr/bin/env python3
"""Tests for gāthā group width fit → stack overflowing bat pairs."""

from __future__ import annotations

import unittest
from pathlib import Path

from paths import ensure_import_paths

ensure_import_paths()

from cs_roman_gatha_fit import (  # noqa: E402
    GathaBatFitCandidate,
    gatha_fit_string_width_pt,
    gatha_fit_textwidth_pt,
    resolve_gatha_bat_stack_keys,
)
from generate_cs_roman_tex import (  # noqa: E402
    DEFAULT_LAYOUT,
    gatha_bat_tex,
    gatha_group_measure_payloads,
    generate_reading_lines,
    measure_gatha_group_stack_keys,
)

try:
    import fitz
except ImportError:  # pragma: no cover
    fitz = None  # type: ignore


def _wak(thai: str) -> dict:
    return {"text": [{"script": "thai", "value": thai}]}


def _bat(left: str, right: str) -> dict:
    return {"waks": [_wak(left), _wak(right)]}


@unittest.skipUnless(fitz is not None, "pymupdf required")
class GathaFitMeasureTests(unittest.TestCase):
    def test_abhikkama_pair_stacks_in_printing(self) -> None:
        """04Vin04 p.303: long Abhikkama bat overflows; short neighbours stay paired."""
        cands = [
            GathaBatFitCandidate(
                0, 0, "“สตํ หตฺถี สตํ อสฺสา,", "สตํ อสฺสตรีรถา."
            ),
            GathaBatFitCandidate(
                0, 1, "สตํ กญฺญาสหสฺสานิ,", "อามุกฺกมณิกุณฺฑลา."
            ),
            GathaBatFitCandidate(
                1, 0, "เอกสฺส ปทวีติหารสฺส,", "กลํ นาคฺฆนฺติ โสฬสิํ1."
            ),
            GathaBatFitCandidate(
                1,
                1,
                "อภิกฺกม คหปติ อภิกฺกม คหปติ,",
                "อภิกฺกนฺตํ เต เสยฺโย โน ปฏิกฺกนฺตนฺ”ติ.",
            ),
        ]
        stacked = resolve_gatha_bat_stack_keys(
            cands, mode="printing", word_space=3.5
        )
        self.assertEqual(stacked, frozenset({(1, 1)}))
        tw = gatha_fit_textwidth_pt("printing")
        # Sanity: stacked pair alone exceeds the block with shared leftcol.
        leftcol = max(
            gatha_fit_string_width_pt(c.left, fontsize=11 * 1.031038, word_space=3.5)
            for c in cands
        )
        long = cands[3]
        pair_w = (
            leftcol
            + 20.0
            + gatha_fit_string_width_pt(
                long.right, fontsize=11 * 1.031038, word_space=3.5
            )
        )
        self.assertGreater(pair_w, tw - 2.0)

    def test_generate_stacks_overflow_bat_as_single_lines(self) -> None:
        segs = [
            {
                "page": 303,
                "order": 1,
                "segment_type": "gatha",
                "source_layout": "bat_line",
                "bats": [
                    _bat("“สตํ หตฺถี สตํ อสฺสา,", "สตํ อสฺสตรีรถา."),
                    _bat("สตํ กญฺญาสหสฺสานิ,", "อามุกฺกมณิกุณฺฑลา."),
                ],
            },
            {
                "page": 303,
                "order": 2,
                "segment_type": "gatha",
                "source_layout": "bat_line",
                "bats": [
                    _bat("เอกสฺส ปทวีติหารสฺส,", "กลํ นาคฺฆนฺติ โสฬสิํ."),
                    _bat(
                        "อภิกฺกม คหปติ อภิกฺกม คหปติ,",
                        "อภิกฺกนฺตํ เต เสยฺโย โน ปฏิกฺกนฺตนฺ”ติ.",
                    ),
                ],
            },
        ]
        keys = measure_gatha_group_stack_keys(
            segs, 0, 2, mode="printing", word_space=3.5
        )
        self.assertIn((1, 1), keys)
        lefts, measure, _ = gatha_group_measure_payloads(
            segs, 0, 2, [], stack_keys=keys
        )
        # Stacked บาท left is not part of the shared column.
        self.assertNotIn("อภิกฺกม คหปติ อภิกฺกม คหปติ,", lefts)
        self.assertIn("“สตํ หตฺถี สตํ อสฺสา,", lefts)
        # Measure emits two plain lines for the overflow บาท (no bat macro).
        joined = " \\ ".join(measure)
        self.assertIn("อภิกฺกม คหปติ อภิกฺกม คหปติ,", joined)
        self.assertIn("อภิกฺกนฺตํ เต เสยฺโย โน ปฏิกฺกนฺตนฺ”ติ.", joined)
        self.assertNotIn(
            gatha_bat_tex(
                "อภิกฺกม คหปติ อภิกฺกม คหปติ,",
                "อภิกฺกนฺตํ เต เสยฺโย โน ปฏิกฺกนฺตนฺ”ติ.",
            ),
            joined,
        )
        # Short pairs remain bat macros.
        self.assertIn(
            gatha_bat_tex("“สตํ หตฺถี สตํ อสฺสา,", "สตํ อสฺสตรีรถา."),
            joined,
        )

        doc = {"schema_version": 1, "segments": segs, "layout": DEFAULT_LAYOUT}
        tex = "\n".join(
            generate_reading_lines(
                doc, [], "04Vin04", segs, DEFAULT_LAYOUT, mode="printing"
            )[0]
        )
        self.assertIn(
            gatha_bat_tex("“สตํ หตฺถี สตํ อสฺสา,", "สตํ อสฺสตรีรถา."),
            tex,
        )
        self.assertNotIn(
            gatha_bat_tex(
                "อภิกฺกม คหปติ อภิกฺกม คหปติ,",
                "อภิกฺกนฺตํ เต เสยฺโย โน ปฏิกฺกนฺตนฺ”ติ.",
            ),
            tex,
        )
        # Stacked lines appear as separate \\-joined stanza lines.
        self.assertIn(
            r"อภิกฺกม คหปติ อภิกฺกม คหปติ, \\ อภิกฺกนฺตํ เต เสยฺโย โน ปฏิกฺกนฺตนฺ”ติ.",
            tex,
        )


if __name__ == "__main__":
    unittest.main()
