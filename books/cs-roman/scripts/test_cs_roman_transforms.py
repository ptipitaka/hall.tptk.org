"""Unit tests for cs-roman publication transform rules."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from paths import BOOKS, ensure_import_paths

ensure_import_paths()

from cs_roman_segments import DEFAULT_LAYOUT, save_document  # noqa: E402
from cs_roman_text import roman_to_thai  # noqa: E402
from cs_roman_transforms import (  # noqa: E402
    apply_transforms,
    load_transforms_file,
    load_volume_transforms,
    parse_transforms_document,
)
from generate_cs_roman_tex import build_body, generate  # noqa: E402
from sync_volume_data import sync_transforms_file  # noqa: E402


def _rule(
    rule_id: str = "fix",
    *,
    pattern: str = "Bhagavaa",
    replacement: str = "Bhagavā",
    pages: list[int] | None = None,
    orders: list[int] | None = None,
    segment_types: list[str] | None = None,
    match: str | None = None,
    enabled: bool = True,
    flags: str = "",
) -> dict:
    when: dict = {}
    if pages is not None:
        when["pages"] = pages
    if orders is not None:
        when["orders"] = orders
    if segment_types is not None:
        when["segment_types"] = segment_types
    if match is not None:
        when["match"] = match
    return {
        "id": rule_id,
        "enabled": enabled,
        "when": when,
        "do": {"replace": {"pattern": pattern, "with": replacement, "flags": flags}},
    }


class ParseTransformsTests(unittest.TestCase):
    def test_parses_ordered_rules(self) -> None:
        rules = parse_transforms_document(
            {
                "schema_version": 1,
                "rules": [
                    _rule("a", pattern="aa", replacement="a"),
                    _rule("b", pattern="bb", replacement="b"),
                ],
            },
            source="mem",
        )
        self.assertEqual([r.id for r in rules], ["a", "b"])

    def test_rejects_duplicate_ids(self) -> None:
        with self.assertRaises(ValueError):
            parse_transforms_document(
                {
                    "schema_version": 1,
                    "rules": [_rule("same"), _rule("same")],
                },
                source="mem",
            )

    def test_missing_file_is_empty(self) -> None:
        self.assertEqual(
            load_transforms_file(Path("/no/such/transforms.json")),
            [],
        )


class ApplyTransformsTests(unittest.TestCase):
    def test_page_filter_and_replace(self) -> None:
        rules = parse_transforms_document(
            {
                "schema_version": 1,
                "rules": [_rule(pages=[12], orders=[3])],
            },
            source="mem",
        )
        self.assertEqual(
            apply_transforms(
                "Bhagavaa āha",
                rules,
                page=12,
                order=3,
                segment_type="prose",
            ),
            "Bhagavā āha",
        )
        self.assertEqual(
            apply_transforms(
                "Bhagavaa āha",
                rules,
                page=11,
                order=3,
                segment_type="prose",
            ),
            "Bhagavaa āha",
        )

    def test_disabled_rule_skipped(self) -> None:
        rules = parse_transforms_document(
            {"schema_version": 1, "rules": [_rule(enabled=False)]},
            source="mem",
        )
        self.assertEqual(
            apply_transforms(
                "Bhagavaa",
                rules,
                page=1,
                order=1,
                segment_type="prose",
            ),
            "Bhagavaa",
        )

    def test_shared_then_volume_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shared = root / "shared.json"
            volume = root / "volume.json"
            shared.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "rules": [
                            _rule("s1", pattern="AA", replacement="BB"),
                        ],
                    }
                ),
                encoding="utf-8",
            )
            volume.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "rules": [
                            _rule("v1", pattern="BB", replacement="CC"),
                        ],
                    }
                ),
                encoding="utf-8",
            )
            rules = load_volume_transforms(
                "x",
                shared_path=shared,
                volume_path=volume,
            )
            self.assertEqual(
                apply_transforms(
                    "AA",
                    rules,
                    page=1,
                    order=1,
                    segment_type="prose",
                ),
                "CC",
            )


class GenerateWithTransformsTests(unittest.TestCase):
    def test_build_body_rederives_thai_when_roman_changes(self) -> None:
        rules = parse_transforms_document(
            {"schema_version": 1, "rules": [_rule()]},
            source="mem",
        )
        seg = {
            "page": 12,
            "order": 3,
            "segment_type": "prose",
            "text": [
                {"script": "roman", "value": "Bhagavaa āha."},
                {"script": "thai", "value": "WRONG"},
            ],
        }
        body, _ = build_body(seg, rules)
        expected = roman_to_thai("Bhagavā āha.")
        self.assertIn(expected, body)
        self.assertNotIn("WRONG", body)

    def test_generate_applies_volume_transforms(self) -> None:
        volume_id = "_transforms_test_vol"
        vol = BOOKS / "volumes" / volume_id
        data = vol / "data"
        data.mkdir(parents=True, exist_ok=True)
        out_path = vol / "tex" / "body.generated.tex"
        try:
            save_document(
                data / "segments.json",
                {
                    "schema_version": 1,
                    "source": "books/cs-roman/source/01Vin01.pdf",
                    "content_start_pdf_page": 24,
                    "layout": dict(DEFAULT_LAYOUT),
                    "segments": [
                        {
                            "page": 1,
                            "order": 1,
                            "segment_type": "prose",
                            "item": 1,
                            "text": [
                                {
                                    "script": "roman",
                                    "value": "Bhagavaa āha.",
                                },
                                {
                                    "script": "thai",
                                    "value": "ภควาอาห.",
                                },
                            ],
                        }
                    ],
                },
            )
            (data / "transforms.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "rules": [_rule(pages=[1], orders=[1])],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            path = generate(volume_id)
            tex = path.read_text(encoding="utf-8")
            self.assertIn("% transform_rules: 1", tex)
            self.assertIn(roman_to_thai("Bhagavā āha."), tex)
        finally:
            if out_path.is_file():
                out_path.unlink()
            for name in ("segments.json", "layout.json", "transforms.json"):
                p = data / name
                if p.is_file():
                    p.unlink()


class SyncTransformsTests(unittest.TestCase):
    def test_sync_copies_and_removes_stale_transforms(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "out.transforms.json"
            dst = root / "data" / "transforms.json"
            dst.parent.mkdir(parents=True)
            src.write_text(
                json.dumps({"schema_version": 1, "rules": [_rule("sync-demo")]}),
                encoding="utf-8",
            )
            sync_transforms_file(src, dst)
            self.assertTrue(dst.is_file())
            self.assertIn("sync-demo", dst.read_text(encoding="utf-8"))

            src.unlink()
            sync_transforms_file(src, dst)
            self.assertFalse(dst.is_file())


if __name__ == "__main__":
    unittest.main()
