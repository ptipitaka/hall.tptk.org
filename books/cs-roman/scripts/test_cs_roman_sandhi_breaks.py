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
    compose_finer_break_parts,
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

    def test_elision_a_plus_e(self) -> None:
        # na + eva → neva (a absorbed before e)
        word = "nevasaññānāsaññāyatanaṃ"
        parts = parse_plus_parts("na + eva + saññā + na + asaññā + āyatana")
        breaks = align_parts(word, parts)
        self.assertIsNotNone(breaks)
        chunks = surface_chunks(word, parts)
        assert chunks is not None
        self.assertEqual("".join(chunks), word)

    def test_contraction_a_plus_a_to_ā(self) -> None:
        # na + asaññā → nāsaññā (a+a → ā)
        word = "nāsaññāyatanaṃ"
        parts = parse_plus_parts("na + asaññā + āyatana")
        breaks = align_parts(word, parts)
        self.assertIsNotNone(breaks)
        chunks = surface_chunks(word, parts)
        assert chunks is not None
        self.assertEqual("".join(chunks), word)

    def test_cross_vowel_contraction_a_plus_i_to_ā(self) -> None:
        # paramatthena + iti → paramatthenāti (a+i → ā)
        word = "saccikaṭṭhaparamatthenāti"
        parts = parse_plus_parts("saccikaṭṭha + paramatthena + iti")
        breaks = align_parts(word, parts)
        self.assertIsNotNone(breaks)
        chunks = surface_chunks(word, parts)
        assert chunks is not None
        self.assertEqual("".join(chunks), word)

    def test_long_vowel_fusion_ā_plus_ā(self) -> None:
        # asaññā + āyatana → asaññāyatana (ā+ā → ā, single vowel shared)
        word = "asaññāyatanaṃ"
        parts = parse_plus_parts("asaññā + āyatana")
        breaks = align_parts(word, parts)
        self.assertIsNotNone(breaks)
        chunks = surface_chunks(word, parts)
        assert chunks is not None
        self.assertEqual("".join(chunks), word)

    def test_compound_construction_bold_stripped(self) -> None:
        # compound_construction has <b> markup; parse_plus_parts must strip it.
        parts = parse_plus_parts("nevasaññānāsaññ<b>āya</b> + āyatana")
        self.assertEqual(parts, ["nevasaññānāsaññāya", "āyatana"])

    def test_construction_gt_marker_handled(self) -> None:
        # construction uses ``>`` for derivation (``na > an + aññāta``)
        parts = parse_plus_parts("na > an + aññāta + ñassāmi + iti + indriya")
        self.assertEqual(parts, ["na", "an", "aññāta", "ñassāmi", "iti", "indriya"])

    def test_last_vowel_case_ending_substitution(self) -> None:
        # upekkhā + sambojjhaṅga + nom. o → upekkhāsambojjhaṅgo
        # (stem ...ga, surface ...go; is_last must accept the vowel swap)
        word = "upekkhāsambojjhaṅgo"
        parts = parse_plus_parts("upekkhā + sambojjhaṅga")
        breaks = align_parts(word, parts)
        self.assertIsNotNone(breaks)
        chunks = surface_chunks(word, parts)
        assert chunks is not None
        self.assertEqual("".join(chunks), word)


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

    def test_compound_construction_source_used(self) -> None:
        # nevasaññānāsaññāyatanaṃ has empty deconstructor but a
        # compound_construction with <b> markup; the lookup must recover it.
        from cs_roman_sandhi_breaks import DpdSandhiLookup

        with DpdSandhiLookup() as dpd:
            sb = dpd.break_for_word("nevasaññānāsaññāyatanaṃ")
        self.assertIsNotNone(sb)
        assert sb is not None
        self.assertGreaterEqual(len(sb.parts_roman), 2)
        self.assertEqual("".join(sb.parts_roman), "nevasaññānāsaññāyatanaṃ")

    def test_prefix_strip_fallback_for_no_row_word(self) -> None:
        # nocittasaṃsaṭṭhasamuṭṭhāno has no lookup row; the ``no`` prefix
        # strip + remainder lookup must recover a split.
        from cs_roman_sandhi_breaks import DpdSandhiLookup

        with DpdSandhiLookup() as dpd:
            sb = dpd.break_for_word("nocittasaṃsaṭṭhasamuṭṭhāno")
        self.assertIsNotNone(sb)
        assert sb is not None
        self.assertGreaterEqual(len(sb.parts_roman), 2)
        self.assertEqual("".join(sb.parts_roman), "nocittasaṃsaṭṭhasamuṭṭhāno")


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
        out = inject_soft_breaks_in_thai(thai, roman, breaks, min_roman_len=99)
        self.assertEqual(out, thai)

    def test_injects_when_roman_long_but_thai_display_short(self) -> None:
        word = "sattāhānatikkante"
        thai = convert(word, Script.ROMAN, Script.THAI)
        breaks = {normalize_lookup_key(word): ["sattāhā", "natikkante"]}
        out = inject_soft_breaks_in_thai(thai, word, breaks, min_roman_len=15)
        self.assertIn(SOFT_BREAK_MARKER, out)
        self.assertEqual(out.replace(SOFT_BREAK_MARKER, ""), thai)

    def test_unknown_token_unchanged(self) -> None:
        thai = "ธมฺโม"
        out = inject_soft_breaks_in_thai(thai, "dhammo", {}, min_thai_len=1)
        self.assertEqual(out, thai)

    def test_drops_break_that_leaves_short_trailing_fragment(self) -> None:
        # ``sippikasambukāpi`` = ``sippikasambukā`` + ``pi`` (``ปิ`` = 1 spacing
        # glyph; ``ิ`` is a nonspacing mark). The sandhi split is real but the
        # only break point leaves a 1-glyph widow, so no marker should be
        # injected and TeX moves the whole word to the next line instead.
        word = "sippikasambukāpi"
        thai = convert(word, Script.ROMAN, Script.THAI)
        breaks = {normalize_lookup_key(word): ["sippikasambukā", "pi"]}
        out = inject_soft_breaks_in_thai(thai, word, breaks, min_roman_len=15)
        self.assertNotIn(SOFT_BREAK_MARKER, out)
        self.assertEqual(out, thai)

    def test_keeps_balanced_break_for_same_root(self) -> None:
        # ``sippikasambukampi`` = ``sippika`` + ``sambukampi`` — both sides
        # comfortably above the fragment floor, so the break is kept.
        word = "sippikasambukampi"
        thai = convert(word, Script.ROMAN, Script.THAI)
        breaks = {normalize_lookup_key(word): ["sippika", "sambukampi"]}
        out = inject_soft_breaks_in_thai(thai, word, breaks, min_roman_len=15)
        self.assertIn(SOFT_BREAK_MARKER, out)
        self.assertEqual(out.replace(SOFT_BREAK_MARKER, ""), thai)

    def test_keeps_only_balanced_breaks_in_multi_part_word(self) -> None:
        # ``sokajjhāyikānampi`` (in DPD cache) splits as ``soka`` + ``jjhāyikāna``
        # + ``mpi``. The second break leaves a 2-glyph trailing ``mpi`` (``มฺปิ``)
        # so only the first break should survive.
        word = "sokajjhāyikānampi"
        thai = convert(word, Script.ROMAN, Script.THAI)
        breaks = {
            normalize_lookup_key(word): ["soka", "jjhāyikāna", "mpi"],
        }
        out = inject_soft_breaks_in_thai(thai, word, breaks, min_roman_len=15)
        self.assertEqual(out.count(SOFT_BREAK_MARKER), 1)
        self.assertEqual(out.replace(SOFT_BREAK_MARKER, ""), thai)

    def test_min_fragment_zero_keeps_all_breaks(self) -> None:
        word = "sippikasambukāpi"
        thai = convert(word, Script.ROMAN, Script.THAI)
        breaks = {normalize_lookup_key(word): ["sippikasambukā", "pi"]}
        out = inject_soft_breaks_in_thai(
            thai, word, breaks, min_roman_len=15, min_fragment_len=0
        )
        self.assertIn(SOFT_BREAK_MARKER, out)

    def test_compose_refines_arupa_stem_plus_suffix(self) -> None:
        # Coarse DPD: ākāsānañcāyatana|sahagatā (left chunk Thai len 13).
        # Finer stem splits to ākāsā|nañcā|yatana → inject ākāsā|nañcā|yatanasahagatā.
        word = "ākāsānañcāyatanasahagatā"
        stem = "ākāsānañcāyatana"
        breaks = {
            normalize_lookup_key(word): [stem, "sahagatā"],
            normalize_lookup_key(stem): ["ākāsā", "nañcā", "yatana"],
        }
        composed = compose_finer_break_parts(word, breaks[word], breaks)
        self.assertEqual(composed, ["ākāsā", "nañcā", "yatanasahagatā"])
        thai = convert(word, Script.ROMAN, Script.THAI)
        out = inject_soft_breaks_in_thai(thai, word, breaks, min_roman_len=15)
        self.assertEqual(out.count(SOFT_BREAK_MARKER), 2)
        self.assertTrue(out.startswith("อากาสา" + SOFT_BREAK_MARKER + "นญฺจา"))
        self.assertEqual(out.replace(SOFT_BREAK_MARKER, ""), thai)

    def test_compose_iterates_for_neva_ayatana_long_form(self) -> None:
        # Two-layer refine: …samāpattiyā|pi → …yatana|samāpattiyāpi →
        # ne|va|saññā|nā|saññā|yatanasamāpattiyāpi
        word = "nevasaññānāsaññāyatanasamāpattiyāpi"
        mid = "nevasaññānāsaññāyatanasamāpattiyā"
        stem = "nevasaññānāsaññāyatana"
        breaks = {
            normalize_lookup_key(word): [mid, "pi"],
            normalize_lookup_key(mid): [stem, "samāpattiyā"],
            normalize_lookup_key(stem): [
                "ne",
                "va",
                "saññā",
                "nā",
                "saññā",
                "yatana",
            ],
        }
        composed = compose_finer_break_parts(word, breaks[word], breaks)
        self.assertEqual(
            composed,
            ["ne", "va", "saññā", "nā", "saññā", "yatanasamāpattiyāpi"],
        )
        thai = convert(word, Script.ROMAN, Script.THAI)
        out = inject_soft_breaks_in_thai(thai, word, breaks, min_roman_len=15)
        self.assertGreaterEqual(out.count(SOFT_BREAK_MARKER), 3)
        self.assertEqual(out.replace(SOFT_BREAK_MARKER, ""), thai)

    def test_compose_rejects_when_max_chunk_worsens(self) -> None:
        # Guard: do not accept a refine that enlarges the longest Thai chunk.
        word = "abcdefghijklmnop"
        # Coarse 8|8; "finer" head of 4 yields 3 + 13 — worse max chunk.
        breaks = {
            normalize_lookup_key(word): ["abcdefgh", "ijklmnop"],
            normalize_lookup_key("abcdefgh"): ["abc", "defgh"],
        }
        composed = compose_finer_break_parts(word, breaks[word], breaks)
        self.assertEqual(composed, ["abcdefgh", "ijklmnop"])

    def test_compose_expands_known_tail_after_prefix(self) -> None:
        # ``na|nevavipākanavipākadhammadhammo`` — head is a short prefix; the
        # usable finer split lives on the tail key.
        word = "nanevavipākanavipākadhammadhammo"
        tail = "nevavipākanavipākadhammadhammo"
        breaks = {
            normalize_lookup_key(word): ["na", tail],
            normalize_lookup_key(tail): [
                "ne",
                "va",
                "vipāka",
                "na",
                "vipāka",
                "dhamma",
                "dhammo",
            ],
        }
        composed = compose_finer_break_parts(word, breaks[word], breaks)
        self.assertEqual(
            composed,
            ["na", "ne", "va", "vipāka", "na", "vipāka", "dhamma", "dhammo"],
        )
        thai = convert(word, Script.ROMAN, Script.THAI)
        out = inject_soft_breaks_in_thai(thai, word, breaks, min_roman_len=15)
        self.assertGreaterEqual(out.count(SOFT_BREAK_MARKER), 4)
        self.assertEqual(out.replace(SOFT_BREAK_MARKER, ""), thai)


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

    def test_civara_parikkha_inflection_overrides_inject(self) -> None:
        # DPD cache has …parikkhārā / …raṃ / …rānaṃ but misses these endings
        # (01Vin01 p.177 overflow: …parikkhātena).
        stem = [
            "cīvara",
            "piṇḍapāta",
            "senāsana",
            "gilānappaccaya",
            "bhesajja",
        ]
        cases = {
            "cīvarapiṇḍapātasenāsanagilānappaccayabhesajjaparikkhārena": (
                stem + ["parikkhārena"]
            ),
            "cīvarapiṇḍapātasenāsanagilānappaccayabhesajjaparikkhātena": (
                stem + ["parikkhātena"]
            ),
        }
        for word, parts in cases.items():
            with self.subTest(word=word):
                self.assertEqual("".join(parts), word)
                self.assertIsNotNone(thai_slices_from_roman_chunks(word, parts))
                thai = convert(word, Script.ROMAN, Script.THAI)
                out = inject_soft_breaks_in_thai(
                    thai,
                    word,
                    {normalize_lookup_key(word): parts},
                    min_thai_len=15,
                )
                self.assertIn(SOFT_BREAK_MARKER, out)
                self.assertEqual(out.replace(SOFT_BREAK_MARKER, ""), thai)
                self.assertGreaterEqual(out.count(SOFT_BREAK_MARKER), 5)

    @unittest.skipUnless(
        DEFAULT_OVERRIDES_PATH.is_file(), "overrides file not present"
    )
    def test_repo_overrides_include_tiracchana_case(self) -> None:
        loaded = load_break_overrides()
        key = normalize_lookup_key("tiracchānanagatubhatobyañjanakassa")
        self.assertIn(key, loaded)
        self.assertEqual("".join(loaded[key]), key)

    @unittest.skipUnless(
        DEFAULT_OVERRIDES_PATH.is_file(), "overrides file not present"
    )
    def test_repo_overrides_include_civara_parikkha_inflections(self) -> None:
        loaded = load_break_overrides()
        for word in (
            "cīvarapiṇḍapātasenāsanagilānappaccayabhesajjaparikkhārena",
            "cīvarapiṇḍapātasenāsanagilānappaccayabhesajjaparikkhātena",
            "cīvarapiṇḍapātasenāsanagilānappaccayabhesajjaparikkhārehi",
            "cīvarapiṇḍapātasenāsanagilānappaccayabhesajjaparikkhāran",
            "cīvarapiṇḍapātasenāsanagilānappaccayabhesajjaparikkhārānan",
            "itarītaracīvarapiṇḍapātasenāsanagilānappaccayabhesajjaparikkhārena",
        ):
            with self.subTest(word=word):
                key = normalize_lookup_key(word)
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


