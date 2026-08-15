#!/usr/bin/env python3
"""Peel section ``Name nāma.`` labels mistagged inside folded gāthā.

CS prints short centered end-labels after a finished pabba/kaṇḍa (etc.):

  ``Maddīpabbaṃ nāma.`` / ``มทฺทีปพฺพํ นาม.``

When the PDF blank line after the verse is missing, extract folds the label
as a leftover วรรค (irregular mixed stanza). Labels are centered prose
furniture, not verse.

Repair:
  - last บาท that is a single-wak ``Name nāma.`` → peel to centered ``prose``
  - whole gāthā that is only that label → convert to centered ``prose``
  - clear ``irregular_gatha_stanza`` when the leftover bat was the only cause

Does not re-extract from PDF. Root-cause guard:
``is_section_nama_colophon`` in extract fold.

  python books/cs-roman/scripts/fixup_glued_gatha_nama_colophons.py --volume 23Khu06
  python books/cs-roman/scripts/fixup_glued_gatha_nama_colophons.py --all
  python books/cs-roman/scripts/fixup_glued_gatha_nama_colophons.py --all --dry-run
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
from cs_roman_text import is_section_nama_colophon, script_text_entries  # noqa: E402

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


def _wak_roman(wak: dict[str, Any]) -> str:
    text = wak.get("text")
    if isinstance(text, list):
        for e in text:
            if isinstance(e, dict) and e.get("script") == "roman":
                return str(e.get("value") or "")
        for e in text:
            if isinstance(e, dict) and e.get("value"):
                return str(e.get("value") or "")
        return ""
    return str(text or "")


def _bat_is_nama_colophon(bat: dict[str, Any]) -> bool:
    waks = bat.get("waks") or []
    if not isinstance(waks, list) or len(waks) != 1:
        return False
    wak = waks[0]
    if not isinstance(wak, dict):
        return False
    return is_section_nama_colophon(_wak_roman(wak))


def _make_label_segment(
    template: dict[str, Any], text_field: Any
) -> dict[str, Any]:
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
    if isinstance(text_field, list):
        seg["text"] = copy.deepcopy(text_field)
    else:
        entries, _ = script_text_entries(str(text_field or ""), normalize_spacing=False)
        seg["text"] = entries
    seg["flags"] = []
    seg["source_layout"] = "center"
    return seg


def _clear_irregular_if_clean(seg: dict[str, Any]) -> None:
    bats = seg.get("bats") or []
    if not isinstance(bats, list):
        return
    # One clean บาท (2 วรรค) or full บท (2×2) no longer needs irregular review
    # when the peeled label was the leftover half.
    wak_n = sum(len(b.get("waks") or []) for b in bats if isinstance(b, dict))
    if wak_n not in {2, 4}:
        return
    reasons = [
        r
        for r in (seg.get("review_reasons") or [])
        if r != "irregular_gatha_stanza"
    ]
    if reasons != (seg.get("review_reasons") or []):
        seg["review_reasons"] = reasons
        seg["needs_review"] = bool(reasons)
    if wak_n == 2 and seg.get("source_layout") == "mixed":
        seg["source_layout"] = "bat_line"


def unglue_nama_colophons(
    segments: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    """Return new segment list and how many ``nāma.`` labels were peeled."""
    out: list[dict[str, Any]] = []
    splits = 0
    for seg in segments:
        kind = str(seg.get("segment_type") or "")
        if kind not in _GATHA_TYPES:
            out.append(seg)
            continue
        bats = seg.get("bats")
        if not isinstance(bats, list) or not bats:
            out.append(seg)
            continue
        last = bats[-1]
        if not isinstance(last, dict) or not _bat_is_nama_colophon(last):
            out.append(seg)
            continue
        waks = last.get("waks") or []
        label_text = waks[0].get("text") if isinstance(waks[0], dict) else None
        splits += 1
        if len(bats) == 1:
            out.append(_make_label_segment(seg, label_text))
            continue
        seg["bats"] = bats[:-1]
        _clear_irregular_if_clean(seg)
        out.append(seg)
        out.append(_make_label_segment(seg, label_text))

    for i, seg in enumerate(out, start=1):
        seg["order"] = i
    return out, splits


def fix_path(path: Path, *, dry_run: bool) -> int:
    if not path.is_file():
        print(f"Skip missing: {path}", file=sys.stderr)
        return 0
    doc = load_document(path)
    segments = list(doc.get("segments") or [])
    new_segs, splits = unglue_nama_colophons(segments)
    if splits == 0:
        print(f"{path}: no glued gatha nāma colophons")
        return 0
    print(f"{path}: peeled {splits} gatha nāma colophon(s)")
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
