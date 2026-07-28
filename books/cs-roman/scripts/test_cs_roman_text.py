"""Unit tests for cs-roman text helpers (sentence stop → {{sp1}})."""

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
    demigrate_sp_markers,
    ensure_script_text,
    needs_spacing_normalize,
    normalize_pot_ma_gyi,
    prepare_roman_body,
    roman_to_thai,
    script_text_entries,
    strip_sentence_spacers,
    text_field_has_bold_runs,
    thai_digits_to_arabic,
    uses_sentence_spacer,
)

_SP1 = SP1_MARKER
_SP1X2 = SP1_MARKER + SP1_MARKER


class PotMaGyiNormalizeTests(unittest.TestCase):
    def test_maps_dot_space_dot_to_double_sp1(self) -> None:
        self.assertEqual(
            normalize_pot_ma_gyi("āpatti pārājikassa. . Anodissa"),
            f"āpatti pārājikassa.{_SP1X2}Anodissa",
        )

    def test_ordinary_stop_gets_sp1_keeps_space(self) -> None:
        self.assertEqual(
            normalize_pot_ma_gyi("hoti. So bhikkhu."),
            f"hoti.{_SP1} So bhikkhu.",
        )

    def test_digit_ref_unchanged(self) -> None:
        self.assertEqual(
            normalize_pot_ma_gyi("ที 1. 46, 109"),
            "ที 1. 46, 109",
        )

    def test_requires_exactly_one_space_for_pot_ma_gyi(self) -> None:
        # Two spaces: not pot-ma-gyi; the second stop still gets an ordinary gap.
        self.assertEqual(normalize_pot_ma_gyi("a.  . b"), f"a.  .{_SP1} b")
        self.assertEqual(normalize_pot_ma_gyi("a..b"), "a..b")

    def test_multiple_occurrences(self) -> None:
        src = "mukhe. . Manussa. mukhe. . Paṇḍaka."
        out = normalize_pot_ma_gyi(src)
        # two pot-ma-gyi × 2, plus ordinary stop after Manussa.
        self.assertEqual(out.count(SP1_MARKER), 5)
        self.assertNotIn(". .", out)
        self.assertIn(f"Manussa.{_SP1} mukhe.", out)

    def test_upgrades_legacy_single_sp1_pot_ma_gyi(self) -> None:
        self.assertEqual(
            normalize_pot_ma_gyi(f"pārājikassa.{_SP1}Anodissa"),
            f"pārājikassa.{_SP1X2}Anodissa",
        )

    def test_repairs_glued_sp1_missing_stop(self) -> None:
        self.assertEqual(
            normalize_pot_ma_gyi(f"pārājikassa{_SP1}Anodissa"),
            f"pārājikassa.{_SP1X2}Anodissa",
        )

    def test_does_not_double_ordinary_stop_sp1(self) -> None:
        src = f"hoti.{_SP1} So bhikkhu."
        self.assertEqual(normalize_pot_ma_gyi(src), src)


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
    def test_entries_normalize_and_preserve_marker_in_thai(self) -> None:
        entries, had_rule = script_text_entries(
            "Marati, āpatti pārājikassa. . Anodissa opātaṃ."
        )
        self.assertFalse(had_rule)
        roman = next(e["value"] for e in entries if e["script"] == "roman")
        thai = next(e["value"] for e in entries if e["script"] == "thai")
        self.assertIn(_SP1X2, roman)
        self.assertNotIn(". .", roman)
        self.assertIn(SP1_MARKER, thai)
        self.assertIn("ปาราชิกสฺส.", thai)
        self.assertIn("อโนทิสฺส", thai)

    def test_roman_to_thai_keeps_sp1(self) -> None:
        thai = roman_to_thai(f"pārājikassa.{_SP1X2}Anodissa")
        self.assertIn(SP1_MARKER, thai)
        self.assertTrue(thai.startswith("ปาราชิกสฺส."))

    def test_roman_to_thai_can_skip_sentence_stop_normalize(self) -> None:
        """Footnote path: abbreviation-heavy notes must not gain {{sp1}}."""
        src = "Imāni vatthūni Saṃ 1. 446 piṭṭhādīsupi āgatāni. So hoti."
        thai = roman_to_thai(src, normalize_spacing=False)
        self.assertNotIn(SP1_MARKER, thai)
        # Default body path still injects ordinary stop gaps.
        body = roman_to_thai(src)
        self.assertIn(SP1_MARKER, body)

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
        self.assertEqual(roman, f"pārājikassa.{_SP1X2}Anodissa")
        self.assertIn(SP1_MARKER, thai)
        self.assertNotIn(". .", thai)

    def test_ensure_rebuilds_ordinary_stop_without_sp1(self) -> None:
        legacy = [
            {"script": "roman", "value": "hoti. So bhikkhu."},
            {"script": "thai", "value": "โหติ. โส ภิกฺขุ."},
        ]
        self.assertTrue(needs_spacing_normalize(legacy[0]["value"]))
        entries, _, lost = ensure_script_text(legacy)
        self.assertFalse(lost)
        roman = next(e["value"] for e in entries if e["script"] == "roman")
        self.assertEqual(roman, f"hoti.{_SP1} So bhikkhu.")

    def test_ensure_rebuilds_legacy_sp3(self) -> None:
        legacy = [
            {"script": "roman", "value": f"pārājikassa.{SP3_MARKER}Anodissa"},
            {"script": "thai", "value": f"ปาราชิกสฺส.{SP3_MARKER}อโนทิสฺส"},
        ]
        entries, _, lost = ensure_script_text(legacy)
        self.assertFalse(lost)
        roman = next(e["value"] for e in entries if e["script"] == "roman")
        self.assertNotIn(SP3_MARKER, roman)
        self.assertIn(SP1_MARKER, roman)

    def test_prepare_roman_body(self) -> None:
        body, rule = prepare_roman_body("mukhe. . Manussa. _____")
        self.assertTrue(rule)
        self.assertEqual(body, f"mukhe.{_SP1X2}Manussa.")


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
        self.assertIn(_SP1X2, roman["value"])
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
        self.assertIn("{{sp1}}", "".join(r["value"] for r in thai["runs"]))
        self.assertNotIn("สฺปฺ", "".join(r["value"] for r in thai["runs"]))
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


if __name__ == "__main__":
    unittest.main()
