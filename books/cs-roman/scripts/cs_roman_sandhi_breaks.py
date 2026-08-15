"""Sandhi / compound soft-break helpers for cs-roman TeX generate.

Reads precomputed Digital Pāḷi Dictionary ``lookup.deconstructor`` (and
optionally headword ``construction``) from a local ``dpd.db``. Inserts
``{{sb}}`` markers between Thai morphemes so generate can emit TeX
``\\-`` without mutating stored Roman / Thai segment text.
"""

from __future__ import annotations

import json
import re
import sqlite3
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from paths import BOOKS, VOLUMES_DIR, ensure_import_paths

ensure_import_paths()

from pali_script import Script, convert  # noqa: E402

from scan_long_words import (  # noqa: E402
    MARKER_RE,
    TOKEN_RE,
    roman_letter_len,
    roman_strings,
    thai_display_len,
)

VENDOR_DPD_DIR = BOOKS / "vendor" / "dpd"
DEFAULT_DB_PATH = VENDOR_DPD_DIR / "dpd.db"
DEFAULT_CACHE_PATH = BOOKS / "shared" / "sandhi_breaks.json"
# Curated surface splits when DPD lookup / align cannot provide a break.
# Wins over the DPD cache for the same Roman key; not rewritten by rebuild.
DEFAULT_OVERRIDES_PATH = BOOKS / "shared" / "sandhi_breaks_overrides.json"

# Inline marker consumed by generate_cs_roman_tex (parallel to {{sp1}}).
SOFT_BREAK_MARKER = "{{sb}}"

# Default: only long Roman tokens get soft breaks (build + inject).
DEFAULT_MIN_ROMAN_LEN = 15
# Back-compat alias for older imports / call sites.
DEFAULT_MIN_THAI_LEN = DEFAULT_MIN_ROMAN_LEN
# Minimum Thai display glyphs on EACH side of an injected soft break.
# A break that leaves a sub-3-glyph fragment (e.g. trailing ``pi`` → ``ปิ``)
# produces a typographic widow; skip such break points even when the
# sandhi split itself is linguistically valid.
DEFAULT_MIN_FRAGMENT_LEN = 3

_TOKEN_RE = re.compile(
    r"[^\W\d_]+(?:-[^\W\d_]+)*",
    re.UNICODE,
)
_MARKER_RE = re.compile(r"\{\{(?:n\d+|\*|sp1|sp3|sb|\+|\[\]|\(\))\}\}")

# Vowel length / niggahita folding for surface ↔ construction align.
_FOLD = str.maketrans(
    {
        "Ā": "a",
        "ā": "a",
        "Ī": "i",
        "ī": "i",
        "Ū": "u",
        "ū": "u",
        "Ṁ": "m",
        "ṁ": "m",
        "Ṃ": "m",
        "ṃ": "m",
        "Ṅ": "n",
        "ṅ": "n",
        "Ñ": "n",
        "ñ": "n",
        "Ṇ": "n",
        "ṇ": "n",
    }
)

# Folded vowel set (used by elision / same-vowel-merge sandhi rules).
_VOWELS_FOLD = frozenset("aiuoe")

# Folded nasal set for niggahita assimilation (``ṃ + c → ñc``, ``ṃ + k → ṅk``).
# The surface nasal folds to one of these before the next consonant.
_NIGGAHITA_NASALS_FOLD = frozenset("nm")

# Nominal case endings stripped when a surface word has no ``lookup`` row, to
# recover the stem in ``dpd_headwords.lemma_1``. Ordered longest-first so the
# most specific ending is tried before the bare-vowel fallbacks.
_CASE_ENDINGS = (
    "smiṃ", "smi", "mhā", "mhi",
    "ānaṃ", "ānaṃ", "āni", "assa", "āyaṃ", "āya",
    "enaṃ", "ena", "esu", "eso", "yo", "to",
    "ā", "ī", "ū", "e", "o", "u", "i", "a", "ṃ",
)

# Cross-vowel contraction: surface long/diphthong vowel ← (part1 final short
# vowel + part2 initial short vowel). Used when part2 starts on a surface
# vowel that is the sandhi result, not its own initial vowel. Maps
# surface_vowel → set of part2 initial vowels that can contract INTO it
# (with part1's final vowel absorbed). E.g. surface ``ā`` ← part2 ``i``
# via ``a + i → ā`` (``paramatthena`` + ``iti`` → ``paramatthenāti``).
_CONTRACTION_TO: dict[str, frozenset[str]] = {
    "ā": frozenset("aiuā"),   # a+a→ā, a+i→ā, a+u→ā(←o), ā+any→ā
    "e": frozenset("ei"),     # a+e→e, a+i→e
    "o": frozenset("ou"),     # a+o→o, a+u→o
    "ī": frozenset("i"),      # i+i→ī
    "ū": frozenset("u"),      # u+u→ū
}


def normalize_lookup_key(word: str) -> str:
    """DPD lookup keys are lowercase; unify niggahita spellings."""
    w = word.strip().lower().replace("-", "")
    return w.replace("ṁ", "ṃ")


