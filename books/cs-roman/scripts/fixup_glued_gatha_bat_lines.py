#!/usr/bin/env python3
"""Peel gāthā printed lines glued by PDF block-join in stored segments JSON.

When the PDF text layer omits a blank line between consecutive verse lines,
``_split_blocks`` joins them into one paragraph. Fold then treats

  ``A, B.{{sp1}} C…``

as one bat line and the right วรรค absorbs the next printed line. Extract now
expands those joins in ``_fold_gatha_printed_lines``; this fixup repairs older
JSON without re-extracting.

Also re-folds ``bat_line`` บาท that stayed as one วรรค because a trailing
``_____`` section rule defeated comma-split (``A, B. _____``). Extract now
peels the rule before the shape test; this fixup repairs stored irregular
stanzas.

  python books/cs-roman/scripts/fixup_glued_gatha_bat_lines.py --volume 13Sam02
  python books/cs-roman/scripts/fixup_glued_gatha_bat_lines.py --all
  python books/cs-roman/scripts/fixup_glued_gatha_bat_lines.py --all --dry-run
"""

from __future__ import annotations

import argparse
import copy
import sys
from pathlib import Path
from typing import Any

from paths import BOOKS, OUTPUT_DIR, ensure_import_paths

ensure_import_paths()
from cs_roman_segments import load_document, save_content  # noqa: E402
from cs_roman_text import (  # noqa: E402
    SECTION_RULE_FLAG,
    roman_value_from_text_field,
    script_text_entries,
)
from extract_cs_roman_pdf import (  # noqa: E402
    Segment,
    _is_bat_printed_line,
    expand_glued_gatha_printed_lines,
    group_gatha_stanzas,
)

_GATHA_TYPES = frozenset({"gatha", "gatha_continuation"})


