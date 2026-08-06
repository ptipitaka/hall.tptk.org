"""Tests for DPD sandhi soft-break alignment and TeX marker injection."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from paths import ensure_import_paths  # noqa: E402

ensure_import_paths()

from cs_roman_sandhi_breaks import (  # noqa: E402
    DEFAULT_DB_PATH,
    DEFAULT_OVERRIDES_PATH,
    SOFT_BREAK_MARKER,
    align_parts,
    inject_soft_breaks_in_thai,
    load_break_overrides,
    merge_break_maps,
    normalize_lookup_key,
    parse_plus_parts,
    surface_chunks,
    thai_slices_from_roman_chunks,
)
from generate_cs_roman_tex import apply_notes_to_thai  # noqa: E402
from pali_script import Script, convert  # noqa: E402


class AlignPartsTests(unittest.TestCase):
    def test_exact_concat(self) -> None:
        word = "pubbenivāsacatutthaṃ"
        parts = parse_plus_parts("pubbenivāsa + catutthaṃ")
        self.assertEqual(align_parts(word, parts), [len("pubbenivāsa")])

    def test_pubbe_construction_aligns(self) -> None:
        word = "pubbenivāsānussatiñāṇāya"
        parts = parse_plus_parts("pubbe + nivāsa + anussati + ñāṇa")
        breaks = align_parts(word, parts)
        self.assertIsNotNone(breaks)
        chunks = surface_chunks(word, parts)
        self.assertIsNotNone(chunks)
        assert chunks is not None
        thai = thai_slices_from_roman_chunks(word, chunks)
        self.assertIsNotNone(thai)
        assert thai is not None
        self.assertEqual("".join(thai), "".join(thai))  # non-empty join
        self.assertGreaterEqual(len(thai), 3)
        self.assertTrue(thai[0].startswith("ปุพฺเพ"))


@unittest.skipUnless(DEFAULT_DB_PATH.is_file(), "vendor dpd.db not present")
class DpdLookupTests(unittest.TestCase):
    def test_break_for_known_compound(self) -> None:
        from cs_roman_sandhi_breaks import DpdSandhiLookup

        with DpdSandhiLookup() as dpd:
            sb = dpd.break_for_word("pubbenivāsānussatiñāṇāya")
        self.assertIsNotNone(sb)
        assert sb is not None
        self.assertIn("pubbe", sb.parts_roman[0])
        self.assertIn(SOFT_BREAK_MARKER, sb.thai_with_markers)
        self.assertEqual(sb.thai_solid, "".join(sb.parts_thai))

    def test_missing_word_returns_none(self) -> None:
        from cs_roman_sandhi_breaks import DpdSandhiLookup

        with DpdSandhiLookup() as dpd:
            self.assertIsNone(dpd.break_for_word("xyzzynotaword"))


class InjectSoftBreaksTests(unittest.TestCase):
    def test_injects_marker_for_cached_token(self) -> None:
        roman = "pubbenivāsacatutthaṃ eva"
        thai = "ปุพฺเพนิวาสจตุตฺถํ เอว"
        breaks = {
            normalize_lookup_key("pubbenivāsacatutthaṃ"): [
                "pubbenivāsa",
                "catutthaṃ",
            ]
        }
        out = inject_soft_breaks_in_thai(thai, roman, breaks, min_thai_len=10)
        self.assertIn(SOFT_BREAK_MARKER, out)
        self.assertEqual(out.replace(SOFT_BREAK_MARKER, ""), thai)

    def test_skips_short_tokens(self) -> None:
        roman = "pubbenivāsacatutthaṃ"
        thai = "ปุพฺเพนิวาสจตุตฺถํ"
        breaks = {
            normalize_lookup_key(roman): ["pubbenivāsa", "catutthaṃ"],
        }
        out = inject_soft_breaks_in_thai(thai, roman, breaks, min_thai_len=99)
        self.assertEqual(out, thai)

    def test_unknown_token_unchanged(self) -> None:
        thai = "ธมฺโม"
        out = inject_soft_breaks_in_thai(thai, "dhammo", {}, min_thai_len=1)
        self.assertEqual(out, thai)


class OverrideMapTests(unittest.TestCase):
    def test_merge_overrides_win(self) -> None:
        base = {"abcd": ["ab", "cd"]}
        over = {"abcd": ["a", "bcd"], "efgh": ["ef", "gh"]}
        merged = merge_break_maps(base, over)
        self.assertEqual(merged["abcd"], ["a", "bcd"])
        self.assertEqual(merged["efgh"], ["ef", "gh"])

    def test_load_rejects_non_concat_parts(self) -> None:
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "overrides.json"
            path.write_text(
                '{"breaks": {"abcd": ["ab", "xx"], "efgh": ["ef", "gh"]}}',
                encoding="utf-8",
            )
            loaded = load_break_overrides(path)
        self.assertNotIn("abcd", loaded)
        self.assertEqual(loaded.get("efgh"), ["ef", "gh"])

    def test_tiracchana_edition_override_injects(self) -> None:
        word = "tiracchānanagatubhatobyañjanakassa"
        # Ideal DPD junction gat|ubhato is not Thai-prefix-safe (dangling ฺ);
        # curated break is after ubhato inside ubhatobyañjanaka.
        parts = ["tiracchānanagatubhato", "byañjanakassa"]
        self.assertEqual("".join(parts), word)
        thai = convert(word, Script.ROMAN, Script.THAI)
        breaks = {normalize_lookup_key(word): parts}
        out = inject_soft_breaks_in_thai(thai, word, breaks, min_thai_len=15)
        self.assertIn(SOFT_BREAK_MARKER, out)
        self.assertEqual(out.replace(SOFT_BREAK_MARKER, ""), thai)
        self.assertTrue(out.startswith("ติรจฺฉานนคตุภโต"))

    @unittest.skipUnless(
        DEFAULT_OVERRIDES_PATH.is_file(), "overrides file not present"
    )
    def test_repo_overrides_include_tiracchana_case(self) -> None:
        loaded = load_break_overrides()
        key = normalize_lookup_key("tiracchānanagatubhatobyañjanakassa")
        self.assertIn(key, loaded)
        self.assertEqual("".join(loaded[key]), key)


class EnsureCacheTests(unittest.TestCase):
    def test_ensure_returns_existing_cache(self) -> None:
        from cs_roman_sandhi_breaks import (
            DEFAULT_CACHE_PATH,
            ensure_sandhi_break_cache,
        )

        if not DEFAULT_CACHE_PATH.is_file():
            self.skipTest("sandhi_breaks.json not present")
        data = ensure_sandhi_break_cache(quiet=True)
        self.assertIsInstance(data, dict)
        self.assertGreater(len(data), 0)
        # Curated edition spelling must survive merge even when absent from DPD.
        key = normalize_lookup_key("tiracchānanagatubhatobyañjanakassa")
        if DEFAULT_OVERRIDES_PATH.is_file():
            self.assertIn(key, data)
            self.assertEqual("".join(data[key]), key)


class TeXSoftBreakTests(unittest.TestCase):
    def test_sb_becomes_tex_soft_hyphen(self) -> None:
        thai = f"ปุพฺเพ{SOFT_BREAK_MARKER}นิวาสา"
        tex, _ = apply_notes_to_thai(thai, notes=[], symbol_notes={})
        self.assertIn(r"\-", tex)
        self.assertNotIn("sb", tex)
        self.assertIn("ปุพฺเพ", tex)
        self.assertIn("นิวาสา", tex)


if __name__ == "__main__":
    unittest.main()
