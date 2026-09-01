#!/usr/bin/env python3
"""Close mid-token bold splits left by soft-hyphen joins in segment JSON.

Extract joins ``samādahāpeyy-`` + ``a`` into ``samādahāpeyya`` but older runs
kept the leftover letter plain. Thai convert of the stump then emits
``สมาทหาเปยฺยฺ`` + ``อ``. Newer extract snaps bold to the token end; this
repairs stored volumes without re-extracting.

  python books/cs-roman/scripts/fixup_midword_bold_splits.py --volume 02Vin02
  python books/cs-roman/scripts/fixup_midword_bold_splits.py --all
  python books/cs-roman/scripts/fixup_midword_bold_splits.py --all --dry-run
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from paths import BOOKS, OUTPUT_DIR, ensure_import_paths

ensure_import_paths()
from cs_roman_bold import snap_runs_to_token_end  # noqa: E402
from cs_roman_segments import load_document, save_content  # noqa: E402
from cs_roman_text import transliterate_runs  # noqa: E402


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


def _snap_script_entries(entries: list[Any]) -> tuple[list[Any], int]:
    roman_i = next(
        (
            i
            for i, e in enumerate(entries)
            if isinstance(e, dict) and e.get("script") == "roman"
        ),
        None,
    )
    if roman_i is None:
        return entries, 0
    roman = dict(entries[roman_i])
    runs = roman.get("runs")
    value = str(roman.get("value") or "")
    if not isinstance(runs, list) or not runs or not value:
        return entries, 0
    new_runs = snap_runs_to_token_end(value, runs)
    if new_runs is runs:
        return entries, 0
    roman["runs"] = new_runs
    out = list(entries)
    out[roman_i] = roman
    thai_i = next(
        (
            i
            for i, e in enumerate(out)
            if isinstance(e, dict) and e.get("script") == "thai"
        ),
        None,
    )
    if thai_i is not None:
        thai = dict(out[thai_i])
        if new_runs:
            thai["runs"] = transliterate_runs(new_runs)
        else:
            thai.pop("runs", None)
        out[thai_i] = thai
    return out, 1


def _snap_text_field(text: Any) -> tuple[Any, int]:
    if isinstance(text, list):
        return _snap_script_entries(text)
    return text, 0


def snap_document_midword_bold_splits(doc: dict[str, Any]) -> int:
    """Mutate ``doc`` in place; return number of text fields repaired."""
    fixed = 0
    for seg in doc.get("segments") or []:
        if not isinstance(seg, dict):
            continue
        if "text" in seg:
            seg["text"], n = _snap_text_field(seg["text"])
            fixed += n
        hanging = seg.get("hanging_lines")
        if isinstance(hanging, list):
            new_hanging: list[Any] = []
            for hl in hanging:
                new_hl, n = _snap_text_field(hl)
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
                    bat[key], n = _snap_text_field(bat[key])
                    fixed += n
                for wak in bat.get("waks") or []:
                    if not isinstance(wak, dict) or "text" not in wak:
                        continue
                    wak["text"], n = _snap_text_field(wak["text"])
                    fixed += n
                lines = bat.get("lines")
                if isinstance(lines, list):
                    new_lines: list[Any] = []
                    for line in lines:
                        new_line, n = _snap_text_field(line)
                        new_lines.append(new_line)
                        fixed += n
                    bat["lines"] = new_lines
    return fixed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--volume", help="e.g. 02Vin02")
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
        help="Report repairs without writing",
    )
    args = parser.parse_args(argv)

    paths = _iter_segment_paths(
        volume=args.volume,
        all_volumes=args.all_volumes,
        output_only=args.output_only,
    )
    if not paths:
        print("No segments.json paths found", file=sys.stderr)
        return 1

    total = 0
    for path in paths:
        if not path.is_file():
            print(f"skip missing {path}")
            continue
        doc = load_document(path)
        n = snap_document_midword_bold_splits(doc)
        total += n
        if n == 0:
            print(f"{path}: no mid-word bold splits")
            continue
        if args.dry_run:
            print(f"{path}: would repair {n} field(s)")
        else:
            save_content(path, doc)
            print(f"{path}: repaired {n} field(s)")

    print(f"total repaired: {total}" + (" (dry-run)" if args.dry_run else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