def fold_roman(s: str) -> str:
    return s.translate(_FOLD).lower().replace("-", "")


def parse_plus_parts(spec: str) -> list[str]:
    """Split a deconstructor / construction string on ``+``.

    Strips DPD ``<b>…</b>`` tags and ``>`` derivation markers. For
    ``compound_construction`` use :func:`parse_compound_construction` instead —
    it also drops the bold case-ending content from the first part.
    """
    cleaned = spec.replace("<b>", "").replace("</b>", "")
    cleaned = cleaned.replace(">", "+")
    # Some construction entries embed a newline-separated alt form; keep only
    # the first line (the primary construction).
    cleaned = cleaned.split("\n")[0]
    return [p.strip() for p in cleaned.split("+") if p.strip()]


def parse_compound_construction(spec: str) -> list[str]:
    """Parse ``compound_construction``: strip ``<b>…</b>`` CONTENT from part1.

    DPD ``compound_construction`` marks the case ending of the first part that
    sandhi absorbs with ``<b>…</b>``. When the bold ending is a vowel + ``ṃ``
    (``aṃ``), the vowel survives the niggahita-doubling sandhi (``aṃ + p →
    app``) and only the ``ṃ`` is dropped — so strip just ``ṃ``. Otherwise strip
    the whole bold content (``āya``, ``ena``, ``assa`` are fully absorbed).
    """
    import re

    bold = re.search(r"<b>(.*?)</b>", spec)
    if bold:
        content = bold.group(1)
        if content.endswith("ṃ") and len(content) >= 2:
            # Niggahita doubling: keep the vowel, drop only the ṃ.
            replacement = content[:-1]  # keep vowel, drop ṃ
            spec = spec.replace(f"<b>{content}</b>", replacement)
        else:
            spec = spec.replace(f"<b>{content}</b>", "")
    else:
        spec = spec.replace("<b>", "").replace("</b>", "")
    spec = spec.split("\n")[0]
    return [p.strip() for p in spec.split("+") if p.strip()]


def pick_break_parts(word: str, candidates: Iterable[str]) -> list[str] | None:
    """Choose a candidate split that aligns to ``word``; return Roman parts."""
    key = normalize_lookup_key(word)
    best: list[str] | None = None
    best_breaks = -1
    for cand in candidates:
        parts = parse_plus_parts(cand)
        if len(parts) < 2:
            continue
        if align_parts(key, parts) is not None:
            if len(parts) > best_breaks:
                best = parts
                best_breaks = len(parts)
    return best


def surface_chunks(word: str, parts: list[str]) -> list[str] | None:
    """Slice ``word`` at aligned break offsets (surface forms, not stems)."""
    key = normalize_lookup_key(word)
    breaks = align_parts(key, parts)
    if breaks is None:
        return None
    snapped = snap_roman_breaks(key, breaks)
    if snapped is None:
        return None
    chunks: list[str] = []
    prev = 0
    for off in snapped:
        if off <= prev or off >= len(key):
            return None
        chunks.append(key[prev:off])
        prev = off
    if prev >= len(key):
        return None
    chunks.append(key[prev:])
    return chunks if len(chunks) >= 2 else None


def snap_roman_breaks(word: str, breaks: list[int]) -> list[int] | None:
    """Nudge Roman offsets so ``convert(word[:off])`` is a prefix of ``convert(word)``.

    Needed when sandhi lengthens a vowel at the boundary (``nivāsa`` + ``anussati``
    inside ``…nivāsānussati…``): the aligner may land on a short ``a`` while Thai
    orthography only prefixes cleanly after the long ``ā``.
    """
    solid_thai = convert(word, Script.ROMAN, Script.THAI)
    snapped: list[int] = []
    prev_thai_len = 0
    for off in breaks:
        found: int | None = None
        for delta in (0, 1, -1, 2, -2, 3, -3):
            cand = off + delta
            if cand <= (snapped[-1] if snapped else 0) or cand >= len(word):
                continue
            pref = convert(word[:cand], Script.ROMAN, Script.THAI)
            if (
                pref
                and solid_thai.startswith(pref)
                and len(pref) > prev_thai_len
            ):
                found = cand
                prev_thai_len = len(pref)
                break
        if found is None:
            return None
        snapped.append(found)
    return snapped


def thai_slices_from_roman_chunks(word: str, chunks: list[str]) -> list[str] | None:
    """Slice solid Thai at prefix lengths of successive Roman chunk joins."""
    solid = normalize_lookup_key(word)
    solid_thai = convert(solid, Script.ROMAN, Script.THAI)
    out: list[str] = []
    pos = 0
    thai_pos = 0
    for i, chunk in enumerate(chunks):
        pos += len(chunk)
        if i == len(chunks) - 1:
            piece = solid_thai[thai_pos:]
            if not piece or unicodedata.category(piece[0]) == "Mn":
                return None
            out.append(piece)
            break
        pref = convert(solid[:pos], Script.ROMAN, Script.THAI)
        if not solid_thai.startswith(pref) or len(pref) <= thai_pos:
            return None
        # Do not start a Thai piece on a nonspacing mark (ิ ฺ ํ …).
        cut = len(pref)
        while cut < len(solid_thai) and unicodedata.category(solid_thai[cut]) == "Mn":
            cut += 1
        if cut <= thai_pos or cut >= len(solid_thai):
            return None
        piece = solid_thai[thai_pos:cut]
        if not piece or unicodedata.category(piece[0]) == "Mn":
            return None
        out.append(piece)
        thai_pos = cut
    return out if len(out) == len(chunks) else None


