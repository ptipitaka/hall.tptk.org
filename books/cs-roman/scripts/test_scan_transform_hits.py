"""Tests for scan_transform_hits helpers (no full corpus walk)."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from cs_roman_transforms import parse_transforms_document  # noqa: E402
from scan_transform_hits import (  # noqa: E402
    collect_hits,
    hits_in_segment,
    iter_roman_blobs,
    snippet_around,
)


def _rules(raw: dict) -> list:
    return parse_transforms_document(raw, source="test")


def _replace_rule(match: str, *, loci: list[dict] | None = None) -> dict:
    when: dict = {"match": match}
    if loci:
        when["loci"] = loci
    return {
        "id": "r1",
        "when": when,
        "do": {"replace": {"with": "X", "remark": "test"}},
    }


class ScanTransformHitsTests(unittest.TestCase):
    def test_iter_roman_blobs_reads_gatha_wak(self) -> None:
        seg = {
            "segment_type": "gatha",
            "bats": [
                {
                    "waks": [
                        {
                            "text": [
                                {"script": "roman", "value": "dighamaddhānaṃ"},
                                {"script": "thai", "value": "ทีฆมทฺธานํ"},
                            ]
                        }
                    ]
                }
            ],
        }
        self.assertEqual(list(iter_roman_blobs(seg)), ["dighamaddhānaṃ"])

    def test_iter_roman_blobs_skips_edition_notes(self) -> None:
        seg = {
            "segment_type": "prose",
            "text": [{"script": "roman", "value": "paggāhikasālaṃ{{n0}}"}],
            "notes": ["Paṭaggāhikasālaṃ (?)"],
            "symbol_notes": {"*": "Ito paraṃ yāva"},
        }
        self.assertEqual(list(iter_roman_blobs(seg)), ["paggāhikasālaṃ{{n0}}"])

    def test_token_match_skips_longer_word(self) -> None:
        rules = _rules({"schema_version": 2, "rules": [_replace_rule("bandhiṃ")]})
        seg = {
            "page": 1,
            "order": 2,
            "segment_type": "prose",
            "text": [
                {"script": "roman", "value": "anubandhiṃsu bandhiṃ yeva"},
            ],
        }
        hits = list(
            hits_in_segment(
                seg,
                volume_id="01Vin01",
                needle="bandhiṃ",
                substring=False,
                rules=rules,
            )
        )
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].matched, "bandhiṃ")
        self.assertEqual(hits[0].applying, ("r1",))

    def test_plus_match_hits_affixed_core(self) -> None:
        rules = _rules(
            {"schema_version": 2, "rules": [_replace_rule("+bandhiṃ")]}
        )
        seg = {
            "page": 1,
            "order": 2,
            "segment_type": "prose",
            "text": [
                {"script": "roman", "value": "anubandhiṃsu anubandhiṃ bandhiṃ"},
            ],
        }
        hits = list(
            hits_in_segment(
                seg,
                volume_id="01Vin01",
                needle="+bandhiṃ",
                substring=False,
                rules=rules,
            )
        )
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].matched, "bandhiṃ")
        self.assertEqual(hits[0].applying, ("r1",))

    def test_volume_filter_counts_as_not_applied(self) -> None:
        rules = _rules(
            {
                "schema_version": 2,
                "rules": [_replace_rule("kukuccaṃ", loci=[{"volume": "02Vin02"}])],
            }
        )
        seg = {
            "page": 8,
            "order": 10,
            "segment_type": "prose",
            "text": [{"script": "roman", "value": "tassa kukuccaṃ uppajjati"}],
        }
        hits = list(
            hits_in_segment(
                seg,
                volume_id="01Vin01",
                needle="kukuccaṃ",
                substring=False,
                rules=rules,
            )
        )
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].applying, ())

    def test_snippet_around_marks_edges(self) -> None:
        text = "aaa dighamaddhānaṃ bbb"
        start = text.index("dighamaddhānaṃ")
        self.assertIn("dighamaddhānaṃ", snippet_around(text, start, 14, radius=4))

    def test_collect_hits_reads_temp_volume(self) -> None:
        rules = _rules(
            {"schema_version": 2, "rules": [_replace_rule("dighamaddhānaṃ")]}
        )
        with tempfile.TemporaryDirectory() as tmp:
            vol = Path(tmp) / "01Vin01" / "data"
            vol.mkdir(parents=True)
            (vol / "segments.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "segments": [
                            {
                                "page": 10,
                                "order": 34,
                                "segment_type": "prose",
                                "text": [
                                    {
                                        "script": "roman",
                                        "value": "ciraṃ dighamaddhānaṃ ṭhapesuṃ",
                                    }
                                ],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            with mock.patch("scan_transform_hits.VOLUMES_DIR", Path(tmp)):
                hits = collect_hits(
                    needle="dighamaddhānaṃ",
                    substring=False,
                    rules=rules,
                    volume="01Vin01",
                )
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].page, 10)
        self.assertEqual(hits[0].applying, ("r1",))


if __name__ == "__main__":
    unittest.main()
