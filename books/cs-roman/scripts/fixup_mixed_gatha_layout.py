#!/usr/bin/env python3
"""Normalize CS mixed / long-single gāthā ``source_layout``.

Roman CS sometimes prints one บท as a ``วรรค, วรรค.`` line plus long
single-วรรค lines. Extract must not force those long lines into
``\\csromangathabat`` pairs (overflow / huge gap).

Rules (bats/waks text unchanged):
  - comma-left + stop-left บาท → ``mixed`` (Roman mixed shape)
  - stop-left only (all singles folded as bat pairs) → ``wak_line``
  - also upgrades prior ``wak_line`` over-normalize back to ``mixed``

  python books/cs-roman/scripts/fixup_mixed_gatha_layout.py --volume 04Vin04
  python books/cs-roman/scripts/fixup_mixed_gatha_layout.py --all
  python books/cs-roman/scripts/fixup_mixed_gatha_layout.py --all --dry-run
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from paths import OUTPUT_DIR, ensure_import_paths

ensure_import_paths()
from cs_roman_segments import load_document, save_content  # noqa: E402
from extract_cs_roman_pdf import gatha_layout_fix_target  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
VOLUMES = ROOT / "volumes"


def fix_segment(seg: dict) -> bool:
    """Set ``source_layout`` to mixed / wak_line when the บท shape requires it."""
    target = gatha_layout_fix_target(seg)
    if target is None:
        return False
    changed = False
    if seg.get("source_layout") != target:
        seg["source_layout"] = target
        changed = True
    if target == "mixed":
        reasons = list(seg.get("review_reasons") or [])
        if "mixed_gatha_layout" not in reasons:
            reasons.append("mixed_gatha_layout")
            seg["review_reasons"] = reasons
            changed = True
    return changed


def fix_document(data: dict) -> int:
    n = 0
    for seg in data.get("segments") or []:
        if isinstance(seg, dict) and fix_segment(seg):
            n += 1
    return n


def volume_paths(volume: str) -> list[Path]:
    paths: list[Path] = []
    vol_seg = VOLUMES / volume / "data" / "segments.json"
    if vol_seg.is_file():
        paths.append(vol_seg)
    out_seg = OUTPUT_DIR / f"{volume}.segments.json"
    if out_seg.is_file() and out_seg.resolve() not in {p.resolve() for p in paths}:
        paths.append(out_seg)
    return paths


def all_volumes() -> list[str]:
    return sorted(
        p.name
        for p in VOLUMES.iterdir()
        if p.is_dir() and (p / "data" / "segments.json").is_file()
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--volume", help="Volume id (e.g. 04Vin04)")
    ap.add_argument("--all", action="store_true", help="All volumes with segments")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if bool(args.volume) == bool(args.all):
        ap.error("Specify exactly one of --volume or --all")

    volumes = all_volumes() if args.all else [args.volume]
    total = 0
    for vol in volumes:
        for path in volume_paths(vol):
            data = load_document(path)
            n = fix_document(data)
            total += n
            if n:
                print(f"{path}: {n} gatha layout fix(es)")
                if not args.dry_run:
                    save_content(path, data)
            else:
                print(f"{path}: ok")
    print(f"Done ({total} segment(s))" + (" [dry-run]" if args.dry_run else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