def align_parts(word: str, parts: list[str]) -> list[int] | None:
    """Return break character offsets in ``word`` after each part except last.

    Matching is left-to-right with vowel-length / niggahita folding. The last
    part may consume a longer inflectional tail (``ñāṇa`` → ``ñāṇāya``).
    Sandhi vowel fusion (``a``+``ā`` → ``ā``) is resolved with lookahead so the
    shared long vowel stays with the following part when needed.
    """
    if len(parts) < 2:
        return None
    # Fast path: exact concatenation.
    if "".join(parts) == word:
        offsets: list[int] = []
        pos = 0
        for part in parts[:-1]:
            pos += len(part)
            offsets.append(pos)
        return offsets

    return _align_parts_flex(word, parts, 0)


def _align_parts_flex(
    word: str, parts: list[str], start: int
) -> list[int] | None:
    """Recursive flexible align from ``parts[0]`` at ``word[start:]``."""
    if not parts:
        return [] if start == len(word) else None
    part = parts[0]
    rest = parts[1:]
    is_last = not rest
    for end in _candidate_ends(word, start, part, is_last=is_last):
        if is_last:
            return [] if end == len(word) else None
        sub = _align_parts_flex(word, rest, end)
        if sub is not None:
            return [end, *sub]
    return None


def _candidate_ends(
    word: str, start: int, part: str, *, is_last: bool
) -> list[int]:
    """Possible end indices in ``word`` after matching ``part`` at ``start``."""
    rem = word[start:]
    if not rem or not part:
        return []
    ends: list[int] = []
    if rem.startswith(part):
        ends.append(start + len(part))
        if is_last:
            # Prefer consuming the whole inflectional tail.
            return [len(word)] if start + len(part) <= len(word) else ends

    fold_part = fold_roman(part)
    wj = 0
    pj = 0
    # Contraction entry: if part starts with a vowel and the surface starts
    # with a different long/diphthong vowel that is the sandhi result of
    # (previous part's final vowel + this part's initial vowel), allow the
    # part to start by consuming the surface vowel as its contracted initial.
    # E.g. part ``iti`` at surface ``āti…`` (from ``…a + iti → …āti``):
    # surface ``ā`` is consumed as part's ``i`` (a+i→ā contraction).
    if (
        pj == 0
        and fold_part
        and fold_part[0] in _VOWELS_FOLD
        and rem
        and rem[0] in _CONTRACTION_TO
        and fold_part[0] in _CONTRACTION_TO[rem[0]]
    ):
        # Consume the surface contraction vowel as part's initial vowel.
        wj = 1
        pj = 1
    elif (
        pj == 0
        and len(fold_part) >= 2
        and fold_part[0] not in _VOWELS_FOLD
        and len(rem) >= 2
        and fold_roman(rem[0]) == fold_part[0]
        and fold_roman(rem[1]) == fold_part[0]
    ):
        # Niggahita consonant doubling: ``aṃ + p → app`` leaves the surface
        # with a doubled consonant. Skip the first (niggahita-inserted) copy
        # so part2 ``paṭipanna`` matches surface ``ppaṭipanna…`` starting at
        # the second ``p``.
        wj = 1
        pj = 0
    elif (
        pj == 0
        and len(fold_part) >= 2
        and fold_part[0] not in _VOWELS_FOLD
        and len(rem) >= 2
        and fold_roman(rem[0]) in _NIGGAHITA_NASALS_FOLD
        and fold_roman(rem[1]) == fold_part[0]
    ):
        # Niggahita nasal assimilation: ``ṃ + c → ñc``, ``ṃ + k → ṅk``,
        # ``ṃ + t → nt``, ``ṃ + p → mp``. The surface gets a homorganic nasal
        # before the consonant; skip the nasal so part2 ``ca`` matches surface
        # ``ñca…`` starting at ``c``.
        wj = 1
        pj = 0
    while pj < len(fold_part) and wj < len(rem):
        if fold_roman(rem[wj]) != fold_part[pj]:
            break
        wj += 1
        pj += 1
    if pj == len(fold_part):
        flex_end = start + wj
        if flex_end not in ends:
            ends.append(flex_end)
        # Sandhi vowel fusion: if part ends with a short vowel and word has the
        # long counterpart, also try ending before that long vowel so the next
        # part can claim it (``picchilla`` + ``ādīnaṃ`` in ``…picchillādīnaṃ``,
        # and contraction ``na``+``asaññā`` → ``nāsaññā``).
        if (
            not is_last
            and wj > 0
            and part[-1] in "aiuāīū"
            and rem[wj - 1] in "āīū"
        ):
            short_end = start + wj - 1
            if short_end > start and short_end not in ends:
                ends.append(short_end)
        # Same-vowel merge: ``na`` + ``attha`` → ``nattha`` (a+a → a, the single
        # surface vowel is shared; part gives up its final vowel so the next
        # part can start at it). Only when the next surface char is a consonant
        # (otherwise the next part would start on a vowel it cannot match).
        if (
            not is_last
            and wj > 0
            and wj < len(rem)
            and part[-1] in "aiu"
            and rem[wj - 1] == part[-1]
            and fold_roman(rem[wj]) not in _VOWELS_FOLD
        ):
            merge_end = start + wj - 1
            if merge_end > start and merge_end not in ends:
                ends.append(merge_end)
    elif pj == len(fold_part) - 1 and pj > 0:
        # Elision: fold match broke on the last char of part (a vowel) because
        # the surface has a different vowel there (``na`` + ``eva`` → ``neva``:
        # part ``na`` should map to ``n``, with ``a`` absorbed before ``e``).
        # Try ending at the break so the next part claims the surface vowel.
        if (
            fold_part[pj] in _VOWELS_FOLD
            and wj < len(rem)
            and fold_roman(rem[wj]) in _VOWELS_FOLD
            and fold_part[pj] != fold_roman(rem[wj])
        ):
            elision_end = start + wj
            if elision_end > start and elision_end not in ends:
                ends.append(elision_end)
        # Niggahita drop: part ends in ``ṃ`` (folded to ``m``) and the surface
        # at the break is a consonant — the ``ṃ`` is absorbed/dropped before
        # the next consonant (``evaṃsukhadukkhaṃ`` + ``ppaṭisaṃvedī`` →
        # ``evaṃsukhadukkhappaṭisaṃvedī``: part1's final ``ṃ`` is dropped).
        if (
            not is_last
            and part[-1] == "ṃ"
            and wj < len(rem)
            and fold_roman(rem[wj]) not in _VOWELS_FOLD
        ):
            nig_end = start + wj
            if nig_end > start and nig_end not in ends:
                ends.append(nig_end)

    if is_last:
        # Stem matched as prefix; case ending may follow. Also accept a
        # last-vowel substitution (stem ``...ga`` + nom. ``o`` → surface
        # ``...go``) where the fold match broke on the final vowel: the stem
        # is still a valid prefix up to that point.
        out: list[int] = []
        for e in ends:
            if e <= len(word):
                out.append(len(word))
        if not out and pj > 0 and pj >= len(fold_part) - 1:
            # Partial fold match reached the tail of the part: treat as stem
            # match with a different case-ending vowel.
            stem_end = start + wj
            if stem_end <= len(word) and stem_end > start:
                out.append(len(word))
        # Deduplicate while preferring full consume.
        return [len(word)] if out else []

    # Prefer longer exact-ish matches first, then shorter sandhi variants.
    return sorted(set(ends), reverse=True)


