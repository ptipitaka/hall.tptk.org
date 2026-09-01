#!/usr/bin/env python3
"""Remap printed Tipiṭaka item typos in stored segment JSON.

Extract keeps the number as printed. Known identity corrections live in
``shared/item_corrections.json``. This repairs already-extracted volumes
without re-extracting; newer extract applies the same catalog.

  python books/cs-roman/scripts/fixup_item_corrections.py --volume 01Vin01
  python books/cs-roman/scripts/fixup_item_corrections.py --all
  python books/cs-roman/scripts/fixup_item_corrections.py --all --dry-run
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from paths import BOOKS, OUTPUT_DIR, ensure_import_paths

ensure_import_paths()
from cs_roman_item_corrections import (  # noqa: E402
    apply_item_corrections,
    volume_id_from_segments_path,
)
from cs_roman_segments import load_document, save_content  # noqa: E402


def _iter_segment_paths(
    *, volume: str | None, all_volumes: bool, output_only: bool
) -> list[Path]:
    paths: list[Path] = []
    if volume:
        paths.append(BOOKS / "volumes" / volume / "data" / "segments.json")
        out = OUTPUT_DIR / f"{volume}.segments.json"
        if out.is_file():
            paths.append(out)
    elif all_volumes:
        paths.extend(sorted((BOOKS / "volumes").glob("*/data/segments.json")))
        paths.extend(sorted(OUTPUT_DIR.glob("*.segments.json")))
    elif output_only:
        paths.extend(sorted(OUTPUT_DIR.glob("*.segments.json")))

    seen: set[Path] = set()
    unique: list[Path] = []
    for p in paths:
        rp = p.resolve()
        if rp in seen:
            continue
        seen.add(rp)
        unique.append(p)
    return unique


def fix_document_item_corrections(doc: dict[str, Any], volume_id: str) -> int:
    """Mutate ``doc`` in place; return how many segments changed."""
    segments = doc.get("segments")
    if not isinstance(segments, list):
        return 0
    return apply_item_corrections(segments, volume_id)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--volume", help="e.g. 01Vin01")
    group.add_argument(
        "--all",
        action="store_true",
        dest="all_volumes",
        help="All volumes + output/*.segments.json",
    )
    group.add_argument(
        "--output",
        action="store_true",
        dest="output_only",
        help="Only books/cs-roman/output/*.segments.json",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report corrections without writing",
    )
    args = parser.parse_args(argv)

    paths = _iter_segment_paths(
        volume=args.volume,
        all_volumes=args.all_volumes,
        output_only=args.output_only,
    )
    if not paths:
        print("No segments.json paths found", file=sys.stderr)
        return 1

    total = 0
    for path in paths:
        if not path.is_file():
            print(f"skip missing {path}")
            continue
        volume_id = args.volume or volume_id_from_segments_path(path)
        if not volume_id:
            print(f"{path}: skip (no volume id)")
            continue
        doc = load_document(path)
        n = fix_document_item_corrections(doc, volume_id)
        total += n
        if n == 0:
            print(f"{path}: no item corrections")
            continue
        if args.dry_run:
            print(f"{path}: would correct {n} item(s)")
        else:
            save_content(path, doc)
            print(f"{path}: corrected {n} item(s)")

    print(f"Done: {total} correction(s)" + (" [dry-run]" if args.dry_run else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
