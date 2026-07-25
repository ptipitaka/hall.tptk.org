"""
Enrich cs-roman segment JSON: ``text`` string → multi-script list.

  [{ "script": "roman", "value": "..." }, { "script": "thai", "value": "..." }]

Example:
  docker compose exec -T web python books/cs-roman/scripts/enrich_cs_roman_thai.py
  docker compose exec -T web python books/cs-roman/scripts/enrich_cs_roman_thai.py \\
      books/cs-roman/output/01Vin01.segments.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from paths import OUTPUT_DIR, ensure_import_paths

ensure_import_paths()
from cs_roman_segments import save as save_segments  # noqa: E402
from cs_roman_text import (  # noqa: E402
    SECTION_RULE_FLAG,
    ensure_script_text,
    needs_spacing_normalize,
)

DEFAULT_DIR = OUTPUT_DIR


def enrich_document(data: dict, *, force: bool = False) -> tuple[dict, int]:
    """Return (updated doc, number of segments converted)."""
    data = dict(data)
    converted = 0
    segments = []
    for seg in data.get("segments") or []:
        seg = dict(seg)
        before = seg.get("text")
        already = (
            isinstance(before, list)
            and any(isinstance(e, dict) and e.get("script") == "thai" for e in before)
        )
        entries, had_rule = ensure_script_text(before, force=force)
        seg["text"] = entries
        hanging = seg.get("hanging_lines")
        if isinstance(hanging, list) and hanging:
            hl_out: list = []
            for hl in hanging:
                hl_entries, hl_rule = ensure_script_text(hl, force=force)
                had_rule = had_rule or hl_rule
                hl_out.append(hl_entries)
            seg["hanging_lines"] = hl_out
        flags = [f for f in (seg.get("flags") or []) if f != SECTION_RULE_FLAG]
        if had_rule:
            flags.append(SECTION_RULE_FLAG)
        seg["flags"] = flags
        if force or not already or had_rule:
            converted += 1
        segments.append(seg)
    data["segments"] = segments
    return data, converted


def enrich_file(path: Path, *, force: bool = False) -> tuple[int, int]:
    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    segs = data.get("segments") or []
    already = bool(
        segs
        and isinstance(segs[0].get("text"), list)
        and any(
            isinstance(e, dict) and e.get("script") == "thai"
            for e in segs[0]["text"]
        )
    )
    # Still rewrite when sentence-stop / pot-ma-gyi spacing needs {{sp1}}.
    needs_spacing = needs_spacing_normalize(raw)
    if not force and already and not needs_spacing:
        return 0, len(segs)

    data, converted = enrich_document(data, force=force or needs_spacing)
    save_segments(path, data, normalize=True)
    return converted, len(data["segments"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="JSON file(s) or directory (default: books/cs-roman/output)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-transliterate even if thai entries already exist",
    )
    args = parser.parse_args(argv)

    targets: list[Path] = []
    paths = args.paths or [DEFAULT_DIR]
    for p in paths:
        if p.is_dir():
            targets.extend(sorted(p.glob("*.segments.json")))
        elif p.is_file():
            targets.append(p)
        else:
            print(f"Skip missing: {p}", file=sys.stderr)

    if not targets:
        print("No segment JSON files found.", file=sys.stderr)
        return 1

    for path in targets:
        converted, total = enrich_file(path, force=args.force)
        print(f"{path.name}: {converted}/{total} segments -> multi-script text")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
