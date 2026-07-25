"""Round-trip tests for pali_script (shared fixtures)."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

# Allow running without install: packages/pali_script/python on path
_ROOT = Path(__file__).resolve().parents[1]
_PYTHON = _ROOT / "python"
if str(_PYTHON) not in sys.path:
    sys.path.insert(0, str(_PYTHON))

from pali_script import Script, convert  # noqa: E402

FIXTURES = _ROOT / "tests" / "fixtures" / "roundtrips.json"


class RoundTripTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pairs = json.loads(FIXTURES.read_text(encoding="utf-8"))

    def test_roman_to_thai(self) -> None:
        for row in self.pairs:
            with self.subTest(roman=row["roman"]):
                got = convert(row["roman"], Script.ROMAN, Script.THAI)
                self.assertEqual(got, row["thai"])

    def test_thai_to_roman(self) -> None:
        for row in self.pairs:
            with self.subTest(thai=row["thai"]):
                got = convert(row["thai"], Script.THAI, Script.ROMAN)
                self.assertEqual(got, row["roman"])

    def test_roundtrip_roman(self) -> None:
        for row in self.pairs:
            with self.subTest(roman=row["roman"]):
                thai = convert(row["roman"], Script.ROMAN, Script.THAI)
                back = convert(thai, Script.THAI, Script.ROMAN)
                self.assertEqual(back, row["roman"])

    def test_niggahita_alt(self) -> None:
        self.assertEqual(
            convert("dhammaṁ", Script.ROMAN, Script.THAI),
            "ธมฺมํ",
        )

    def test_i_niggahita_not_sara_ue(self) -> None:
        """iṃ must stay as ิํ; Thai sara ue ึ is not used in Pāli."""
        self.assertEqual(
            convert("sandhiṃ", Script.ROMAN, Script.THAI),
            "สนฺธิํ",
        )
        self.assertNotIn("ึ", convert("sandhiṃ", Script.ROMAN, Script.THAI))
        # Legacy composite form still decodes to iṃ.
        self.assertEqual(
            convert("สนฺธึ", Script.THAI, Script.ROMAN),
            "sandhiṃ",
        )

    def test_detect_and_auto(self) -> None:
        self.assertEqual(
            convert("พุทฺโธ", Script.AUTO, Script.ROMAN),
            "buddho",
        )


if __name__ == "__main__":
    unittest.main()
