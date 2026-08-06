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

# Default: only long Thai display tokens get soft breaks.
DEFAULT_MIN_THAI_LEN = 15

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


def normalize_lookup_key(word: str) -> str:
    """DPD lookup keys are lowercase; unify niggahita spellings."""
    w = word.strip().lower().replace("-", "")
    return w.replace("ṁ", "ṃ")


def fold_roman(s: str) -> str:
    return s.translate(_FOLD).lower().replace("-", "")


def parse_plus_parts(spec: str) -> list[str]:
    """Split a deconstructor / construction string on ``+``."""
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
        # part can claim it (``picchilla`` + ``ādīnaṃ`` in ``…picchillādīnaṃ``).
        if (
            not is_last
            and part[-1] in "aiu"
            and wj > 0
            and rem[wj - 1] in "āīū"
        ):
            short_end = start + wj - 1
            if short_end > start and short_end not in ends:
                ends.append(short_end)

    if is_last:
        # Stem matched as prefix; case ending may follow.
        out: list[int] = []
        for e in ends:
            if e <= len(word):
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
        if row and row["headwords"]:
            try:
                ids = json.loads(row["headwords"])
            except json.JSONDecodeError:
                ids = []
            for hid in ids[:5]:
                crow = self._con.execute(
                    "SELECT construction FROM dpd_headwords WHERE id = ?",
                    (int(hid),),
                ).fetchone()
                if crow and crow["construction"] and "+" in crow["construction"]:
                    out.append(str(crow["construction"]))
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
    min_thai_len: int = DEFAULT_MIN_THAI_LEN,
    source_db: str | None = None,
) -> Path:
    p = Path(path) if path else DEFAULT_CACHE_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "min_thai_len": min_thai_len,
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
    min_thai_len: int = DEFAULT_MIN_THAI_LEN,
    db_path: Path | None = None,
    out_path: Path | None = None,
    progress: bool = True,
) -> tuple[Path, int, int]:
    """Scan volumes + DPD; write cache. Returns (path, hits, long_token_count)."""
    db = Path(db_path) if db_path else DEFAULT_DB_PATH
    out = Path(out_path) if out_path else DEFAULT_CACHE_PATH
    tokens = collect_roman_tokens(volume)
    long_tokens = sorted(
        w
        for w in tokens
        if roman_letter_len(w) >= min_thai_len
        and thai_display_len(convert(w, Script.ROMAN, Script.THAI)) >= min_thai_len
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
        min_thai_len=min_thai_len,
        source_db=str(db),
    )
    return path, hit, len(long_tokens)


def ensure_sandhi_break_cache(
    *,
    force: bool = False,
    min_thai_len: int = DEFAULT_MIN_THAI_LEN,
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
            min_thai_len=min_thai_len,
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


def inject_soft_breaks_in_thai(
    thai: str,
    roman: str,
    breaks: dict[str, list[str]],
    *,
    min_thai_len: int = DEFAULT_MIN_THAI_LEN,
) -> str:
    """Replace long solid Thai tokens with ``{{sb}}``-joined morpheme Thai.

    Uses Roman ``breaks`` keyed by normalized Roman; only tokens whose Thai
    display length is ``>= min_thai_len`` are considered. Markers already in
    ``thai`` are preserved.
    """
    if not thai or not roman or not breaks:
        return thai

    # Build replacement map: solid Thai → marked Thai (longest keys first).
    repl: list[tuple[str, str]] = []
    cleaned_roman = _MARKER_RE.sub(" ", roman)
    for m in _TOKEN_RE.finditer(cleaned_roman):
        tok = normalize_lookup_key(m.group(0))
        parts = breaks.get(tok)
        if not parts or len(parts) < 2:
            continue
        thai_parts = thai_slices_from_roman_chunks(tok, parts)
        if not thai_parts:
            continue
        solid = "".join(thai_parts)
        if thai_display_len(solid) < min_thai_len:
            continue
        marked = SOFT_BREAK_MARKER.join(thai_parts)
        if solid and solid != marked:
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
    min_thai_len: int = DEFAULT_MIN_THAI_LEN,
) -> list[dict]:
    """Inject ``{{sb}}`` into Thai run values (bold spans kept per run)."""
    # Re-join runs, inject on full string, then not trivially re-split —
    # markers may fall inside a run; process each run independently when
    # the solid token lies wholly in one run; otherwise join→inject→single run.
    joined = "".join(str(r.get("value") or "") for r in runs if isinstance(r, dict))
    injected = inject_soft_breaks_in_thai(
        joined, roman, breaks, min_thai_len=min_thai_len
    )
    if injected == joined:
        return runs
    # Bold metadata cannot be preserved across re-segmentation cheaply;
    # callers may drop runs and use plain Thai when markers appear.
    return [{"value": injected, "bold": False}]
