#!/usr/bin/env python3
"""Clear mistagged ``heading_kind`` on ``Idaṃ …`` / ``อิทํ …`` center labels.

These are body centers (``\\csromancenter``), not outline heads. Extract /
assign now skip them; this repairs older ``segments.json``.

Canonical data lives in ``output/<id>.segments.json``. ``build.ps1`` syncs
that file into ``volumes/<id>/data/segments.json``, so fixups must update
**both** (same pattern as ``fixup_tassuddana_labels.py``).

  python books/cs-roman/scripts/fixup_idam_center_labels.py --volume 01Vin01
  python books/cs-roman/scripts/fixup_idam_center_labels.py --all
  python books/cs-roman/scripts/fixup_idam_center_labels.py --all --dry-run
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from paths import BOOKS, OUTPUT_DIR, ensure_import_paths

ensure_import_paths()
from assign_cs_roman_heading_levels import (  # noqa: E402
    _roman_text,
    is_plain_centered_label,
)
from cs_roman_segments import load_document, save_content  # noqa: E402


def fix_document(data: dict[str, Any]) -> int:
    n = 0
    for seg in data.get("segments") or []:
        if not seg.get("heading_kind"):
            continue
        text = _roman_text(seg)
        if not is_plain_centered_label(seg, text):
            continue
        seg.pop("heading_kind", None)
        seg.pop("in_toc", None)
        n += 1
    return n


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


def _label_for(path: Path) -> str:
    if path.parent.name == "data":
        return path.parent.parent.name
    return path.name


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--volume", help="Volume id (volume data + output JSON)")
    g.add_argument("--all", action="store_true", help="All volume + output JSON")
    g.add_argument(
        "--output-only",
        action="store_true",
        help="Only books/cs-roman/output/*.segments.json",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    paths = _iter_segment_paths(
        volume=args.volume,
        all_volumes=args.all,
        output_only=args.output_only,
    )
    if not paths:
        print("No segment JSON files found.", file=sys.stderr)
        return 1

    total = 0
    for path in paths:
        if not path.is_file():
            print(f"skip (missing): {path}", file=sys.stderr)
            continue
        data = load_document(path)
        n = fix_document(data)
        total += n
        if n:
            print(f"{_label_for(path)}: {n} Idam label(s) demoted")
            if not args.dry_run:
                save_content(path, data)
    print(f"total: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
