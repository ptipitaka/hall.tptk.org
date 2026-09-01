"""Tests for printed Tipiṭaka item-number corrections."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from cs_roman_item_corrections import (  # noqa: E402
    ItemCorrectionLocus,
    ItemCorrectionRule,
    SHARED_ITEM_CORRECTIONS_PATH,
    apply_item_corrections,
    load_item_corrections_file,
    volume_id_from_segments_path,
)
from paths import VOLUMES_DIR  # noqa: E402


def _rule(
    *,
    from_item: int = 238,
    to_item: int = 283,
    page: int = 186,
    order: int | None = None,
    volume: str = "01Vin01",
) -> ItemCorrectionRule:
    return ItemCorrectionRule(
        id="test-238-to-283",
        enabled=True,
        from_item=from_item,
        to_item=to_item,
        loci=(ItemCorrectionLocus(volume=volume, page=page, order=order),),
    )


class VolumeIdFromPathTests(unittest.TestCase):
    def test_output_stem(self) -> None:
        self.assertEqual(
            volume_id_from_segments_path(Path("output/01Vin01.segments.json")),
            "01Vin01",
        )

    def test_git_copy(self) -> None:
        self.assertEqual(
            volume_id_from_segments_path(
                Path("volumes/01Vin01/data/segments.json")
            ),
            "01Vin01",
        )


class ApplyItemCorrectionsTests(unittest.TestCase):
    def test_remaps_locus_and_following_same_item(self) -> None:
        segments = [
            {"page": 154, "order": 851, "segment_type": "prose", "item": 238},
            {"page": 186, "order": 1198, "segment_type": "title"},
            {
                "page": 186,
                "order": 1199,
                "segment_type": "prose",
                "item": 238,
            },
            {
                "page": 187,
                "order": 1200,
                "segment_type": "prose_continuation",
                "item": 238,
            },
            {"page": 187, "order": 1201, "segment_type": "prose", "item": 284},
        ]
        n = apply_item_corrections(segments, "01Vin01", rules=[_rule()])
        self.assertEqual(n, 2)
        self.assertEqual(segments[0]["item"], 238)
        self.assertEqual(segments[2]["item"], 283)
        self.assertEqual(segments[3]["item"], 283)
        self.assertEqual(segments[4]["item"], 284)

    def test_idempotent_after_remap(self) -> None:
        segments = [
            {"page": 186, "order": 1199, "segment_type": "prose", "item": 283},
        ]
        n = apply_item_corrections(segments, "01Vin01", rules=[_rule()])
        self.assertEqual(n, 0)
        self.assertEqual(segments[0]["item"], 283)

    def test_other_volume_untouched(self) -> None:
        segments = [
            {"page": 186, "order": 1199, "segment_type": "prose", "item": 238},
        ]
        n = apply_item_corrections(segments, "02Vin02", rules=[_rule()])
        self.assertEqual(n, 0)
        self.assertEqual(segments[0]["item"], 238)


class SharedCatalogTests(unittest.TestCase):
    def test_loads_and_pins_01vin01_dutthulla(self) -> None:
        rules = load_item_corrections_file(SHARED_ITEM_CORRECTIONS_PATH)
        self.assertTrue(rules)
        ids = [r.id for r in rules]
        self.assertIn("01vin01-page186-item-238-to-283", ids)
        rule = next(r for r in rules if r.id == "01vin01-page186-item-238-to-283")
        self.assertEqual(rule.from_item, 238)
        self.assertEqual(rule.to_item, 283)
        self.assertEqual(rule.loci[0].volume, "01Vin01")
        self.assertEqual(rule.loci[0].page, 186)

    def test_01vin01_opening_becomes_283_real_238_kept(self) -> None:
        path = VOLUMES_DIR / "01Vin01" / "data" / "segments.json"
        if not path.is_file():
            self.skipTest("01Vin01 segments.json missing")
        doc = json.loads(path.read_text(encoding="utf-8"))
        segments = list(doc.get("segments") or [])
        apply_item_corrections(segments, "01Vin01")
        opening = [
            s
            for s in segments
            if s.get("page") == 186
            and s.get("segment_type") == "prose"
            and "Tena samayena Buddho Bhagavā Sāvatthiyaṃ"
            in str((s.get("text") or [{}])[0].get("value") or "")
        ]
        self.assertEqual(len(opening), 1)
        self.assertEqual(opening[0]["item"], 283)
        cont = [
            s
            for s in segments
            if s.get("page") == 187
            and s.get("segment_type") == "prose_continuation"
            and str(s.get("item")) in {"238", "283"}
        ]
        self.assertTrue(cont)
        self.assertTrue(all(s.get("item") == 283 for s in cont))
        real = [
            s
            for s in segments
            if s.get("page") == 154
            and s.get("item") == 238
            and "Ajjhattarūpe" in str((s.get("text") or [{}])[0].get("value") or "")
        ]
        self.assertTrue(real)


if __name__ == "__main__":
    unittest.main()
