#!/usr/bin/env python3
"""Normalize ordinal section closers (…วคฺโค ปฐโม. / …vaggo paṭhamo.).

1. Strip mistagged ``heading_kind`` / TOC flags (they are closers, not heads).
2. Ensure ``section_rule`` — CS sometimes drops the underscore rule when the
   closer sits on a page foot that already has a footnote separator; our
   pagination differs, so restore the conventional end rule.

  python books/cs-roman/scripts/fixup_ordinal_section_closers.py --volume 02Vin02
  python books/cs-roman/scripts/fixup_ordinal_section_closers.py --all
  python books/cs-roman/scripts/fixup_ordinal_section_closers.py --all --dry-run
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from paths import OUTPUT_DIR, ensure_import_paths

ensure_import_paths()
from cs_roman_segments import load_document, save_content  # noqa: E402
from cs_roman_text import (  # noqa: E402
    SECTION_RULE_FLAG,
    is_ordinal_section_closer,
    roman_value_from_text_field,
)

ROOT = Path(__file__).resolve().parents[1]
VOLUMES = ROOT / "volumes"

_HEADING_REVIEW = frozenset(
    {"weak_heading_heuristic", "heading_level_unmatched_matika"}
)


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


def fix_segment(seg: dict) -> bool:
    """Normalize one ordinal closer; return True if changed."""
    probe = _thai_or_roman(seg)
    if not is_ordinal_section_closer(probe):
        return False
    changed = False
    if seg.pop("heading_kind", None) is not None:
        changed = True
    if seg.pop("in_toc", None):
        changed = True
    flags = list(seg.get("flags") or [])
    if SECTION_RULE_FLAG not in flags:
        flags.append(SECTION_RULE_FLAG)
        seg["flags"] = flags
        changed = True
    reasons = [
        r for r in (seg.get("review_reasons") or []) if r not in _HEADING_REVIEW
    ]
    if reasons != (seg.get("review_reasons") or []):
        if reasons:
            seg["review_reasons"] = reasons
            seg["needs_review"] = True
        else:
            seg.pop("review_reasons", None)
            seg.pop("needs_review", None)
        changed = True
    elif not reasons:
        if seg.pop("needs_review", None) is not None:
            changed = True
        if seg.pop("review_reasons", None) is not None:
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
    names: list[str] = []
    for p in sorted(VOLUMES.iterdir()):
        if (p / "data" / "segments.json").is_file():
            names.append(p.name)
    return names


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--volume", help="Volume id (e.g. 02Vin02)")
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
                print(f"{path}: {n} ordinal closer(s) normalized")
                if not args.dry_run:
                    save_content(path, data)
            else:
                print(f"{path}: ok")
    print(f"Done ({total} segment(s))" + (" [dry-run]" if args.dry_run else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
