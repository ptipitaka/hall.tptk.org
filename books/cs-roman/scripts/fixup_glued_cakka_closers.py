#!/usr/bin/env python3
"""Peel ``Khaṇḍacakkaṃ.`` cakka closers glued after a prose/verse sentence stop.

CS Roman prints the bare cakka closer ``Khaṇḍacakkaṃ.`` on its own centered
line (cf. 01Vin01 p204/206/208/209/211/214/215, each stored as its own
``prose`` + ``source_layout: center`` segment keeping the preceding ``item``).
One folio (01Vin01 p212 order 1423 item 327) was extracted with the closer
glued onto the prose body ``…āpatti saṃghādisesassa. Khaṇḍacakkaṃ.`` instead
of being split out. Re-extract reproduces the glue, so this fixup repairs the
stored artifact without re-extracting.

Repair:
  - prose / prose_continuation: peel ``Khaṇḍacakkaṃ.`` trailer; insert a
    centered ``prose`` segment after, keeping ``item``
  - gāthā: peel from the last wak of the last บาท (same shape, if ever seen)

The trailer must follow a sentence stop and leave a substantial body, so
standalone closer segments (value exactly ``Khaṇḍacakkaṃ.``) are left alone.

  python books/cs-roman/scripts/fixup_glued_cakka_closers.py --volume 01Vin01
  python books/cs-roman/scripts/fixup_glued_cakka_closers.py --all
  python books/cs-roman/scripts/fixup_glued_cakka_closers.py --all --dry-run
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
from cs_roman_text import script_text_entries, strip_sentence_spacers  # noqa: E402

_PROSE_TYPES = frozenset({"prose", "prose_continuation"})
_GATHA_TYPES = frozenset({"gatha", "gatha_continuation"})

# Bare cakka closer markers. Extend when new glued cakka families appear.
_CAKKA_CLOSER_ROMAN = "Kha\u1e47\u1e0dacakka\u1e43."
_CAKKA_CLOSER_THAI = "\u0e02\u0e13\u0e3a\u0e11\u0e08\u0e01\u0e3a\u0e01\u0e4d."
_SENTENCE_STOPS = frozenset(".!?\u2026\u201c\u201d\u2019\u2018\"'")


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


def _peel_cakka(value: str, marker: str) -> tuple[str, str] | None:
    """Split a trailing cakka closer after a sentence stop.

    Returns ``(body, closer)`` or ``None``. ``body`` keeps its trailing stop;
    the closer is the exact marker. Standalone-marker segments (no real body
    before it) are rejected so already-split closers are left alone.
    """
    raw = (value or "").rstrip()
    if not raw or not raw.endswith(marker):
        return None
    body = raw[: len(raw) - len(marker)].rstrip()
    if not body or body[-1] not in _SENTENCE_STOPS:
        return None
    if len(strip_sentence_spacers(body).strip()) < 2:
        return None
    return body, marker


def _peel_text_field(text: Any) -> tuple[Any, str] | None:
    """Peel cakka closer from a multi-script ``text`` list or plain string."""
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
        probe = _peel_cakka(roman_v, _CAKKA_CLOSER_ROMAN)
        if probe is None and thai_v:
            probe = _peel_cakka(thai_v, _CAKKA_CLOSER_THAI)
        if probe is None:
            return None
        new_text = copy.deepcopy(text)
        closer = probe[1]
        if roman_i is not None:
            r_peel = _peel_cakka(roman_v, _CAKKA_CLOSER_ROMAN)
            if r_peel is not None:
                new_text[roman_i] = {**new_text[roman_i], "value": r_peel[0]}
                new_text[roman_i].pop("runs", None)
                closer = r_peel[1]
        if thai_i is not None:
            t_peel = _peel_cakka(thai_v, _CAKKA_CLOSER_THAI)
            if t_peel is not None:
                new_text[thai_i] = {**new_text[thai_i], "value": t_peel[0]}
                new_text[thai_i].pop("runs", None)
                if roman_i is None:
                    closer = t_peel[1]
        return new_text, closer
    if isinstance(text, str):
        for marker in (_CAKKA_CLOSER_ROMAN, _CAKKA_CLOSER_THAI):
            peeled = _peel_cakka(text, marker)
            if peeled is not None:
                return peeled[0], peeled[1]
    return None


def _peel_gatha_segment(seg: dict[str, Any]) -> str | None:
    """Peel cakka closer from the last wak; mutate ``seg``; return closer or None."""
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
    new_text, closer = peeled
    last_wak["text"] = new_text
    return closer


def _make_cakka_segment(template: dict[str, Any], closer: str) -> dict[str, Any]:
    """Build a centered ``prose`` closer segment, keeping ``item`` from template."""
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
            "heading_kind",
            "in_toc",
            "section_no",
            "section_rule",
            "needs_review",
            "review_reasons",
        }
    }
    seg["segment_type"] = "prose"
    entries, _has_rule = script_text_entries(closer, normalize_spacing=False)
    seg["text"] = entries
    seg["flags"] = []
    seg["source_layout"] = "center"
    return seg


def unglue_cakka_closers(
    segments: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    """Return new segment list and how many cakka closers were peeled."""
    out: list[dict[str, Any]] = []
    splits = 0
    for seg in segments:
        kind = str(seg.get("segment_type") or "")
        if kind in _GATHA_TYPES:
            closer = _peel_gatha_segment(seg)
            out.append(seg)
            if closer is not None:
                out.append(_make_cakka_segment(seg, closer))
                splits += 1
            continue
        if kind in _PROSE_TYPES:
            peeled = _peel_text_field(seg.get("text"))
            if peeled is None:
                out.append(seg)
                continue
            new_text, closer = peeled
            seg["text"] = new_text
            out.append(seg)
            out.append(_make_cakka_segment(seg, closer))
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
    new_segs, splits = unglue_cakka_closers(segments)
    if splits == 0:
        print(f"{path}: no glued cakka closers")
        return 0
    print(f"{path}: peeled {splits} glued cakka closer(s)")
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