@dataclass(frozen=True)
class SandhiBreak:
    """Surface Roman chunks and matching Thai pieces for one solid token."""

    roman: str
    parts_roman: tuple[str, ...]
    parts_thai: tuple[str, ...]

    @property
    def thai_solid(self) -> str:
        return "".join(self.parts_thai)

    @property
    def thai_with_markers(self) -> str:
        return SOFT_BREAK_MARKER.join(self.parts_thai)


class DpdSandhiLookup:
    """Read-only access to DPD deconstructor / construction data."""

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        if not self.db_path.is_file():
            raise FileNotFoundError(
                f"DPD database not found: {self.db_path}. "
                "Run: python books/cs-roman/scripts/fetch_dpd_db.py"
            )
        self._con = sqlite3.connect(
            f"file:{self.db_path.resolve().as_posix()}?mode=ro",
            uri=True,
        )
        self._con.row_factory = sqlite3.Row

    def close(self) -> None:
        self._con.close()

    def __enter__(self) -> DpdSandhiLookup:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def deconstructor_candidates(self, word: str) -> list[str]:
        key = normalize_lookup_key(word)
        row = self._con.execute(
            "SELECT deconstructor, headwords FROM lookup WHERE lookup_key = ?",
            (key,),
        ).fetchone()
        out: list[str] = []
        if row and row["deconstructor"]:
            try:
                loaded = json.loads(row["deconstructor"])
            except json.JSONDecodeError:
                loaded = []
            if isinstance(loaded, list):
                out.extend(str(x) for x in loaded if x)

        # Headword construction fallback when deconstructor empty / unusable.
        # Try compound_construction first (sandhi-resolved at the compound level,
        # closer to surface than the stem-level construction), then construction.
        if row and row["headwords"]:
            try:
                ids = json.loads(row["headwords"])
            except json.JSONDecodeError:
                ids = []
            for hid in ids[:5]:
                crow = self._con.execute(
                    "SELECT construction, compound_construction "
                    "FROM dpd_headwords WHERE id = ?",
                    (int(hid),),
                ).fetchone()
                if not crow:
                    continue
                cc = crow["compound_construction"] or ""
                if cc and "+" in cc:
                    out.append(" + ".join(parse_compound_construction(str(cc))))
                cons = crow["construction"] or ""
                if cons and "+" in cons:
                    out.append(str(cons))

        # No lookup row: try stripping a sandhi prefix (na/neva/no) and looking
        # up the remainder, then stripping a case ending and looking up the
        # stem in dpd_headwords.lemma_1. These recover inflected / negated
        # forms DPD does not index in ``lookup``.
        if not row:
            out.extend(self._fallback_candidates(key))
        return out

    def _fallback_candidates(self, key: str) -> list[str]:
        """Recover construction data for words with no ``lookup`` row."""
        out: list[str] = []
        # 1. Strip a negation/sandhi prefix and look up the remainder.
        for pfx in ("neva", "na", "no"):
            if not key.startswith(pfx) or len(key) - len(pfx) < 8:
                continue
            rest = key[len(pfx):]
            row = self._con.execute(
                "SELECT deconstructor, headwords FROM lookup WHERE lookup_key = ?",
                (rest,),
            ).fetchone()
            if row and (row["deconstructor"] or row["headwords"]):
                # Rebuild the full split: prefix + the remainder's parts.
                # Deconstructor gives surface parts; prepend the prefix.
                if row["deconstructor"]:
                    try:
                        loaded = json.loads(row["deconstructor"])
                    except json.JSONDecodeError:
                        loaded = []
                    if isinstance(loaded, list):
                        for spec in loaded:
                            if "+" in spec:
                                parts = parse_plus_parts(spec)
                                out.append(pfx + " + " + " + ".join(parts))
                if row["headwords"]:
                    try:
                        ids = json.loads(row["headwords"])
                    except json.JSONDecodeError:
                        ids = []
                    for hid in ids[:3]:
                        crow = self._con.execute(
                            "SELECT construction, compound_construction "
                            "FROM dpd_headwords WHERE id = ?",
                            (int(hid),),
                        ).fetchone()
                        if not crow:
                            continue
                        for field, is_cc in (
                            (crow["compound_construction"] or "", True),
                            (crow["construction"] or "", False),
                        ):
                            if field and "+" in field:
                                if is_cc:
                                    parts = parse_compound_construction(field)
                                else:
                                    parts = parse_plus_parts(field)
                                out.append(pfx + " + " + " + ".join(parts))
                break  # first matching prefix is enough

        # 2. Strip a case ending and look up the stem in dpd_headwords.lemma_1.
        if not out:
            for end in _CASE_ENDINGS:
                if not key.endswith(end) or len(key) - len(end) < 6:
                    continue
                stem = key[: -len(end)]
                # lemma_1 is usually the a-stem nominative singular; try the
                # bare stem and the stem + 'a' (if stem ends in a consonant).
                candidates = [stem]
                if stem and stem[-1] not in "aiuāīūeoṃ":
                    candidates.append(stem + "a")
                for cand in candidates:
                    h = self._con.execute(
                        "SELECT construction, compound_construction "
                        "FROM dpd_headwords WHERE lemma_1 = ?",
                        (cand,),
                    ).fetchone()
                    if h and (h["compound_construction"] or h["construction"]):
                        cc = h["compound_construction"] or ""
                        if cc and "+" in cc:
                            out.append(" + ".join(parse_compound_construction(str(cc))))
                        cons = h["construction"] or ""
                        if cons and "+" in cons:
                            out.append(str(cons))
                        break
                if out:
                    break
        return out

    def break_for_word(self, word: str) -> SandhiBreak | None:
        solid = normalize_lookup_key(word)
        if not solid:
            return None
        dict_parts = pick_break_parts(solid, self.deconstructor_candidates(solid))
        if not dict_parts:
            return None
        chunks = surface_chunks(solid, dict_parts)
        if not chunks:
            return None
        thai_parts = thai_slices_from_roman_chunks(solid, chunks)
        if not thai_parts:
            return None
        return SandhiBreak(
            roman=solid,
            parts_roman=tuple(chunks),
            parts_thai=tuple(thai_parts),
        )


