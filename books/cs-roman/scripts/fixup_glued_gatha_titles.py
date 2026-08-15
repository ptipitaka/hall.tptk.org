#!/usr/bin/env python3
"""Peel uddāna / gāthā titles glued to verse lines in stored segments JSON.

When the PDF text layer omits the blank line after ``Tassuddānaṃ`` (etc.),
extract keeps title + bat/wak verses in one ``prose`` segment; center geometry
then emits ``\\csromancenter{title verse…}`` instead of title + gāthā.

Repair:
  - splits title + each verse line into separate segments
  - promotes title to ``title``; leaves verses as ``prose`` so
    ``fixup_gatha_geometry`` can retag + fold into ``bats``
  - moves ``section_rule`` flag onto the last verse line when present
  - renumbers ``order`` from 1

Does not re-extract from PDF. After this fixup run::

  python books/cs-roman/scripts/fixup_gatha_geometry.py --volume <id>
  python books/cs-roman/scripts/fixup_center_layout.py --volume <id>

  python books/cs-roman/scripts/fixup_glued_gatha_titles.py --volume 01Vin01
  python books/cs-roman/scripts/fixup_glued_gatha_titles.py --all
  python books/cs-roman/scripts/fixup_glued_gatha_titles.py --all --dry-run
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from paths import BOOKS, OUTPUT_DIR, ensure_import_paths

ensure_import_paths()
from assign_cs_roman_heading_levels import fallback_kind  # noqa: E402
from cs_roman_segments import load_document, save_content  # noqa: E402
from cs_roman_text import (  # noqa: E402
    SECTION_RULE_FLAG,
    is_tassuddana_label,
    roman_value_from_text_field,
    script_text_entries,
)
from extract_cs_roman_pdf import peel_glued_gatha_title_text  # noqa: E402

_PEELABLE_TYPES = frozenset({"prose", "prose_continuation", "centered"})


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


def _make_text(roman: str, *, heading: bool) -> list[dict[str, Any]]:
    entries, _has_rule = script_text_entries(
        roman, normalize_spacing=not heading
    )
    return entries


def _apply_heading_meta(seg: dict[str, Any]) -> None:
    roman = roman_value_from_text_field(seg.get("text"))
    kind, in_toc = fallback_kind(seg, roman)
    if kind:
        seg["heading_kind"] = kind
    else:
        seg.pop("heading_kind", None)
    if in_toc:
        seg["in_toc"] = True
    else:
        seg.pop("in_toc", None)


def unglue_gatha_titles(segments: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    """Return new segment list and how many glued titles were split."""
    out: list[dict[str, Any]] = []
    splits = 0
    for seg in segments:
        kind = str(seg.get("segment_type") or "")
        if kind not in _PEELABLE_TYPES:
            out.append(seg)
            continue
        roman = roman_value_from_text_field(seg.get("text"))
        peeled = peel_glued_gatha_title_text(roman)
        if peeled is None:
            out.append(seg)
            continue
        title, verses = peeled
        splits += 1
        flags = list(seg.get("flags") or [])
        had_rule = SECTION_RULE_FLAG in flags
        flags_no_rule = [f for f in flags if f != SECTION_RULE_FLAG]

        title_seg = {
            k: v
            for k, v in seg.items()
            if k
            not in {
                "text",
                "text_thai",
                "runs",
                "notes",
                "source_layout",
                "bats",
                "hanging_lines",
                "flags",
                "item",
                "heading_kind",
                "in_toc",
            }
        }
        if is_tassuddana_label(title):
            title_seg["segment_type"] = "tassuddānaṃ"
            title_seg["text"] = _make_text(title, heading=True)
            title_seg["flags"] = []
            title_seg["source_layout"] = "center"
            title_seg.pop("heading_kind", None)
            title_seg.pop("in_toc", None)
        else:
            title_seg["segment_type"] = "title"
            title_seg["text"] = _make_text(title, heading=True)
            title_seg["flags"] = []
            title_seg.pop("source_layout", None)
            _apply_heading_meta(title_seg)
        out.append(title_seg)

        for i, verse in enumerate(verses):
            verse_seg = {
                k: v
                for k, v in seg.items()
                if k
                not in {
                    "text",
                    "text_thai",
                    "runs",
                    "notes",
                    "source_layout",
                    "bats",
                    "hanging_lines",
                    "flags",
                    "heading_kind",
                    "in_toc",
                }
            }
            verse_seg["segment_type"] = "prose"
            verse_seg["item"] = None
            verse_seg["text"] = _make_text(verse, heading=False)
            verse_flags = list(flags_no_rule)
            if had_rule and i == len(verses) - 1:
                verse_flags.append(SECTION_RULE_FLAG)
            verse_seg["flags"] = verse_flags
            verse_seg.pop("source_layout", None)
            verse_seg.pop("heading_kind", None)
            verse_seg.pop("in_toc", None)
            out.append(verse_seg)

    for i, seg in enumerate(out, start=1):
        seg["order"] = i
    return out, splits


def fix_path(path: Path, *, dry_run: bool) -> int:
    if not path.is_file():
        print(f"Skip missing: {path}", file=sys.stderr)
        return 0
    doc = load_document(path)
    segments = list(doc.get("segments") or [])
    new_segs, splits = unglue_gatha_titles(segments)
    if splits == 0:
        print(f"{path}: no glued gatha titles")
        return 0
    print(f"{path}: split {splits} glued gatha title(s)")
    if dry_run:
        return splits
    doc["segments"] = new_segs
    save_content(path, doc)
    return splits


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
        total += fix_path(path, dry_run=args.dry_run)
    print(f"Done: {total} split(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
