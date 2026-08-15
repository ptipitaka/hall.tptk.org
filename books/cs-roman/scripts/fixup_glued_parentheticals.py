#!/usr/bin/env python3
"""Peel expansion parentheticals glued after a verse/prose sentence stop.

CS Roman often prints ``…padanti.\\n(Appamādavaggo … vitthāretabbo.)`` with
only a single newline. Older extract collapsed that into the last gāthā วรรค
(or prose body). Expansion notes are centered prose furniture, not verse.

Repair:
  - gāthā: peel from the last wak of the last บาท; insert centered ``prose``
  - prose / prose_continuation: peel trailer; insert centered ``prose``

Does not re-extract from PDF. Rejects short refs ``(12-13)`` / ``(150)``.

  python books/cs-roman/scripts/fixup_glued_parentheticals.py --volume 14Sam03
  python books/cs-roman/scripts/fixup_glued_parentheticals.py --all
  python books/cs-roman/scripts/fixup_glued_parentheticals.py --all --dry-run
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
    peel_trailing_expansion_parenthetical,
    script_text_entries,
)

_PROSE_TYPES = frozenset({"prose", "prose_continuation"})
_GATHA_TYPES = frozenset({"gatha", "gatha_continuation"})


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


def _make_paren_segment(template: dict[str, Any], paren: str) -> dict[str, Any]:
    seg = {
        k: copy.deepcopy(v)
        for k, v in template.items()
        if k
        not in {
            "text",
            "text_thai",
            "runs",
            "notes",
            "symbol_notes",
            "source_layout",
            "bats",
            "hanging_lines",
            "flags",
            "item",
            "heading_kind",
            "in_toc",
            "section_no",
            "section_rule",
            "needs_review",
            "review_reasons",
        }
    }
    seg["segment_type"] = "prose"
    entries, _has_rule = script_text_entries(paren, normalize_spacing=False)
    seg["text"] = entries
    seg["flags"] = []
    seg["source_layout"] = "center"
    return seg


def _peel_text_field(text: Any) -> tuple[Any, str] | None:
    """Peel expansion paren from a multi-script ``text`` list or plain string."""
    if isinstance(text, list):
        roman_i = thai_i = None
        roman_v = thai_v = ""
        for i, entry in enumerate(text):
            if not isinstance(entry, dict):
                continue
            script = entry.get("script")
            val = str(entry.get("value") or "")
            if script == "roman":
                roman_i, roman_v = i, val
            elif script == "thai":
                thai_i, thai_v = i, val
        probe = roman_v or thai_v
        peeled = peel_trailing_expansion_parenthetical(probe)
        if peeled is None:
            return None
        body, paren = peeled
        new_text = copy.deepcopy(text)
        if roman_i is not None:
            r_peel = peel_trailing_expansion_parenthetical(roman_v)
            if r_peel is not None:
                new_text[roman_i] = {**new_text[roman_i], "value": r_peel[0]}
                new_text[roman_i].pop("runs", None)
                paren = r_peel[1]
        if thai_i is not None:
            t_peel = peel_trailing_expansion_parenthetical(thai_v)
            if t_peel is not None:
                new_text[thai_i] = {**new_text[thai_i], "value": t_peel[0]}
                new_text[thai_i].pop("runs", None)
                if roman_i is None:
                    paren = t_peel[1]
        return new_text, paren
    if isinstance(text, str):
        peeled = peel_trailing_expansion_parenthetical(text)
        if peeled is None:
            return None
        body, paren = peeled
        return body, paren
    return None


def _peel_gatha_segment(seg: dict[str, Any]) -> str | None:
    """Peel paren from the last wak; mutate ``seg``; return paren or None."""
    bats = seg.get("bats")
    if not isinstance(bats, list) or not bats:
        return None
    last_bat = bats[-1]
    if not isinstance(last_bat, dict):
        return None
    waks = last_bat.get("waks")
    if not isinstance(waks, list) or not waks:
        return None
    last_wak = waks[-1]
    if not isinstance(last_wak, dict):
        return None
    peeled = _peel_text_field(last_wak.get("text"))
    if peeled is None:
        return None
    new_text, paren = peeled
    last_wak["text"] = new_text
    # Drop irregular review if the long wak was only due to the glue.
    reasons = [
        r
        for r in (seg.get("review_reasons") or [])
        if r != "irregular_gatha_stanza"
    ]
    if reasons != (seg.get("review_reasons") or []):
        seg["review_reasons"] = reasons
        seg["needs_review"] = bool(reasons)
    return paren


def unglue_parentheticals(
    segments: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    """Return new segment list and how many parentheticals were peeled."""
    out: list[dict[str, Any]] = []
    splits = 0
    for seg in segments:
        kind = str(seg.get("segment_type") or "")
        if kind in _GATHA_TYPES:
            paren = _peel_gatha_segment(seg)
            out.append(seg)
            if paren is not None:
                out.append(_make_paren_segment(seg, paren))
                splits += 1
            continue
        if kind in _PROSE_TYPES:
            peeled = _peel_text_field(seg.get("text"))
            if peeled is None:
                out.append(seg)
                continue
            new_text, paren = peeled
            seg["text"] = new_text
            out.append(seg)
            out.append(_make_paren_segment(seg, paren))
            splits += 1
            continue
        out.append(seg)

    for i, seg in enumerate(out, start=1):
        seg["order"] = i
    return out, splits


def fix_path(path: Path, *, dry_run: bool) -> int:
    if not path.is_file():
        print(f"Skip missing: {path}", file=sys.stderr)
        return 0
    doc = load_document(path)
    segments = list(doc.get("segments") or [])
    new_segs, splits = unglue_parentheticals(segments)
    if splits == 0:
        print(f"{path}: no glued expansion parentheticals")
        return 0
    print(f"{path}: peeled {splits} expansion parenthetical(s)")
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
    print(f"Done: {total} peel(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
