"""Unit tests for cs-roman publication transform rules (schema_version 2)."""

from __future__ import annotations

import json
import tempfile
import time
import unittest
from pathlib import Path

from paths import BOOKS, ensure_import_paths

ensure_import_paths()

from cs_roman_segments import DEFAULT_LAYOUT, save_document  # noqa: E402
from cs_roman_text import roman_to_thai  # noqa: E402
from cs_roman_transforms import (  # noqa: E402
    SHARED_TRANSFORMS_PATH,
    _apply_transforms_linear,
    apply_transforms,
    apply_unbold_to_runs,
    collect_transform_soft_breaks,
    compile_transforms,
    load_shared_transforms,
    load_transforms_file,
    parse_match_pattern,
    parse_transforms_document,
    select_rules_for_volume,
)
from generate_cs_roman_tex import build_body, generate, note_to_thai, tex_numbered_footnote  # noqa: E402


def _replace_rule(
    rule_id: str = "fix",
    *,
    match: str = "Bhagavaa",
    replacement: str = "Bhagavā",
    loci: list[dict] | None = None,
    segment_types: list[str] | None = None,
    enabled: bool = True,
    remark: str | None = None,
    soft_breaks: list[str] | None = None,
) -> dict:
    when: dict = {"match": match}
    if loci is not None:
        when["loci"] = loci
    if segment_types is not None:
        when["segment_types"] = segment_types
    repl: dict = {"with": replacement}
    if remark is not None:
        repl["remark"] = remark
    if soft_breaks is not None:
        repl["soft_breaks"] = soft_breaks
    rule: dict = {
        "id": rule_id,
        "when": when,
        "do": {"replace": repl},
    }
    if not enabled:
        rule["enabled"] = False
    return rule


def _annotate_rule(
    rule_id: str = "note",
    *,
    match: str = "cīra",
    footnote: str = "note body",
    loci: list[dict] | None = None,
    segment_types: list[str] | None = None,
    enabled: bool = True,
    soft_breaks: list[str] | None = None,
) -> dict:
    when: dict = {"match": match}
    if loci is not None:
        when["loci"] = loci
    if segment_types is not None:
        when["segment_types"] = segment_types
    ann: dict = {"footnote": footnote}
    if soft_breaks is not None:
        ann["soft_breaks"] = soft_breaks
    rule: dict = {
        "id": rule_id,
        "when": when,
        "do": {"annotate": ann},
    }
    if not enabled:
        rule["enabled"] = False
    return rule