def _parse_breaks_map(
    raw: object,
    *,
    require_concat: bool = False,
) -> dict[str, list[str]]:
    """Normalize a ``breaks`` object into ``roman → [surface parts…]``.

    When ``require_concat`` is true (curated overrides), drop entries whose
    parts do not concatenate to the key — surface chunks must spell the token.
    """
    if not isinstance(raw, dict):
        return {}
    out: dict[str, list[str]] = {}
    for k, v in raw.items():
        if not isinstance(v, list) or len(v) < 2:
            continue
        if not all(isinstance(x, str) for x in v):
            continue
        key = normalize_lookup_key(str(k))
        parts = [normalize_lookup_key(x) for x in v]
        if require_concat and "".join(parts) != key:
            continue
        out[key] = parts
    return out


def load_break_cache(path: Path | None = None) -> dict[str, list[str]]:
    """Load ``roman → [roman_parts…]`` cache; empty dict if missing."""
    p = Path(path) if path else DEFAULT_CACHE_PATH
    if not p.is_file():
        return {}
    data = json.loads(p.read_text(encoding="utf-8"))
    breaks = data.get("breaks") if isinstance(data, dict) else data
    return _parse_breaks_map(breaks, require_concat=False)


def load_break_overrides(path: Path | None = None) -> dict[str, list[str]]:
    """Load curated overrides; empty dict if missing.

    Parts must concatenate to the Roman key (edition surface form) and must
    slice to Thai prefixes of the solid conversion (same rule as inject).
    """
    p = Path(path) if path else DEFAULT_OVERRIDES_PATH
    if not p.is_file():
        return {}
    data = json.loads(p.read_text(encoding="utf-8"))
    breaks = data.get("breaks") if isinstance(data, dict) else data
    parsed = _parse_breaks_map(breaks, require_concat=True)
    out: dict[str, list[str]] = {}
    for key, parts in parsed.items():
        if thai_slices_from_roman_chunks(key, parts) is None:
            continue
        out[key] = parts
    return out


