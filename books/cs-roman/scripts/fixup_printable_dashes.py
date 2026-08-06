#!/usr/bin/env python3
"""Map PDF U+23AF (HORIZONTAL LINE EXTENSION) → en-dash in segment JSON.

Sarabun has no U+23AF glyph. Newer extract / ``roman_to_thai`` / TeX escape
normalize automatically; this repairs stored volumes without re-extracting.

  python books/cs-roman/scripts/fixup_printable_dashes.py --volume 04Vin04
  python books/cs-roman/scripts/fixup_printable_dashes.py --all
  python books/cs-roman/scripts/fixup_printable_dashes.py --all --dry-run
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
    HORIZONTAL_LINE_EXTENSION,
    normalize_printable_dashes,
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


def _fix_string(value: str) -> tuple[str, int]:
    if HORIZONTAL_LINE_EXTENSION not in value:
        return value, 0
    return normalize_printable_dashes(value), value.count(HORIZONTAL_LINE_EXTENSION)


def _fix_script_entries(entries: list[Any]) -> tuple[list[Any], int]:
    out: list[Any] = []
    n = 0
    for entry in entries:
        if not isinstance(entry, dict):
            out.append(entry)
            continue
        entry = dict(entry)
        value = entry.get("value")
        if isinstance(value, str):
            new_value, hits = _fix_string(value)
            entry["value"] = new_value
            n += hits
        runs = entry.get("runs")
        if isinstance(runs, list):
            new_runs: list[Any] = []
            for run in runs:
                if not isinstance(run, dict):
                    new_runs.append(run)
                    continue
                run = dict(run)
                rv = run.get("value")
                if isinstance(rv, str):
                    new_rv, hits = _fix_string(rv)
                    run["value"] = new_rv
                    n += hits
                new_runs.append(run)
            entry["runs"] = new_runs
        out.append(entry)
    return out, n


def _fix_text_field(text: Any) -> tuple[Any, int]:
    if isinstance(text, str):
        return _fix_string(text)
    if isinstance(text, list):
        return _fix_script_entries(text)
    return text, 0


def fix_document_printable_dashes(doc: dict[str, Any]) -> int:
    """Mutate ``doc`` in place; return number of U+23AF characters replaced."""
    fixed = 0
    for seg in doc.get("segments") or []:
        if not isinstance(seg, dict):
            continue
        if "text" in seg:
            seg["text"], n = _fix_text_field(seg["text"])
            fixed += n
        notes = seg.get("notes")
        if isinstance(notes, list):
            new_notes: list[Any] = []
            for note in notes:
                if isinstance(note, str):
                    new_note, n = _fix_string(note)
                    new_notes.append(new_note)
                    fixed += n
                else:
                    new_notes.append(note)
            seg["notes"] = new_notes
        symbol_notes = seg.get("symbol_notes")
        if isinstance(symbol_notes, dict):
            new_sym: dict[Any, Any] = {}
            for key, value in symbol_notes.items():
                if isinstance(value, str):
                    new_value, n = _fix_string(value)
                    new_sym[key] = new_value
                    fixed += n
                else:
                    new_sym[key] = value
            seg["symbol_notes"] = new_sym
        hanging = seg.get("hanging_lines")
        if isinstance(hanging, list):
            new_hanging: list[Any] = []
            for hl in hanging:
                new_hl, n = _fix_text_field(hl)
                new_hanging.append(new_hl)
                fixed += n
            seg["hanging_lines"] = new_hanging
        bats = seg.get("bats")
        if isinstance(bats, list):
            for bat in bats:
                if not isinstance(bat, dict):
                    continue
                for key in ("left", "right", "text"):
                    if key not in bat:
                        continue
                    bat[key], n = _fix_text_field(bat[key])
                    fixed += n
                lines = bat.get("lines")
                if isinstance(lines, list):
                    new_lines: list[Any] = []
                    for line in lines:
                        new_line, n = _fix_text_field(line)
                        new_lines.append(new_line)
                        fixed += n
                    bat["lines"] = new_lines
    return fixed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--volume", help="e.g. 04Vin04")
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
        help="Report counts without writing",
    )
    args = parser.parse_args(argv)

    paths = _iter_segment_paths(
        volume=args.volume,
        all_volumes=args.all_volumes,
        output_only=args.output_only,
    )
    if not paths:
        print("No segment files found", file=sys.stderr)
        return 1

    total = 0
    for path in paths:
        if not path.is_file():
            print(f"SKIP missing {path}")
            continue
        doc = load_document(path)
        n = fix_document_printable_dashes(doc)
        total += n
        if n == 0:
            print(f"{path}: no U+23AF")
            continue
        if args.dry_run:
            print(f"{path}: would replace {n} U+23AF")
        else:
            save_content(path, doc)
            print(f"{path}: replaced {n} U+23AF → en-dash")

    print(f"total replaced: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
