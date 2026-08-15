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
    parse_transforms_document,
    select_rules_for_volume,
)
from generate_cs_roman_tex import build_body, generate, note_to_thai, tex_numbered_footnote  # noqa: E402


def _replace_rule(
    rule_id: str = "fix",
    *,
    match: str = "Bhagavaa",
    replacement: str = "Bhagavā",
    pages: list[int] | None = None,
    orders: list[int] | None = None,
    volumes: list[str] | None = None,
    segment_types: list[str] | None = None,
    enabled: bool = True,
    remark: str | None = None,
    soft_breaks: list[str] | None = None,
    token: bool = False,
) -> dict:
    when: dict = {"match": match}
    if pages is not None:
        when["pages"] = pages
    if orders is not None:
        when["orders"] = orders
    if volumes is not None:
        when["volumes"] = volumes
    if segment_types is not None:
        when["segment_types"] = segment_types
    if token:
        when["token"] = True
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
    token: bool = False,
) -> dict:
    when: dict = {"match": match}
    if pages is not None:
        when["pages"] = pages
    if orders is not None:
        when["orders"] = orders
    if segment_types is not None:
        when["segment_types"] = segment_types
    if token:
        when["token"] = True
    ann: dict = {"footnote": footnote}
    if soft_breaks is not None:
        ann["soft_breaks"] = soft_breaks
    return {
        "id": rule_id,
        "enabled": enabled,
        "when": when,
        "do": {"annotate": ann},
    }


def _unbold_rule(
    rule_id: str = "unbold",
    *,
    match: str = "”ti",
    skip: int = 1,
    token: bool = False,
    remark: str | None = None,
    enabled: bool = True,
) -> dict:
    when: dict = {"match": match, "token": token}
    spec: dict = {"skip": skip}
    if remark is not None:
        spec["remark"] = remark
    return {
        "id": rule_id,
        "enabled": enabled,
        "when": when,
        "do": {"unbold": spec},
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

    def test_parses_volume_filter(self) -> None:
        rules = parse_transforms_document(
            {
                "schema_version": 2,
                "rules": [
                    _replace_rule(
                        "pin",
                        match="bandhiṃ",
                        replacement="bandhaṃ",
                        volumes=["01Vin01"],
                        pages=[79],
                        token=True,
                    )
                ],
            },
            source="mem",
        )
        self.assertEqual(rules[0].volumes, frozenset({"01Vin01"}))
        kept = select_rules_for_volume(rules, "01Vin01")
        dropped = select_rules_for_volume(rules, "02Vin02")
        self.assertEqual([r.id for r in kept], ["pin"])
        self.assertEqual(dropped, [])

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
        self.assertFalse(rules[0].token)


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
                    _unbold_rule("iti", match="”ti", skip=1),
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
        self.assertIn(tex_numbered_footnote(note_to_thai("existing note")), body)
        self.assertIn(
            tex_numbered_footnote(note_to_thai("cīra- pāṭho, cīvara-")),
            body,
        )
        # Soft breaks from the annotate rule should appear (edition form not in DPD).
        self.assertIn(r"\-", body)

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
    def test_shared_catalog_rules_set_token(self) -> None:
        missing = [
            r.id
            for r in load_transforms_file(SHARED_TRANSFORMS_PATH)
            if not r.token and r.action != "unbold"
        ]
        self.assertEqual(missing, [])
        unbold = [
            r
            for r in load_transforms_file(SHARED_TRANSFORMS_PATH)
            if r.action == "unbold"
        ]
        self.assertTrue(unbold)
        self.assertTrue(all(not r.token for r in unbold))

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
        peeled = apply_unbold_to_runs(
            text,
            runs,
            rules,
            page=56,
            order=224,
            segment_type="prose",
            volume_id="01Vin01",
        )
        self.assertEqual(
            peeled,
            [
                {"value": "ayampi pārājiko hoti asaṃvāso”", "bold": True},
                {"value": "ti.", "bold": False},
            ],
        )
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
        other_page = [
            {"value": "asaṃvāso”ti", "bold": True},
            {"value": ".", "bold": False},
        ]
        self.assertIs(
            apply_unbold_to_runs(
                "asaṃvāso”ti.",
                other_page,
                rules,
                page=57,
                order=224,
                segment_type="prose",
                volume_id="01Vin01",
            ),
            other_page,
        )

    def test_quote_iti_unbold_skips_thenositi_inside_quote(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        text = "corosi bālosi mūḷhosi thenosīti, tathārūpaṃ”ti."
        runs = [
            {"value": "corosi bālosi mūḷhosi thenosīti, tathārūpaṃ”", "bold": True},
            {"value": "ti.", "bold": False},
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
        self.assertIs(peeled, runs)
        bold = "".join(r["value"] for r in peeled if r.get("bold"))
        self.assertIn("thenosīti", bold)

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
        # token: longer forms on the same page must not be rewritten.
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

    def test_haneyyum_vati_space_replace(self) -> None:
        rules = load_transforms_file(SHARED_TRANSFORMS_PATH)
        cases = (
            ("Haneyyuṃvāti hatthena", "Haneyyuṃ vāti hatthena"),
            ("Bandheyyuṃvāti rajju", "Bandheyyuṃ vāti rajju"),
            ("Pabbājeyyuṃvāti gāmā", "Pabbājeyyuṃ vāti gāmā"),
        )
        for src, expected in cases:
            with self.subTest(src=src):
                text, extra = apply_transforms(
                    src, rules, page=57, order=235, segment_type="prose"
                )
                self.assertEqual(text, expected)
                self.assertEqual(extra, [])
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

    def test_token_match_skips_embedded_substring(self) -> None:
        rules = parse_transforms_document(
            {
                "schema_version": 2,
                "rules": [
                    _annotate_rule(
                        "tok",
                        match="taṃ yeva",
                        footnote="taṃyeva niggahītasandhi – ม.พ.ป.",
                        token=True,
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


class TransformIndexTests(unittest.TestCase):
    def test_compile_buckets_token_runs_and_phrases(self) -> None:
        rules = parse_transforms_document(
            {
                "schema_version": 2,
                "rules": [
                    _replace_rule(
                        "run",
                        match="bandhiṃ",
                        replacement="bandhaṃ",
                        token=True,
                    ),
                    _annotate_rule(
                        "phrase",
                        match="taṃ yeva",
                        footnote="n",
                        token=True,
                    ),
                    _replace_rule(
                        "sub",
                        match="aa",
                        replacement="AA",
                        token=False,
                    ),
                    _replace_rule(
                        "off",
                        match="skipme",
                        replacement="x",
                        token=True,
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
                        "a", match="foo", replacement="bar", token=True
                    ),
                    _replace_rule(
                        "b", match="bar", replacement="baz", token=True
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
                        "a", match="foo", replacement="bar", token=True
                    ),
                    _replace_rule(
                        "b", match="bar", replacement="baz", token=True
                    ),
                    _replace_rule(
                        "c", match="aa", replacement="AA", token=False
                    ),
                    _replace_rule(
                        "d",
                        match="taṃ yeva",
                        replacement="taṃyeva",
                        token=True,
                    ),
                    _replace_rule(
                        "e",
                        match="pin",
                        replacement="PIN",
                        pages=[3],
                        token=True,
                    ),
                    _annotate_rule(
                        "f",
                        match="Athakho",
                        footnote="note",
                        token=True,
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
                token=True,
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
                        token=True,
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
                        token=True,
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