def merge_break_maps(
    base: dict[str, list[str]],
    overrides: dict[str, list[str]],
) -> dict[str, list[str]]:
    """Return ``base`` with ``overrides`` winning on key collision."""
    if not overrides:
        return dict(base)
    merged = dict(base)
    merged.update(overrides)
    return merged


def save_break_cache(
    breaks: dict[str, list[str]],
    path: Path | None = None,
    *,
    min_roman_len: int = DEFAULT_MIN_ROMAN_LEN,
    source_db: str | None = None,
) -> Path:
    p = Path(path) if path else DEFAULT_CACHE_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "min_roman_len": min_roman_len,
        "source_db": source_db,
        "count": len(breaks),
        "breaks": {
            k: v
            for k, v in sorted(breaks.items(), key=lambda kv: (len(kv[0]), kv[0]))
        },
    }
    p.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return p


def collect_roman_tokens(volume_glob: str | None = None) -> set[str]:
    """Unique normalized Roman tokens from volume ``segments.json`` files."""
    words: set[str] = set()
    paths = sorted(VOLUMES_DIR.glob("*/data/segments.json"))
    if volume_glob:
        paths = [p for p in paths if volume_glob in p.parts]
    for seg_path in paths:
        data = json.loads(seg_path.read_text(encoding="utf-8"))
        for seg in data.get("segments") or []:
            for raw in roman_strings(seg):
                cleaned = MARKER_RE.sub(" ", raw)
                for match in TOKEN_RE.finditer(cleaned):
                    words.add(normalize_lookup_key(match.group(0)))
    return words


def rebuild_sandhi_break_cache(
    *,
    volume: str | None = None,
    min_roman_len: int = DEFAULT_MIN_ROMAN_LEN,
    db_path: Path | None = None,
    out_path: Path | None = None,
    progress: bool = True,
) -> tuple[Path, int, int]:
    """Scan volumes + DPD; write cache. Returns (path, hits, long_token_count)."""
    db = Path(db_path) if db_path else DEFAULT_DB_PATH
    out = Path(out_path) if out_path else DEFAULT_CACHE_PATH
    tokens = collect_roman_tokens(volume)
    long_tokens = sorted(
        w for w in tokens if roman_letter_len(w) >= min_roman_len
    )
    breaks: dict[str, list[str]] = {}
    hit = miss = 0
    with DpdSandhiLookup(db) as dpd:
        for i, word in enumerate(long_tokens, 1):
            sb = dpd.break_for_word(word)
            if sb is None:
                miss += 1
            else:
                hit += 1
                breaks[sb.roman] = list(sb.parts_roman)
            if progress and (i % 500 == 0 or i == len(long_tokens)):
                print(f"  … {i}/{len(long_tokens)} hit={hit} miss={miss}")
    path = save_break_cache(
        breaks,
        out,
        min_roman_len=min_roman_len,
        source_db=str(db),
    )
    return path, hit, len(long_tokens)


