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
    merge_hanging_into_segments,
    normalize_match_text,
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


if __name__ == "__main__":
    unittest.main()