class PartialExtensionTests(unittest.TestCase):
    """Decompose a missing word as (known break key) + (leftover run).

    Regression for the curated-review-queue tool: a missing word whose prefix
    or suffix is already a break key should be detectable, and the proposed
    split (known parts + leftover) should slice cleanly into Thai prefixes
    when the boundary is on a real morpheme edge.
    """

    def test_prefix_extension_reuses_known_parts_and_appends_tail(self) -> None:
        from scan_sandhi_partial_extensions import (
            candidate_parts_prefix,
            find_prefix_extension,
        )

        # ``cīvarapiṇḍapātasenāsanagilānapaccayabhesajjaparikkhārānan`` is
        # missing; its prefix ``…parikkhārā`` is a known break key. The leftover
        # ``nan`` is kept as one unsplit chunk (no data for it).
        breaks = {
            "cīvarapiṇḍapātasenāsanagilānapaccayabhesajjaparikkhārā": [
                "cīvara",
                "piṇḍapāta",
                "senāsana",
                "gilānapaccaya",
                "bhesajja",
                "parikkhārā",
            ]
        }
        word = "cīvarapiṇḍapātasenāsanagilānapaccayabhesajjaparikkhārānan"
        hit = find_prefix_extension(word, breaks, min_key_len=8)
        self.assertIsNotNone(hit)
        assert hit is not None
        matched_key, known_parts, tail = hit
        self.assertEqual(matched_key, "cīvarapiṇḍapātasenāsanagilānapaccayabhesajjaparikkhārā")
        self.assertEqual(tail, "nan")
        parts = candidate_parts_prefix(known_parts, tail)
        self.assertEqual(parts[-1], "nan")
        self.assertEqual("".join(parts), word)
        # Thai-slice must accept the boundary: each piece is a clean Thai prefix.
        self.assertIsNotNone(thai_slices_from_roman_chunks(word, parts))

    def test_suffix_extension_prepends_head_to_known_parts(self) -> None:
        from scan_sandhi_partial_extensions import (
            candidate_parts_suffix,
            find_suffix_extension,
        )

        # ``asammāsambuddhappavedito`` is missing; its suffix
        # ``sammāsambuddhappavedito`` is a known break key. The leftover head
        # ``a`` is kept as one unsplit chunk.
        breaks = {
            "sammāsambuddhappavedito": ["sammāsambuddha", "ppavedito"]
        }
        word = "asammāsambuddhappavedito"
        hit = find_suffix_extension(word, breaks, min_key_len=8)
        self.assertIsNotNone(hit)
        assert hit is not None
        head, matched_key, known_parts = hit
        self.assertEqual(head, "a")
        self.assertEqual(matched_key, "sammāsambuddhappavedito")
        parts = candidate_parts_suffix(head, known_parts)
        self.assertEqual(parts[0], "a")
        self.assertEqual("".join(parts), word)
        self.assertIsNotNone(thai_slices_from_roman_chunks(word, parts))

    def test_no_extension_when_word_is_itself_a_key(self) -> None:
        from scan_sandhi_partial_extensions import (
            find_prefix_extension,
            find_suffix_extension,
        )

        breaks = {"abcdefgh": ["abcd", "efgh"]}
        # The exact key is excluded (it already has a break — no extension).
        self.assertIsNone(find_prefix_extension("abcdefgh", breaks, min_key_len=4))
        self.assertIsNone(find_suffix_extension("abcdefgh", breaks, min_key_len=4))

    def test_short_anchor_below_min_key_len_ignored(self) -> None:
        from scan_sandhi_partial_extensions import find_prefix_extension

        # ``cī`` is too short to be a trustworthy anchor.
        breaks = {"cī": ["cī"]}
        self.assertIsNone(
            find_prefix_extension("cīvarapiṇḍapāta", breaks, min_key_len=8)
        )

    def test_thai_slice_rejects_non_morpheme_boundary(self) -> None:
        """Greedy longest-suffix can pass string match but cut at a wrong edge.

        ``kaḷ|ambadāyaka…`` is not a real morpheme boundary even though the
        suffix ``ambadāyaka…`` is a known break key. The Thai-slice guard must
        reject it so the review queue can flag it for human eyes.
        """
        from scan_sandhi_partial_extensions import (
            candidate_parts_suffix,
            find_suffix_extension,
        )

        breaks = {
            "ambadāyakattherassāpadānaṃ": [
                "ambadāyaka",
                "tthera",
                "assāpadānaṃ",
            ]
        }
        word = "kaḷambadāyakattherassāpadānaṃ"
        hit = find_suffix_extension(word, breaks, min_key_len=8)
        # String match finds the suffix, but the proposed split must NOT slice
        # cleanly into Thai prefixes — that is the signal to skip auto-apply.
        self.assertIsNotNone(hit)
        assert hit is not None
        head, _matched_key, known_parts = hit
        parts = candidate_parts_suffix(head, known_parts)
        self.assertIsNone(thai_slices_from_roman_chunks(word, parts))


if __name__ == "__main__":
    unittest.main()