def ensure_sandhi_break_cache(
    *,
    force: bool = False,
    min_roman_len: int = DEFAULT_MIN_ROMAN_LEN,
    quiet: bool = False,
) -> dict[str, list[str]]:
    """Return sandhi break map; build from DPD if cache missing and DB present.

    Always merges ``shared/sandhi_breaks_overrides.json`` on top (overrides win).
    Used by TeX generate for every mode so ``build.ps1`` / batch prepare do not
    need a separate manual cache step. Does **not** download ``dpd.db`` (too
    large); run ``fetch_dpd_db.py`` once when the cache must be (re)built.
    """
    cache_path = DEFAULT_CACHE_PATH
    base: dict[str, list[str]] = {}
    if cache_path.is_file() and not force:
        base = load_break_cache(cache_path)
    elif not DEFAULT_DB_PATH.is_file():
        if not quiet:
            print(
                "sandhi soft breaks: no cache and no vendor/dpd/dpd.db "
                f"(expected {cache_path.name}); generate continues without \\- "
                "(curated overrides still apply if present)",
                flush=True,
            )
    else:
        if not quiet:
            print(
                "sandhi soft breaks: building cache from DPD "
                f"({DEFAULT_DB_PATH.name}) …",
                flush=True,
            )
        path, hit, total = rebuild_sandhi_break_cache(
            min_roman_len=min_roman_len,
            progress=not quiet,
        )
        if not quiet:
            print(
                f"sandhi soft breaks: wrote {path.name} "
                f"entries={hit} coverage={hit}/{total}",
                flush=True,
            )
        base = load_break_cache(path)

    overrides = load_break_overrides()
    if overrides and not quiet:
        print(
            f"sandhi soft breaks: applied {len(overrides)} curated "
            f"override(s) from {DEFAULT_OVERRIDES_PATH.name}",
            flush=True,
        )
    return merge_break_maps(base, overrides)


def _select_break_offsets(thai_parts: list[str], min_fragment: int) -> list[int]:
    """Return chunk indices ``i`` (break after chunk ``i``) worth keeping.

    A kept break at ``i`` lets TeX split so that ``chunks[0..i]`` stay on the
    current line and ``chunks[i+1..]`` move to the next. Keep ``i`` only when
    both joined runs are at least ``min_fragment`` Thai display glyphs, so a
    linguistically valid sandhi boundary that leaves a 2-glyph widow (e.g.
    ``sippikasambukā|pi`` → trailing ``ปิ``) is dropped.
    """
    n = len(thai_parts)
    if n < 2:
        return []
    if min_fragment <= 0:
        return list(range(n - 1))
    pref = [0] * (n + 1)
    for i, p in enumerate(thai_parts):
        pref[i + 1] = pref[i] + thai_display_len(p)
    total = pref[n]
    kept: list[int] = []
    for i in range(n - 1):
        left = pref[i + 1]
        right = total - pref[i + 1]
        if left >= min_fragment and right >= min_fragment:
            kept.append(i)
    return kept


def _max_thai_chunk_len(thai_parts: list[str]) -> int:
    return max((thai_display_len(p) for p in thai_parts), default=0)


def _typography_improves(
    old_thai: list[str],
    new_thai: list[str],
    min_fragment: int,
) -> bool:
    """True when the candidate split is typographically better than ``old``.

    Prefer a smaller max Thai display chunk. When max length is unchanged,
    prefer more kept soft-break points (more places TeX may wrap). Reject
    candidates that enlarge the longest unbreakable chunk.
    """
    old_max = _max_thai_chunk_len(old_thai)
    new_max = _max_thai_chunk_len(new_thai)
    if new_max < old_max:
        return True
    if new_max > old_max:
        return False
    return len(_select_break_offsets(new_thai, min_fragment)) > len(
        _select_break_offsets(old_thai, min_fragment)
    )


def compose_finer_break_parts(
    word: str,
    parts: list[str],
    breaks: dict[str, list[str]],
    *,
    min_fragment_len: int = DEFAULT_MIN_FRAGMENT_LEN,
) -> list[str]:
    """Expand a coarse 2-part DPD split by reusing a finer known head or tail.

    When ``parts == [head, tail]``:

    - If ``breaks[head]`` has ≥2 chunks, try
      ``inner_head[:-1] + [inner_head[-1] + tail]`` (stem + suffix cases such as
      ``ākāsānañcāyatana|samāpatti``).
    - If ``breaks[tail]`` has ≥2 chunks, try ``[head] + inner_tail`` (prefix +
      known compound, e.g. ``na|nevavipākanavipākadhammadhammo``).

    Accept a candidate only when Thai-slice succeeds and typography improves
    (see ``_typography_improves``). When both sides expand, pick the candidate
    with the smaller max Thai chunk (then more kept breaks). Repeat while the
    result is still a 2-part split that expands further.

    Does not mutate ``sandhi_breaks.json``; applied at inject time only.
    Curated overrides already merged into ``breaks`` win as the starting
    ``parts``; if an override is already multi-part, this is a no-op.
    """
    if not parts or len(parts) < 2 or not word:
        return list(parts)
    current = list(parts)
    seen: set[tuple[str, ...]] = set()
    while len(current) == 2:
        key = tuple(current)
        if key in seen:
            break
        seen.add(key)
        head, tail = current[0], current[1]
        old_thai = thai_slices_from_roman_chunks(word, current)
        if not old_thai:
            break

        candidates: list[list[str]] = []
        inner_head = breaks.get(head)
        if inner_head and len(inner_head) >= 2:
            candidates.append(list(inner_head[:-1]) + [inner_head[-1] + tail])
        inner_tail = breaks.get(tail)
        if inner_tail and len(inner_tail) >= 2:
            candidates.append([head] + list(inner_tail))

        best: list[str] | None = None
        best_thai: list[str] | None = None
        for cand in candidates:
            if "".join(cand) != word:
                continue
            new_thai = thai_slices_from_roman_chunks(word, cand)
            if not new_thai:
                continue
            if not _typography_improves(old_thai, new_thai, min_fragment_len):
                continue
            if best is None or best_thai is None:
                best, best_thai = cand, new_thai
                continue
            # Prefer smaller max chunk; tie-break on more kept breaks.
            if _max_thai_chunk_len(new_thai) < _max_thai_chunk_len(best_thai):
                best, best_thai = cand, new_thai
            elif _max_thai_chunk_len(new_thai) == _max_thai_chunk_len(
                best_thai
            ) and len(_select_break_offsets(new_thai, min_fragment_len)) > len(
                _select_break_offsets(best_thai, min_fragment_len)
            ):
                best, best_thai = cand, new_thai
        if best is None:
            break
        current = best
    return current