def _unbold_rule(
    rule_id: str = "unbold",
    *,
    match: str = "”ti",
    skip: int = 1,
    remark: str | None = None,
    enabled: bool = True,
) -> dict:
    when: dict = {"match": match}
    spec: dict = {"skip": skip}
    if remark is not None:
        spec["remark"] = remark
    rule: dict = {
        "id": rule_id,
        "when": when,
        "do": {"unbold": spec},
    }
    if not enabled:
        rule["enabled"] = False
    return rule


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

    def test_parses_volume_filter(self) -> None:
        rules = parse_transforms_document(
            {
                "schema_version": 2,
                "rules": [
                    _replace_rule(
                        "pin",
                        match="bandhiṃ",
                        replacement="bandhaṃ",
                        loci=[{"volume": "01Vin01", "page": 79}],
                    )
                ],
            },
            source="mem",
        )
        self.assertEqual(
            {loc.volume for loc in (rules[0].loci or ())}, {"01Vin01"}
        )
        kept = select_rules_for_volume(rules, "01Vin01")
        dropped = select_rules_for_volume(rules, "02Vin02")
        self.assertEqual([r.id for r in kept], ["pin"])
        self.assertEqual(dropped, [])

    def test_parses_loci(self) -> None:
        rules = parse_transforms_document(
            {
                "schema_version": 2,
                "rules": [
                    _replace_rule(
                        "multi",
                        match="gacchantiṃ",
                        replacement="gacchantaṃ",
                        loci=[
                            {"volume": "01Vin01", "page": 145, "order": 801},
                            {"volume": "01Vin01", "page": 145, "order": 802},
                        ],
                    )
                ],
            },
            source="mem",
        )
        assert rules[0].loci is not None
        self.assertEqual(len(rules[0].loci), 2)
        self.assertEqual(rules[0].loci[0].volume, "01Vin01")
        self.assertEqual(rules[0].loci[0].page, 145)
        self.assertEqual(rules[0].loci[0].order, 801)
        self.assertEqual(rules[0].loci[1].order, 802)

    def test_rejects_empty_loci(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            parse_transforms_document(
                {
                    "schema_version": 2,
                    "rules": [
                        {
                            "id": "empty",
                            "when": {"match": "foo", "loci": []},
                            "do": {"replace": {"with": "bar"}},
                        }
                    ],
                },
                source="mem",
            )
        self.assertIn("when.loci must be a non-empty list", str(ctx.exception))

    def test_rejects_legacy_pages_orders_volumes(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            parse_transforms_document(
                {
                    "schema_version": 2,
                    "rules": [
                        {
                            "id": "bad",
                            "when": {"match": "foo", "volumes": ["01Vin01"]},
                            "do": {"replace": {"with": "bar"}},
                        }
                    ],
                },
                source="mem",
            )
        self.assertIn("moved to when.loci", str(ctx.exception))

    def test_rejects_token_key(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            parse_transforms_document(
                {
                    "schema_version": 2,
                    "rules": [
                        {
                            "id": "bad",
                            "when": {"match": "foo", "token": True},
                            "do": {"replace": {"with": "bar"}},
                        }
                    ],
                },
                source="mem",
            )
        self.assertIn("when.token removed", str(ctx.exception))

    def test_rejects_order_without_page(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            parse_transforms_document(
                {
                    "schema_version": 2,
                    "rules": [
                        _replace_rule(
                            "bad",
                            loci=[{"volume": "01Vin01", "order": 2}],
                        )
                    ],
                },
                source="mem",
            )
        self.assertIn("order requires page", str(ctx.exception))

    def test_rejects_locus_without_volume(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            parse_transforms_document(
                {
                    "schema_version": 2,
                    "rules": [
                        _replace_rule(
                            "bad",
                            loci=[{"page": 1, "order": 2}],
                        )
                    ],
                },
                source="mem",
            )
        self.assertIn("volume must be a non-empty string", str(ctx.exception))

    def test_rejects_duplicate_ids(self) -> None:
        with self.assertRaises(ValueError):
            parse_transforms_document(
                {
                    "schema_version": 2,
                    "rules": [_replace_rule("same"), _replace_rule("same")],
                },
                source="mem",
            )

    def test_rejects_unknown_when_keys(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            parse_transforms_document(
                {
                    "schema_version": 2,
                    "rules": [
                        {
                            "id": "x",
                            "when": {"match": "foo", "tokens": True},
                            "do": {"replace": {"with": "bar"}},
                        }
                    ],
                },
                source="mem",
            )
        self.assertIn("unsupported when keys", str(ctx.exception))

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

    def test_parses_unbold(self) -> None:
        rules = parse_transforms_document(
            {
                "schema_version": 2,
                "rules": [_unbold_rule(skip=1, remark="roman stroke")],
            },
            source="mem",
        )
        self.assertEqual(rules[0].action, "unbold")
        self.assertEqual(rules[0].unbold_skip, 1)
        self.assertEqual(rules[0].remark, "roman stroke")
        self.assertEqual(rules[0].core, "”ti")
        self.assertFalse(rules[0].leading_plus)
        self.assertFalse(rules[0].trailing_plus)

    def test_parses_plus_affixes(self) -> None:
        self.assertEqual(
            parse_match_pattern("bandhiṃ"), ("bandhiṃ", False, False)
        )
        self.assertEqual(
            parse_match_pattern("+bandhiṃ"), ("bandhiṃ", True, False)
        )
        self.assertEqual(
            parse_match_pattern("bandhiṃ+"), ("bandhiṃ", False, True)
        )
        self.assertEqual(
            parse_match_pattern("+bandhiṃ+"), ("bandhiṃ", True, True)
        )
        rules = parse_transforms_document(
            {
                "schema_version": 2,
                "rules": [
                    _replace_rule("pre", match="+bandhiṃ", replacement="bandhaṃ")
                ],
            },
            source="mem",
        )
        self.assertEqual(rules[0].match, "+bandhiṃ")
        self.assertEqual(rules[0].core, "bandhiṃ")
        self.assertTrue(rules[0].leading_plus)
        self.assertFalse(rules[0].trailing_plus)

    def test_rejects_plus_in_middle(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            parse_match_pattern("ban+hiṃ")
        self.assertIn("start or end", str(ctx.exception))

    def test_rejects_plus_on_phrase(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            parse_match_pattern("+taṃ yeva")
        self.assertIn("single letter-run", str(ctx.exception))

    def test_rejects_empty_plus_core(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            parse_match_pattern("+")
        self.assertIn("core must be non-empty", str(ctx.exception))


class MatchAffixTests(unittest.TestCase):
    def test_plus_prefix_suffix_both(self) -> None:
        prefix = parse_transforms_document(
            {
                "schema_version": 2,
                "rules": [
                    _replace_rule(
                        "pre", match="+bandhiṃ", replacement="bandhaṃ"
                    )
                ],
            },
            source="mem",
        )
        suffix = parse_transforms_document(
            {
                "schema_version": 2,
                "rules": [
                    _replace_rule(
                        "suf", match="bandhiṃ+", replacement="bandhaṃ"
                    )
                ],
            },
            source="mem",
        )
        both = parse_transforms_document(
            {
                "schema_version": 2,
                "rules": [
                    _replace_rule(
                        "both", match="+bandhiṃ+", replacement="bandhaṃ"
                    )
                ],
            },
            source="mem",
        )
        kwargs = dict(page=1, order=1, segment_type="prose")
        text, extra = apply_transforms("Sāmikā anubandhiṃ.", prefix, **kwargs)
        self.assertEqual(text, "Sāmikā anubandhaṃ.")
        self.assertEqual(extra, [])
        bare, _ = apply_transforms("Pāse bandhiṃ migaṃ", prefix, **kwargs)
        self.assertEqual(bare, "Pāse bandhiṃ migaṃ")
        longer, _ = apply_transforms("anubandhiṃsu", prefix, **kwargs)
        self.assertEqual(longer, "anubandhiṃsu")
        text, _ = apply_transforms("bandhiṃsu migā", suffix, **kwargs)
        self.assertEqual(text, "bandhaṃsu migā")
        prefix_only, _ = apply_transforms("anubandhiṃ", suffix, **kwargs)
        self.assertEqual(prefix_only, "anubandhiṃ")
        infix, _ = apply_transforms("xybandhiṃz", both, **kwargs)
        self.assertEqual(infix, "xybandhaṃz")
        not_infix, _ = apply_transforms("anubandhiṃ bandhiṃsu", both, **kwargs)
        self.assertEqual(not_infix, "anubandhiṃ bandhiṃsu")

    def test_plus_punctuation_is_not_an_affix(self) -> None:
        rules = parse_transforms_document(
            {
                "schema_version": 2,
                "rules": [
                    _replace_rule("exact", match="bandhiṃ", replacement="bandhaṃ")
                ],
            },
            source="mem",
        )
        text, extra = apply_transforms(
            "bandhiṃ. anubandhiṃ",
            rules,
            page=1,
            order=1,
            segment_type="prose",
        )
        self.assertEqual(text, "bandhaṃ. anubandhiṃ")
        self.assertEqual(extra, [])

    def test_plus_annotate_attaches_after_core(self) -> None:
        rules = parse_transforms_document(
            {
                "schema_version": 2,
                "rules": [
                    _annotate_rule("pre", match="+bandhiṃ", footnote="n")
                ],
            },
            source="mem",
        )
        text, extra = apply_transforms(
            "anubandhiṃ yeva",
            rules,
            page=1,
            order=1,
            segment_type="prose",
        )
        self.assertEqual(text, "anubandhiṃ{{n0}} yeva")
        self.assertEqual(extra, ["n"])


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
                "rules": [
                    _replace_rule(
                        loci=[{"volume": "01Vin01", "page": 12, "order": 3}]
                    )
                ],
            },
            source="mem",
        )
        text, extra = apply_transforms(
            "Bhagavaa āha",
            rules,
            page=12,
            order=3,
            segment_type="prose",
            volume_id="01Vin01",
        )
        self.assertEqual(text, "Bhagavā āha")
        self.assertEqual(extra, [])
        text2, extra2 = apply_transforms(
            "Bhagavaa āha",
            rules,
            page=11,
            order=3,
            segment_type="prose",
            volume_id="01Vin01",
        )
        self.assertEqual(text2, "Bhagavaa āha")
        self.assertEqual(extra2, [])

    def test_loci_pairs_page_and_order(self) -> None:
        rules = parse_transforms_document(
            {
                "schema_version": 2,
                "rules": [
                    _replace_rule(
                        match="gacchantiṃ",
                        replacement="gacchantaṃ",
                        loci=[
                            {"volume": "01Vin01", "page": 145, "order": 801},
                            {"volume": "01Vin01", "page": 145, "order": 802},
                        ],
                    )
                ],
            },
            source="mem",
        )
        hit_801, extra = apply_transforms(
            "vehāsaṃ gacchantiṃ.",
            rules,
            page=145,
            order=801,
            segment_type="prose",
            volume_id="01Vin01",
        )
        self.assertEqual(hit_801, "vehāsaṃ gacchantaṃ.")
        self.assertEqual(extra, [])
        hit_802, extra2 = apply_transforms(
            "purisaṃ gacchantiṃ.",
            rules,
            page=145,
            order=802,
            segment_type="prose",
            volume_id="01Vin01",
        )
        self.assertEqual(hit_802, "purisaṃ gacchantaṃ.")
        self.assertEqual(extra2, [])
        skip_same_page, extra3 = apply_transforms(
            "pesiṃ gacchantiṃ.",
            rules,
            page=145,
            order=800,
            segment_type="prose",
            volume_id="01Vin01",
        )
        self.assertEqual(skip_same_page, "pesiṃ gacchantiṃ.")
        self.assertEqual(extra3, [])
        skip_cartesian, extra4 = apply_transforms(
            "vehāsaṃ gacchantiṃ.",
            rules,
            page=148,
            order=801,
            segment_type="prose",
            volume_id="01Vin01",
        )
        self.assertEqual(skip_cartesian, "vehāsaṃ gacchantiṃ.")
        self.assertEqual(extra4, [])
        other_book, extra5 = apply_transforms(
            "vehāsaṃ gacchantiṃ.",
            rules,
            page=145,
            order=801,
            segment_type="prose",
            volume_id="15An01",
        )
        self.assertEqual(other_book, "vehāsaṃ gacchantiṃ.")
        self.assertEqual(extra5, [])

    def test_loci_multiple_volumes(self) -> None:
        rules = parse_transforms_document(
            {
                "schema_version": 2,
                "rules": [
                    _replace_rule(
                        match="Aññāthā",
                        replacement="Aññathā",
                        loci=[
                            {"volume": "01Vin01"},
                            {"volume": "15An01"},
                        ],
                    )
                ],
            },
            source="mem",
        )
        for volume_id in ("01Vin01", "15An01"):
            text, extra = apply_transforms(
                "Aññāthā hoti",
                rules,
                page=1,
                order=1,
                segment_type="prose",
                volume_id=volume_id,
            )
            self.assertEqual(text, "Aññathā hoti")
            self.assertEqual(extra, [])
        skipped, extra2 = apply_transforms(
            "Aññāthā hoti",
            rules,
            page=1,
            order=1,
            segment_type="prose",
            volume_id="11Ma03",
        )
        self.assertEqual(skipped, "Aññāthā hoti")
        self.assertEqual(extra2, [])
        self.assertEqual(
            [r.id for r in select_rules_for_volume(rules, "01Vin01")],
            ["fix"],
        )
        self.assertEqual(select_rules_for_volume(rules, "11Ma03"), [])
        narrowed = select_rules_for_volume(rules, "01Vin01")
        assert narrowed[0].loci is not None
        self.assertEqual([loc.volume for loc in narrowed[0].loci], ["01Vin01"])

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

    def test_load_shared_transforms_uses_given_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "shared.json"
            path.write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "rules": [
                            _replace_rule("s1", match="AA", replacement="BB"),
                            _replace_rule("s2", match="BB", replacement="CC"),
                        ],
                    }
                ),
                encoding="utf-8",
            )
            rules = load_shared_transforms(path=path)
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
                        loci=[{"volume": "01Vin01", "page": 280, "order": 1854}],
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

    def test_build_body_replace_keeps_lemma_bold_across_space(self) -> None:
        rules = parse_transforms_document(
            {
                "schema_version": 2,
                "rules": [
                    _replace_rule(
                        "vati",
                        match="Haneyyuṃvāti",
                        replacement="Haneyyuṃ vāti",
                    )
                ],
            },
            source="mem",
        )
        seg = {
            "page": 57,
            "order": 235,
            "segment_type": "prose",
            "text": [
                {
                    "script": "roman",
                    "value": "Haneyyuṃvāti hatthena.",
                    "runs": [
                        {"value": "Haneyyuṃvā", "bold": True},
                        {"value": "ti hatthena.", "bold": False},
                    ],
                },
                {
                    "script": "thai",
                    "value": "WRONG",
                    "runs": [
                        {"value": "หเนยฺยุํวา", "bold": True},
                        {"value": "ติ หตฺเถน.", "bold": False},
                    ],
                },
            ],
        }
        body, _ = build_body(seg, rules)
        self.assertNotIn("WRONG", body)
        bold_lemma = roman_to_thai("Haneyyuṃ vā")
        self.assertIn(r"\textbf{" + bold_lemma + "}", body)
        self.assertIn(roman_to_thai("ti hatthena."), body)

    def test_build_body_peels_closing_quote_ti_from_stored_runs(self) -> None:
        """Reuse-stored-runs path (no string transform) still unbolds ``”ติ.``."""
        rules = parse_transforms_document(
            {
                "schema_version": 2,
                "rules": [
                    _unbold_rule("iti", match="asaṃvāso”ti", skip=9),
                ],
            },
            source="mem",
        )
        roman = "ayampi pārājiko hoti asaṃvāso”ti."
        thai = roman_to_thai(roman)
        quote = roman_to_thai("ayampi pārājiko hoti asaṃvāso”")
        ti = roman_to_thai("ti.")
        seg = {
            "page": 56,
            "order": 224,
            "segment_type": "prose",
            "text": [
                {
                    "script": "roman",
                    "value": roman,
                    "runs": [
                        {"value": roman[:-1], "bold": True},
                        {"value": ".", "bold": False},
                    ],
                },
                {
                    "script": "thai",
                    "value": thai,
                    "runs": [
                        {"value": thai[:-1], "bold": True},
                        {"value": ".", "bold": False},
                    ],
                },
            ],
        }
        body, _ = build_body(seg, rules)
        self.assertIn(r"\textbf{" + quote + "}", body)
        self.assertIn(ti, body)
        self.assertNotIn(r"\textbf{" + thai[:-1] + "}", body)

    def test_build_body_snaps_hyphen_leftover_letter_in_stored_runs(self) -> None:
        """Stored Thai ``สมาทหาเปยฺยฺ`` + ``อ`` must not print; close the token."""
        roman = (
            "“Yo pana bhikkhu agilāno visibbanāpekkho jotiṃ "
            "samādaheyya vā samādahāpeyya vā aññatra "
            "tathārūpappaccayā pācittiyan”ti."
        )
        thai = roman_to_thai(roman)
        seg = {
            "page": 153,
            "order": 1147,
            "segment_type": "prose",
            "text": [
                {
                    "script": "roman",
                    "value": roman,
                    "runs": [
                        {"value": "“", "bold": False},
                        {
                            "value": (
                                "Yo pana bhikkhu agilāno visibbanāpekkho "
                                "jotiṃ samādaheyya vā"
                            ),
                            "bold": True,
                        },
                        {"value": " ", "bold": False},
                        {"value": "samādahāpeyy", "bold": True},
                        {
                            "value": (
                                "a vā aññatra tathārūpappaccayā "
                                "pācittiyan”ti."
                            ),
                            "bold": False,
                        },
                    ],
                },
                {
                    "script": "thai",
                    "value": thai,
                    "runs": [
                        {"value": "“", "bold": False},
                        {
                            "value": roman_to_thai(
                                "Yo pana bhikkhu agilāno visibbanāpekkho "
                                "jotiṃ samādaheyya vā"
                            ),
                            "bold": True,
                        },
                        {"value": " ", "bold": False},
                        {"value": roman_to_thai("samādahāpeyy"), "bold": True},
                        {
                            "value": roman_to_thai(
                                "a vā aññatra tathārūpappaccayā "
                                "pācittiyan”ti."
                            ),
                            "bold": False,
                        },
                    ],
                },
            ],
        }
        body, _ = build_body(seg, [])
        self.assertIn(r"\textbf{" + roman_to_thai("samādahāpeyya") + "}", body)
        self.assertNotIn(roman_to_thai("samādahāpeyy"), body)
        self.assertNotIn(roman_to_thai("a vā"), body)

    def test_build_body_replace_keeps_lemma_bold_when_sandhi_splits(self) -> None:
        rules = parse_transforms_document(
            {
                "schema_version": 2,
                "rules": [
                    _replace_rule(
                        "vati",
                        match="Bandheyyuṃvāti",
                        replacement="Bandheyyuṃ vāti",
                    )
                ],
            },
            source="mem",
        )
        roman = (
            "Bandheyyuṃvāti rajjubandhanena vā andubandhanena vā "
            "saṅkhalikabandhanena vā bandheyyuṃ."
        )
        seg = {
            "page": 57,
            "order": 236,
            "segment_type": "prose",
            "text": [
                {
                    "script": "roman",
                    "value": roman,
                    "runs": [
                        {"value": "Bandheyyuṃvā", "bold": True},
                        {
                            "value": roman[len("Bandheyyuṃvā") :],
                            "bold": False,
                        },
                    ],
                },
                {"script": "thai", "value": "WRONG"},
            ],
        }
        body, _ = build_body(seg, rules)
        self.assertNotIn("WRONG", body)
        bold_lemma = roman_to_thai("Bandheyyuṃ vā")
        self.assertIn(r"\textbf{" + bold_lemma + "}", body)
        self.assertIn(r"\-", body)

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
                        loci=[{"volume": "01Vin01", "page": 280, "order": 1854}],
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
        self.assertIn(tex_numbered_footnote(note_to_thai("existing note")), body)
        self.assertIn(
            tex_numbered_footnote(note_to_thai("cīra- pāṭho, cīvara-")),
            body,
        )
        # Soft breaks from the annotate rule should appear (edition form not in DPD).
        self.assertIn(r"\-", body)

    def test_build_body_does_not_apply_transforms_to_edition_notes(self) -> None:
        """01Vin01 p316 o2099: body paggāhikasālaṃ; apparatus Paṭaggāhikasālaṃ (?)."""
        rules = parse_transforms_document(
            {
                "schema_version": 2,
                "rules": [
                    _replace_rule(
                        "body",
                        match="paggāhikasālaṃ",
                        replacement="paggahikasālaṃ",
                    ),
                    _replace_rule(
                        "note",
                        match="Paṭaggāhikasālaṃ",
                        replacement="SHOULDNOT",
                    ),
                    _annotate_rule(
                        "ann",
                        match="Paṭaggāhikasālaṃ",
                        footnote="should not inject – ม.พ.ป.",
                    ),
                ],
            },
            source="mem",
        )
        seg = {
            "page": 316,
            "order": 2099,
            "segment_type": "prose_continuation",
            "notes": ["Paṭaggāhikasālaṃ (?)"],
            "symbol_notes": {"*": "Paṭaggāhikasālaṃ (Syā)"},
            "text": [
                {
                    "script": "roman",
                    "value": "paggāhikasālaṃ{{n0}} vā pasāressantī”ti.{{*}}",
                },
                {"script": "thai", "value": "WRONG"},
            ],
        }
        body, _ = build_body(seg, rules)
        edition = note_to_thai("Paṭaggāhikasālaṃ (?)")
        self.assertIn(tex_numbered_footnote(edition), body)
        self.assertNotIn("SHOULDNOT", body)
        self.assertNotIn(note_to_thai("SHOULDNOT"), body)
        self.assertNotIn(
            tex_numbered_footnote(note_to_thai("should not inject – ม.พ.ป.")),
            body,
        )
        self.assertIn(note_to_thai("Paṭaggāhikasālaṃ (Syā)"), body)
        self.assertIn(roman_to_thai("paggahikasālaṃ"), body)

    def test_generate_applies_shared_transforms(self) -> None:
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
                                    "value": "ciraṃ dighamaddhānaṃ ṭhapesuṃ.",
                                },
                                {
                                    "script": "thai",
                                    "value": "WRONG",
                                },
                            ],
                        }
                    ],
                },
            )
            path = generate(volume_id)
            tex = path.read_text(encoding="utf-8")
            n_rules = len(
                select_rules_for_volume(load_shared_transforms(), volume_id)
            )
            self.assertIn(f"% transform_rules: {n_rules}", tex)
            self.assertIn(roman_to_thai("ciraṃ dīghamaddhānaṃ ṭhapesuṃ."), tex)
            self.assertNotIn("WRONG", tex)
            self.assertFalse((data / "transforms.json").is_file())
        finally:
            if out_path.is_file():
                out_path.unlink()
            for name in ("segments.json", "layout.json"):
                p = data / name
                if p.is_file():
                    p.unlink()


