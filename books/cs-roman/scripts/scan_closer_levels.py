#!/usr/bin/env python3
"""Audit section-closer structural levels across volumes.

Reports counts per ``closer_level`` / visual tier and lists ``unknown``
samples so new lexical families can be added to ``cs_roman_text.py``.

  python books/cs-roman/scripts/scan_closer_levels.py --volume 13Sam02
  python books/cs-roman/scripts/scan_closer_levels.py --all
  python books/cs-roman/scripts/scan_closer_levels.py --all --unknowns 40
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

from paths import ensure_import_paths

ensure_import_paths()
from cs_roman_text import (  # noqa: E402
    classify_section_closer,
    closer_tier,
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


def scan_volume(volume: str) -> tuple[Counter[str], Counter[str], list[str]]:
    path = VOLUMES / volume / "data" / "segments.json"
    if not path.is_file():
        return Counter(), Counter(), []
    data = json.loads(path.read_text(encoding="utf-8"))
    levels: Counter[str] = Counter()
    tiers: Counter[str] = Counter()
    unknowns: list[str] = []
    for seg in data.get("segments") or []:
        if not isinstance(seg, dict) or not _is_closer_segment(seg):
            continue
        text = _thai_or_roman(seg)
        level = classify_section_closer(text)
        levels[level] += 1
        tiers[closer_tier(level)] += 1
        if level == "unknown":
            unknowns.append(f"{volume} p.{seg.get('page')} o.{seg.get('order')}: {text}")
    return levels, tiers, unknowns


def all_volumes() -> list[str]:
    return [
        p.name
        for p in sorted(VOLUMES.iterdir())
        if (p / "data" / "segments.json").is_file()
    ]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--volume", help="Volume id")
    ap.add_argument("--all", action="store_true")
    ap.add_argument(
        "--unknowns",
        type=int,
        default=30,
        help="Max unknown samples to print (default 30)",
    )
    args = ap.parse_args()
    if bool(args.volume) == bool(args.all):
        ap.error("specify exactly one of --volume or --all")
    volumes = [args.volume] if args.volume else all_volumes()

    total_levels: Counter[str] = Counter()
    total_tiers: Counter[str] = Counter()
    all_unknowns: list[str] = []
    per_vol_unknown: dict[str, int] = defaultdict(int)

    for vol in volumes:
        levels, tiers, unknowns = scan_volume(vol)
        total_levels.update(levels)
        total_tiers.update(tiers)
        all_unknowns.extend(unknowns)
        per_vol_unknown[vol] = sum(1 for u in unknowns)
        n = sum(levels.values())
        if n:
            unk = levels.get("unknown", 0)
            print(
                f"{vol}: closers={n} unknown={unk} "
                f"major={tiers.get('major', 0)} "
                f"mid={tiers.get('mid', 0)} "
                f"leaf={tiers.get('leaf', 0)}"
            )

    print("---")
    print("levels:", dict(total_levels.most_common()))
    print("tiers:", dict(total_tiers.most_common()))
    total = sum(total_levels.values())
    unk = total_levels.get("unknown", 0)
    if total:
        print(f"unknown rate: {unk}/{total} ({100.0 * unk / total:.1f}%)")
    if args.unknowns > 0 and all_unknowns:
        print("--- unknown samples ---")
        for line in all_unknowns[: args.unknowns]:
            print(line)
        if len(all_unknowns) > args.unknowns:
            print(f"... +{len(all_unknowns) - args.unknowns} more")
    return 0


if __name__ == "__main__":
    sys.exit(main())
