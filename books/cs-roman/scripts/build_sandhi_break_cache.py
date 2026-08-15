"""Build sandhi soft-break cache for long CS Roman tokens from local dpd.db.

Usage:
  python books/cs-roman/scripts/build_sandhi_break_cache.py --all
  python books/cs-roman/scripts/build_sandhi_break_cache.py --volume 01Vin01
  python books/cs-roman/scripts/build_sandhi_break_cache.py --all --min-len 15

TeX generate also calls ``ensure_sandhi_break_cache`` automatically when the
cache file is missing and ``vendor/dpd/dpd.db`` is present.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from paths import ensure_import_paths

ensure_import_paths()

from cs_roman_sandhi_breaks import (  # noqa: E402
    DEFAULT_CACHE_PATH,
    DEFAULT_DB_PATH,
    DEFAULT_MIN_ROMAN_LEN,
    rebuild_sandhi_break_cache,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--all", action="store_true", help="scan every volume")
    g.add_argument("--volume", type=str, help="volume id substring, e.g. 01Vin01")
    parser.add_argument(
        "--min-len",
        type=int,
        default=DEFAULT_MIN_ROMAN_LEN,
        help=f"min roman_letter_len (default {DEFAULT_MIN_ROMAN_LEN})",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB_PATH,
        help="path to dpd.db",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_CACHE_PATH,
        help="output JSON cache path",
    )
    args = parser.parse_args()

    path, hit, total = rebuild_sandhi_break_cache(
        volume=None if args.all else args.volume,
        min_roman_len=args.min_len,
        db_path=args.db,
        out_path=args.out,
        progress=True,
    )
    print(f"wrote {path} entries={hit} coverage={hit}/{total}")


if __name__ == "__main__":
    main()
