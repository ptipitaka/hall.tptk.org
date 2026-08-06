#!/usr/bin/env python3
"""Re-bind orphan footnotes to callouts in segment JSON (no PDF re-extract).

Covers:
  - numbered orphans (spaced/glued ``word 1`` / ``word1``)
  - mid-paragraph `` + `` / `` * `` apparatus orphans
  - bracket ``[  ] …`` apparatus orphans (Syāma omission notes)
  - empty-paren ``(  ) …`` apparatus orphans (non-folio body ``(``)
  - repair folio-stolen ``({{()}}150)`` back onto numbered callouts

  python books/cs-roman/scripts/fixup_orphan_footnote_callouts.py --volume 01Vin01
  python books/cs-roman/scripts/fixup_orphan_footnote_callouts.py --all
  python books/cs-roman/scripts/fixup_orphan_footnote_callouts.py --all --dry-run
"""

from __future__ import annotations

import argparse
import copy
import re
import sys
from pathlib import Path
from typing import Any

from paths import BOOKS, OUTPUT_DIR, ensure_import_paths

ensure_import_paths()
from cs_roman_segments import load_document, save_content  # noqa: E402
from cs_roman_text import (  # noqa: E402
    ensure_script_text,
    roman_value_from_text_field,
)
from extract_cs_roman_pdf import (  # noqa: E402
    FOOTNOTE_CALLOUT_RE,
    _BRACKET_NOTE_RE,
    _INLINE_PLUS_CALLOUT_RE,
    _INLINE_STAR_CALLOUT_RE,
    _PAREN_NOTE_RE,
    _insert_empty_paren_marker,
    apply_numbered_footnote_callouts,
    is_spaced_outline_number,
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


def _is_orphan_note(seg: dict[str, Any]) -> bool:
    if seg.get("segment_type") != "note":
        return False
    reasons = seg.get("review_reasons") or []
    return "orphan_note" in reasons


def _rewrite_roman(seg: dict[str, Any], new_roman: str) -> None:
    entries, _rule, _bold_lost = ensure_script_text(
        new_roman, force=True, normalize_spacing=True
    )
    seg["text"] = entries


def _rebind_numbered(segments: list[dict[str, Any]], bound_ids: set[int]) -> int:
    orphans_by_page: dict[int, list[dict[str, Any]]] = {}
    for seg in segments:
        if not _is_orphan_note(seg) or id(seg) in bound_ids:
            continue
        if not isinstance(seg.get("item"), int):
            continue
        page = seg.get("page")
        if isinstance(page, int):
            orphans_by_page.setdefault(page, []).append(seg)

    fixed = 0
    for seg in segments:
        st = seg.get("segment_type") or ""
        if st not in _BODY_TYPES:
            continue
        page = seg.get("page")
        if not isinstance(page, int):
            continue
        page_orphans = [
            n for n in orphans_by_page.get(page, []) if id(n) not in bound_ids
        ]
        if not page_orphans:
            continue

        numbered = {
            int(n["item"]): roman_value_from_text_field(n.get("text"))
            for n in page_orphans
            if roman_value_from_text_field(n.get("text"))
        }
        if not numbered:
            continue

        roman = roman_value_from_text_field(seg.get("text"))
        if not roman:
            continue

        existing_notes = list(seg.get("notes") or [])
        new_roman, bound_notes, used_items = apply_numbered_footnote_callouts(
            roman,
            numbered,
            note_index_base=len(existing_notes),
        )
        if not used_items:
            continue

        _rewrite_roman(seg, new_roman)
        seg["notes"] = existing_notes + bound_notes
        for n in page_orphans:
            if int(n["item"]) in used_items:
                bound_ids.add(id(n))
                fixed += 1
    return fixed


def _rebind_inline_symbol(
    segments: list[dict[str, Any]], bound_ids: set[int], *, mark: str
) -> int:
    callout_re = (
        _INLINE_PLUS_CALLOUT_RE if mark == "+" else _INLINE_STAR_CALLOUT_RE
    )
    flag = "plus" if mark == "+" else "star"
    marker = "{{" + mark + "}}"
    orphans_by_page: dict[int, list[dict[str, Any]]] = {}
    for seg in segments:
        if not _is_orphan_note(seg) or id(seg) in bound_ids:
            continue
        flags = seg.get("flags") or []
        if flag not in flags:
            continue
        page = seg.get("page")
        if isinstance(page, int):
            orphans_by_page.setdefault(page, []).append(seg)

    fixed = 0
    for seg in segments:
        st = seg.get("segment_type") or ""
        if st not in _BODY_TYPES:
            continue
        page = seg.get("page")
        if not isinstance(page, int):
            continue
        page_orphans = [
            n for n in orphans_by_page.get(page, []) if id(n) not in bound_ids
        ]
        if not page_orphans:
            continue
        roman = roman_value_from_text_field(seg.get("text"))
        if not roman or marker in roman or not callout_re.search(roman):
            continue
        note = page_orphans[0]
        note_roman = roman_value_from_text_field(note.get("text"))
        if not note_roman:
            continue
        new_roman = callout_re.sub(marker, roman, count=1)
        _rewrite_roman(seg, new_roman)
        sym = dict(seg.get("symbol_notes") or {})
        sym[mark] = note_roman
        seg["symbol_notes"] = sym
        bound_ids.add(id(note))
        fixed += 1
    return fixed


def _rebind_bracket(segments: list[dict[str, Any]], bound_ids: set[int]) -> int:
    orphans_by_page: dict[int, list[dict[str, Any]]] = {}
    for seg in segments:
        if not _is_orphan_note(seg) or id(seg) in bound_ids:
            continue
        if isinstance(seg.get("item"), int):
            continue
        roman = roman_value_from_text_field(seg.get("text"))
        if not roman or not _BRACKET_NOTE_RE.match(roman.strip()):
            continue
        page = seg.get("page")
        if isinstance(page, int):
            orphans_by_page.setdefault(page, []).append(seg)

    fixed = 0
    for seg in segments:
        st = seg.get("segment_type") or ""
        if st not in _BODY_TYPES:
            continue
        page = seg.get("page")
        if not isinstance(page, int):
            continue
        page_orphans = [
            n for n in orphans_by_page.get(page, []) if id(n) not in bound_ids
        ]
        if not page_orphans:
            continue
        roman = roman_value_from_text_field(seg.get("text"))
        if not roman or "[" not in roman or "{{[]}}" in roman:
            continue
        note = page_orphans[0]
        note_roman = roman_value_from_text_field(note.get("text")) or ""
        m = _BRACKET_NOTE_RE.match(note_roman.strip())
        if m is None:
            continue
        new_roman = roman.replace("[", "[{{[]}}", 1)
        _rewrite_roman(seg, new_roman)
        sym = dict(seg.get("symbol_notes") or {})
        sym["[]"] = m.group(1).strip()
        seg["symbol_notes"] = sym
        bound_ids.add(id(note))
        fixed += 1
    return fixed


def _rebind_paren(segments: list[dict[str, Any]], bound_ids: set[int]) -> int:
    orphans_by_page: dict[int, list[dict[str, Any]]] = {}
    for seg in segments:
        if not _is_orphan_note(seg) or id(seg) in bound_ids:
            continue
        # Numbered footnotes whose body starts with ``( )`` stay numbered.
        if isinstance(seg.get("item"), int):
            continue
        roman = roman_value_from_text_field(seg.get("text"))
        if not roman or not _PAREN_NOTE_RE.match(roman.strip()):
            continue
        page = seg.get("page")
        if isinstance(page, int):
            orphans_by_page.setdefault(page, []).append(seg)

    fixed = 0
    for seg in segments:
        st = seg.get("segment_type") or ""
        if st not in _BODY_TYPES:
            continue
        page = seg.get("page")
        if not isinstance(page, int):
            continue
        page_orphans = [
            n for n in orphans_by_page.get(page, []) if id(n) not in bound_ids
        ]
        if not page_orphans:
            continue
        roman = roman_value_from_text_field(seg.get("text"))
        if not roman or "{{()}}" in roman:
            continue
        marked = _insert_empty_paren_marker(roman)
        if marked is None:
            continue
        note = page_orphans[0]
        note_roman = roman_value_from_text_field(note.get("text")) or ""
        m = _PAREN_NOTE_RE.match(note_roman.strip())
        if m is None:
            continue
        _rewrite_roman(seg, marked)
        sym = dict(seg.get("symbol_notes") or {})
        sym["()"] = m.group(1).strip()
        seg["symbol_notes"] = sym
        bound_ids.add(id(note))
        fixed += 1
    return fixed


_FOLIO_BOUND_PAREN_RE = re.compile(r"\(\{\{\(\)\}\}(\d+(?:-\d+)?)\)")


def _repair_folio_bound_paren_notes(segments: list[dict[str, Any]]) -> int:
    """Undo ``({{()}}150)`` when a numbered ``( ) …`` note was stolen onto a folio.

    Restores the folio marker, rebuilds the note body as ``( ) …``, and binds
    it to an unbound numbered callout on the same page (e.g. ``(te)2``).
    """
    stolen_by_page: dict[int, list[str]] = {}
    fixed = 0
    for seg in segments:
        st = seg.get("segment_type") or ""
        if st not in _BODY_TYPES:
            continue
        page = seg.get("page")
        if not isinstance(page, int):
            continue
        roman = roman_value_from_text_field(seg.get("text"))
        if not roman:
            continue
        m = _FOLIO_BOUND_PAREN_RE.search(roman)
        if m is None:
            continue
        sym = dict(seg.get("symbol_notes") or {})
        body_tail = sym.get("()")
        if not body_tail:
            continue
        new_roman = _FOLIO_BOUND_PAREN_RE.sub(r"(\1)", roman, count=1)
        _rewrite_roman(seg, new_roman)
        sym.pop("()", None)
        if sym:
            seg["symbol_notes"] = sym
        else:
            seg.pop("symbol_notes", None)
        stolen_by_page.setdefault(page, []).append("( ) " + body_tail)
        fixed += 1

    if not stolen_by_page:
        return 0

    for page, bodies in stolen_by_page.items():
        remaining = list(bodies)
        for seg in segments:
            if not remaining:
                break
            st = seg.get("segment_type") or ""
            if st not in _BODY_TYPES or seg.get("page") != page:
                continue
            roman = roman_value_from_text_field(seg.get("text"))
            if not roman:
                continue
            # Offer each stolen body under every still-literal callout digit;
            # apply_numbered_footnote_callouts binds only digits present.
            candidates: dict[int, str] = {}
            body_iter = iter(remaining)
            used_body_for_num: dict[int, str] = {}
            for match in FOOTNOTE_CALLOUT_RE.finditer(roman):
                spaces, num_s, trailer = (
                    match.group(1),
                    match.group(2),
                    match.group(3),
                )
                if is_spaced_outline_number(spaces, trailer):
                    continue
                num = int(num_s)
                if num in candidates:
                    continue
                try:
                    note_body = next(body_iter)
                except StopIteration:
                    break
                candidates[num] = note_body
                used_body_for_num[num] = note_body
            if not candidates:
                continue
            existing_notes = list(seg.get("notes") or [])
            new_roman, bound_notes, used_items = apply_numbered_footnote_callouts(
                roman,
                candidates,
                note_index_base=len(existing_notes),
            )
            if not used_items:
                continue
            _rewrite_roman(seg, new_roman)
            seg["notes"] = existing_notes + bound_notes
            for num in used_items:
                body = used_body_for_num[num]
                if body in remaining:
                    remaining.remove(body)
        # leftover stolen bodies stay unbound (should not happen on known pages)

    return fixed


def rebind_orphan_footnote_callouts(segments: list[dict[str, Any]]) -> int:
    """Mutate ``segments`` in place; return number of notes bound."""
    bound_ids: set[int] = set()
    fixed = 0
    fixed += _repair_folio_bound_paren_notes(segments)
    fixed += _rebind_numbered(segments, bound_ids)
    fixed += _rebind_inline_symbol(segments, bound_ids, mark="+")
    fixed += _rebind_inline_symbol(segments, bound_ids, mark="*")
    fixed += _rebind_bracket(segments, bound_ids)
    fixed += _rebind_paren(segments, bound_ids)

    if not fixed:
        return 0

    segments[:] = [s for s in segments if id(s) not in bound_ids]
    for i, seg in enumerate(segments, start=1):
        seg["order"] = i
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
        help="Report bindings without writing",
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
        segments = doc.get("segments") or []
        if args.dry_run:
            trial = copy.deepcopy(segments)
            fixed = rebind_orphan_footnote_callouts(trial)
        else:
            fixed = rebind_orphan_footnote_callouts(segments)
        total += fixed
        if fixed:
            print(f"{path}: bound {fixed} orphan note(s)")
            if not args.dry_run:
                save_content(path, doc)
        else:
            print(f"{path}: no orphan callouts rebound")

    print(f"total bound: {total}" + (" (dry-run)" if args.dry_run else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
