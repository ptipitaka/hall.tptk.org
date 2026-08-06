#!/usr/bin/env python3
"""Report unbound footnote segments (``orphan_note``) in segments.json.

These become ``\\orphannote{…}`` at the end of generated TeX — the “stray
footnote on the last page” symptom. Prefer fixing via extract + 
``fixup_orphan_footnote_callouts.py``, not hand-editing one volume.

Example:
  python books/cs-roman/scripts/scan_orphan_notes.py --volume 01Vin01
  python books/cs-roman/scripts/scan_orphan_notes.py --all --strict
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from paths import BOOKS, OUTPUT_DIR, ensure_import_paths

ensure_import_paths()
from cs_roman_segments import load_document  # noqa: E402
from cs_roman_text import roman_value_from_text_field  # noqa: E402
from extract_cs_roman_pdf import (  # noqa: E402
    _BRACKET_NOTE_RE,
    _INLINE_PLUS_CALLOUT_RE,
    _INLINE_STAR_CALLOUT_RE,
    _PAREN_NOTE_RE,
    FOOTNOTE_CALLOUT_RE,
)

_BODY_TYPES = frozenset(
    {
        "prose",
        "prose_continuation",
        "verse",
        "verse_continuation",
        "gatha",
        "gatha_continuation",
        "chapter",
        "title",
        "subhead",
        "centered",
        "niṭṭhitaṃ",
    }
)


def _iter_paths(*, volume: str | None, all_volumes: bool) -> list[Path]:
    paths: list[Path] = []
    if volume:
        paths.append(BOOKS / "volumes" / volume / "data" / "segments.json")
    elif all_volumes:
        paths.extend(sorted((BOOKS / "volumes").glob("*/data/segments.json")))
    return [p for p in paths if p.is_file()]


def _bodies_on_page(segments: list[dict[str, Any]], page: int) -> list[str]:
    out: list[str] = []
    for seg in segments:
        if seg.get("page") != page:
            continue
        if (seg.get("segment_type") or "") not in _BODY_TYPES:
            continue
        roman = roman_value_from_text_field(seg.get("text"))
        if roman:
            out.append(roman)
    return out


def classify_orphan(
    note: dict[str, Any], *, page_bodies: list[str]
) -> str:
    """Return ``bindable_*`` if fixup/extract should have bound this note."""
    flags = note.get("flags") or []
    roman = (roman_value_from_text_field(note.get("text")) or "").strip()
    joined = "\n".join(page_bodies)

    if isinstance(note.get("item"), int):
        item = int(note["item"])
        if FOOTNOTE_CALLOUT_RE.search(joined) and str(item) in joined:
            return "bindable_numbered"
        return "residual_numbered"

    if "plus" in flags:
        if _INLINE_PLUS_CALLOUT_RE.search(joined) or "{{+}}" in joined:
            return "bindable_plus"
        return "residual_plus"

    if "star" in flags:
        if _INLINE_STAR_CALLOUT_RE.search(joined) or "{{*}}" in joined:
            return "bindable_star"
        return "residual_star"

    if _BRACKET_NOTE_RE.match(roman):
        if "[" in joined and "{{[]}}" not in joined:
            return "bindable_bracket"
        return "residual_bracket"

    if _PAREN_NOTE_RE.match(roman):
        if "(" in joined and "{{()}}" not in joined:
            return "bindable_paren"
        return "residual_paren"

    return "residual_other"


def scan_segments(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    orphans = [
        s
        for s in segments
        if s.get("segment_type") == "note"
        and "orphan_note" in (s.get("review_reasons") or [])
    ]
    rows: list[dict[str, Any]] = []
    for note in orphans:
        page = note.get("page")
        bodies = _bodies_on_page(segments, page) if isinstance(page, int) else []
        roman = roman_value_from_text_field(note.get("text")) or ""
        rows.append(
            {
                "page": page,
                "order": note.get("order"),
                "item": note.get("item"),
                "flags": list(note.get("flags") or []),
                "class": classify_orphan(note, page_bodies=bodies),
                "text": roman[:100],
            }
        )
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--volume", help="e.g. 01Vin01")
    group.add_argument("--all", action="store_true", dest="all_volumes")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 if any bindable_* orphan remains (fixup should clear these)",
    )
    parser.add_argument(
        "--forbid-any",
        action="store_true",
        help="Exit 1 if any orphan_note remains",
    )
    args = parser.parse_args(argv)

    paths = _iter_paths(volume=args.volume, all_volumes=args.all_volumes)
    if not paths:
        print("No segments.json found", file=sys.stderr)
        return 1

    total = 0
    bindable = 0
    for path in paths:
        doc = load_document(path)
        rows = scan_segments(list(doc.get("segments") or []))
        vol = path.parent.parent.name if path.parent.name == "data" else path.stem
        total += len(rows)
        n_bind = sum(1 for r in rows if str(r["class"]).startswith("bindable_"))
        bindable += n_bind
        if not rows:
            print(f"{vol}: 0 orphan_note")
            continue
        print(f"{vol}: {len(rows)} orphan_note ({n_bind} bindable)")
        for r in rows:
            print(
                f"  p.{r['page']} order={r['order']} {r['class']}: {r['text']!r}"
            )

    print(f"total orphan_note: {total} (bindable: {bindable})")
    if args.forbid_any and total:
        return 1
    if args.strict and bindable:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
