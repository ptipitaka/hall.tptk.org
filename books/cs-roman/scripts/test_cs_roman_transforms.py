"""Unit tests for cs-roman publication transform rules (schema_version 2)."""

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
    collect_transform_soft_breaks,
    load_transforms_file,
    load_volume_transforms,
    parse_transforms_document,
)
from generate_cs_roman_tex import build_body, generate, note_to_thai  # noqa: E402
from sync_volume_data import sync_transforms_file  # noqa: E402


def _replace_rule(
    rule_id: str = "fix",
    *,
    match: str = "Bhagavaa",
    replacement: str = "Bhagavā",
    pages: list[int] | None = None,
    orders: list[int] | None = None,
    segment_types: list[str] | None = None,
    enabled: bool = True,
    remark: str | None = None,
    soft_breaks: list[str] | None = None,
) -> dict:
    when: dict = {"match": match}
    if pages is not None:
        when["pages"] = pages
    if orders is not None:
        when["orders"] = orders
    if segment_types is not None:
        when["segment_types"] = segment_types
    repl: dict = {"with": replacement}
    if remark is not None:
        repl["remark"] = remark
    if soft_breaks is not None:
        repl["soft_breaks"] = soft_breaks
    return {
        "id": rule_id,
        "enabled": enabled,
        "when": when,
        "do": {"replace": repl},
    }


def _annotate_rule(
    rule_id: str = "note",
    *,
    match: str = "cīra",
    footnote: str = "note body",
    pages: list[int] | None = None,
    orders: list[int] | None = None,
    segment_types: list[str] | None = None,
    enabled: bool = True,
    soft_breaks: list[str] | None = None,
) -> dict:
    when: dict = {"match": match}
    if pages is not None:
        when["pages"] = pages
    if orders is not None:
        when["orders"] = orders
    if segment_types is not None:
        when["segment_types"] = segment_types
    ann: dict = {"footnote": footnote}
    if soft_breaks is not None:
        ann["soft_breaks"] = soft_breaks
    return {
        "id": rule_id,
        "enabled": enabled,
        "when": when,
        "do": {"annotate": ann},
    }


