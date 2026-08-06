"""List long Roman tokens with no sandhi soft-break in DPD cache or overrides.

Scans all ``volumes/*/data/segments.json``. A token qualifies when
``thai_display_len >= min_len`` (default 15, same as sandhi inject). Output is
sorted by corpus frequency (count) then Thai length — use for curating
``shared/sandhi_breaks_overrides.json``.

Usage:
  python books/cs-roman/scripts/scan_sandhi_break_gaps.py
  python books/cs-roman/scripts/scan_sandhi_break_gaps.py --min-len 15 --tsv research/sandhi_breaks_missing.tsv
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
    DEFAULT_MIN_THAI_LEN,
    load_break_cache,
    load_break_overrides,
    normalize_lookup_key,
)
from scan_long_words import (  # noqa: E402
    MARKER_RE,
    TOKEN_RE,
    roman_letter_len,
    roman_strings,
    thai_display_len,
)

RESEARCH = BOOKS / "research"


def collect_gap_rows(min_len: int) -> list[tuple[int, int, int, str, str]]:
    cache = load_break_cache()
    overrides = load_break_overrides()

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

    rows: list[tuple[int, int, int, str, str]] = []
    for key, surf in edition.items():
        if roman_letter_len(surf) < min_len:
            continue
        thai = convert(surf, Script.ROMAN, Script.THAI)
        tl = thai_display_len(thai)
        if tl < min_len:
            continue
        if key in cache or key in overrides:
            continue
        rows.append(
            (
                tl,
                counts[key],
                len(volume_hits[key]),
                surf,
                thai,
            )
        )

    rows.sort(key=lambda r: (-r[1], -r[0], r[3]))
    return rows


def write_tsv(rows: list[tuple[int, int, int, str, str]], out_tsv: Path) -> None:
    lines = ["thai_len\tcount\tvolumes\troman\thai"] + [
        f"{tl}\t{c}\t{v}\t{r}\t{t}" for tl, c, v, r, t in rows
    ]
    out_tsv.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--min-len",
        type=int,
        default=DEFAULT_MIN_THAI_LEN,
        help=f"min thai_display_len (default {DEFAULT_MIN_THAI_LEN})",
    )
    parser.add_argument(
        "--tsv",
        type=Path,
        default=RESEARCH / "sandhi_breaks_missing.tsv",
        help="output TSV path",
    )
    args = parser.parse_args()

    rows = collect_gap_rows(args.min_len)
    write_tsv(rows, args.tsv)

    cache = load_break_cache()
    overrides = load_break_overrides()
    print(f"cache_entries={len(cache)} override_entries={len(overrides)}")
    print(f"missing_rows={len(rows)} (thai_display_len>={args.min_len})")
    print(f"wrote {args.tsv}")
    if rows:
        print("--- top 10 by count ---")
        for tl, c, v, r, _t in rows[:10]:
            print(f"{c:4d}  vols={v:2d}  len={tl:2d}  {r}")


if __name__ == "__main__":
    main()
