#!/usr/bin/env python3
"""Cache ``closer_level`` on section-closer segments (audit / enrich).

Generate always re-derives the visual tier from closer text
(``classify_section_closer`` / ``closer_tier``); this field is optional JSON
cache for scans and human review.

  python books/cs-roman/scripts/fixup_closer_levels.py --volume 13Sam02
  python books/cs-roman/scripts/fixup_closer_levels.py --all
  python books/cs-roman/scripts/fixup_closer_levels.py --all --dry-run
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from paths import OUTPUT_DIR, ensure_import_paths

ensure_import_paths()
from cs_roman_segments import load_document, save_content  # noqa: E402
from cs_roman_text import (  # noqa: E402
    classify_section_closer,
    is_section_closer_formula,
    roman_value_from_text_field,
)

ROOT = Path(__file__).resolve().parents[1]
VOLUMES = ROOT / "volumes"


def _thai_or_roman(seg: dict) -> str:
    text = seg.get("text")
    if isinstance(text, list):
        thai = ""
        roman = ""
        for entry in text:
            if not isinstance(entry, dict):
                continue
            if entry.get("script") == "thai":
                thai = str(entry.get("value") or "")
            elif entry.get("script") == "roman":
                roman = str(entry.get("value") or "")
        return thai or roman
    return roman_value_from_text_field(text)


def _is_closer_segment(seg: dict) -> bool:
    if (seg.get("segment_type") or "") == "niṭṭhitaṃ":
        return True
    return is_section_closer_formula(_thai_or_roman(seg))


def fix_segment(seg: dict) -> bool:
    """Set ``closer_level`` from text; return True if changed."""
    if not _is_closer_segment(seg):
        if "closer_level" in seg:
            seg.pop("closer_level", None)
            return True
        return False
    level = classify_section_closer(_thai_or_roman(seg))
    if seg.get("closer_level") == level:
        return False
    seg["closer_level"] = level
    return True


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
    names: list[str] = []
    for p in sorted(VOLUMES.iterdir()):
        if (p / "data" / "segments.json").is_file():
            names.append(p.name)
    return names


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--volume", help="Volume id (e.g. 13Sam02)")
    ap.add_argument("--all", action="store_true", help="All volumes with segments")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if bool(args.volume) == bool(args.all):
        ap.error("specify exactly one of --volume or --all")
    volumes = [args.volume] if args.volume else all_volumes()
    total = 0
    for vol in volumes:
        for path in volume_paths(vol):
            data = load_document(path)
            n = fix_document(data)
            total += n
            if n == 0:
                print(f"{path}: no closer_level changes")
                continue
            print(f"{path}: updated closer_level on {n} segment(s)")
            if not args.dry_run:
                save_content(path, data)
    print(f"total segments touched: {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
