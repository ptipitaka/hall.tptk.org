"""Unit tests for cs-roman text helpers (pot-ma-gyi → ordinary stop)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from cs_roman_text import (  # noqa: E402
    SP1_MARKER,
    SP3_MARKER,
    SP_MARKER,
    EN_DASH,
    HORIZONTAL_LINE_EXTENSION,
    classify_section_closer,
    classify_section_closer_tier,
    closer_tier,
    demigrate_sp_markers,
    ensure_ordinal_closer_section_rule,
    ensure_script_text,
    is_bare_category_closer_label,
    is_expansion_parenthetical,
    is_ordinal_section_closer,
    is_section_closer_formula,
    is_section_nama_colophon,
    is_tassuddana_label,
    join_two_line_category_closer,
    needs_solid_midword_hyphen_strip,
    needs_spacing_normalize,
    normalize_pot_ma_gyi,
    normalize_printable_dashes,
    peel_trailing_expansion_parenthetical,
    peel_trailing_section_closer,
    prepare_roman_body,
    remap_runs_through_edit,
    roman_to_thai,
    script_text_entries,
    strip_sentence_spacers,
    strip_solid_midword_hyphens,
    text_field_has_bold_runs,
    thai_digits_to_arabic,
    uses_sentence_spacer,
)

_SP1 = SP1_MARKER
_STOP = ". "  # ordinary / Thai pot-ma-gyi sentence stop (no spacer marker)


class PotMaGyiNormalizeTests(unittest.TestCase):
    def test_maps_dot_space_dot_to_ordinary_stop(self) -> None:
        self.assertEqual(
            normalize_pot_ma_gyi("āpatti pārājikassa. . Anodissa"),
            f"āpatti pārājikassa{_STOP}Anodissa",
        )

    def test_ordinary_stop_unchanged_no_marker(self) -> None:
        self.assertEqual(
            normalize_pot_ma_gyi("hoti. So bhikkhu."),
            "hoti. So bhikkhu.",
        )

    def test_digit_ref_unchanged(self) -> None:
        self.assertEqual(
            normalize_pot_ma_gyi("ที 1. 46, 109"),
            "ที 1. 46, 109",
        )

    def test_requires_exactly_one_space_for_pot_ma_gyi(self) -> None:
        # Two spaces: not pot-ma-gyi; leave as-is (no marker inject).
        self.assertEqual(normalize_pot_ma_gyi("a.  . b"), "a.  . b")
        self.assertEqual(normalize_pot_ma_gyi("a..b"), "a..b")

    def test_multiple_occurrences(self) -> None:
        src = "mukhe. . Manussa. mukhe. . Paṇḍaka."
        out = normalize_pot_ma_gyi(src)
        self.assertNotIn(SP1_MARKER, out)
        self.assertNotIn(". .", out)
        self.assertIn(f"Manussa{_STOP}mukhe.", out)

    def test_collapses_legacy_double_sp1_pot_ma_gyi(self) -> None:
        self.assertEqual(
            normalize_pot_ma_gyi(f"pārājikassa.{_SP1}{_SP1}Anodissa"),
            f"pārājikassa{_STOP}Anodissa",
        )

    def test_inserts_space_after_glued_stop_sp1(self) -> None:
        self.assertEqual(
            normalize_pot_ma_gyi(f"pārājikassa.{_SP1}Anodissa"),
            f"pārājikassa{_STOP}Anodissa",
        )

    def test_repairs_glued_sp1_missing_stop(self) -> None:
        self.assertEqual(
            normalize_pot_ma_gyi(f"pārājikassa{_SP1}Anodissa"),
            f"pārājikassa{_STOP}Anodissa",
        )

    def test_strips_legacy_ordinary_stop_sp1(self) -> None:
        src = f"hoti{_STOP.rstrip()}{_SP1} So bhikkhu."
        # ``hoti.{{sp1}} So`` → ``hoti. So``
        self.assertEqual(
            normalize_pot_ma_gyi(f"hoti.{_SP1} So bhikkhu."),
            "hoti. So bhikkhu.",
        )
        self.assertEqual(normalize_pot_ma_gyi(src), "hoti. So bhikkhu.")


class DemigrateSpTests(unittest.TestCase):
    def test_double_sp_to_pot_ma_gyi(self) -> None:
        self.assertEqual(
            demigrate_sp_markers(f"a{SP_MARKER}{SP_MARKER}B"),
            "a. . B",
        )

    def test_legacy_sp3_to_sp1(self) -> None:
        self.assertEqual(
            demigrate_sp_markers(f"a.{SP3_MARKER}B"),
            f"a.{SP1_MARKER}B",
        )


class PeyyalaTests(unittest.TestCase):
    def test_pa_to_thai(self) -> None:
        thai = roman_to_thai("Dutiyampi kho -pa-. Tatiyampi")
        self.assertIn("ฯเปฯ", thai)
        self.assertIn("ฯเปฯ.", thai)
        self.assertNotIn("-pa-", thai.lower())

    def test_pa_mid_sentence(self) -> None:
        thai = roman_to_thai("sarāgāya -pa- kāmapariḷāhānaṃ")
        self.assertIn("ฯเปฯ", thai)
        self.assertNotIn("ฯเปฯ.", thai)


class ArabicDigitTests(unittest.TestCase):
    def test_roman_to_thai_keeps_arabic_digits(self) -> None:
        thai = roman_to_thai(
            "1. Cīvaravagga 4. Purāṇacīvarasikkhāpada",
            normalize_spacing=False,
        )
        self.assertIn("1. จีวรวคฺค 4.", thai)
        self.assertNotRegex(thai, r"[๐-๙]")

    def test_thai_digits_to_arabic(self) -> None:
        self.assertEqual(thai_digits_to_arabic("(๕-๑๑)"), "(5-11)")
        self.assertEqual(thai_digits_to_arabic("no digits"), "no digits")


class ScriptTextEntriesTests(unittest.TestCase):
    def test_entries_normalize_and_drop_spacer_markers(self) -> None:
        entries, had_rule = script_text_entries(
            "Marati, āpatti pārājikassa. . Anodissa opātaṃ."
        )
        self.assertFalse(had_rule)
        roman = next(e["value"] for e in entries if e["script"] == "roman")
        thai = next(e["value"] for e in entries if e["script"] == "thai")
        self.assertEqual(roman, f"Marati, āpatti pārājikassa{_STOP}Anodissa opātaṃ.")
        self.assertNotIn(". .", roman)
        self.assertNotIn(SP1_MARKER, roman)
        self.assertNotIn(SP1_MARKER, thai)
        self.assertIn("ปาราชิกสฺส.", thai)
        self.assertIn("อโนทิสฺส", thai)

    def test_roman_to_thai_strips_legacy_sp1(self) -> None:
        thai = roman_to_thai(f"pārājikassa.{_SP1} Anodissa")
        self.assertNotIn(SP1_MARKER, thai)
        self.assertTrue(thai.startswith("ปาราชิกสฺส."))
        self.assertIn(" อโนทิสฺส", thai)

    def test_roman_to_thai_can_skip_sentence_stop_normalize(self) -> None:
        """Footnote path: abbreviation-heavy notes must not gain spacers."""
        src = "Imāni vatthūni Saṃ 1. 446 piṭṭhādīsupi āgatāni. So hoti."
        thai = roman_to_thai(src, normalize_spacing=False)
        self.assertNotIn(SP1_MARKER, thai)
        body = roman_to_thai(src)
        self.assertNotIn(SP1_MARKER, body)
        self.assertIn("โส", body)

    def test_ensure_rebuilds_when_legacy_dot_space_dot(self) -> None:
        legacy = [
            {
                "script": "roman",
                "value": "pārājikassa. . Anodissa",
            },
            {
                "script": "thai",
                "value": "ปาราชิกสฺส. . อโนทิสฺส",
            },
        ]
        entries, _, lost = ensure_script_text(legacy)
        self.assertFalse(lost)
        roman = next(e["value"] for e in entries if e["script"] == "roman")
        thai = next(e["value"] for e in entries if e["script"] == "thai")
        self.assertEqual(roman, f"pārājikassa{_STOP}Anodissa")
        self.assertNotIn(SP1_MARKER, thai)
        self.assertNotIn(". .", thai)

    def test_ensure_leaves_ordinary_stop_without_marker(self) -> None:
        legacy = [
            {"script": "roman", "value": "hoti. So bhikkhu."},
            {"script": "thai", "value": "โหติ. โส ภิกฺขุ."},
        ]
        self.assertFalse(needs_spacing_normalize(legacy[0]["value"]))
        entries, _, lost = ensure_script_text(legacy)
        self.assertFalse(lost)
        roman = next(e["value"] for e in entries if e["script"] == "roman")
        self.assertEqual(roman, "hoti. So bhikkhu.")

    def test_ensure_rebuilds_legacy_sp3(self) -> None:
        legacy = [
            {"script": "roman", "value": f"pārājikassa.{SP3_MARKER}Anodissa"},
            {"script": "thai", "value": f"ปาราชิกสฺส.{SP3_MARKER}อโนทิสฺส"},
        ]
        entries, _, lost = ensure_script_text(legacy)
        self.assertFalse(lost)
        roman = next(e["value"] for e in entries if e["script"] == "roman")
        self.assertNotIn(SP3_MARKER, roman)
        self.assertNotIn(SP1_MARKER, roman)
        self.assertEqual(roman, f"pārājikassa{_STOP}Anodissa")

    def test_prepare_roman_body(self) -> None:
        body, rule = prepare_roman_body("mukhe. . Manussa. _____")
        self.assertTrue(rule)
        self.assertEqual(body, f"mukhe{_STOP}Manussa.")

    def test_printable_dash_from_horizontal_line_extension(self) -> None:
        """PDF U+23AF → en-dash (Sarabun-printable / \\csromandash)."""
        raw = f"dissati{HORIZONTAL_LINE_EXTENSION} “Evaṃ"
        self.assertEqual(
            normalize_printable_dashes(raw),
            f"dissati{EN_DASH} “Evaṃ",
        )
        body, _ = prepare_roman_body(raw, normalize_spacing=False)
        self.assertEqual(body, f"dissati{EN_DASH} “Evaṃ")
        thai = roman_to_thai(raw, normalize_spacing=False)
        self.assertIn(EN_DASH, thai)
        self.assertNotIn(HORIZONTAL_LINE_EXTENSION, thai)


class SolidMidwordHyphenTests(unittest.TestCase):
    def test_strips_editorial_hyphen(self) -> None:
        self.assertEqual(
            strip_solid_midword_hyphens("na-upanissaye"),
            "naupanissaye",
        )
        self.assertEqual(
            strip_solid_midword_hyphens("avitakka-avicāro"),
            "avitakkaavicāro",
        )

    def test_keeps_peyyala_marker(self) -> None:
        self.assertEqual(
            strip_solid_midword_hyphens("Tīhākārehi -pa-. Sattahākārehi"),
            "Tīhākārehi -pa-. Sattahākārehi",
        )
        self.assertEqual(
            strip_solid_midword_hyphens("na-ārammaṇe -pa- na-adhipatiyā"),
            "naārammaṇe -pa- naadhipatiyā",
        )

    def test_prepare_and_thai_drop_hyphen(self) -> None:
        body, _ = prepare_roman_body("na-upanissaye")
        self.assertEqual(body, "naupanissaye")
        thai = roman_to_thai("na-upanissaye", normalize_spacing=False)
        self.assertEqual(thai, "นอุปนิสฺสเย")
        self.assertNotIn("-", thai)

    def test_ensure_rebuilds_hyphenated_roman(self) -> None:
        text = [
            {"script": "roman", "value": "na-upanissaye"},
            {"script": "thai", "value": "น-อุปนิสฺสเย"},
        ]
        self.assertTrue(needs_solid_midword_hyphen_strip(text[0]["value"]))
        entries, _, _ = ensure_script_text(text, normalize_spacing=False)
        roman = next(e["value"] for e in entries if e["script"] == "roman")
        thai = next(e["value"] for e in entries if e["script"] == "thai")
        self.assertEqual(roman, "naupanissaye")
        self.assertEqual(thai, "นอุปนิสฺสเย")


class BoldRunsPreserveTests(unittest.TestCase):
    def test_force_preserves_bold_when_text_unchanged(self) -> None:
        text = [
            {
                "script": "roman",
                "value": "Namo tassa",
                "runs": [
                    {"value": "Namo", "bold": True},
                    {"value": " tassa", "bold": False},
                ],
            },
            {
                "script": "thai",
                "value": "นโม ตสฺส",
                "runs": [
                    {"value": "นโม", "bold": True},
                    {"value": " ตสฺส", "bold": False},
                ],
            },
        ]
        entries, _, lost = ensure_script_text(text, force=True)
        self.assertFalse(lost)
        self.assertTrue(text_field_has_bold_runs(entries))
        roman = next(e for e in entries if e["script"] == "roman")
        self.assertTrue(any(r.get("bold") for r in roman["runs"]))
        self.assertEqual("".join(r["value"] for r in roman["runs"]), roman["value"])

    def test_force_does_not_rebled_repeated_lemma(self) -> None:
        """A single bold lemma must not paint a later plain repeat after force."""
        text = [
            {
                "script": "roman",
                "value": (
                    "Bhūmaṭṭhaṃ nāma bhaṇḍaṃ. “Bhūmaṭṭhaṃ bhaṇḍaṃ”ti theyyacitto"
                ),
                "runs": [
                    {"value": "Bhūmaṭṭhaṃ", "bold": True},
                    {
                        "value": (
                            " nāma bhaṇḍaṃ. “Bhūmaṭṭhaṃ bhaṇḍaṃ”ti theyyacitto"
                        ),
                        "bold": False,
                    },
                ],
            },
            {
                "script": "thai",
                "value": (
                    "ภูมฏฺฐํ นาม ภณฺฑํ. “ภูมฏฺฐํ ภณฺฑํ”ติ เถยฺยจิตฺโต"
                ),
                "runs": [
                    {"value": "ภูมฏฺฐํ", "bold": True},
                    {
                        "value": " นาม ภณฺฑํ. “ภูมฏฺฐํ ภณฺฑํ”ติ เถยฺยจิตฺโต",
                        "bold": False,
                    },
                ],
            },
        ]
        entries, _, lost = ensure_script_text(text, force=True)
        self.assertFalse(lost)
        roman = next(e for e in entries if e["script"] == "roman")
        bold_bits = [r["value"] for r in roman["runs"] if r.get("bold")]
        self.assertEqual(bold_bits, ["Bhūmaṭṭhaṃ"])

    def test_spacing_normalize_preserves_bold_span(self) -> None:
        text = [
            {
                "script": "roman",
                "value": "āpatti pārājikassa. . Anodissa",
                "runs": [
                    {"value": "āpatti", "bold": True},
                    {"value": " pārājikassa. . Anodissa", "bold": False},
                ],
            },
            {
                "script": "thai",
                "value": "อาปตฺติ ปาราชิกสฺส. . อโนทิสฺส",
                "runs": [
                    {"value": "อาปตฺติ", "bold": True},
                    {"value": " ปาราชิกสฺส. . อโนทิสฺส", "bold": False},
                ],
            },
        ]
        entries, _, lost = ensure_script_text(text)
        self.assertFalse(lost)
        roman = next(e for e in entries if e["script"] == "roman")
        self.assertIn(_STOP.rstrip(), roman["value"])
        self.assertNotIn(SP1_MARKER, roman["value"])
        self.assertNotIn(". .", roman["value"])
        bold_bits = [r["value"] for r in roman["runs"] if r.get("bold")]
        self.assertEqual(bold_bits, ["āpatti"])
        thai = next(e for e in entries if e["script"] == "thai")
        self.assertTrue(any(r.get("bold") for r in thai["runs"]))

    def test_force_repairs_sp1_digit_bold_collision(self) -> None:
        """PDF stroke ``1`` painted inside ``{{sp1}}`` must not survive force."""
        text = [
            {
                "script": "roman",
                "value": "Bhikkhū abhinetabbā.{{sp1}} Dutiyampi",
                "runs": [
                    {"value": "Bhikkhū abhinetabbā", "bold": True},
                    {"value": ".{{sp", "bold": False},
                    {"value": "1", "bold": True},
                    {"value": "}} Dutiyampi", "bold": False},
                ],
            },
            {
                "script": "thai",
                "value": "ภิกฺขู อภิเนตพฺพา.{{sp1}} ทุติยมฺปิ",
                "runs": [
                    {"value": "ภิกฺขู อภิเนตพฺพา", "bold": True},
                    {"value": ".{{สฺปฺ", "bold": False},
                    {"value": "๑", "bold": True},
                    {"value": "}} ทุติยมฺปิ", "bold": False},
                ],
            },
        ]
        entries, _, lost = ensure_script_text(text, force=True)
        self.assertFalse(lost)
        roman = next(e for e in entries if e["script"] == "roman")
        thai = next(e for e in entries if e["script"] == "thai")
        self.assertEqual(
            "".join(r["value"] for r in roman["runs"]),
            roman["value"],
        )
        self.assertNotIn("{{sp1}}", roman["value"])
        self.assertNotIn("{{sp1}}", "".join(r["value"] for r in thai["runs"]))
        self.assertNotIn("สฺปฺ", "".join(r["value"] for r in thai["runs"]))
        self.assertIn(". Dutiyampi", roman["value"])
        self.assertEqual(
            [r["value"] for r in roman["runs"] if r.get("bold")],
            ["Bhikkhū abhinetabbā"],
        )

    def test_section_rule_clip_keeps_body_bold(self) -> None:
        text = [
            {
                "script": "roman",
                "value": "Namo tassa _____",
                "runs": [
                    {"value": "Namo", "bold": True},
                    {"value": " tassa _____", "bold": False},
                ],
            },
            {
                "script": "thai",
                "value": "นโม ตสฺส _____",
                "runs": [
                    {"value": "นโม", "bold": True},
                    {"value": " ตสฺส _____", "bold": False},
                ],
            },
        ]
        # Already has thai + no spacing normalize → pass-through clip path.
        self.assertFalse(needs_spacing_normalize(text[0]["value"]))
        entries, had_rule, lost = ensure_script_text(text)
        self.assertTrue(had_rule)
        self.assertFalse(lost)
        roman = next(e for e in entries if e["script"] == "roman")
        self.assertEqual(roman["value"], "Namo tassa")
        self.assertTrue(any(r.get("bold") and r["value"] == "Namo" for r in roman["runs"]))


class RemapRunsThroughEditTests(unittest.TestCase):
    def test_space_insert_keeps_bold_split_before_ti(self) -> None:
        old = "Haneyyuṃvāti hatthena."
        new = "Haneyyuṃ vāti hatthena."
        runs = [
            {"value": "Haneyyuṃvā", "bold": True},
            {"value": "ti hatthena.", "bold": False},
        ]
        out = remap_runs_through_edit(old, new, runs)
        self.assertIsNotNone(out)
        assert out is not None
        self.assertEqual("".join(r["value"] for r in out), new)
        self.assertEqual(
            [r["value"] for r in out if r.get("bold")],
            ["Haneyyuṃ vā"],
        )
        self.assertEqual(
            [r["value"] for r in out if not r.get("bold")],
            ["ti hatthena."],
        )

    def test_join_mismatch_drops_runs(self) -> None:
        self.assertIsNone(
            remap_runs_through_edit(
                "Haneyyuṃvāti",
                "Haneyyuṃ vāti",
                [{"value": "Haneyyuṃvā", "bold": True}],
            )
        )

    def test_annotate_marker_is_not_bold(self) -> None:
        old = "Yopanāti rest"
        new = "Yopanāti{{n0}} rest"
        runs = [{"value": old, "bold": True}]
        out = remap_runs_through_edit(old, new, runs)
        self.assertIsNotNone(out)
        assert out is not None
        self.assertEqual("".join(r["value"] for r in out), new)
        bold = "".join(r["value"] for r in out if r.get("bold"))
        self.assertEqual(bold, "Yopanāti rest")
        self.assertNotIn("{{n0}}", bold)


class SentenceSpacerScopeTests(unittest.TestCase):
    def test_uses_sentence_spacer_body_only(self) -> None:
        self.assertTrue(uses_sentence_spacer("prose"))
        self.assertTrue(uses_sentence_spacer("gatha"))
        self.assertFalse(uses_sentence_spacer("chapter"))
        self.assertFalse(uses_sentence_spacer("title"))
        self.assertFalse(uses_sentence_spacer("niṭṭhitaṃ"))
        self.assertFalse(uses_sentence_spacer("note"))

    def test_heading_prepare_does_not_inject_sp1(self) -> None:
        """Outline ``2. Name`` must not gain a sentence spacer."""
        body, _ = prepare_roman_body(
            "Cīvaravagga 2. Udositasikkhāpada",
            normalize_spacing=False,
        )
        self.assertEqual(body, "Cīvaravagga 2. Udositasikkhāpada")
        self.assertNotIn(SP1_MARKER, body)

    def test_strip_sentence_spacers_keeps_word_space(self) -> None:
        self.assertEqual(
            strip_sentence_spacers(f"Cīvaravagga 2.{_SP1} Udositasikkhāpada"),
            "Cīvaravagga 2. Udositasikkhāpada",
        )

    def test_ensure_heading_strips_legacy_sp1(self) -> None:
        legacy = [
            {
                "script": "roman",
                "value": f"Cīvaravagga 2.{_SP1} Udositasikkhāpada",
            },
            {
                "script": "thai",
                "value": f"จีวรวคฺค ๒.{_SP1} อุโทสิตสิกฺขาปท",
            },
        ]
        entries, _, lost = ensure_script_text(
            legacy, normalize_spacing=False
        )
        self.assertFalse(lost)
        roman = next(e["value"] for e in entries if e["script"] == "roman")
        thai = next(e["value"] for e in entries if e["script"] == "thai")
        self.assertEqual(roman, "Cīvaravagga 2. Udositasikkhāpada")
        self.assertNotIn(SP1_MARKER, thai)
        self.assertIn("2.", thai)
        self.assertNotIn("๒", thai)


class OrdinalSectionCloserTests(unittest.TestCase):
    def test_vaggo_ordinal_thai_and_roman(self) -> None:
        self.assertTrue(is_ordinal_section_closer("ปริมณฺฑลวคฺโค ปฐโม."))
        self.assertTrue(is_ordinal_section_closer("Parimaṇḍalavaggo paṭhamo."))
        self.assertTrue(is_ordinal_section_closer("วคฺโค ทุติโย."))
        self.assertTrue(is_ordinal_section_closer("มุสาวาทวคฺโค ปฐโม."))

    def test_rejects_non_category_ordinals(self) -> None:
        self.assertFalse(is_ordinal_section_closer("ทสมสิกฺขาปทํ นิฏฺฐิตํ."))
        self.assertFalse(is_ordinal_section_closer("ปฐมปาราชิกํ สมตฺตํ."))
        self.assertFalse(
            is_ordinal_section_closer(
                "อยมฺปิ อตฺโถ วุตฺโต ภควตา อิติ เม สุตนฺติ.{{sp1}} ปฐมํ."
            )
        )
        self.assertFalse(
            is_ordinal_section_closer("พุทฺธสญฺญกตฺเถรสฺสาปทานํ ตติยํ.")
        )
        self.assertFalse(is_ordinal_section_closer("1. ปริมณฺฑลวคฺค"))

    def test_ensure_section_rule_for_ordinal_closers(self) -> None:
        self.assertTrue(
            ensure_ordinal_closer_section_rule("อุชฺชคฺฆิกวคฺโค ทุติโย.", False)
        )
        self.assertTrue(
            ensure_ordinal_closer_section_rule("ปริมณฺฑลวคฺโค ปฐโม.", True)
        )
        self.assertFalse(
            ensure_ordinal_closer_section_rule("ทสมสิกฺขาปทํ นิฏฺฐิตํ.", False)
        )


class SectionCloserFormulaTests(unittest.TestCase):
    def test_recognizes_gendered_samatta_and_nitthita(self) -> None:
        self.assertTrue(is_section_closer_formula("มูลปณฺณาสโก สมตฺโต."))
        self.assertTrue(is_section_closer_formula("Mūlapaṇṇāsako samatto."))
        self.assertTrue(is_section_closer_formula("ปฐมปาราชิกํ สมตฺตํ."))
        self.assertTrue(is_section_closer_formula("จูฬวคฺโค นิฏฺฐิโต."))
        self.assertTrue(is_section_closer_formula("ทสมสิกฺขาปทํ นิฏฺฐิตํ."))
        self.assertTrue(is_section_closer_formula("ปริมณฺฑลวคฺโค ปฐโม."))
        self.assertTrue(
            is_section_closer_formula("กิญฺจิเลสสิกฺขาปทํ นิฏฺฐิตํ นวมํ.")
        )
        self.assertTrue(
            is_section_closer_formula(
                "kiñcilesasikkhāpadaṃ niṭṭhitaṃ navamaṃ."
            )
        )
        self.assertTrue(
            is_section_closer_formula(
                "(Aññābhāgiya) kiñcilesasikkhāpadaṃ niṭṭhitaṃ navamaṃ."
            )
        )
        self.assertTrue(
            is_section_closer_formula("พฺรหฺมชาลสุตฺตํ นิฏฺฐิตํ ปฐมํ.")
        )

    def test_rejects_body_prose(self) -> None:
        self.assertFalse(
            is_section_closer_formula(
                "เทฺว โสณา เทฺว นนฺทิกฺขเยน จาติ."
            )
        )
        self.assertFalse(is_section_closer_formula("1. ปริมณฺฑลวคฺค"))

    def test_peels_trailing_closer_after_verse_stop(self) -> None:
        peeled = peel_trailing_section_closer(
            "เทฺว โสณา เทฺว นนฺทิกฺขเยน จาติ.{{sp1}} มูลปณฺณาสโก สมตฺโต."
        )
        self.assertIsNotNone(peeled)
        assert peeled is not None
        body, closer = peeled
        self.assertEqual(body, "เทฺว โสณา เทฺว นนฺทิกฺขเยน จาติ.")
        self.assertEqual(closer, "มูลปณฺณาสโก สมตฺโต.")
        roman = peel_trailing_section_closer(
            "dve Soṇā dve Nandikkhayena cāti.{{sp1}} Mūlapaṇṇāsako samatto."
        )
        self.assertEqual(
            roman,
            (
                "dve Soṇā dve Nandikkhayena cāti.",
                "Mūlapaṇṇāsako samatto.",
            ),
        )
        glued = peel_trailing_section_closer(
            "Anāpatti tathāsaññī codeti vā codāpeti vā ummattakassa "
            "ādikammikassāti. (Aññābhāgiya) kiñcilesasikkhāpadaṃ "
            "niṭṭhitaṃ navamaṃ."
        )
        self.assertEqual(
            glued,
            (
                "Anāpatti tathāsaññī codeti vā codāpeti vā ummattakassa "
                "ādikammikassāti.",
                "(Aññābhāgiya) kiñcilesasikkhāpadaṃ niṭṭhitaṃ navamaṃ.",
            ),
        )

    def test_does_not_peel_ordinary_next_sentence(self) -> None:
        self.assertIsNone(
            peel_trailing_section_closer(
                "hoti.{{sp1}} So bhikkhu gacchati."
            )
        )


class SectionCloserLevelTests(unittest.TestCase):
    def test_major_levels(self) -> None:
        cases = [
            ("ปาราชิกปาฬิ นิฏฺฐิตา.", "pāḷi", "major"),
            ("ขนฺธวคฺคสํยุตฺตปาฬิ นิฏฺฐิตา.", "saṃyutta_pāḷi", "major"),
            ("เอกกนิปาตปาฬิ นิฏฺฐิตา.", "nipāta_pāḷi", "major"),
            ("ทีฆนิกาโย สมตฺโต.", "nikāya", "major"),
            ("มหาขนฺธโก นิฏฺฐิโต.", "khandhaka", "major"),
            ("ปาราชิกกณฺฑํ นิฏฺฐิตํ.", "kaṇḍa", "major"),
            ("มูลปณฺณาสโก สมตฺโต.", "paṇṇāsaka", "major"),
            ("เอกกนิปาตํ นิฏฺฐิตํ.", "nipāta", "major"),
            ("Mūlapaṇṇāsako samatto.", "paṇṇāsaka", "major"),
            ("Khandhavaggasaṃyuttapāḷi niṭṭhitā.", "saṃyutta_pāḷi", "major"),
        ]
        for text, level, tier in cases:
            with self.subTest(text=text):
                self.assertEqual(classify_section_closer(text), level)
                self.assertEqual(classify_section_closer_tier(text), tier)
                self.assertEqual(closer_tier(level), tier)

    def test_mid_levels(self) -> None:
        cases = [
            ("ปริมณฺฑลวคฺโค ปฐโม.", "ordinal_vagga", "mid"),
            ("จูฬวคฺโค นิฏฺฐิโต.", "vagga", "mid"),
            ("ภิกฺขุนีสํยุตฺตํ สมตฺตํ.", "saṃyutta", "mid"),
            ("Parimaṇḍalavaggo paṭhamo.", "ordinal_vagga", "mid"),
        ]
        for text, level, tier in cases:
            with self.subTest(text=text):
                self.assertEqual(classify_section_closer(text), level)
                self.assertEqual(classify_section_closer_tier(text), tier)

    def test_leaf_levels(self) -> None:
        cases = [
            ("ทสมสิกฺขาปทํ นิฏฺฐิตํ.", "sikkhāpada", "leaf"),
            ("พฺรหฺมชาลสุตฺตํ นิฏฺฐิตํ ปฐมํ.", "sutta", "leaf"),
            ("สุทฺธิกวารกถา นิฏฺฐิตา.", "kathā", "leaf"),
            ("เวรญฺชภาณวาโร นิฏฺฐิโต.", "bhāṇavāra", "leaf"),
            ("มกฺกฏีวตฺถุ นิฏฺฐิตํ.", "vatthu", "leaf"),
            ("ปฐมปาราชิกํ สมตฺตํ.", "pārājika_unit", "leaf"),
            ("ราคเปยฺยาลํ นิฏฺฐิตํ.", "peyyāla", "leaf"),
            ("สพฺพมูลกํ นิฏฺฐิตํ.", "analytic", "leaf"),
            ("ขณฺฑจกฺกํ นิฏฺฐิตํ.", "analytic", "leaf"),
            ("ลสุณสิกฺขาปทํ ปฐมํ นิฏฺฐิตํ.", "sikkhāpada", "leaf"),
            ("มหาวิภงฺโค นิฏฺฐิโต.", "vibhaṅga", "major"),
            ("อุปชฺฌายวตฺตํ นิฏฺฐิตํ.", "vatta", "leaf"),
            ("ยสสฺส ปพฺพชฺชา นิฏฺฐิตา.", "pabbajjā", "leaf"),
            ("อุปสมฺปทากมฺมํ นิฏฺฐิตํ.", "kamma", "leaf"),
            ("ภิกฺขุเปยฺยาโล นิฏฺฐิโต.", "peyyāla", "leaf"),
            (
                "อุปสมฺปาเทตพฺพปญฺจกโสฬสวาโร นิฏฺฐิโต.",
                "vāra",
                "leaf",
            ),
        ]
        for text, level, tier in cases:
            with self.subTest(text=text):
                self.assertEqual(classify_section_closer(text), level)
                self.assertEqual(classify_section_closer_tier(text), tier)

    def test_unknown_and_non_formula(self) -> None:
        self.assertEqual(classify_section_closer("สุทฺธิกํ นิฏฺฐิตํ."), "unknown")
        self.assertEqual(classify_section_closer_tier("สุทฺธิกํ นิฏฺฐิตํ."), "leaf")
        self.assertEqual(classify_section_closer("1. ปริมณฺฑลวคฺค"), "unknown")
        self.assertEqual(
            classify_section_closer("เทฺว โสณา เทฺว นนฺทิกฺขเยน จาติ."),
            "unknown",
        )

    def test_nested_name_prefers_rightmost_pali(self) -> None:
        # Must not classify as vagga just because วคฺค appears earlier.
        self.assertEqual(
            classify_section_closer("มหาวคฺคปาฬิ นิฏฺฐิตา."),
            "pāḷi",
        )

    def test_two_line_vagga_closer_pair(self) -> None:
        self.assertTrue(is_bare_category_closer_label("โสตาปตฺติวคฺโค."))
        self.assertTrue(is_bare_category_closer_label("Sotāpattivaggo."))
        self.assertFalse(is_bare_category_closer_label("ปริมณฺฑลวคฺโค ปฐโม."))
        self.assertFalse(is_bare_category_closer_label("จูฬวคฺโค นิฏฺฐิโต."))
        joined = join_two_line_category_closer(
            "โสตาปตฺติวคฺโค.",
            "อฏฺฐารสเวยฺยากรณํ นิฏฺฐิตํ.",
        )
        self.assertEqual(
            joined,
            r"โสตาปตฺติวคฺโค.\\อฏฺฐารสเวยฺยากรณํ นิฏฺฐิตํ.",
        )
        self.assertEqual(classify_section_closer(joined), "vagga")
        self.assertEqual(classify_section_closer_tier(joined), "mid")
        self.assertIsNone(
            join_two_line_category_closer(
                "โสตาปตฺติวคฺโค.",
                "ตสฺสุทฺทานํ",
            )
        )


class TassuddanaAndExpansionParenTests(unittest.TestCase):
    def test_tassuddana_label(self) -> None:
        self.assertTrue(is_tassuddana_label("Tassuddānaṃ"))
        self.assertTrue(is_tassuddana_label("ตสฺสุทฺทานํ"))
        self.assertFalse(is_tassuddana_label("Uddānaṃ"))
        self.assertFalse(is_tassuddana_label("Tassuddānaṃ gāthā"))

    def test_expansion_parenthetical_recognizer(self) -> None:
        long_paren = (
            "(Appamādavaggo Bojjhaṅgasaṃyuttassa "
            "bojjhaṅgavasena vitthāretabbo.)"
        )
        self.assertTrue(is_expansion_parenthetical(long_paren))
        self.assertFalse(is_expansion_parenthetical("(12-13)"))
        self.assertFalse(is_expansion_parenthetical("(150)"))
        self.assertFalse(is_expansion_parenthetical("(te)"))

    def test_section_nama_colophon_recognizer(self) -> None:
        self.assertTrue(is_section_nama_colophon("Maddīpabbaṃ nāma."))
        self.assertTrue(is_section_nama_colophon("มทฺทีปพฺพํ นาม."))
        self.assertTrue(is_section_nama_colophon("Dohaḷakaṇḍaṃ nāma."))
        self.assertFalse(is_section_nama_colophon("so hāro lakkhaṇo nāma."))
        self.assertFalse(is_section_nama_colophon("Maddīpabbaṃ nāma. Sakkapabba"))

    def test_peels_trailing_expansion_paren(self) -> None:
        peeled = peel_trailing_expansion_parenthetical(
            "Vatthena dasamaṃ padanti. "
            "(Appamādavaggo Bojjhaṅgasaṃyuttassa "
            "bojjhaṅgavasena vitthāretabbo.)"
        )
        self.assertIsNotNone(peeled)
        assert peeled is not None
        body, paren = peeled
        self.assertEqual(body, "Vatthena dasamaṃ padanti.")
        self.assertTrue(paren.startswith("(Appamādavaggo"))
        self.assertIsNone(
            peel_trailing_expansion_parenthetical(
                "āpannā hoti.{{sp1}} (12-13)"
            )
        )
        with_rule = peel_trailing_expansion_parenthetical(
            "Vatthena dasamaṃ padanti. "
            "(Appamādavaggo Bojjhaṅgasaṃyuttassa "
            "bojjhaṅgavasena vitthāretabbo.) _____"
        )
        self.assertIsNotNone(with_rule)
        assert with_rule is not None
        self.assertEqual(with_rule[0], "Vatthena dasamaṃ padanti.")
        self.assertIn("_____", with_rule[1])
        self.assertTrue(with_rule[1].startswith("(Appamādavaggo"))


if __name__ == "__main__":
    unittest.main()