class ParseTransformsTests(unittest.TestCase):
    def test_parses_ordered_rules(self) -> None:
        rules = parse_transforms_document(
            {
                "schema_version": 2,
                "rules": [
                    _replace_rule("a", match="aa", replacement="a"),
                    _replace_rule("b", match="bb", replacement="b"),
                ],
            },
            source="mem",
        )
        self.assertEqual([r.id for r in rules], ["a", "b"])
        self.assertEqual(rules[0].action, "replace")

    def test_rejects_duplicate_ids(self) -> None:
        with self.assertRaises(ValueError):
            parse_transforms_document(
                {
                    "schema_version": 2,
                    "rules": [_replace_rule("same"), _replace_rule("same")],
                },
                source="mem",
            )

    def test_rejects_schema_version_1(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            parse_transforms_document(
                {"schema_version": 1, "rules": []},
                source="mem",
            )
        self.assertIn("schema_version", str(ctx.exception))

    def test_rejects_both_actions(self) -> None:
        with self.assertRaises(ValueError):
            parse_transforms_document(
                {
                    "schema_version": 2,
                    "rules": [
                        {
                            "id": "both",
                            "when": {"match": "foo"},
                            "do": {
                                "annotate": {"footnote": "n"},
                                "replace": {"with": "bar"},
                            },
                        }
                    ],
                },
                source="mem",
            )

    def test_rejects_soft_breaks_that_do_not_concat(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            parse_transforms_document(
                {
                    "schema_version": 2,
                    "rules": [
                        _annotate_rule(
                            match="abcdef",
                            soft_breaks=["ab", "XX"],
                        )
                    ],
                },
                source="mem",
            )
        self.assertIn("concatenate", str(ctx.exception))

    def test_missing_file_is_empty(self) -> None:
        self.assertEqual(
            load_transforms_file(Path("/no/such/transforms.json")),
            [],
        )

    def test_parses_annotate_and_replace(self) -> None:
        rules = parse_transforms_document(
            {
                "schema_version": 2,
                "rules": [
                    _annotate_rule(
                        "fn",
                        match="cīrapiṇḍ",
                        footnote="cīra pāṭho, cīvara",
                    ),
                    _replace_rule(
                        "fix",
                        match="Bhagavaa",
                        replacement="Bhagavā",
                        remark="editor only",
                    ),
                ],
            },
            source="mem",
        )
        self.assertEqual(rules[0].action, "annotate")
        self.assertEqual(rules[0].footnote, "cīra pāṭho, cīvara")
        self.assertEqual(rules[1].action, "replace")
        self.assertEqual(rules[1].remark, "editor only")


class SoftBreaksCollectTests(unittest.TestCase):
    def test_collect_keys_by_action_surface(self) -> None:
        word = "cīrapiṇḍapāta"
        fixed = "cīvarapiṇḍapāta"
        rules = parse_transforms_document(
            {
                "schema_version": 2,
                "rules": [
                    _annotate_rule(
                        "a",
                        match=word,
                        soft_breaks=["cīra", "piṇḍapāta"],
                    ),
                    _replace_rule(
                        "b",
                        match=word,
                        replacement=fixed,
                        soft_breaks=["cīvara", "piṇḍapāta"],
                    ),
                ],
            },
            source="mem",
        )
        collected = collect_transform_soft_breaks(rules)
        self.assertEqual(collected[word], ["cīra", "piṇḍapāta"])
        self.assertEqual(collected[fixed], ["cīvara", "piṇḍapāta"])


class ApplyTransformsTests(unittest.TestCase):
    def test_page_filter_and_replace(self) -> None:
        rules = parse_transforms_document(
            {
                "schema_version": 2,
                "rules": [_replace_rule(pages=[12], orders=[3])],
            },
            source="mem",
        )
        text, extra = apply_transforms(
            "Bhagavaa āha",
            rules,
            page=12,
            order=3,
            segment_type="prose",
        )
        self.assertEqual(text, "Bhagavā āha")
        self.assertEqual(extra, [])
        text2, extra2 = apply_transforms(
            "Bhagavaa āha",
            rules,
            page=11,
            order=3,
            segment_type="prose",
        )
        self.assertEqual(text2, "Bhagavaa āha")
        self.assertEqual(extra2, [])

    def test_disabled_rule_skipped(self) -> None:
        rules = parse_transforms_document(
            {"schema_version": 2, "rules": [_replace_rule(enabled=False)]},
            source="mem",
        )
        text, extra = apply_transforms(
            "Bhagavaa",
            rules,
            page=1,
            order=1,
            segment_type="prose",
        )
        self.assertEqual(text, "Bhagavaa")
        self.assertEqual(extra, [])

    def test_shared_then_volume_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shared = root / "shared.json"
            volume = root / "volume.json"
            shared.write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "rules": [
                            _replace_rule("s1", match="AA", replacement="BB"),
                        ],
                    }
                ),
                encoding="utf-8",
            )
            volume.write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "rules": [
                            _replace_rule("v1", match="BB", replacement="CC"),
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
            text, extra = apply_transforms(
                "AA",
                rules,
                page=1,
                order=1,
                segment_type="prose",
            )
            self.assertEqual(text, "CC")
            self.assertEqual(extra, [])

    def test_annotate_keeps_word_and_injects_footnote(self) -> None:
        word = "cīrapiṇḍapātasenāsanagilānappaccayabhesajjaparikkhārā"
        rules = parse_transforms_document(
            {
                "schema_version": 2,
                "rules": [
                    _annotate_rule(
                        "cira",
                        match=word,
                        footnote="cīra- pāṭho, cīvara-",
                        pages=[280],
                        orders=[1854],
                    )
                ],
            },
            source="mem",
        )
        src = f"tattha paṭibaddhā {word}."
        text, extra = apply_transforms(
            src,
            rules,
            page=280,
            order=1854,
            segment_type="prose",
            note_base_index=2,
        )
        self.assertIn(f"{word}{{{{n2}}}}", text)
        self.assertIn("cīrapiṇḍ", text)
        self.assertEqual(extra, ["cīra- pāṭho, cīvara-"])

    def test_replace_has_no_footnote(self) -> None:
        rules = parse_transforms_document(
            {
                "schema_version": 2,
                "rules": [
                    _replace_rule(
                        "x",
                        match="foo",
                        replacement="bar",
                        remark="should not appear in PDF",
                    )
                ],
            },
            source="mem",
        )
        text, extra = apply_transforms(
            "foo",
            rules,
            page=1,
            order=1,
            segment_type="prose",
            note_base_index=0,
        )
        self.assertEqual(text, "bar")
        self.assertEqual(extra, [])

    def test_emit_footnotes_false_skips_annotate(self) -> None:
        rules = parse_transforms_document(
            {
                "schema_version": 2,
                "rules": [
                    _annotate_rule(
                        "x",
                        match="foo",
                        footnote="should not inject",
                    )
                ],
            },
            source="mem",
        )
        text, extra = apply_transforms(
            "foo",
            rules,
            page=1,
            order=1,
            segment_type="prose",
            emit_footnotes=False,
        )
        self.assertEqual(text, "foo")
        self.assertEqual(extra, [])


class GenerateWithTransformsTests(unittest.TestCase):
    def test_build_body_rederives_thai_when_roman_changes(self) -> None:
        rules = parse_transforms_document(
            {"schema_version": 2, "rules": [_replace_rule()]},
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

    def test_build_body_annotate_keeps_edition_and_footnote(self) -> None:
        word = "cīrapiṇḍapātasenāsanagilānappaccayabhesajjaparikkhārā"
        rules = parse_transforms_document(
            {
                "schema_version": 2,
                "rules": [
                    _annotate_rule(
                        "cira",
                        match=word,
                        footnote="cīra- pāṭho, cīvara-",
                        pages=[280],
                        orders=[1854],
                        soft_breaks=[
                            "cīra",
                            "piṇḍapāta",
                            "senāsana",
                            "gilānappaccaya",
                            "bhesajja",
                            "parikkhārā",
                        ],
                    )
                ],
            },
            source="mem",
        )
        seg = {
            "page": 280,
            "order": 1854,
            "segment_type": "prose",
            "notes": ["existing note"],
            "text": [
                {
                    "script": "roman",
                    "value": (
                        "Upanissāya{{n0}} viharatīti tattha paṭibaddhā "
                        f"{word}."
                    ),
                },
                {
                    "script": "thai",
                    "value": "WRONG",
                },
            ],
        }
        body, _ = build_body(seg, rules)
        self.assertNotIn("WRONG", body)
        thai_word = roman_to_thai(word)
        # Soft breaks inject \-; compare without them.
        self.assertIn(thai_word, body.replace(r"\-", ""))
        self.assertIn(r"\footnote{" + note_to_thai("existing note") + "}", body)
        self.assertIn(r"\footnote{" + note_to_thai("cīra- pāṭho, cīvara-") + "}", body)
        # Soft breaks from the annotate rule should appear (edition form not in DPD).
        self.assertIn(r"\-", body)

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
                        "schema_version": 2,
                        "rules": [_replace_rule(pages=[1], orders=[1])],
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
                json.dumps(
                    {
                        "schema_version": 2,
                        "rules": [_replace_rule("sync-demo")],
                    }
                ),
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