def _iter_segment_paths(
    *, volume: str | None, all_volumes: bool
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
    seen: set[Path] = set()
    unique: list[Path] = []
    for p in paths:
        rp = p.resolve()
        if rp in seen or not p.is_file():
            continue
        seen.add(rp)
        unique.append(p)
    return unique


def _wak_roman(wak: dict[str, Any]) -> str:
    return roman_value_from_text_field(wak.get("text"))


def reconstruct_gatha_printed_romans(seg: dict[str, Any]) -> list[str]:
    """Rebuild printed-line roman strings from folded ``bats``."""
    layout = seg.get("source_layout") or "bat_line"
    lines: list[str] = []
    for bat in seg.get("bats") or []:
        if not isinstance(bat, dict):
            continue
        waks = [w for w in (bat.get("waks") or []) if isinstance(w, dict)]
        if layout != "wak_line" and len(waks) == 2:
            left = _wak_roman(waks[0]).strip()
            right = _wak_roman(waks[1]).strip()
            if left.endswith(","):
                lines.append(f"{left} {right}".strip())
                continue
        for w in waks:
            r = _wak_roman(w).strip()
            if r:
                lines.append(r)
    return lines


def gatha_has_glued_printed_lines(seg: dict[str, Any]) -> bool:
    """True when any reconstructed printed line expands into more than one."""
    for line in reconstruct_gatha_printed_romans(seg):
        if len(expand_glued_gatha_printed_lines(line)) > 1:
            return True
    return False


def gatha_has_unsplit_bat_wak(seg: dict[str, Any]) -> bool:
    """True when a บาท is still one วรรค but that วรรค is ``A, B.`` shape.

    Typical after extract glued ``_____`` onto the last uddāna line and fold
    skipped comma-split; serialize later stripped the rule into ``section_rule``.

    Mixed print is out of scope: a trailing 1-wak ``A, B.`` is a full printed
    บาท line (05Vin05 p.257 item 336). Full reconstruct+``group_gatha_stanzas``
    would shred the mixed บท (split internal commas, drop the last line).
    """
    layout = seg.get("source_layout") or "bat_line"
    if layout in {"wak_line", "mixed"}:
        return False
    for bat in seg.get("bats") or []:
        if not isinstance(bat, dict):
            continue
        waks = [w for w in (bat.get("waks") or []) if isinstance(w, dict)]
        if len(waks) != 1:
            continue
        if _is_bat_printed_line(_wak_roman(waks[0])):
            return True
    return False


def gatha_needs_bat_refold(seg: dict[str, Any]) -> bool:
    return gatha_has_glued_printed_lines(seg) or gatha_has_unsplit_bat_wak(seg)


def _wak_json_from_roman(roman: str) -> dict[str, Any]:
    entries, _ = script_text_entries(roman, normalize_spacing=False)
    return {"text": entries}


def _segment_obj_to_json(
    grouped: Segment, *, template: dict[str, Any]
) -> dict[str, Any]:
    """Convert a folded extract ``Segment`` back to bilingual JSON."""
    out = {
        k: copy.deepcopy(v)
        for k, v in template.items()
        if k
        not in {
            "text",
            "bats",
            "source_layout",
            "needs_review",
            "review_reasons",
            "hanging_lines",
            "notes",
            "symbol_notes",
        }
    }
    out["segment_type"] = grouped.segment_type
    out["page"] = grouped.page
    if grouped.pdf_page is not None:
        out["pdf_page"] = grouped.pdf_page
    layout = grouped.source_layout
    if layout:
        out["source_layout"] = layout
    else:
        out.pop("source_layout", None)
    bats_in = grouped.bats or []
    json_bats: list[dict[str, Any]] = []
    for bat in bats_in:
        if not isinstance(bat, dict):
            continue
        json_waks: list[dict[str, Any]] = []
        for wak in bat.get("waks") or []:
            if not isinstance(wak, dict):
                continue
            roman = str(wak.get("text") or "")
            json_waks.append(_wak_json_from_roman(roman))
        if json_waks:
            json_bats.append({"waks": json_waks})
    out["bats"] = json_bats
    flags = list(out.get("flags") or [])
    for fl in grouped.flags:
        if fl not in flags:
            flags.append(fl)
    if SECTION_RULE_FLAG in (template.get("flags") or []):
        if SECTION_RULE_FLAG not in flags:
            flags.append(SECTION_RULE_FLAG)
    if flags:
        out["flags"] = flags
    else:
        out.pop("flags", None)
    if grouped.needs_review:
        out["needs_review"] = True
        out["review_reasons"] = list(grouped.review_reasons)
    else:
        out.pop("needs_review", None)
        reasons = [
            r
            for r in (template.get("review_reasons") or [])
            if r != "irregular_gatha_stanza"
        ]
        if reasons:
            out["review_reasons"] = reasons
        else:
            out.pop("review_reasons", None)
    if grouped.notes:
        out["notes"] = list(grouped.notes)
    if grouped.symbol_notes:
        out["symbol_notes"] = dict(grouped.symbol_notes)
    out.pop("text", None)
    out.pop("hanging_lines", None)
    return out


def unglue_gatha_bat_lines(
    segments: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    """Return repaired segments and how many gāthā blocks were re-folded."""
    out: list[dict[str, Any]] = []
    repairs = 0
    for seg in segments:
        if not isinstance(seg, dict) or seg.get("segment_type") not in _GATHA_TYPES:
            out.append(seg)
            continue
        bats = seg.get("bats")
        if not isinstance(bats, list) or not bats:
            out.append(seg)
            continue
        if not gatha_needs_bat_refold(seg):
            out.append(seg)
            continue

        printed: list[str] = []
        for line in reconstruct_gatha_printed_romans(seg):
            printed.extend(expand_glued_gatha_printed_lines(line))
        printed_clean = [p for p in printed if p.strip()]
        line_flags = list(seg.get("flags") or [])
        orig_notes = list(seg.get("notes") or [])
        orig_sym = dict(seg.get("symbol_notes") or {})
        line_segs = [
            Segment(
                page=int(seg.get("page") or 0),
                order=int(seg.get("order") or 0),
                item=None,
                segment_type="gatha",
                text=line,
                pdf_page=seg.get("pdf_page"),
                flags=list(line_flags) if i == len(printed_clean) - 1 else [],
                # Keep markers in ``line``; notes reattached after fold.
                notes=list(orig_notes) if i == 0 else [],
                symbol_notes=dict(orig_sym) if i == 0 else {},
            )
            for i, line in enumerate(printed_clean)
        ]
        grouped = group_gatha_stanzas(line_segs)
        gathas = [
            g
            for g in grouped
            if g.segment_type in {"gatha", "gatha_continuation"}
        ]
        if not gathas:
            out.append(seg)
            continue
        repairs += 1
        # group_gatha_stanzas remaps markers when merging note-carrying lines.
        for g in gathas:
            out.append(_segment_obj_to_json(g, template=seg))
        # Preserve non-gatha peel products (closers / centered parens) if any.
        for g in grouped:
            if g.segment_type in {"gatha", "gatha_continuation"}:
                continue
            trail = {
                k: copy.deepcopy(v)
                for k, v in seg.items()
                if k
                not in {
                    "text",
                    "bats",
                    "source_layout",
                    "needs_review",
                    "review_reasons",
                    "hanging_lines",
                }
            }
            trail["segment_type"] = g.segment_type
            trail["text"] = script_text_entries(g.text, normalize_spacing=False)[0]
            if g.source_layout:
                trail["source_layout"] = g.source_layout
            else:
                trail.pop("source_layout", None)
            trail.pop("bats", None)
            out.append(trail)

    for idx, seg in enumerate(out, start=1):
        if isinstance(seg, dict):
            seg["order"] = idx
    return out, repairs


def fix_document(data: dict[str, Any]) -> int:
    segs = [s for s in (data.get("segments") or []) if isinstance(s, dict)]
    new_segs, n = unglue_gatha_bat_lines(segs)
    if n:
        data["segments"] = new_segs
    return n


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--volume", help="Volume id (e.g. 13Sam02)")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    if bool(args.volume) == bool(args.all):
        ap.error("Specify exactly one of --volume or --all")

    paths = _iter_segment_paths(volume=args.volume, all_volumes=args.all)
    if not paths:
        print("No segments.json found", file=sys.stderr)
        return 1

    total = 0
    for path in paths:
        data = load_document(path)
        n = fix_document(data)
        total += n
        if n:
            print(f"{path}: unglued {n} gatha block(s)")
            if not args.dry_run:
                save_content(path, data, normalize=True)
        else:
            print(f"{path}: ok")
    print(f"Done ({total} repair(s))" + (" [dry-run]" if args.dry_run else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