def _join_with_breaks(thai_parts: list[str], kept: list[int]) -> str:
    """Join Thai chunks, inserting ``{{sb}}`` only at kept break offsets."""
    kept_set = set(kept)
    out: list[str] = []
    for i, p in enumerate(thai_parts):
        if i > 0:
            out.append(SOFT_BREAK_MARKER if (i - 1) in kept_set else "")
        out.append(p)
    return "".join(out)


def inject_soft_breaks_in_thai(
    thai: str,
    roman: str,
    breaks: dict[str, list[str]],
    *,
    min_roman_len: int = DEFAULT_MIN_ROMAN_LEN,
    min_thai_len: int | None = None,
    min_fragment_len: int = DEFAULT_MIN_FRAGMENT_LEN,
) -> str:
    """Replace long solid Thai tokens with ``{{sb}}``-joined morpheme Thai.

    Uses Roman ``breaks`` keyed by normalized Roman; only tokens whose Roman
    letter length is ``>= min_roman_len`` are considered. Coarse 2-part cache
    entries may be refined via ``compose_finer_break_parts`` before slicing.
    A break point that leaves either side shorter than ``min_fragment_len``
    Thai display glyphs is dropped so TeX moves the whole word rather than
    emitting a short fragment. Markers already in ``thai`` are preserved.
    """
    if min_thai_len is not None:
        min_roman_len = min_thai_len
    if not thai or not roman or not breaks:
        return thai

    # Build replacement map: solid Thai → marked Thai (longest keys first).
    repl: list[tuple[str, str]] = []
    cleaned_roman = _MARKER_RE.sub(" ", roman)
    for m in _TOKEN_RE.finditer(cleaned_roman):
        tok = normalize_lookup_key(m.group(0))
        if roman_letter_len(tok) < min_roman_len:
            continue
        parts = breaks.get(tok)
        if not parts or len(parts) < 2:
            continue
        parts = compose_finer_break_parts(
            tok, parts, breaks, min_fragment_len=min_fragment_len
        )
        thai_parts = thai_slices_from_roman_chunks(tok, parts)
        if not thai_parts:
            continue
        kept = _select_break_offsets(thai_parts, min_fragment_len)
        if not kept:
            continue
        solid = "".join(thai_parts)
        marked = _join_with_breaks(thai_parts, kept)
        if solid and marked != solid:
            repl.append((solid, marked))

    if not repl:
        return thai

    # Longest solid forms first to avoid partial clobbering.
    repl.sort(key=lambda pair: len(pair[0]), reverse=True)

    # Replace only outside existing {{…}} markers.
    pieces: list[str] = []
    last = 0
    for m in _MARKER_RE.finditer(thai):
        pieces.append(_multi_replace(thai[last : m.start()], repl))
        pieces.append(m.group(0))
        last = m.end()
    pieces.append(_multi_replace(thai[last:], repl))
    return "".join(pieces)


def _multi_replace(text: str, repl: list[tuple[str, str]]) -> str:
    if not text or not repl:
        return text
    out = text
    for solid, marked in repl:
        if solid in out:
            out = out.replace(solid, marked)
    return out


def apply_soft_break_markers_to_runs(
    runs: list[dict],
    roman: str,
    breaks: dict[str, list[str]],
    *,
    min_roman_len: int = DEFAULT_MIN_ROMAN_LEN,
    min_thai_len: int | None = None,
    min_fragment_len: int = DEFAULT_MIN_FRAGMENT_LEN,
) -> list[dict]:
    """Inject ``{{sb}}`` into Thai run values (bold spans kept per run)."""
    # Re-join runs, inject on full string, then not trivially re-split —
    # markers may fall inside a run; process each run independently when
    # the solid token lies wholly in one run; otherwise join→inject→single run.
    joined = "".join(str(r.get("value") or "") for r in runs if isinstance(r, dict))
    injected = inject_soft_breaks_in_thai(
        joined,
        roman,
        breaks,
        min_roman_len=min_roman_len,
        min_thai_len=min_thai_len,
        min_fragment_len=min_fragment_len,
    )
    if injected == joined:
        return runs
    # Bold metadata cannot be preserved across re-segmentation cheaply;
    # callers may drop runs and use plain Thai when markers appear.
    return [{"value": injected, "bold": False}]
