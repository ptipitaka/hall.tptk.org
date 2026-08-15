#!/usr/bin/env python3
"""Retag exact Tassuddānaṃ labels as segment_type ``tassuddānaṃ``.

The label is a recitation topic-summary cue (what heads were just covered),
not a TOC heading and not an end-formula. Older extracts stored it as
``title`` (+ often bold → ``\\titlehead``).

Repair:
  - exact ``Tassuddānaṃ`` / ``ตสฺสุทฺทานํ`` → ``tassuddānaṃ``
  - clear ``heading_kind`` / ``in_toc``
  - ensure ``source_layout: center``

Does not re-extract from PDF.

  python books/cs-roman/scripts/fixup_tassuddana_labels.py --volume 14Sam03
  python books/cs-roman/scripts/fixup_tassuddana_labels.py --all
  python books/cs-roman/scripts/fixup_tassuddana_labels.py --all --dry-run
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from paths import BOOKS, OUTPUT_DIR, ensure_import_paths

ensure_import_paths()
from cs_roman_segments import load_document, save_content  # noqa: E402
from cs_roman_text import (  # noqa: E402
    is_tassuddana_label,
    roman_value_from_text_field,
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


def _probe_text(seg: dict[str, Any]) -> str:
    roman = roman_value_from_text_field(seg.get("text"))
    if roman:
        return roman
    text = seg.get("text")
    if isinstance(text, list):
        for entry in text:
            if isinstance(entry, dict) and entry.get("script") == "thai":
                return str(entry.get("value") or "")
    return ""


def retag_tassuddana_labels(
    segments: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    """Return segments and how many labels were retagged."""
    n = 0
    for seg in segments:
        probe = _probe_text(seg)
        if not is_tassuddana_label(probe):
            continue
        changed = False
        if seg.get("segment_type") != "tassuddānaṃ":
            seg["segment_type"] = "tassuddānaṃ"
            changed = True
        if seg.get("source_layout") != "center":
            seg["source_layout"] = "center"
            changed = True
        if "heading_kind" in seg:
            seg.pop("heading_kind", None)
            changed = True
        if seg.get("in_toc"):
            seg.pop("in_toc", None)
            changed = True
        if changed:
            n += 1
    return segments, n


def fix_path(path: Path, *, dry_run: bool) -> int:
    if not path.is_file():
        print(f"Skip missing: {path}", file=sys.stderr)
        return 0
    doc = load_document(path)
    segments = list(doc.get("segments") or [])
    new_segs, n = retag_tassuddana_labels(segments)
    if n == 0:
        print(f"{path}: no Tassuddānaṃ retags")
        return 0
    print(f"{path}: retagged {n} Tassuddānaṃ label(s)")
    if dry_run:
        return n
    doc["segments"] = new_segs
    save_content(path, doc)
    return n


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
    print(f"Done: {total} retag(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
