#!/usr/bin/env python3
"""Undo false ``-pa-`` soft-hyphen joins at page boundaries in segment JSON.

Older extract treated the trailing hyphen of peyyāla ``-pa-`` as a line-break
hyphen and glued the next page's leading word (e.g. ``-paaññaṃ``).

Does not re-extract from PDF — repairs stored Roman text, then optionally
re-enriches Thai.

  python books/cs-roman/scripts/fixup_false_pa_hyphen_joins.py --all
  python books/cs-roman/scripts/fixup_false_pa_hyphen_joins.py --volume 01Vin01
  python books/cs-roman/scripts/fixup_false_pa_hyphen_joins.py --all --enrich
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from paths import BOOKS, OUTPUT_DIR, ensure_import_paths

ensure_import_paths()
from cs_roman_segments import load_document, save_content  # noqa: E402
from enrich_cs_roman_thai import enrich_file  # noqa: E402
from extract_cs_roman_pdf import unglue_false_pa_page_joins  # noqa: E402


def _enrich_with_retry(path: Path, *, attempts: int = 4) -> tuple[int, int, int]:
    """``enrich_file`` with retries for flaky Docker/Windows volume writes."""
    last: BaseException | None = None
    for i in range(attempts):
        try:
            return enrich_file(path, force=True)
        except OSError as exc:
            last = exc
            time.sleep(0.5 * (i + 1))
    assert last is not None
    raise last


def _iter_segment_paths(*, volume: str | None, all_volumes: bool, output_only: bool) -> list[Path]:
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
        "--enrich",
        action="store_true",
        help="Re-transliterate Thai after Roman repair (--force)",
    )
    parser.add_argument(
        "--enrich-only",
        action="store_true",
        help="Skip join repair; only --force enrich matching files",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report repairs without writing",
    )
    args = parser.parse_args(argv)

    unique_paths = _iter_segment_paths(
        volume=args.volume,
        all_volumes=args.all_volumes,
        output_only=args.output_only,
    )

    if not unique_paths:
        print("No segment JSON files found.", file=sys.stderr)
        return 1

    total_fixed = 0
    for path in unique_paths:
        if not path.is_file():
            print(f"Skip missing: {path}", file=sys.stderr)
            continue
        if args.enrich_only:
            if args.dry_run:
                print(f"{path}: enrich-only (dry-run)")
                continue
            converted, total, bold_lost = _enrich_with_retry(path)
            print(
                f"{path}: enrich --force {converted}/{total}"
                + (f" bold_lost={bold_lost}" if bold_lost else "")
            )
            continue

        doc = load_document(path)
        segments = list(doc.get("segments") or [])
        fixed = unglue_false_pa_page_joins(segments)
        total_fixed += fixed
        print(f"{path}: repaired={fixed}")
        if args.dry_run or fixed == 0:
            continue
        doc["segments"] = segments
        save_content(path, doc, normalize=True)
        if args.enrich:
            converted, total, bold_lost = _enrich_with_retry(path)
            print(
                f"  enrich --force: {converted}/{total}"
                + (f" bold_lost={bold_lost}" if bold_lost else "")
            )

    print(f"Total repaired joins: {total_fixed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
