#!/usr/bin/env python3
"""Apply edition ``par_skip`` / ``gatha_stanza_skip`` defaults to layout JSON.

Keeps both keys equal to ``DEFAULT_LAYOUT`` (edition rhythm). Optical match
between prose paragraphs and gāthā บท is handled in TeX
(``\\csromangathastanza`` adds open leading on top of ``\\gathastanzaskip``).

  python books/cs-roman/scripts/fixup_edition_layout_rhythm.py --volume 01Vin01
  python books/cs-roman/scripts/fixup_edition_layout_rhythm.py --all
  python books/cs-roman/scripts/fixup_edition_layout_rhythm.py --all --dry-run
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from paths import BOOKS, OUTPUT_DIR, ensure_import_paths

ensure_import_paths()
from cs_roman_segments import DEFAULT_LAYOUT, load, save_layout  # noqa: E402

_RHYTHM_KEYS = ("par_skip", "gatha_stanza_skip")


def _iter_layout_paths(
    *, volume: str | None, all_volumes: bool, output_only: bool
) -> list[Path]:
    paths: list[Path] = []
    if volume:
        paths.append(BOOKS / "volumes" / volume / "data" / "layout.json")
        out = OUTPUT_DIR / f"{volume}.layout.json"
        if out.is_file():
            paths.append(out)
    elif all_volumes:
        for p in sorted((BOOKS / "volumes").glob("*/data/layout.json")):
            if p.parts[-3].startswith("_"):
                continue
            paths.append(p)
        paths.extend(sorted(OUTPUT_DIR.glob("*.layout.json")))
    elif output_only:
        paths.extend(sorted(OUTPUT_DIR.glob("*.layout.json")))

    seen: set[Path] = set()
    unique: list[Path] = []
    for p in paths:
        if not p.is_file():
            continue
        rp = p.resolve()
        if rp in seen:
            continue
        seen.add(rp)
        unique.append(p)
    return unique


def fix_layout(path: Path, *, dry_run: bool) -> bool:
    data = load(path)
    layout = data.get("layout")
    if not isinstance(layout, dict):
        layout = {}
        data["layout"] = layout
    changed = False
    for key in _RHYTHM_KEYS:
        target = DEFAULT_LAYOUT[key]
        if layout.get(key) != target:
            layout[key] = target
            changed = True
    if changed and not dry_run:
        save_layout(path, data, normalize=True)
    return changed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--volume", help="Volume id (e.g. 01Vin01)")
    group.add_argument("--all", action="store_true", help="All real volumes + output/")
    group.add_argument(
        "--output-only",
        action="store_true",
        help="Only books/cs-roman/output/*.layout.json",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    paths = _iter_layout_paths(
        volume=args.volume,
        all_volumes=args.all,
        output_only=args.output_only,
    )
    if not paths:
        print("No layout.json files found", file=sys.stderr)
        return 1

    n_changed = 0
    for path in paths:
        if fix_layout(path, dry_run=args.dry_run):
            n_changed += 1
            verb = "would update" if args.dry_run else "updated"
            print(f"{verb}: {path}")
    targets = ", ".join(f"{k}={DEFAULT_LAYOUT[k]!r}" for k in _RHYTHM_KEYS)
    print(f"{n_changed}/{len(paths)} file(s) ({targets})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
