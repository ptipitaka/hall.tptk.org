#!/usr/bin/env python3
"""Demote false heading segments (speech-intro dash / weak+not centered).

CS extract used a weak short-line heuristic that mistagged verse/speech
lead-ins (``…abhāsi–``, ``…paṭicodetha–``) and other flush-left phrases as
``title`` + ``heading_kind``. Basic cues: real short labels are centered
(and preferably bold); a trailing en/em dash means intro-to-quote, not a
heading; Mātikā alignment is preferred for TOC levels.

This repair (no PDF re-extract):
  - trailing ``–`` / ``—`` on ``title`` / ``subhead`` → ``prose``
  - ``weak_heading_heuristic`` without ``source_layout='center'`` → ``prose``
  - clears ``heading_kind`` / ``in_toc`` / related review flags

  python books/cs-roman/scripts/fixup_false_heading_guesses.py --volume 03Vin03
  python books/cs-roman/scripts/fixup_false_heading_guesses.py --all
  python books/cs-roman/scripts/fixup_false_heading_guesses.py --all --dry-run
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from paths import BOOKS, OUTPUT_DIR, ensure_import_paths

ensure_import_paths()
from cs_roman_segments import load_document, save_content  # noqa: E402
from cs_roman_text import roman_value_from_text_field  # noqa: E402
from extract_cs_roman_pdf import ends_with_speech_intro_dash  # noqa: E402

_DEMOTABLE = frozenset({"title", "subhead"})
_HEADING_REVIEW = frozenset(
    {"weak_heading_heuristic", "heading_level_unmatched_matika"}
)


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


def _roman(seg: dict[str, Any]) -> str:
    return roman_value_from_text_field(seg.get("text"))


def fix_segment(seg: dict[str, Any]) -> bool:
    """Demote one false heading; return True if changed."""
    if seg.get("segment_type") not in _DEMOTABLE:
        return False
    roman = _roman(seg)
    reasons = list(seg.get("review_reasons") or [])
    demote = False
    if ends_with_speech_intro_dash(roman):
        demote = True
    elif (
        "weak_heading_heuristic" in reasons
        and seg.get("source_layout") != "center"
    ):
        demote = True
    if not demote:
        return False

    changed = False
    if seg.get("segment_type") != "prose":
        seg["segment_type"] = "prose"
        changed = True
    if seg.pop("heading_kind", None) is not None:
        changed = True
    if seg.pop("in_toc", None):
        changed = True
    new_reasons = [r for r in reasons if r not in _HEADING_REVIEW]
    if new_reasons != reasons:
        if new_reasons:
            seg["review_reasons"] = new_reasons
            seg["needs_review"] = True
        else:
            seg.pop("review_reasons", None)
            seg.pop("needs_review", None)
        changed = True
    elif not new_reasons:
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


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--volume", help="Volume id (e.g. 03Vin03)")
    g.add_argument("--all", action="store_true", help="All volumes with segments")
    g.add_argument(
        "--output-only",
        action="store_true",
        help="Only books/cs-roman/output/*.segments.json",
    )
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    paths = _iter_segment_paths(
        volume=args.volume,
        all_volumes=bool(args.all),
        output_only=bool(args.output_only),
    )
    if not paths:
        print("No segments.json found", file=sys.stderr)
        return 1

    total = 0
    for path in paths:
        if not path.is_file():
            print(f"{path}: missing", file=sys.stderr)
            continue
        data = load_document(path)
        n = fix_document(data)
        total += n
        if n:
            print(f"{path}: {n} false heading(s) demoted")
            if not args.dry_run:
                save_content(path, data)
        else:
            print(f"{path}: ok")
    print(f"Done ({total} segment(s))" + (" [dry-run]" if args.dry_run else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
