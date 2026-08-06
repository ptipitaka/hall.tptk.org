#!/usr/bin/env python3
"""Strip solid editorial mid-word hyphens from existing segment JSON.

CS Roman compounds such as ``na-upanissaye`` are extract-normalized to
``naupanissaye`` (peyyāla ``-pa-`` kept). Newer extract/enrich does this
automatically; this script repairs stored volumes without re-extracting PDF.

  python books/cs-roman/scripts/fixup_solid_midword_hyphens.py --volume 01Vin01
  python books/cs-roman/scripts/fixup_solid_midword_hyphens.py --all
  python books/cs-roman/scripts/fixup_solid_midword_hyphens.py --all --dry-run
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
    ensure_script_text,
    needs_solid_midword_hyphen_strip,
    uses_sentence_spacer,
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


def strip_document_midword_hyphens(doc: dict[str, Any]) -> int:
    """Mutate ``doc`` in place; return number of fields repaired.

    Body / hanging Roman is stripped; Thai is re-derived part-wise from the
    hyphenated form first. Footnote ``notes`` / ``symbol_notes`` keep source
    hyphens so generate-time ``roman_to_thai`` can still split morphemes
    (Thai output omits the hyphen).
    """
    fixed = 0
    for seg in doc.get("segments") or []:
        if not isinstance(seg, dict):
            continue
        normalize_spacing = uses_sentence_spacer(
            str(seg.get("segment_type") or "")
        )
        text = seg.get("text")
        if needs_solid_midword_hyphen_strip(
            str(text) if isinstance(text, str) else ""
        ) or (
            isinstance(text, list)
            and any(
                isinstance(e, dict)
                and e.get("script") == "roman"
                and needs_solid_midword_hyphen_strip(str(e.get("value") or ""))
                for e in text
            )
        ):
            entries, _rule, _lost = ensure_script_text(
                text, normalize_spacing=normalize_spacing
            )
            seg["text"] = entries
            fixed += 1

        hanging = seg.get("hanging_lines")
        if isinstance(hanging, list) and hanging:
            hl_out: list[Any] = []
            hl_changed = False
            for hl in hanging:
                needs = False
                if isinstance(hl, str):
                    needs = needs_solid_midword_hyphen_strip(hl)
                elif isinstance(hl, list):
                    needs = any(
                        isinstance(e, dict)
                        and e.get("script") == "roman"
                        and needs_solid_midword_hyphen_strip(
                            str(e.get("value") or "")
                        )
                        for e in hl
                    )
                if needs:
                    entries, _rule, _lost = ensure_script_text(
                        hl, normalize_spacing=normalize_spacing
                    )
                    hl_out.append(entries)
                    hl_changed = True
                    fixed += 1
                else:
                    hl_out.append(hl)
            if hl_changed:
                seg["hanging_lines"] = hl_out

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
        help="Report repairs without writing",
    )
    args = parser.parse_args(argv)

    unique_paths = _iter_segment_paths(
        volume=args.volume,
        all_volumes=args.all_volumes,
        output_only=args.output_only,
    )
    if not unique_paths:
        print("No segments.json paths found", file=sys.stderr)
        return 1

    total = 0
    for path in unique_paths:
        if not path.is_file():
            print(f"skip missing {path}")
            continue
        doc = load_document(path)
        fixed = strip_document_midword_hyphens(doc)
        total += fixed
        if fixed:
            print(f"{path}: repaired {fixed} field(s)")
            if not args.dry_run:
                save_content(path, doc)
        else:
            print(f"{path}: no solid mid-word hyphens")

    print(f"total repaired: {total}" + (" (dry-run)" if args.dry_run else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
