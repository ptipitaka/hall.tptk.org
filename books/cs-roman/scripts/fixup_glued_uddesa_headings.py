#!/usr/bin/env python3
"""Peel pātimokkha uddesa prose glued onto short headings in segment JSON.

PDF extract often joins ``Cīvaravagga 1. Paṭhamakathinasikkhāpada`` with
``Ime kho… uddesaṃ āgacchanti.`` (no blank line). That fails the 80-char
heading gate and lands as ``prose`` with a false Tipiṭaka ``item``.

This repair:
  - splits heading + uddesa body into two segments
  - promotes a leading false ``item`` to ``section_no`` on the heading
  - assigns ``heading_kind`` / ``in_toc`` via ``fallback_kind``
  - renumbers ``order`` sequentially from 1

Does not re-extract from PDF.

  python books/cs-roman/scripts/fixup_glued_uddesa_headings.py --volume 01Vin01
  python books/cs-roman/scripts/fixup_glued_uddesa_headings.py --all
  python books/cs-roman/scripts/fixup_glued_uddesa_headings.py --all --dry-run
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
    roman_value_from_text_field,
    script_text_entries,
)
from extract_cs_roman_pdf import (  # noqa: E402
    _classify_heading,
    peel_glued_uddesa_heading,
)

_PEELABLE_TYPES = frozenset({"prose", "chapter", "title", "subhead", "centered"})


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
    seg["in_toc"] = in_toc


def unglue_uddesa_headings(segments: list[dict[str, Any]]) -> int:
    """Mutate ``segments`` in place; return number of peels performed."""
    out: list[dict[str, Any]] = []
    fixed = 0
    for seg in segments:
        st = seg.get("segment_type") or ""
        if st not in _PEELABLE_TYPES:
            out.append(seg)
            continue
        roman = roman_value_from_text_field(seg.get("text"))
        peeled = peel_glued_uddesa_heading(roman)
        if peeled is None:
            out.append(seg)
            continue

        title, body = peeled
        heading_kind, reasons = _classify_heading(title)
        assert heading_kind is not None

        heading: dict[str, Any] = {
            "page": seg.get("page"),
            "order": seg.get("order"),
            "segment_type": heading_kind,
            "text": _make_text(title, heading=True),
        }
        item = seg.get("item")
        if item is not None and item != "":
            # Leading outline number was mis-stored as Tipiṭaka item.
            heading["section_no"] = item
        elif seg.get("section_no") is not None:
            heading["section_no"] = seg["section_no"]

        layout = seg.get("source_layout")
        if layout:
            heading["source_layout"] = layout

        # Preserve prior heading meta when already classified; else fallback.
        if seg.get("heading_kind") and st in {"chapter", "title", "subhead"}:
            heading["heading_kind"] = seg["heading_kind"]
            heading["in_toc"] = bool(seg.get("in_toc"))
        else:
            _apply_heading_meta(heading)

        if reasons:
            heading["needs_review"] = True
            heading["review_reasons"] = list(reasons)

        prose: dict[str, Any] = {
            "page": seg.get("page"),
            "order": seg.get("order"),
            "segment_type": "prose",
            "text": _make_text(body, heading=False),
        }
        if layout:
            prose["source_layout"] = layout

        out.append(heading)
        out.append(prose)
        fixed += 1

    if fixed:
        for i, seg in enumerate(out, start=1):
            seg["order"] = i
        segments[:] = out
    return fixed


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
        help="Report peels without writing",
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

    total = 0
    for path in unique_paths:
        if not path.is_file():
            print(f"Skip missing: {path}", file=sys.stderr)
            continue
        doc = load_document(path)
        segments = list(doc.get("segments") or [])
        fixed = unglue_uddesa_headings(segments)
        total += fixed
        print(f"{path}: peeled={fixed}")
        if args.dry_run or fixed == 0:
            continue
        doc["segments"] = segments
        save_content(path, doc, normalize=True)

    print(f"Total peeled headings: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