class SharedTransformsTests(unittest.TestCase):
    def test_shared_catalog_omits_token(self) -> None:
        data = json.loads(SHARED_TRANSFORMS_PATH.read_text(encoding="utf-8"))
        extras = [
            rule["id"]
            for rule in data["rules"]
            if "token" in (rule.get("when") or {})
        ]
        self.assertEqual(extras, [])
        for rule in load_transforms_file(SHARED_TRANSFORMS_PATH):
            self.assertEqual(rule.core, rule.match)
            self.assertFalse(rule.leading_plus)
            self.assertFalse(rule.trailing_plus)

    def test_shared_catalog_omits_enabled_true(self) -> None:
        data = json.loads(SHARED_TRANSFORMS_PATH.read_text(encoding="utf-8"))
        extras = [
            rule["id"]
            for rule in data["rules"]
            if rule.get("enabled") is True
        ]
        self.assertEqual(extras, [])

    def test_dighamaddhana_long_i_replace(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        text, extra = apply_transforms(
            "ciraṃ dighamaddhānaṃ ṭhapesuṃ",
            rules,
            page=10,
            order=34,
            segment_type="prose",
        )
        self.assertEqual(text, "ciraṃ dīghamaddhānaṃ ṭhapesuṃ")
        self.assertEqual(extra, [])
        unchanged, _ = apply_transforms(
            "ciraṃ dīghamaddhānaṃ ṭhapesuṃ",
            rules,
            page=10,
            order=34,
            segment_type="prose",
        )
        self.assertEqual(unchanged, "ciraṃ dīghamaddhānaṃ ṭhapesuṃ")

    def test_bahukaraniya_long_i_replace(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        text, extra = apply_transforms(
            "rājāno nāma bahukiccā bahukaraṇiyā datvāpi",
            rules,
            page=54,
            order=218,
            segment_type="prose",
        )
        self.assertEqual(text, "rājāno nāma bahukiccā bahukaraṇīyā datvāpi")
        self.assertEqual(extra, [])
        unchanged, extra2 = apply_transforms(
            "bahukiccā gharāvāsā bahukaraṇīyā, adhivāsetu",
            rules,
            page=12,
            order=38,
            segment_type="prose",
        )
        self.assertEqual(unchanged, "bahukiccā gharāvāsā bahukaraṇīyā, adhivāsetu")
        self.assertEqual(extra2, [])

    def test_sinditva_bhinditva_replace(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        text, extra = apply_transforms(
            "temāsaccayena tiṇakuṭiyo sinditvā tiṇañca kaṭṭhañca",
            rules,
            volume_id="01Vin01",
            page=51,
            order=210,
            segment_type="prose_continuation",
        )
        self.assertEqual(
            text, "temāsaccayena tiṇakuṭiyo bhinditvā tiṇañca kaṭṭhañca"
        )
        self.assertEqual(extra, [])
        unchanged, extra2 = apply_transforms(
            "tiṇakuṭikaṃ bhinditvā tiṇañca kaṭṭhañca",
            rules,
            volume_id="01Vin01",
            page=51,
            order=210,
            segment_type="prose_continuation",
        )
        self.assertEqual(unchanged, "tiṇakuṭikaṃ bhinditvā tiṇañca kaṭṭhañca")
        self.assertEqual(extra2, [])

    def test_teyyacitta_theyya_replace(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        text, extra = apply_transforms(
            "Bhikkhū “pure sāmikā passantī”ti teyyacittā paribhuñjiṃsu.",
            rules,
            page=77,
            order=355,
            segment_type="prose_continuation",
        )
        self.assertEqual(
            text, "Bhikkhū “pure sāmikā passantī”ti theyyacittā paribhuñjiṃsu."
        )
        self.assertEqual(extra, [])
        unchanged, extra2 = apply_transforms(
            "Bhikkhū “pure sāmikā passantī”ti theyyacittā paribhuñjiṃsu.",
            rules,
            page=76,
            order=353,
            segment_type="prose",
        )
        self.assertEqual(
            unchanged,
            "Bhikkhū “pure sāmikā passantī”ti theyyacittā paribhuñjiṃsu.",
        )
        self.assertEqual(extra2, [])

    def test_anadinavadasso_long_i_replace(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        text, extra = apply_transforms(
            "apaññatte sikkhāpade anādinavadasso purāṇadutiyikāya",
            rules,
            page=21,
            order=66,
            segment_type="prose_continuation",
        )
        self.assertEqual(
            text, "apaññatte sikkhāpade anādīnavadasso purāṇadutiyikāya"
        )
        self.assertEqual(extra, [])
        unchanged, extra2 = apply_transforms(
            "ajjhopannā anādīnavadassāvino anissaraṇapaññā",
            rules,
            page=231,
            order=1171,
            segment_type="prose",
        )
        self.assertEqual(
            unchanged, "ajjhopannā anādīnavadassāvino anissaraṇapaññā"
        )
        self.assertEqual(extra2, [])

    def test_attiyamano_long_i_replace(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        text, extra = apply_transforms(
            "bhikkhubhāvaṃ aṭṭiyamāno harāyamāno jigucchamāno",
            rules,
            page=30,
            order=99,
            segment_type="prose",
        )
        self.assertEqual(
            text, "bhikkhubhāvaṃ aṭṭīyamāno harāyamāno jigucchamāno"
        )
        self.assertEqual(extra, [])
        unchanged, extra2 = apply_transforms(
            "bhikkhubhāvaṃ aṭṭīyamāno harāyamāno jigucchamāno",
            rules,
            page=29,
            order=95,
            segment_type="prose",
        )
        self.assertEqual(
            unchanged, "bhikkhubhāvaṃ aṭṭīyamāno harāyamāno jigucchamāno"
        )
        self.assertEqual(extra2, [])

    def test_dukkatassati_long_a_replace(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        text, extra = apply_transforms(
            "Anāpatti bhikkhu pārājikassa, āpatti dukkaṭassati. (55)",
            rules,
            page=74,
            order=341,
            segment_type="prose",
        )
        self.assertEqual(
            text, "Anāpatti bhikkhu pārājikassa, āpatti dukkaṭassāti. (55)"
        )
        self.assertEqual(extra, [])
        unchanged, extra2 = apply_transforms(
            "yo vaseyya, āpatti dukkaṭassāti. (3)",
            rules,
            page=139,
            order=768,
            segment_type="prose",
        )
        self.assertEqual(unchanged, "yo vaseyya, āpatti dukkaṭassāti. (3)")
        self.assertEqual(extra2, [])

    def test_parajikassati_long_a_replace(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        text, extra = apply_transforms(
            "Anāpatti bhikkhave adinnādāne pārājikassa, āpatti methunadhammasamāyoge pārājikassati. (149)",
            rules,
            page=85,
            order=404,
            segment_type="prose",
        )
        self.assertEqual(
            text,
            "Anāpatti bhikkhave adinnādāne pārājikassa, āpatti methunadhammasamāyoge pārājikassāti. (149)",
        )
        self.assertEqual(extra, [])
        unchanged, extra2 = apply_transforms(
            "moghapuriso na vā vediyi, āpatti pārājikassāti. (41)",
            rules,
            page=46,
            order=189,
            segment_type="prose",
        )
        self.assertEqual(unchanged, "moghapuriso na vā vediyi, āpatti pārājikassāti. (41)")
        self.assertEqual(extra2, [])

    def test_samika_long_a_replace(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        text, extra = apply_transforms(
            "sūkaraṃ “pure samikā passantī”ti theyyacitto muñci.",
            rules,
            page=79,
            order=366,
            segment_type="prose",
        )
        self.assertEqual(
            text, "sūkaraṃ “pure sāmikā passantī”ti theyyacitto muñci."
        )
        self.assertEqual(extra, [])
        unchanged, extra2 = apply_transforms(
            "migaṃ “pure sāmikā passantī”ti theyyacitto muñci.",
            rules,
            page=79,
            order=367,
            segment_type="prose",
        )
        self.assertEqual(
            unchanged, "migaṃ “pure sāmikā passantī”ti theyyacitto muñci."
        )
        self.assertEqual(extra2, [])

    def test_assamanaka_long_a_replace(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        text, extra = apply_transforms(
            "appatirūpaṃ assamaṇakaṃ akappiyaṃ akaraṇiyaṃ, kathaṃ hi nāma",
            rules,
            page=54,
            order=218,
            segment_type="prose",
        )
        self.assertEqual(
            text, "appatirūpaṃ assāmaṇakaṃ akappiyaṃ akaraṇīyaṃ, kathaṃ hi nāma"
        )
        self.assertEqual(extra, [])
        unchanged, extra2 = apply_transforms(
            "appatirūpaṃ assāmaṇakaṃ akappiyaṃ akaraṇīyaṃ, kathaṃ hi nāma",
            rules,
            page=21,
            order=87,
            segment_type="prose",
        )
        self.assertEqual(
            unchanged,
            "appatirūpaṃ assāmaṇakaṃ akappiyaṃ akaraṇīyaṃ, kathaṃ hi nāma",
        )
        self.assertEqual(extra2, [])

    def test_akaraniya_long_i_replace(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        text, extra = apply_transforms(
            "akappiyaṃ akaraṇiyaṃ, kathaṃ hi nāma",
            rules,
            page=54,
            order=218,
            segment_type="prose",
        )
        self.assertEqual(text, "akappiyaṃ akaraṇīyaṃ, kathaṃ hi nāma")
        self.assertEqual(extra, [])
        unchanged, extra2 = apply_transforms(
            "akappiyaṃ akaraṇīyaṃ, kathaṃ hi nāma",
            rules,
            page=21,
            order=87,
            segment_type="prose",
        )
        self.assertEqual(unchanged, "akappiyaṃ akaraṇīyaṃ, kathaṃ hi nāma")
        self.assertEqual(extra2, [])

    def test_quote_iti_unbold_skips_quote(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        text = "ayampi pārājiko hoti asaṃvāso”ti."
        runs = [
            {"value": "ayampi pārājiko hoti asaṃvāso”ti", "bold": True},
            {"value": ".", "bold": False},
        ]
        expected = [
            {"value": "ayampi pārājiko hoti asaṃvāso”", "bold": True},
            {"value": "ti.", "bold": False},
        ]
        for page, order in ((56, 224), (116, 589), (117, 592)):
            peeled = apply_unbold_to_runs(
                text,
                runs,
                rules,
                page=page,
                order=order,
                segment_type="prose",
                volume_id="01Vin01",
            )
            self.assertEqual(peeled, expected)
        already = [
            {"value": "pārājiko hoti asaṃvāso”", "bold": True},
            {"value": "ti.", "bold": False},
        ]
        self.assertIs(
            apply_unbold_to_runs(
                "pārājiko hoti asaṃvāso”ti.",
                already,
                rules,
                page=25,
                order=74,
                segment_type="prose",
                volume_id="01Vin01",
            ),
            already,
        )
        other_formula = [
            {"value": "saṃghādiseso”ti", "bold": True},
            {"value": ".", "bold": False},
        ]
        self.assertIs(
            apply_unbold_to_runs(
                "sa parāmasanaṃ, saṃghādiseso”ti.",
                other_formula,
                rules,
                page=173,
                order=1059,
                segment_type="prose",
                volume_id="01Vin01",
            ),
            other_formula,
        )

    def test_quote_iti_unbold_skips_thenositi_inside_quote(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        text = (
            "corosi bālosi mūḷhosi thenosīti, tathārūpaṃ "
            "ayampi pārājiko hoti asaṃvāso”ti."
        )
        runs = [
            {
                "value": (
                    "corosi bālosi mūḷhosi thenosīti, tathārūpaṃ "
                    "ayampi pārājiko hoti asaṃvāso”ti"
                ),
                "bold": True,
            },
            {"value": ".", "bold": False},
        ]
        peeled = apply_unbold_to_runs(
            text,
            runs,
            rules,
            page=56,
            order=224,
            segment_type="prose",
            volume_id="01Vin01",
        )
        self.assertIsNot(peeled, runs)
        bold = "".join(r["value"] for r in peeled if r.get("bold"))
        self.assertIn("thenosīti", bold)
        self.assertTrue(bold.endswith("asaṃvāso”"))
        self.assertEqual(peeled[-1], {"value": "ti.", "bold": False})

    def test_bandhim_acc_replace(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        text, extra = apply_transforms(
            "pāse bandhaṃ migaṃ kāruññena muñci. Pāse bandhiṃ migaṃ “pure",
            rules,
            page=79,
            order=367,
            segment_type="prose",
            volume_id="01Vin01",
        )
        self.assertEqual(
            text,
            "pāse bandhaṃ migaṃ kāruññena muñci. Pāse bandhaṃ migaṃ “pure",
        )
        self.assertEqual(extra, [])
        other_vol, extra_v = apply_transforms(
            "Pāse bandhiṃ migaṃ “pure",
            rules,
            page=79,
            order=367,
            segment_type="prose",
            volume_id="02Vin02",
        )
        self.assertEqual(other_vol, "Pāse bandhiṃ migaṃ “pure")
        self.assertEqual(extra_v, [])
        # exact word: longer forms on the same page must not be rewritten.
        inflected, extra_i = apply_transforms(
            "Pāse bandhiṃsu migā. Sāmikā anubandhiṃ.",
            rules,
            page=79,
            order=367,
            segment_type="prose",
        )
        self.assertEqual(inflected, "Pāse bandhiṃsu migā. Sāmikā anubandhiṃ.")
        self.assertEqual(extra_i, [])
        aorist, extra2 = apply_transforms(
            "na issiṃ na upadussiṃ na issaṃ bandhiṃ, sāhaṃ bhante",
            rules,
            page=526,
            order=3501,
            segment_type="prose",
        )
        self.assertEqual(
            aorist, "na issiṃ na upadussiṃ na issaṃ bandhiṃ, sāhaṃ bhante"
        )
        self.assertEqual(extra2, [])
        plural, extra3 = apply_transforms(
            "Sāmikā te corake anubandhiṃsu. Corakā sāmike",
            rules,
            page=76,
            order=351,
            segment_type="prose",
        )
        self.assertEqual(
            plural, "Sāmikā te corake anubandhiṃsu. Corakā sāmike"
        )
        self.assertEqual(extra3, [])

    def test_kukucc_geminate_kk_replace(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        text, extra = apply_transforms(
            "tesaṃ appamattakepi kukuccaṃ uppajjati",
            rules,
            page=54,
            order=218,
            segment_type="prose",
        )
        self.assertEqual(text, "tesaṃ appamattakepi kukkuccaṃ uppajjati")
        self.assertEqual(extra, [])
        inflected, extra3 = apply_transforms(
            "kukuccāyantā bhikkhū",
            rules,
            page=83,
            order=397,
            segment_type="prose",
        )
        self.assertEqual(inflected, "kukkuccāyantā bhikkhū")
        self.assertEqual(extra3, [])
        unchanged, extra2 = apply_transforms(
            "tassa kukkuccaṃ ahosi -pa-.",
            rules,
            page=44,
            order=173,
            segment_type="prose",
        )
        self.assertEqual(unchanged, "tassa kukkuccaṃ ahosi -pa-.")
        self.assertEqual(extra2, [])

    def test_sariputta_vipassi_space_replace(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        text, extra = apply_transforms(
            "Bhagavā ca SāriputtaVipassī Bhagavā ca Sikhī",
            rules,
            page=9,
            order=32,
            segment_type="prose",
        )
        self.assertEqual(text, "Bhagavā ca Sāriputta Vipassī Bhagavā ca Sikhī")
        self.assertEqual(extra, [])

    def test_kuttam_upatthambhesi_space_replace(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        text, extra = apply_transforms(
            "attano vihārassa kuṭṭaṃupatthambhesi.",
            rules,
            page=82,
            order=391,
            segment_type="prose",
        )
        self.assertEqual(text, "attano vihārassa kuṭṭaṃ upatthambhesi.")
        self.assertEqual(extra, [])

    def test_kim_taya_space_replace(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        text, extra = apply_transforms(
            "Kiṃtayā āvuso katanti, so tamatthaṃ ārocesi.",
            rules,
            page=86,
            order=406,
            segment_type="prose_continuation",
        )
        self.assertEqual(text, "Kiṃ tayā āvuso katanti, so tamatthaṃ ārocesi.")
        self.assertEqual(extra, [])

    def test_haneyyum_vati_dve_pada_annotate(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        cases = (
            (
                "Haneyyuṃvāti hatthena",
                "Haneyyuṃvāti{{n0}} hatthena",
                "haneyyuṃ vāti dve padāni – ม.พ.ป.",
            ),
            (
                "Bandheyyuṃvāti rajju",
                "Bandheyyuṃvāti{{n0}} rajju",
                "bandheyyuṃ vāti dve padāni – ม.พ.ป.",
            ),
            (
                "Pabbājeyyuṃvāti gāmā",
                "Pabbājeyyuṃvāti{{n0}} gāmā",
                "pabbājeyyuṃ vāti dve padāni – ม.พ.ป.",
            ),
        )
        for src, expected, note in cases:
            with self.subTest(src=src):
                text, extra = apply_transforms(
                    src, rules, page=57, order=235, segment_type="prose"
                )
                self.assertEqual(text, expected)
                self.assertEqual(extra, [note])
        # Spaced Myanmar form — no annotate (printed Roman is glued).
        unchanged, extra2 = apply_transforms(
            "Haneyyuṃ vāti hatthena",
            rules,
            page=57,
            order=235,
            segment_type="prose",
        )
        self.assertEqual(unchanged, "Haneyyuṃ vāti hatthena")
        self.assertEqual(extra2, [])

    def test_sa_upadanaya_linewrap_replace(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        text, extra = apply_transforms(
            "anupādānāya dhammo desito no sa- upādānāya.",
            rules,
            page=22,
            order=69,
            segment_type="prose",
        )
        self.assertEqual(text, "anupādānāya dhammo desito no saupādānāya.")
        self.assertEqual(extra, [])
        unchanged, _ = apply_transforms(
            "anupādānāya dhamme desite saupādānāya cetessasi.",
            rules,
            page=23,
            order=71,
            segment_type="prose",
        )
        self.assertEqual(
            unchanged, "anupādānāya dhamme desite saupādānāya cetessasi."
        )

    def test_aharupaharo_join_and_pagebreak(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        joined, extra = apply_transforms(
            "saddhiṃ āhārūpa hāro, gaṇakiyā",
            rules,
            page=199,
            order=1298,
            segment_type="prose",
        )
        self.assertEqual(joined, "saddhiṃ āhārūpahāro, gaṇakiyā")
        self.assertEqual(extra, [])
        head, _ = apply_transforms(
            "samaṇena saddhiṃ amhākaṃ āhārūpa",
            rules,
            page=198,
            order=1296,
            segment_type="prose",
        )
        self.assertEqual(head, "samaṇena saddhiṃ amhākaṃ āhārūpahāro,")
        tail, _ = apply_transforms(
            "hāro, gaccha tvaṃ, na mayaṃ",
            rules,
            page=199,
            order=1297,
            segment_type="prose_continuation",
        )
        self.assertEqual(tail, "gaccha tvaṃ, na mayaṃ")
        intact, _ = apply_transforms(
            "saddhiṃ amhākaṃ āhārūpahāro, samaṇena",
            rules,
            page=198,
            order=1296,
            segment_type="prose",
        )
        self.assertEqual(intact, "saddhiṃ amhākaṃ āhārūpahāro, samaṇena")

    def test_sasannayapare_join_replace(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        text, extra = apply_transforms(
            "sasaññā yapare duve.",
            rules,
            page=69,
            order=306,
            segment_type="gatha",
        )
        self.assertEqual(text, "sasaññāyapare duve.")
        self.assertEqual(extra, [])
        unchanged, extra2 = apply_transforms(
            "Sasaññā bhikkhave uppajjanti",
            rules,
            page=81,
            order=616,
            segment_type="prose",
        )
        self.assertEqual(unchanged, "Sasaññā bhikkhave uppajjanti")
        self.assertEqual(extra2, [])

    def test_pamsukulasannissati_join_replace(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        text, extra = apply_transforms(
            "Anāpatti bhikkhu paṃ sukūlasaññissāti.",
            rules,
            page=80,
            order=374,
            segment_type="prose",
        )
        self.assertEqual(text, "Anāpatti bhikkhu paṃsukūlasaññissāti.")
        self.assertEqual(extra, [])
        unchanged, extra2 = apply_transforms(
            "Anāpatti bhikkhave paṃsukūlasaññissāti.",
            rules,
            page=76,
            order=351,
            segment_type="prose",
        )
        self.assertEqual(unchanged, "Anāpatti bhikkhave paṃsukūlasaññissāti.")
        self.assertEqual(extra2, [])

    def test_annataro_bhikkhuno_genitive_replace(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        text, extra = apply_transforms(
            "Tena kho pana samayena aññataro bhikkhuno nadiṃ tarantassa",
            rules,
            page=80,
            order=375,
            segment_type="prose",
        )
        self.assertEqual(
            text,
            "Tena kho pana samayena aññatarassa bhikkhuno nadiṃ tarantassa",
        )
        self.assertEqual(extra, [])
        unchanged, extra2 = apply_transforms(
            "Tena kho pana samayena aññataro gopālako rukkhe",
            rules,
            page=80,
            order=374,
            segment_type="prose",
        )
        self.assertEqual(
            unchanged, "Tena kho pana samayena aññataro gopālako rukkhe"
        )
        self.assertEqual(extra2, [])
        already, extra3 = apply_transforms(
            "Tena kho pana samayena aññatarassa bhikkhuno nadiṃ tarantassa",
            rules,
            page=80,
            order=376,
            segment_type="prose",
        )
        self.assertEqual(
            already,
            "Tena kho pana samayena aññatarassa bhikkhuno nadiṃ tarantassa",
        )
        self.assertEqual(extra3, [])

    def test_chambhitatta_join_replace(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        text, extra = apply_transforms(
            "tesaṃ tasmiṃ samaye hoti yeva bhayaṃ, hoti chambhi tattaṃ, hoti lomahaṃso.",
            rules,
            page=87,
            order=411,
            segment_type="prose",
        )
        self.assertEqual(
            text,
            "tesaṃ tasmiṃ samaye hoti yeva{{n0}} bhayaṃ, hoti chambhitattaṃ, hoti lomahaṃso.",
        )
        self.assertEqual(extra, ["hotiyeva sandhi – ม.พ.ป."])
        unchanged, extra2 = apply_transforms(
            "bhayaṃ vā chambhitattaṃ vā lomahaṃso vā",
            rules,
            page=87,
            order=410,
            segment_type="prose",
        )
        self.assertEqual(unchanged, "bhayaṃ vā chambhitattaṃ vā lomahaṃso vā")
        self.assertEqual(extra2, [])

    def test_eva_mahamsu_join_replace(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        text, extra = apply_transforms(
            "Te eva māhaṃsu “na mayaṃ pārājikā”ti.",
            rules,
            page=81,
            order=380,
            segment_type="prose",
        )
        self.assertEqual(text, "Te evamāhaṃsu “na mayaṃ pārājikā”ti.")
        self.assertEqual(extra, [])
        unchanged, extra2 = apply_transforms(
            "Te evamāhaṃsu “na mayaṃ pārājikā”ti.",
            rules,
            page=81,
            order=379,
            segment_type="prose_continuation",
        )
        self.assertEqual(unchanged, "Te evamāhaṃsu “na mayaṃ pārājikā”ti.")
        self.assertEqual(extra2, [])
        # exact word — do not join inside kireva māhaṃsu
        kira, extra3 = apply_transforms(
            "Saccaṃ kireva māhaṃsu,",
            rules,
            page=271,
            order=3344,
            segment_type="gatha",
        )
        self.assertEqual(kira, "Saccaṃ kireva māhaṃsu,")
        self.assertEqual(extra3, [])

    def test_evam_vutte_space_replace(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        text, extra = apply_transforms(
            "nāyyo Udāyī evaṃ karissatī”ti. Evaṃvutte “karissati na karissatī”ti",
            rules,
            page=201,
            order=1304,
            segment_type="prose",
        )
        self.assertEqual(
            text,
            "nāyyo Udāyī evaṃ karissatī”ti. Evaṃ vutte “karissati na karissatī”ti",
        )
        self.assertEqual(extra, [])
        unchanged, extra2 = apply_transforms(
            "Evaṃ vutte te bhikkhū Bhagavantaṃ etadavocuṃ",
            rules,
            page=54,
            order=200,
            segment_type="prose",
        )
        self.assertEqual(unchanged, "Evaṃ vutte te bhikkhū Bhagavantaṃ etadavocuṃ")
        self.assertEqual(extra2, [])

    def test_eva_maha_join_replace(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        text, extra = apply_transforms(
            "sā eva māha “ahaṃ khvayyo tumhe na jānāmi",
            rules,
            page=198,
            order=1294,
            segment_type="prose",
        )
        self.assertEqual(text, "sā evamāha “ahaṃ khvayyo tumhe na jānāmi")
        self.assertEqual(extra, [])
        unchanged, extra2 = apply_transforms(
            "Sā evamāha “ahaṃ khvayyo",
            rules,
            page=197,
            order=1293,
            segment_type="prose",
        )
        self.assertEqual(unchanged, "Sā evamāha “ahaṃ khvayyo")
        self.assertEqual(extra2, [])
        # exact word — do not join inside eva māhaṃsu (own rule) or kireva
        mahamsu, extra3 = apply_transforms(
            "Te eva māhaṃsu “na mayaṃ pārājikā”ti.",
            rules,
            page=81,
            order=380,
            segment_type="prose",
        )
        self.assertEqual(mahamsu, "Te evamāhaṃsu “na mayaṃ pārājikā”ti.")
        self.assertEqual(extra3, [])

    def test_amantesi_tena_dash_space_replace(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        text, extra = apply_transforms(
            "āmantesi–tena kho bhagavā",
            rules,
            page=24,
            order=73,
            segment_type="prose",
        )
        self.assertEqual(text, "āmantesi– tena kho bhagavā")
        self.assertEqual(extra, [])
        unchanged, _ = apply_transforms(
            "āmantesi– tena kho bhagavā",
            rules,
            page=76,
            order=418,
            segment_type="prose",
        )
        self.assertEqual(unchanged, "āmantesi– tena kho bhagavā")

    def test_addha_mahaddhana_dve_pada_annotate(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        text, extra = apply_transforms(
            "ñātī aḍḍhāmahaddhanā mahābhogā",
            rules,
            page=17,
            order=55,
            segment_type="prose",
        )
        self.assertEqual(text, "ñātī aḍḍhāmahaddhanā{{n0}} mahābhogā")
        self.assertEqual(extra, ["aḍḍhā mahaddhanā dve padāni – ม.พ.ป."])
        # Spaced form elsewhere (e.g. 12Sam01) — no annotate.
        unchanged, extra2 = apply_transforms(
            "ñātī aḍḍhā mahaddhanā mahābhogā",
            rules,
            page=70,
            order=726,
            segment_type="prose",
        )
        self.assertEqual(unchanged, "ñātī aḍḍhā mahaddhanā mahābhogā")
        self.assertEqual(extra2, [])

    def test_yopanati_dve_pada_annotate(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        text, extra = apply_transforms(
            "Yopanāti yo yādiso yathāyutto",
            rules,
            page=28,
            order=90,
            segment_type="prose",
        )
        self.assertEqual(text, "Yopanāti{{n0}} yo yādiso yathāyutto")
        self.assertEqual(extra, ["yo panāti dve padāni – ม.พ.ป."])
        # Spaced form already correct — no annotate.
        unchanged, extra2 = apply_transforms(
            "Yo panāti yo yādiso -pa-.",
            rules,
            page=173,
            order=1057,
            segment_type="prose",
        )
        self.assertEqual(unchanged, "Yo panāti yo yādiso -pa-.")
        self.assertEqual(extra2, [])

    def test_panasa_coraka_samaso_annotate(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        text, extra = apply_transforms(
            "Labujacorakā. Panasa corakā. Tālapakkacorakā.",
            rules,
            page=76,
            order=352,
            segment_type="prose",
        )
        self.assertEqual(
            text, "Labujacorakā. Panasa corakā{{n0}}. Tālapakkacorakā."
        )
        self.assertEqual(extra, ["panasacorakā samāso – ม.พ.ป."])
        # Joined form already correct (same page, later vatthu) — no annotate.
        unchanged, extra2 = apply_transforms(
            "Labujacorakā. Panasacorakā. Tālapakkacorakā.",
            rules,
            page=76,
            order=354,
            segment_type="prose",
        )
        self.assertEqual(
            unchanged, "Labujacorakā. Panasacorakā. Tālapakkacorakā."
        )
        self.assertEqual(extra2, [])

    def test_hoti_yeva_sandhi_annotate(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        text, extra = apply_transforms(
            "tesaṃ tasmiṃ samaye hoti yeva bhayaṃ",
            rules,
            page=87,
            order=411,
            segment_type="prose",
        )
        self.assertEqual(text, "tesaṃ tasmiṃ samaye hoti yeva{{n0}} bhayaṃ")
        self.assertEqual(extra, ["hotiyeva sandhi – ม.พ.ป."])
        unchanged, extra2 = apply_transforms(
            "tesaṃ tasmiṃ samaye hotiyeva bhayaṃ",
            rules,
            page=87,
            order=411,
            segment_type="prose",
        )
        self.assertEqual(unchanged, "tesaṃ tasmiṃ samaye hotiyeva bhayaṃ")
        self.assertEqual(extra2, [])

    def test_eso_yeva_sandhi_annotate(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        text, extra = apply_transforms(
            "Eso yeva kho āvuso seyyo",
            rules,
            page=36,
            order=240,
            segment_type="prose_continuation",
        )
        self.assertEqual(text, "Eso yeva{{n0}} kho āvuso seyyo")
        self.assertEqual(extra, ["esoyeva sandhi – ม.พ.ป."])
        unchanged, extra2 = apply_transforms(
            "esoyeva tassa",
            rules,
            page=273,
            order=1165,
            segment_type="prose",
        )
        self.assertEqual(unchanged, "esoyeva tassa")
        self.assertEqual(extra2, [])

    def test_eka_yeva_sandhi_annotate(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        text, extra = apply_transforms(
            "Atthesā bhikkhave Sobhitassa, sā ca kho ekā yeva jāti.",
            rules,
            page=150,
            order=825,
            segment_type="prose",
            volume_id="01Vin01",
        )
        self.assertEqual(
            text,
            "Atthesā bhikkhave Sobhitassa, sā ca kho ekā yeva{{n0}} jāti.",
        )
        self.assertEqual(extra, ["ekāyeva sandhi – ม.พ.ป."])
        # Same spaced form in 28Khu11 is left as printed.
        other, extra2 = apply_transforms(
            "Pathavī mahārāja mahantī. sā ekā yeva.",
            rules,
            page=233,
            order=1356,
            segment_type="prose",
            volume_id="28Khu11",
        )
        self.assertEqual(other, "Pathavī mahārāja mahantī. sā ekā yeva.")
        self.assertEqual(extra2, [])
        glued, extra3 = apply_transforms(
            "ekāyeva sā itthī hoti",
            rules,
            page=161,
            order=759,
            segment_type="prose_continuation",
            volume_id="07Di02",
        )
        self.assertEqual(glued, "ekāyeva sā itthī hoti")
        self.assertEqual(extra3, [])

    def test_imasmim_yeva_agama_sandhi_annotate(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        note = "imasmiṃyeva āgamasandhi – ม.พ.ป."
        text, extra = apply_transforms(
            "Eso bhikkhave satto imasmiṃ yeva Rājagahe goghātako ahosi",
            rules,
            page=145,
            order=798,
            segment_type="prose_continuation",
        )
        self.assertEqual(
            text,
            "Eso bhikkhave satto imasmiṃ yeva{{n0}} Rājagahe goghātako ahosi",
        )
        self.assertEqual(extra, [note])
        comma, extra2 = apply_transforms(
            "Eso bhikkhave satto imasmiṃ, yeva Rājagahe goghātako ahosi",
            rules,
            page=145,
            order=799,
            segment_type="prose",
        )
        self.assertEqual(
            comma,
            "Eso bhikkhave satto imasmiṃ, yeva{{n0}} Rājagahe goghātako ahosi",
        )
        self.assertEqual(extra2, [note])
        glued, extra3 = apply_transforms(
            "imasmiṃyeva āsane virajaṃ vītamalaṃ",
            rules,
            page=1,
            order=1,
            segment_type="prose",
        )
        self.assertEqual(glued, "imasmiṃyeva āsane virajaṃ vītamalaṃ")
        self.assertEqual(extra3, [])

    def test_tesam_yeva_niggahita_sandhi_annotate(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        text, extra = apply_transforms(
            "pātimokkhaṃ tesaṃ yeva āsavaṭṭhānīyānaṃ",
            rules,
            page=10,
            order=35,
            segment_type="prose",
        )
        self.assertEqual(text, "pātimokkhaṃ tesaṃ yeva{{n0}} āsavaṭṭhānīyānaṃ")
        self.assertEqual(extra, ["tesaṃyeva niggahītasandhi – ม.พ.ป."])
        # Joined form already correct — no annotate.
        unchanged, extra2 = apply_transforms(
            "pātimokkhaṃ tesaṃyeva āsavaṭṭhānīyānaṃ",
            rules,
            page=10,
            order=35,
            segment_type="prose",
        )
        self.assertEqual(unchanged, "pātimokkhaṃ tesaṃyeva āsavaṭṭhānīyānaṃ")
        self.assertEqual(extra2, [])

    def test_vayamati_phassa_na_ca_locus_replace(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        sample = (
            "ubho ca naṃ bhikkhussa nissaggiyena nissaggiyaṃ āmasanti, "
            "sevanādhippāyo kāyena vāyamati phassaṃ paṭivijānāti"
        )
        text, extra = apply_transforms(
            sample,
            rules,
            page=183,
            order=1164,
            segment_type="prose",
            volume_id="01Vin01",
        )
        self.assertEqual(
            text,
            "ubho ca naṃ bhikkhussa nissaggiyena nissaggiyaṃ āmasanti, "
            "sevanādhippāyo kāyena vāyamati, na ca  phassaṃ paṭivijānāti",
        )
        self.assertEqual(extra, [])
        skipped, extra2 = apply_transforms(
            sample,
            rules,
            page=183,
            order=1161,
            segment_type="prose",
            volume_id="01Vin01",
        )
        self.assertEqual(skipped, sample)
        self.assertEqual(extra2, [])

    def test_anapatti_bhikkhu_samghadisesassa_locus_replace(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        sample = "Anāpatti saṃghādisesassa, āpatti thullaccayassāti. (6)"
        text, extra = apply_transforms(
            sample,
            rules,
            page=185,
            order=1182,
            segment_type="prose",
            volume_id="01Vin01",
        )
        self.assertEqual(
            text,
            "Anāpatti bhikkhu saṃghādisesassa, āpatti thullaccayassāti. (6)",
        )
        self.assertEqual(extra, [])
        skipped, extra2 = apply_transforms(
            sample,
            rules,
            page=185,
            order=1181,
            segment_type="prose",
            volume_id="01Vin01",
        )
        self.assertEqual(skipped, sample)
        self.assertEqual(extra2, [])

    def test_nacchinna_long_a_locus_replace(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        sample = 'bhikkhū ujjhāpenti “idaṃ bhante nacchinnaṃ nappatirūpaṃ sāmikenapi'
        text, extra = apply_transforms(
            sample,
            rules,
            page=187,
            order=1200,
            segment_type="prose_continuation",
            volume_id="01Vin01",
        )
        self.assertEqual(
            text,
            'bhikkhū ujjhāpenti “idaṃ bhante nacchannaṃ nappatirūpaṃ sāmikenapi',
        )
        self.assertEqual(extra, [])
        skipped, extra2 = apply_transforms(
            sample,
            rules,
            page=187,
            order=1199,
            segment_type="prose_continuation",
            volume_id="01Vin01",
        )
        self.assertEqual(skipped, sample)
        self.assertEqual(extra2, [])

    def test_tam_yeva_niggahita_sandhi_annotate(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        text, extra = apply_transforms(
            "Anujānāmi bhikkhave taṃ yeva upajjhaṃ tameva upasampadaṃ",
            rules,
            page=43,
            order=168,
            segment_type="prose",
        )
        self.assertEqual(
            text,
            "Anujānāmi bhikkhave taṃ yeva{{n0}} upajjhaṃ tameva upasampadaṃ",
        )
        self.assertEqual(extra, ["taṃyeva niggahītasandhi – ม.พ.ป."])
        joined, extra2 = apply_transforms(
            "taṃyeva vā purimaṃ rajjasukhaṃ",
            rules,
            page=340,
            order=332,
            segment_type="prose",
        )
        self.assertEqual(joined, "taṃyeva vā purimaṃ rajjasukhaṃ")
        self.assertEqual(extra2, [])
        # Longer accusative + yeva must not inherit the taṃ yeva lemma.
        embedded, extra3 = apply_transforms(
            "Bhagavantaṃ yeva āyasmanto santaṃ yeva passanti",
            rules,
            page=238,
            order=1002,
            segment_type="prose",
        )
        self.assertEqual(
            embedded, "Bhagavantaṃ yeva āyasmanto santaṃ yeva passanti"
        )
        self.assertEqual(extra3, [])

    def test_masam_yeva_niggahita_sandhi_annotate(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        text, extra = apply_transforms(
            "taṃ kumārikaṃ netvā māsaṃ yeva suṇisabhogena bhuñjiṃsu",
            rules,
            page=198,
            order=1295,
            segment_type="prose",
        )
        self.assertEqual(
            text,
            "taṃ kumārikaṃ netvā māsaṃ yeva{{n0}} suṇisabhogena bhuñjiṃsu",
        )
        self.assertEqual(extra, ["māsaṃyeva niggahītasandhi – ม.พ.ป."])
        unchanged, extra2 = apply_transforms(
            "taṃ kumārikaṃ netvā māsaṃyeva suṇisabhogena bhuñjiṃsu",
            rules,
            page=198,
            order=1295,
            segment_type="prose",
        )
        self.assertEqual(
            unchanged,
            "taṃ kumārikaṃ netvā māsaṃyeva suṇisabhogena bhuñjiṃsu",
        )
        self.assertEqual(extra2, [])

    def test_ayam_pi_niggahita_sandhi_annotate(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        text, extra = apply_transforms(
            "āmantesi “ayaṃ pi kho bhikkhave",
            rules,
            page=88,
            order=414,
            segment_type="prose",
        )
        self.assertEqual(text, "āmantesi “ayaṃ pi{{n0}} kho bhikkhave")
        self.assertEqual(extra, ["ayaṃpi niggahītasandhi – ม.พ.ป."])
        unchanged, extra2 = apply_transforms(
            "ayaṃpi dhammo sāraṇīyo",
            rules,
            page=88,
            order=414,
            segment_type="prose",
        )
        self.assertEqual(unchanged, "ayaṃpi dhammo sāraṇīyo")
        self.assertEqual(extra2, [])
        prefixed, extra3 = apply_transforms(
            "mayaṃ pi kho bhikkhu na jānāma",
            rules,
            page=1,
            order=1,
            segment_type="prose",
        )
        self.assertEqual(prefixed, "mayaṃ pi kho bhikkhu na jānāma")
        self.assertEqual(extra3, [])

    def test_token_match_skips_embedded_substring(self) -> None:
        rules = parse_transforms_document(
            {
                "schema_version": 2,
                "rules": [
                    _annotate_rule(
                        "tok",
                        match="taṃ yeva",
                        footnote="taṃyeva niggahītasandhi – ม.พ.ป.",
                    )
                ],
            },
            source="mem",
        )
        text, extra = apply_transforms(
            "taṃ yeva ca santaṃ yeva",
            rules,
            page=1,
            order=1,
            segment_type="prose",
        )
        self.assertEqual(text, "taṃ yeva{{n0}} ca santaṃ yeva")
        self.assertEqual(extra, ["taṃyeva niggahītasandhi – ม.พ.ป."])

    def test_athakho_dve_nipata_annotate(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        text, extra = apply_transforms(
            "Athakho bhagavā āyasmantaṃ",
            rules,
            page=12,
            order=39,
            segment_type="prose",
        )
        self.assertEqual(text, "Athakho{{n0}} bhagavā āyasmantaṃ")
        self.assertEqual(extra, ["atha kho dve nipātā – ม.พ.ป."])
        lower, extra_l = apply_transforms(
            "athakho bhagavā āyasmantaṃ",
            rules,
            page=12,
            order=39,
            segment_type="prose",
        )
        self.assertEqual(lower, "athakho{{n0}} bhagavā āyasmantaṃ")
        self.assertEqual(extra_l, ["atha kho dve nipātā – ม.พ.ป."])
        unchanged, extra2 = apply_transforms(
            "Atha kho bhagavā āyasmantaṃ",
            rules,
            page=12,
            order=39,
            segment_type="prose",
        )
        self.assertEqual(unchanged, "Atha kho bhagavā āyasmantaṃ")
        self.assertEqual(extra2, [])

    def test_nukho_dve_nipata_annotate(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        text, extra = apply_transforms(
            "“yo nukho āvuso Ānanda",
            rules,
            page=85,
            order=402,
            segment_type="prose_continuation",
        )
        self.assertEqual(text, "“yo nukho{{n0}} āvuso Ānanda")
        self.assertEqual(extra, ["nu kho dve nipātā – ม.พ.ป."])
        unchanged, extra2 = apply_transforms(
            "“ko nu kho bhante Ānanda",
            rules,
            page=84,
            order=401,
            segment_type="prose",
        )
        self.assertEqual(unchanged, "“ko nu kho bhante Ānanda")
        self.assertEqual(extra2, [])

    def test_athakhvetam_dve_pada_annotate(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        text, extra = apply_transforms(
            "bhiyyobhāvāya, athakhvetaṃ āvuso appasannānañceva",
            rules,
            page=26,
            order=80,
            segment_type="prose_continuation",
        )
        self.assertEqual(
            text, "bhiyyobhāvāya, athakhvetaṃ{{n0}} āvuso appasannānañceva"
        )
        self.assertEqual(extra, ["atha khvetaṃ dve padāni – ม.พ.ป."])
        capital, extra_c = apply_transforms(
            "bhiyyobhāvāya. Athakhvetaṃ āvuso appasannānañceva",
            rules,
            page=55,
            order=222,
            segment_type="prose",
        )
        self.assertEqual(
            capital,
            "bhiyyobhāvāya. Athakhvetaṃ{{n0}} āvuso appasannānañceva",
        )
        self.assertEqual(extra_c, ["atha khvetaṃ dve padāni – ม.พ.ป."])
        unchanged, extra2 = apply_transforms(
            "bhiyyobhāvāya, atha khvetaṃ moghapurisā appasannānañceva",
            rules,
            page=56,
            order=223,
            segment_type="prose_continuation",
        )
        self.assertEqual(
            unchanged,
            "bhiyyobhāvāya, atha khvetaṃ moghapurisā appasannānañceva",
        )
        self.assertEqual(extra2, [])

    def test_tassa_kukkuccam_dve_pada_annotate(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        text, extra = apply_transforms(
            "Tassakukkuccaṃ ahosi -pa-.",
            rules,
            page=44,
            order=172,
            segment_type="prose",
        )
        self.assertEqual(text, "Tassakukkuccaṃ{{n0}} ahosi -pa-.")
        self.assertEqual(extra, ["tassa kukkuccaṃ dve padāni – ม.พ.ป."])
        # Spaced form already correct on the same folio — no annotate.
        unchanged, extra2 = apply_transforms(
            "Tassa kukkuccaṃ ahosi -pa-.",
            rules,
            page=44,
            order=173,
            segment_type="prose",
        )
        self.assertEqual(unchanged, "Tassa kukkuccaṃ ahosi -pa-.")
        self.assertEqual(extra2, [])

    def test_tenahananda_dve_pada_annotate(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        text, extra = apply_transforms(
            "Tenahānanda yāvatikā bhikkhū",
            rules,
            page=88,
            order=413,
            segment_type="prose_continuation",
        )
        self.assertEqual(text, "Tenahānanda{{n0}} yāvatikā bhikkhū")
        self.assertEqual(extra, ["tena hānanda dve padāni – ม.พ.ป."])
        lower, extra_l = apply_transforms(
            "tenahānanda Subhaddaṃ pabbājehīti",
            rules,
            page=126,
            order=607,
            segment_type="prose",
        )
        self.assertEqual(lower, "tenahānanda{{n0}} Subhaddaṃ pabbājehīti")
        self.assertEqual(extra_l, ["tena hānanda dve padāni – ม.พ.ป."])
        unchanged, extra2 = apply_transforms(
            "Tena hānanda yāvatikā bhikkhū",
            rules,
            page=88,
            order=413,
            segment_type="prose_continuation",
        )
        self.assertEqual(unchanged, "Tena hānanda yāvatikā bhikkhū")
        self.assertEqual(extra2, [])

    def test_tenahi_dve_pada_annotate(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        text, extra = apply_transforms(
            "Tenahi bhagini aggadānaṃ dehīti",
            rules,
            page=196,
            order=1283,
            segment_type="prose",
        )
        self.assertEqual(text, "Tenahi{{n0}} bhagini aggadānaṃ dehīti")
        self.assertEqual(extra, ["tena hi dve padāni – ม.พ.ป."])
        lower, extra_l = apply_transforms(
            "āṇāpesi “tenahi bhaṇe ekamekaṃ dhenuṃ",
            rules,
            page=342,
            order=1643,
            segment_type="prose_continuation",
        )
        self.assertEqual(lower, "āṇāpesi “tenahi{{n0}} bhaṇe ekamekaṃ dhenuṃ")
        self.assertEqual(extra_l, ["tena hi dve padāni – ม.พ.ป."])
        unchanged, extra2 = apply_transforms(
            "Tena hi bhagini aggadānaṃ dehīti",
            rules,
            page=196,
            order=1283,
            segment_type="prose",
        )
        self.assertEqual(unchanged, "Tena hi bhagini aggadānaṃ dehīti")
        self.assertEqual(extra2, [])

    def test_apicaham_dve_pada_annotate(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        text, extra = apply_transforms(
            "karomi, apicāhaṃ yāvadatthaṃ bhuñjāmi",
            rules,
            page=152,
            order=837,
            segment_type="prose_continuation",
        )
        self.assertEqual(text, "karomi, apicāhaṃ{{n0}} yāvadatthaṃ bhuñjāmi")
        self.assertEqual(extra, ["api cāhaṃ dve padāni – ม.พ.ป."])
        capital, extra_c = apply_transforms(
            "Apicāhaṃ sīlarakkhāya,",
            rules,
            page=405,
            order=5691,
            segment_type="gatha",
        )
        self.assertEqual(capital, "Apicāhaṃ{{n0}} sīlarakkhāya,")
        self.assertEqual(extra_c, ["api cāhaṃ dve padāni – ม.พ.ป."])
        unchanged, extra2 = apply_transforms(
            "api cāhaṃ na byākāsiṃ",
            rules,
            page=145,
            order=799,
            segment_type="prose_continuation",
        )
        self.assertEqual(unchanged, "api cāhaṃ na byākāsiṃ")
        self.assertEqual(extra2, [])

    def test_tassa_kukkuccam_long_a_replace(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        text, extra = apply_transforms(
            "“assamaṇīsi tvan”ti. Tassa kukkuccaṃ ahosi -pa-.",
            rules,
            volume_id="01Vin01",
            page=84,
            order=400,
            segment_type="prose",
        )
        self.assertEqual(
            text, "“assamaṇīsi tvan”ti. Tassā kukkuccaṃ ahosi -pa-."
        )
        self.assertEqual(extra, [])
        unchanged, extra2 = apply_transforms(
            "Tassa kukkuccaṃ ahosi -pa-.",
            rules,
            volume_id="01Vin01",
            page=42,
            order=160,
            segment_type="prose",
        )
        self.assertEqual(unchanged, "Tassa kukkuccaṃ ahosi -pa-.")
        self.assertEqual(extra2, [])

    def test_kalamakasi_pa_duplicate_kukkucca_replace(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        wrong = (
            "So tatraṭṭhito bandhanto paripatitvā kālamakāsi. "
            "Tassa kukkuccaṃ ahosi -pa- paripatitvā na kālamakāsi. "
            "Tassa kukkuccaṃ ahosi -pa-."
        )
        text, extra = apply_transforms(
            wrong,
            rules,
            volume_id="01Vin01",
            page=104,
            order=515,
            segment_type="prose",
        )
        self.assertEqual(
            text,
            "So tatraṭṭhito bandhanto paripatitvā kālamakāsi -pa-. "
            "paripatitvā na kālamakāsi. Tassa kukkuccaṃ ahosi -pa-.",
        )
        self.assertEqual(extra, [])
        formula, extra2 = apply_transforms(
            "So papatitvā kālamakāsi. Tassa kukkuccaṃ ahosi -pa-. Kiṃcitto tvaṃ bhikkhūti.",
            rules,
            volume_id="01Vin01",
            page=101,
            order=496,
            segment_type="prose",
        )
        self.assertEqual(
            formula,
            "So papatitvā kālamakāsi. Tassa kukkuccaṃ ahosi -pa-. Kiṃcitto tvaṃ bhikkhūti.",
        )
        self.assertEqual(extra2, [])
        sibling, extra3 = apply_transforms(
            "paripatitvā kālamakāsi -pa- paripatitvā na kālamakāsi. "
            "Tassa kukkuccaṃ ahosi -pa-.",
            rules,
            volume_id="01Vin01",
            page=104,
            order=517,
            segment_type="prose",
        )
        self.assertEqual(
            sibling,
            "paripatitvā kālamakāsi -pa- paripatitvā na kālamakāsi. "
            "Tassa kukkuccaṃ ahosi -pa-.",
        )
        self.assertEqual(extra3, [])

    def test_civara_pindapata_join_01vin01_195(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        spaced = (
            "cīvara piṇḍapāta senāsana gilānappaccaya "
            "bhesajjaparikkhārena"
        )
        joined = "cīvarapiṇḍapātasenāsanagilānappaccayabhesajjaparikkhārena"
        text, extra = apply_transforms(
            f"Anāpatti “{spaced} upaṭṭhahā”ti bhaṇati",
            rules,
            volume_id="01Vin01",
            page=195,
            order=1279,
            segment_type="prose",
        )
        self.assertEqual(
            text, f"Anāpatti “{joined} upaṭṭhahā”ti bhaṇati"
        )
        self.assertEqual(extra, [])
        other, extra2 = apply_transforms(
            f"paccupaṭṭhitā {spaced}",
            rules,
            volume_id="16An02",
            page=323,
            order=2091,
            segment_type="prose",
        )
        self.assertEqual(other, f"paccupaṭṭhitā {spaced}")
        self.assertEqual(extra2, [])

    def test_cira_civara_patho_annotate(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        word = "cīrapiṇḍapātasenāsanagilānappaccayabhesajjaparikkhārā"
        text, extra = apply_transforms(
            f"tattha paṭibaddhā {word}.",
            rules,
            page=280,
            order=1854,
            segment_type="prose",
        )
        self.assertEqual(text, f"tattha paṭibaddhā {word}{{{{n0}}}}.")
        self.assertEqual(extra, ["cīra- pāṭho, cīvara- – ม.พ.ป."])
        unchanged, extra2 = apply_transforms(
            "cīvarapiṇḍapātasenāsanagilānappaccayabhesajjaparikkhārā",
            rules,
            page=280,
            order=1854,
            segment_type="prose",
        )
        self.assertEqual(
            unchanged,
            "cīvarapiṇḍapātasenāsanagilānappaccayabhesajjaparikkhārā",
        )
        self.assertEqual(extra2, [])

    def test_pibbhamissami_vibbhama_patho_annotate(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        text, extra = apply_transforms(
            "“assamaṇo ahaṃ bhante pibbhamissāmī”ti.",
            rules,
            page=86,
            order=406,
            segment_type="prose_continuation",
        )
        self.assertEqual(
            text, "“assamaṇo ahaṃ bhante pibbhamissāmī{{n0}}”ti."
        )
        self.assertEqual(
            extra, ["pibbhamissāmīti pāṭho, vibbhamissāmīti – ม.พ.ป."]
        )
        unchanged, extra2 = apply_transforms(
            "“assamaṇo ahaṃ vibbhamissāmī”ti",
            rules,
            page=49,
            order=199,
            segment_type="prose",
        )
        self.assertEqual(unchanged, "“assamaṇo ahaṃ vibbhamissāmī”ti")
        self.assertEqual(extra2, [])

    def test_labhimhiti_patho_annotate(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        text, extra = apply_transforms(
            "pañcahākārehi paṭhamassa jhānassa lābhimhiti sampajānamusā",
            rules,
            page=122,
            order=639,
            segment_type="prose",
        )
        self.assertEqual(
            text,
            "pañcahākārehi paṭhamassa jhānassa lābhimhiti{{n0}} sampajānamusā",
        )
        self.assertEqual(extra, ["lābhimhīti – ม.พ.ป."])
        unchanged, extra2 = apply_transforms(
            "tīhākārehi paṭhamassa jhānassa lābhimhīti sampajānamusā",
            rules,
            page=121,
            order=637,
            segment_type="prose",
        )
        self.assertEqual(
            unchanged,
            "tīhākārehi paṭhamassa jhānassa lābhimhīti sampajānamusā",
        )
        self.assertEqual(extra2, [])

    def test_sacchikata_maggo_replace_only_locus(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        text, extra = apply_transforms(
            "Ariyo aṭṭhaṅgiko maggo sacchikatā mayāti",
            rules,
            page=125,
            order=662,
            segment_type="prose",
            volume_id="01Vin01",
        )
        self.assertEqual(text, "Ariyo aṭṭhaṅgiko maggo sacchikato mayāti")
        self.assertEqual(extra, [])
        unchanged, extra2 = apply_transforms(
            "Satta bojjhaṅgā sacchikatā mayāti",
            rules,
            page=124,
            order=661,
            segment_type="prose",
            volume_id="01Vin01",
        )
        self.assertEqual(unchanged, "Satta bojjhaṅgā sacchikatā mayāti")
        self.assertEqual(extra2, [])
        reverted, extra3 = apply_transforms(
            "Appaṇihitā samāpatti sacchikatā mayāti",
            rules,
            page=124,
            order=657,
            segment_type="prose",
            volume_id="01Vin01",
        )
        self.assertEqual(reverted, "Appaṇihitā samāpatti sacchikatā mayāti")
        self.assertEqual(extra3, [])

    def test_samepajjim_samapajjim_long_a_replace(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        text, extra = apply_transforms(
            "Anāgāmiphalaṃ. Arahattaṃ samepajjiṃ. Samāpajjāmi.",
            rules,
            page=125,
            order=663,
            segment_type="prose",
            volume_id="01Vin01",
        )
        self.assertEqual(text, "Anāgāmiphalaṃ. Arahattaṃ samāpajjiṃ. Samāpajjāmi.")
        self.assertEqual(extra, [])
        unchanged, extra2 = apply_transforms(
            "aññataraṃ samādhiṃ samāpajjitvā.",
            rules,
            page=123,
            order=1309,
            segment_type="prose",
            volume_id="18Khu01",
        )
        self.assertEqual(unchanged, "aññataraṃ samādhiṃ samāpajjitvā.")
        self.assertEqual(extra2, [])

    def test_samepajji_samapajji_long_a_replace(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        text, extra = apply_transforms(
            "Tena kho pana samayena aññataro bhikkhu dārudhītalikāya kāyasaṃsaggaṃ samepajji. "
            "Tassa kukkuccaṃ ahosi -pa-. Anāpatti bhikkhu saṃghādisesassa, āpatti dukkaṭassāti. (10)",
            rules,
            page=185,
            order=1186,
            segment_type="prose",
            volume_id="01Vin01",
        )
        self.assertIn("kāyasaṃsaggaṃ samāpajji.", text)
        self.assertNotIn("samepajji", text)
        self.assertEqual(extra, [])

    def test_tihakarehi_long_a_replace(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        text, extra = apply_transforms(
            "Tīhākarehi suññataṃ samādhiṃ.",
            rules,
            page=124,
            order=656,
            segment_type="prose",
            volume_id="01Vin01",
        )
        self.assertEqual(text, "Tīhākārehi suññataṃ samādhiṃ.")
        self.assertEqual(extra, [])
        unchanged, extra2 = apply_transforms(
            "Tīhākārehi suññataṃ vimokkhaṃ.",
            rules,
            page=124,
            order=655,
            segment_type="prose",
            volume_id="01Vin01",
        )
        self.assertEqual(unchanged, "Tīhākārehi suññataṃ vimokkhaṃ.")
        self.assertEqual(extra2, [])

    def test_gacchantim_acc_replace_only_loci(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        text, extra = apply_transforms(
            "addasaṃ maṃsapiṇḍaṃ vehāsaṃ gacchantiṃ. Tamenaṃ",
            rules,
            page=145,
            order=801,
            segment_type="prose",
            volume_id="01Vin01",
        )
        self.assertEqual(text, "addasaṃ maṃsapiṇḍaṃ vehāsaṃ gacchantaṃ. Tamenaṃ")
        self.assertEqual(extra, [])
        second, extra2 = apply_transforms(
            "addasaṃ nicchaviṃ purisaṃ vehāsaṃ gacchantiṃ. Tamenaṃ",
            rules,
            page=145,
            order=802,
            segment_type="prose",
            volume_id="01Vin01",
        )
        self.assertEqual(
            second, "addasaṃ nicchaviṃ purisaṃ vehāsaṃ gacchantaṃ. Tamenaṃ"
        )
        self.assertEqual(extra2, [])
        feminine_pesi, extra3 = apply_transforms(
            "addasaṃ maṃsapesiṃ vehāsaṃ gacchantiṃ, tamenaṃ",
            rules,
            page=145,
            order=800,
            segment_type="prose",
            volume_id="01Vin01",
        )
        self.assertEqual(
            feminine_pesi, "addasaṃ maṃsapesiṃ vehāsaṃ gacchantiṃ, tamenaṃ"
        )
        self.assertEqual(extra3, [])
        feminine_itthi, extra4 = apply_transforms(
            "addasaṃ nicchaviṃ itthiṃ vehāsaṃ gacchantiṃ. Tamenaṃ",
            rules,
            page=147,
            order=813,
            segment_type="prose",
            volume_id="01Vin01",
        )
        self.assertEqual(
            feminine_itthi, "addasaṃ nicchaviṃ itthiṃ vehāsaṃ gacchantiṃ. Tamenaṃ"
        )
        self.assertEqual(extra4, [])

    def test_na_sambahula_comma_replace_only_locus(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        snippet = (
            "abbheti, na sambahulā na ekapuggalo, tena vuccati “saṃghādiseso”ti."
        )
        text, extra = apply_transforms(
            snippet,
            rules,
            page=153,
            order=848,
            segment_type="prose",
            volume_id="01Vin01",
        )
        self.assertEqual(
            text,
            "abbheti, na sambahulā, na ekapuggalo, tena vuccati “saṃghādiseso”ti.",
        )
        self.assertEqual(extra, [])
        skip_p283, extra2 = apply_transforms(
            snippet,
            rules,
            page=283,
            order=1872,
            segment_type="prose",
            volume_id="01Vin01",
        )
        self.assertEqual(skip_p283, snippet)
        self.assertEqual(extra2, [])

    def test_kasmim_kismim_replace_only_locus(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        snippet = "kassa vā’ti, kasmiṃ viya kumārikāya vatthuṃ, sace"
        text, extra = apply_transforms(
            snippet,
            rules,
            page=197,
            order=1292,
            segment_type="prose",
            volume_id="01Vin01",
        )
        self.assertEqual(text, "kassa vā’ti, kismiṃ viya kumārikāya vatthuṃ, sace")
        self.assertEqual(extra, [])
        other_page, extra2 = apply_transforms(
            snippet,
            rules,
            page=186,
            order=2016,
            segment_type="gatha",
            volume_id="19Khu02",
        )
        self.assertEqual(other_page, snippet)
        self.assertEqual(extra2, [])
        gatha, extra3 = apply_transforms(
            "Kasmiṃ padese samaṇaṃ vasantaṃ,",
            rules,
            page=186,
            order=2016,
            segment_type="gatha",
            volume_id="19Khu02",
        )
        self.assertEqual(gatha, "Kasmiṃ padese samaṇaṃ vasantaṃ,")
        self.assertEqual(extra3, [])

    def test_cakkabhedaya_ti_drop_quote_only_locus(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        snippet = (
            "Devadatto saṃghabhedāya parakkamissati cakkabhedāyā”ti. "
            "Atha kho te bhikkhū Devadattaṃ anekapariyāyena vigarahitvā "
            "Bhagavato etamatthaṃ ārocesuṃ -pa- “saccaṃ kira tvaṃ Devadatta "
            "saṃghabhedāya parakkamasi cakkabhedāyā”ti."
        )
        text, extra = apply_transforms(
            snippet,
            rules,
            page=265,
            order=1757,
            segment_type="prose_continuation",
            volume_id="01Vin01",
        )
        self.assertEqual(
            text,
            "Devadatto saṃghabhedāya parakkamissati cakkabhedāyāti. "
            "Atha kho te bhikkhū Devadattaṃ anekapariyāyena vigarahitvā "
            "Bhagavato etamatthaṃ ārocesuṃ -pa- “saccaṃ kira tvaṃ Devadatta "
            "saṃghabhedāya parakkamasi cakkabhedāyāti.",
        )
        self.assertEqual(extra, [])
        skip_p264, extra2 = apply_transforms(
            "Devadatto Bhagavato saṃghabhedāya parakkamissati cakkabhedāyā”ti.",
            rules,
            page=264,
            order=1756,
            segment_type="prose",
            volume_id="01Vin01",
        )
        self.assertEqual(
            skip_p264,
            "Devadatto Bhagavato saṃghabhedāya parakkamissati cakkabhedāyā”ti.",
        )
        self.assertEqual(extra2, [])

    def test_yakaci_space_replace_spares_sya_note(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        lower, extra = apply_transforms(
            "Gahapatānī nāma yākāci agāraṃ ajjhāvasati.",
            rules,
            page=314,
            order=2085,
            segment_type="prose",
            volume_id="01Vin01",
        )
        self.assertEqual(lower, "Gahapatānī nāma yā kāci agāraṃ ajjhāvasati.")
        self.assertEqual(extra, [])
        capital, extra_c = apply_transforms(
            "Yā kāci vedanā. Yākāci saññā. Ye keci saṅkhārā.",
            rules,
            page=73,
            order=463,
            segment_type="prose",
            volume_id="13Sam02",
        )
        self.assertEqual(
            capital, "Yā kāci vedanā. Yā kāci saññā. Ye keci saṅkhārā."
        )
        self.assertEqual(extra_c, [])
        sya, extra_s = apply_transforms(
            "Yākāci (Syā)",
            rules,
            page=420,
            order=2243,
            segment_type="prose",
            volume_id="04Vin04",
        )
        self.assertEqual(sya, "Yākāci (Syā)")
        self.assertEqual(extra_s, [])

    def test_mattham_matta_replace_only_locus(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        text, extra = apply_transforms(
            "kathaṃ hi nāma chabbaggiyā bhikkhū na matthaṃ jānitvā bahuṃ cīvaraṃ",
            rules,
            page=316,
            order=2099,
            segment_type="prose_continuation",
            volume_id="01Vin01",
        )
        self.assertEqual(
            text,
            "kathaṃ hi nāma chabbaggiyā bhikkhū na mattaṃ jānitvā bahuṃ cīvaraṃ",
        )
        self.assertEqual(extra, [])
        verse, extra2 = apply_transforms(
            "Kiṃ kicca'matthaṃ idhamatthi tuyhaṃ,",
            rules,
            page=199,
            order=2663,
            segment_type="gatha",
            volume_id="22Khu05",
        )
        self.assertEqual(verse, "Kiṃ kicca'matthaṃ idhamatthi tuyhaṃ,")
        self.assertEqual(extra2, [])

    def test_ayasmanam_ayasmantam_replace(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        text, extra = apply_transforms(
            "upasaṅkamitvā āyasmanaṃ Pilindavacchaṃ abhivādetvā",
            rules,
            page=362,
            order=2419,
            segment_type="prose",
            volume_id="01Vin01",
        )
        self.assertEqual(
            text, "upasaṅkamitvā āyasmantaṃ Pilindavacchaṃ abhivādetvā"
        )
        self.assertEqual(extra, [])
        self.assertNotIn("āyasmanti", text)

    def test_icchamano_short_a_replace_preserves_capital(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        lower, extra = apply_transforms(
            "Ākaṅkhamānoti icchāmāno.",
            rules,
            page=378,
            order=2523,
            segment_type="prose",
            volume_id="01Vin01",
        )
        self.assertEqual(lower, "Ākaṅkhamānoti icchamāno.")
        self.assertEqual(extra, [])
        capital, extra_c = apply_transforms(
            "Icchāmāno cahaṃ ajja,",
            rules,
            page=77,
            order=1117,
            segment_type="gatha",
            volume_id="21Khu04",
        )
        self.assertEqual(capital, "Icchamāno cahaṃ ajja,")
        self.assertEqual(extra_c, [])


class TransformIndexTests(unittest.TestCase):
    def test_compile_buckets_runs_phrases_and_affixes(self) -> None:
        rules = parse_transforms_document(
            {
                "schema_version": 2,
                "rules": [
                    _replace_rule(
                        "run",
                        match="bandhiṃ",
                        replacement="bandhaṃ",
                    ),
                    _annotate_rule(
                        "phrase",
                        match="taṃ yeva",
                        footnote="n",
                    ),
                    _replace_rule(
                        "sub",
                        match="+aa",
                        replacement="AA",
                    ),
                    _replace_rule(
                        "off",
                        match="skipme",
                        replacement="x",
                        enabled=False,
                    ),
                ],
            },
            source="mem",
        )
        program = compile_transforms(rules)
        self.assertIn("bandhiṃ", program.by_run)
        self.assertIn("taṃ", program.by_first_run)
        self.assertEqual(len(program.other), 1)
        self.assertEqual(program.other[0].rule.id, "sub")
        self.assertNotIn("skipme", program.by_run)

    def test_chain_replace_uses_later_rule(self) -> None:
        rules = parse_transforms_document(
            {
                "schema_version": 2,
                "rules": [
                    _replace_rule(
                        "a", match="foo", replacement="bar"
                    ),
                    _replace_rule(
                        "b", match="bar", replacement="baz"
                    ),
                ],
            },
            source="mem",
        )
        text, extra = apply_transforms(
            "foo here",
            rules,
            page=1,
            order=1,
            segment_type="prose",
        )
        self.assertEqual(text, "baz here")
        self.assertEqual(extra, [])

    def test_index_matches_linear(self) -> None:
        rules = parse_transforms_document(
            {
                "schema_version": 2,
                "rules": [
                    _replace_rule(
                        "a", match="foo", replacement="bar"
                    ),
                    _replace_rule(
                        "b", match="bar", replacement="baz"
                    ),
                    _replace_rule(
                        "c", match="+aa", replacement="AA"
                    ),
                    _replace_rule(
                        "d",
                        match="taṃ yeva",
                        replacement="taṃyeva",
                    ),
                    _replace_rule(
                        "e",
                        match="pin",
                        replacement="PIN",
                        loci=[{"volume": "01Vin01", "page": 3}],
                    ),
                    _annotate_rule(
                        "f",
                        match="Athakho",
                        footnote="note",
                    ),
                ],
            },
            source="mem",
        )
        samples = [
            "foo x",
            "bar x",
            "xaa y",
            "taṃ yeva santaṃ yeva",
            "pin here",
            "Athakho āha",
            "athakho āha",
            "nothing matches zzq",
            "foo taṃ yeva pin Athakho",
        ]
        for sample in samples:
            for page in (1, 3):
                indexed, extra_i = apply_transforms(
                    sample,
                    rules,
                    page=page,
                    order=1,
                    segment_type="prose",
                )
                linear, extra_l = _apply_transforms_linear(
                    sample,
                    rules,
                    page=page,
                    order=1,
                    segment_type="prose",
                )
                self.assertEqual(indexed, linear, f"{sample!r} page={page}")
                self.assertEqual(extra_i, extra_l, f"{sample!r} page={page}")

    def test_phrase_among_distractors(self) -> None:
        distractors = [
            _replace_rule(
                f"miss-{i}",
                match=f"zzq{i:05d}xyz",
                replacement="x",
            )
            for i in range(10_000)
        ]
        rules = parse_transforms_document(
            {
                "schema_version": 2,
                "rules": [
                    _annotate_rule(
                        "tesam",
                        match="taṃ yeva",
                        footnote="taṃyeva niggahītasandhi – ม.พ.ป.",
                    ),
                    *distractors,
                ],
            },
            source="mem",
        )
        program = compile_transforms(rules)
        text, extra = apply_transforms(
            "taṃ yeva dhammaṃ",
            program,
            page=1,
            order=1,
            segment_type="prose",
        )
        self.assertEqual(text, "taṃ yeva{{n0}} dhammaṃ")
        self.assertEqual(extra, ["taṃyeva niggahītasandhi – ม.พ.ป."])
        unchanged, extra2 = apply_transforms(
            "santaṃ yeva dhammaṃ",
            program,
            page=1,
            order=1,
            segment_type="prose",
        )
        self.assertEqual(unchanged, "santaṃ yeva dhammaṃ")
        self.assertEqual(extra2, [])

    def test_scale_10000_miss_rules_under_one_second(self) -> None:
        n_rules = 10_000
        n_texts = 3_000
        rules = parse_transforms_document(
            {
                "schema_version": 2,
                "rules": [
                    _replace_rule(
                        f"miss-{i}",
                        match=f"zzq{i:05d}xyz",
                        replacement="x",
                    )
                    for i in range(n_rules)
                ],
            },
            source="mem",
        )
        program = compile_transforms(rules)
        texts = [
            f"evam me sutaṃ ekaṃ samayaṃ bhagavā sāvatthiyaṃ {i} viharati."
            for i in range(n_texts)
        ]
        t0 = time.perf_counter()
        for sample in texts:
            apply_transforms(
                sample,
                program,
                page=1,
                order=1,
                segment_type="prose",
            )
        elapsed = time.perf_counter() - t0
        self.assertLess(
            elapsed,
            1.0,
            f"indexed apply of {n_rules} rules × {n_texts} texts "
            f"took {elapsed:.3f}s",
        )


if __name__ == "__main__":
    unittest.main()
