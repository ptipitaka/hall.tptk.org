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
        entries, _ = ensure_script_text(legacy)
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
        entries, _ = ensure_script_text(legacy)
        roman = next(e["value"] for e in entries if e["script"] == "roman")
        self.assertEqual(roman, f"hoti.{_SP1} So bhikkhu.")

    def test_ensure_rebuilds_legacy_sp3(self) -> None:
        legacy = [
            {"script": "roman", "value": f"pārājikassa.{SP3_MARKER}Anodissa"},
            {"script": "thai", "value": f"ปาราชิกสฺส.{SP3_MARKER}อโนทิสฺส"},
        ]
        entries, _ = ensure_script_text(legacy)
        roman = next(e["value"] for e in entries if e["script"] == "roman")
        self.assertNotIn(SP3_MARKER, roman)
        self.assertIn(SP1_MARKER, roman)

    def test_prepare_roman_body(self) -> None:
        body, rule = prepare_roman_body("mukhe. . Manussa. _____")
        self.assertTrue(rule)
        self.assertEqual(body, f"mukhe.{_SP1X2}Manussa.")


if __name__ == "__main__":
    unittest.main()
