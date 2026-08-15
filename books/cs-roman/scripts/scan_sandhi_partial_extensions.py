"""List missing sandhi words that decompose as a known break key + a short tail/head.

For each long Roman token in the corpus that has no entry in the DPD cache or
the curated overrides, check whether a **prefix** or **suffix** of it is itself
already a break key in the combined map. When the resulting split (known parts
+ the leftover run) also slices cleanly into Thai prefixes via
``thai_slices_from_roman_chunks``, the candidate is emitted to a review queue.

The queue is **not** applied to ``sandhi_breaks_overrides.json`` automatically:
some matches pass the Thai-slice check but cut at a non-morpheme boundary
(e.g. ``kaḷ|ambadāyaka…``). A human curates the queue into overrides.

Usage:
  python books/cs-roman/scripts/scan_sandhi_partial_extensions.py
  python books/cs-roman/scripts/scan_sandhi_partial_extensions.py --min-len 15 \
      --tsv research/sandhi_partial_extensions.tsv
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from paths import BOOKS, VOLUMES_DIR, ensure_import_paths

ensure_import_paths()

from pali_script import Script, convert  # noqa: E402

from cs_roman_sandhi_breaks import (  # noqa: E402
    DEFAULT_MIN_ROMAN_LEN,
    load_break_cache,
    load_break_overrides,
    normalize_lookup_key,
    thai_slices_from_roman_chunks,
)
from scan_long_words import (  # noqa: E402
    MARKER_RE,
    TOKEN_RE,
    roman_letter_len,
    roman_strings,
    thai_display_len,
)

RESEARCH = BOOKS / "research"
DEFAULT_OUT = RESEARCH / "sandhi_partial_extensions.tsv"

# A break key shorter than this is not worth reusing as a partial anchor: the
# leftover run would dominate and the match is likely accidental. 8 keeps the
# known anchor long enough to be a real compound, not a coincidental short
# string.
DEFAULT_MIN_KEY_LEN = 8


def collect_corpus_tokens() -> tuple[
    dict[str, str], dict[str, int], dict[str, set[str]]
]:
    """Return (edition_surface, counts, volume_hits) keyed by normalized Roman."""
    edition: dict[str, str] = {}
    counts: dict[str, int] = defaultdict(int)
    volume_hits: dict[str, set[str]] = defaultdict(set)
    for seg_path in sorted(VOLUMES_DIR.glob("*/data/segments.json")):
        vol = seg_path.parts[-3]
        data = json.loads(seg_path.read_text(encoding="utf-8"))
        for seg in data.get("segments") or []:
            for raw in roman_strings(seg):
                cleaned = MARKER_RE.sub(" ", raw)
                for match in TOKEN_RE.finditer(cleaned):
                    surf = match.group(0)
                    key = normalize_lookup_key(surf)
                    if key not in edition:
                        edition[key] = surf.replace("-", "")
                    counts[key] += 1
                    volume_hits[key].add(vol)
    return edition, counts, volume_hits


def find_prefix_extension(
    key: str, breaks: dict[str, list[str]], min_key_len: int
) -> tuple[str, list[str], str] | None:
    """Longest known break key that is a proper prefix of ``key``.

    Returns ``(matched_key, known_parts, tail)`` where ``tail = key[len(k):]``.
    ``tail`` is kept as a single unsplit chunk (the part without split data, per
    the user's principle). Returns None when no anchor is found.
    """
    best: str | None = None
    for k in breaks:
        if k == key or len(k) < min_key_len:
            continue
        if key.startswith(k) and (best is None or len(k) > len(best)):
            best = k
    if best is None:
        return None
    return best, list(breaks[best]), key[len(best):]


def find_suffix_extension(
    key: str, breaks: dict[str, list[str]], min_key_len: int
) -> tuple[str, str, list[str]] | None:
    """Longest known break key that is a proper suffix of ``key``.

    Returns ``(head, matched_key, known_parts)`` where ``head = key[:-len(k)]``.
    """
    best: str | None = None
    for k in breaks:
        if k == key or len(k) < min_key_len:
            continue
        if key.endswith(k) and (best is None or len(k) > len(best)):
            best = k
    if best is None:
        return None
    return key[: len(key) - len(best)], best, list(breaks[best])


def candidate_parts_prefix(
    matched_parts: list[str], tail: str
) -> list[str]:
    return list(matched_parts) + [tail]


def candidate_parts_suffix(
    head: str, matched_parts: list[str]
) -> list[str]:
    return [head] + list(matched_parts)


def collect_extension_rows(
    *,
    min_len: int = DEFAULT_MIN_ROMAN_LEN,
    min_key_len: int = DEFAULT_MIN_KEY_LEN,
) -> list[tuple[int, int, int, str, str, str, str, str, bool]]:
    """Scan corpus; return rows for missing words with a partial extension.

    Row tuple:
        (thai_len, count, volumes, roman, thai, kind, matched_key, parts_json,
         thai_slice_ok)

    ``kind`` is ``prefix`` or ``suffix``. ``parts_json`` is the proposed split
    (known parts + leftover). ``thai_slice_ok`` is True when
    ``thai_slices_from_roman_chunks`` accepts the split.
    """
    cache = load_break_cache()
    overrides = load_break_overrides()
    combined = dict(cache)
    combined.update(overrides)

    edition, counts, volume_hits = collect_corpus_tokens()

    rows: list[tuple[int, int, int, str, str, str, str, str, bool]] = []
    for key, surf in edition.items():
        if roman_letter_len(surf) < min_len:
            continue
        thai = convert(surf, Script.ROMAN, Script.THAI)
        if key in combined:
            continue  # already has a break

        pref = find_prefix_extension(key, combined, min_key_len)
        if pref is not None:
            matched_key, known_parts, tail = pref
            parts = candidate_parts_prefix(known_parts, tail)
            ok = thai_slices_from_roman_chunks(surf, parts) is not None
            rows.append(
                (
                    thai_display_len(thai),
                    counts[key],
                    len(volume_hits[key]),
                    surf,
                    thai,
                    "prefix",
                    matched_key,
                    json.dumps(parts, ensure_ascii=False),
                    ok,
                )
            )
            continue

        suf = find_suffix_extension(key, combined, min_key_len)
        if suf is not None:
            head, matched_key, known_parts = suf
            parts = candidate_parts_suffix(head, known_parts)
            ok = thai_slices_from_roman_chunks(surf, parts) is not None
            rows.append(
                (
                    thai_display_len(thai),
                    counts[key],
                    len(volume_hits[key]),
                    surf,
                    thai,
                    "suffix",
                    matched_key,
                    json.dumps(parts, ensure_ascii=False),
                    ok,
                )
            )

    # Highest-count first, then longest Thai, then alphabetical.
    rows.sort(key=lambda r: (-r[1], -r[0], r[3]))
    return rows


def write_tsv(
    rows: list[tuple[int, int, int, str, str, str, str, str, bool]],
    out_tsv: Path,
) -> None:
    header = (
        "thai_len\tcount\tvolumes\troman\tthai\tkind\tmatched_key\tparts\t"
        "thai_slice_ok"
    )
    lines = [header]
    for tl, c, v, r, t, kind, mk, parts, ok in rows:
        lines.append(
            f"{tl}\t{c}\t{v}\t{r}\t{t}\t{kind}\t{mk}\t{parts}\t"
            f"{'yes' if ok else 'no'}"
        )
    out_tsv.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--min-len",
        type=int,
        default=DEFAULT_MIN_ROMAN_LEN,
        help=(
            "min roman_letter_len for a token to be considered "
            f"(default {DEFAULT_MIN_ROMAN_LEN})"
        ),
    )
    parser.add_argument(
        "--min-key-len",
        type=int,
        default=DEFAULT_MIN_KEY_LEN,
        help=(
            "min Roman length for a break key to be reused as an anchor "
            f"(default {DEFAULT_MIN_KEY_LEN})"
        ),
    )
    parser.add_argument(
        "--tsv",
        type=Path,
        default=DEFAULT_OUT,
        help="output review-queue TSV path",
    )
    args = parser.parse_args()

    rows = collect_extension_rows(
        min_len=args.min_len, min_key_len=args.min_key_len
    )
    write_tsv(rows, args.tsv)

    total = len(rows)
    ok = sum(1 for r in rows if r[8])
    pref = sum(1 for r in rows if r[5] == "prefix")
    suf = total - pref
    print(f"min_len={args.min_len} min_key_len={args.min_key_len}")
    print(f"partial-extension rows: {total} (prefix={pref} suffix={suf})")
    print(f"thai_slice_ok=yes: {ok}   thai_slice_ok=no: {total - ok}")
    print(f"wrote {args.tsv}")
    print("--- top 10 by count (only thai_slice_ok=yes shown) ---")
    shown = 0
    for tl, c, v, r, _t, kind, mk, parts, ok in rows:
        if not ok:
            continue
        print(f"  cnt={c:3d}  vols={v:2d}  len={tl:2d}  {kind}  {r}")
        print(f"           matched={mk}")
        print(f"           parts={parts}")
        shown += 1
        if shown >= 10:
            break


if __name__ == "__main__":
    main()
