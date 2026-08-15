#!/usr/bin/env python3
"""Peel prose mistagged inside folded gāthā segments.

Repairs stored ``segments.json`` when extract glued narrative into verse:

  - whole-segment prose mistag: every บาท is long prose (>70 char วรรค) →
    peel each บาท to its own ``prose`` segment (no verse remains). Catches
    commentary/approval/closing printed in bat/wak columns (e.g. 10Ma02 p.21).
  - 3rd บาท that is prose (false 1 บทครึ่ง) → peel to ``prose`` after the บท
  - ``wak_line`` / mixed บท whose first วรรค is speech-intro or long prose
    (>70) → peel that line to ``prose``, then re-fold the remaining วรรค
    (absorbing a following irregular half-บท when present). Short quote
    วรรค (``“X”ti …``) stay verse — 19Khu02 / 22Khu05 / 23Khu06.

Does not re-extract from PDF. Root-cause guards live in
``extract_cs_roman_pdf`` (speech-intro / prose-not-wak; bat_line-only บทครึ่ง).

  python books/cs-roman/scripts/fixup_false_gatha_prose.py --volume 03Vin03
  python books/cs-roman/scripts/fixup_false_gatha_prose.py --all
  python books/cs-roman/scripts/fixup_false_gatha_prose.py --all --dry-run
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
from cs_roman_text import script_text_entries  # noqa: E402
from extract_cs_roman_pdf import (  # noqa: E402
    _gatha_line_body,
    _looks_like_prose_not_gatha_wak,
    ends_with_speech_intro_dash,
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


def _wak_thai(wak: dict[str, Any]) -> str:
    text = wak.get("text")
    if isinstance(text, list):
        for e in text:
            if isinstance(e, dict) and e.get("script") == "thai":
                return str(e.get("value") or "")
    return ""


def _flat_waks(seg: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for bat in seg.get("bats") or []:
        if not isinstance(bat, dict):
            continue
        for wak in bat.get("waks") or []:
            if isinstance(wak, dict):
                out.append(wak)
    return out


def _bat_is_prose_like(bat: dict[str, Any]) -> bool:
    waks = bat.get("waks") or []
    if not isinstance(waks, list) or not waks:
        return False
    return any(
        _looks_like_prose_not_gatha_wak(_wak_roman(w))
        for w in waks
        if isinstance(w, dict)
    )


# A วรรค is too long to be a verse line at the same threshold
# ``_looks_like_prose_not_gatha_wak`` uses for its length trigger.
_PROSE_WAK_LEN = 70


def _bat_strongly_prose(bat: dict[str, Any]) -> bool:
    """True when a บาท has any วรรค whose body length marks it prose, not verse.

    ``_looks_like_prose_not_gatha_wak`` also fires on short quote-close
    ``…"ti`` lines (real verse), so ``_bat_is_prose_like`` alone over-reports.
    Requiring a long body (>70 chars) keeps real verse stanzas intact while
    catching whole-segment prose folded into gāthā by extract (e.g. 10Ma02
    p.21: the Brahmā gāthā commentary + Buddha's approval + closing line
    were printed in bat/wak columns but are narrative prose).
    """
    waks = bat.get("waks") or []
    if not isinstance(waks, list) or not waks:
        return False
    for w in waks:
        if not isinstance(w, dict):
            continue
        if len(_gatha_line_body(_wak_roman(w))) > _PROSE_WAK_LEN:
            return True
    return False


def _join_wak_text_field(waks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Join วรรค bilingual ``text`` into one prose ``text`` list."""
    roman_parts: list[str] = []
    thai_parts: list[str] = []
    for w in waks:
        r = _wak_roman(w).strip()
        t = _wak_thai(w).strip()
        if r:
            roman_parts.append(r)
        if t:
            thai_parts.append(t)
    roman = " ".join(roman_parts)
    thai = " ".join(thai_parts)
    if not thai and roman:
        entries, _ = script_text_entries(roman, normalize_spacing=False)
        return entries
    out: list[dict[str, Any]] = []
    if roman:
        out.append({"script": "roman", "value": roman})
    if thai:
        out.append({"script": "thai", "value": thai})
    return out


def _prose_from_template(
    template: dict[str, Any], text_field: list[dict[str, Any]]
) -> dict[str, Any]:
    seg = {
        k: copy.deepcopy(v)
        for k, v in template.items()
        if k
        not in {
            "text",
            "bats",
            "source_layout",
            "notes",
            "symbol_notes",
            "needs_review",
            "review_reasons",
            "hanging_lines",
            "flags",
        }
    }
    seg["segment_type"] = "prose"
    seg["text"] = text_field
    seg["flags"] = []
    return seg


def _bats_from_flat_waks(waks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    bats: list[dict[str, Any]] = []
    i = 0
    while i + 1 < len(waks):
        bats.append({"waks": [waks[i], waks[i + 1]]})
        i += 2
    if i < len(waks):
        bats.append({"waks": [waks[i]]})
    return bats


def _infer_layout(waks: list[dict[str, Any]]) -> str:
    """Prefer bat_line when วรรค alternate comma / stop like printed บาท."""
    if len(waks) == 4:
        bodies = [_gatha_line_body(_wak_roman(w)) for w in waks]
        if (
            bodies[0].endswith(",")
            and re.search(r"[.!?…][\"'\u201c\u201d]?\s*$", bodies[1] or "")
            and bodies[2].endswith(",")
            and re.search(r"[.!?…][\"'\u201c\u201d]?\s*$", bodies[3] or "")
        ):
            return "bat_line"
    if len(waks) == 2:
        bodies = [_gatha_line_body(_wak_roman(w)) for w in waks]
        if bodies[0].endswith(",") and re.search(
            r"[.!?…][\"'\u201c\u201d]?\s*$", bodies[1] or ""
        ):
            return "bat_line"
    return "wak_line"


def _rebuild_gatha(
    template: dict[str, Any], waks: list[dict[str, Any]]
) -> dict[str, Any]:
    seg = copy.deepcopy(template)
    seg["bats"] = _bats_from_flat_waks(waks)
    seg["source_layout"] = _infer_layout(waks)
    seg.pop("text", None)
    if len(waks) == 4:
        seg.pop("needs_review", None)
        reasons = [
            r
            for r in (seg.get("review_reasons") or [])
            if r != "irregular_gatha_stanza"
        ]
        if reasons:
            seg["review_reasons"] = reasons
        else:
            seg.pop("review_reasons", None)
    elif len(waks) != 4:
        seg["needs_review"] = True
        reasons = list(seg.get("review_reasons") or [])
        if "irregular_gatha_stanza" not in reasons:
            reasons.append("irregular_gatha_stanza")
        seg["review_reasons"] = reasons
    return seg


def fix_segments(segments: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    """Return repaired segments and number of peels performed."""
    out: list[dict[str, Any]] = []
    peels = 0
    i = 0
    n = len(segments)
    while i < n:
        seg = segments[i]
        if not isinstance(seg, dict) or seg.get("segment_type") not in _GATHA_TYPES:
            out.append(seg)
            i += 1
            continue

        bats = seg.get("bats")
        if not isinstance(bats, list) or not bats:
            out.append(seg)
            i += 1
            continue

        # Case A0: whole-segment prose mistag — every บาท is long prose.
        # Extract folded narrative printed in bat/wak columns into a gāthā
        # (e.g. 10Ma02 p.21 Sekha: commentary + Buddha approval + closing).
        # Peel each บาท to its own prose segment; no verse remains.
        if len(bats) >= 2 and all(
            _bat_strongly_prose(b) for b in bats if isinstance(b, dict)
        ):
            for bat in bats:
                if not isinstance(bat, dict):
                    continue
                waks = bat.get("waks") or []
                if not waks:
                    continue
                out.append(
                    _prose_from_template(
                        seg, _join_wak_text_field(list(waks))
                    )
                )
            peels += 1
            i += 1
            continue

        # Case A: false 1 บทครึ่ง — peel prose 3rd บาท.
        if len(bats) == 3 and _bat_is_prose_like(bats[2]):
            gatha = copy.deepcopy(seg)
            gatha["bats"] = copy.deepcopy(bats[:2])
            prose = _prose_from_template(
                seg, _join_wak_text_field(list(bats[2].get("waks") or []))
            )
            out.append(gatha)
            out.append(prose)
            peels += 1
            i += 1
            continue

        # Case B: leading speech-intro or long prose วรรค (+ optional orphan).
        # Do not use the short quote-close / narrative-quote prose heuristics:
        # real wak_line verse often begins ``“X”ti …`` (19Khu02 p.320).
        flat = _flat_waks(seg)
        lead = _wak_roman(flat[0]) if flat else ""
        if flat and (
            ends_with_speech_intro_dash(lead)
            or len(_gatha_line_body(lead)) > _PROSE_WAK_LEN
        ):
            prose = _prose_from_template(seg, _join_wak_text_field([flat[0]]))
            rest = flat[1:]
            consumed = 1
            # Absorb following irregular half-บท (leftover วรรค).
            if (
                i + 1 < n
                and isinstance(segments[i + 1], dict)
                and segments[i + 1].get("segment_type") in _GATHA_TYPES
                and "irregular_gatha_stanza"
                in (segments[i + 1].get("review_reasons") or [])
            ):
                nxt_flat = _flat_waks(segments[i + 1])
                if nxt_flat and not any(
                    _looks_like_prose_not_gatha_wak(_wak_roman(w)) for w in nxt_flat
                ):
                    rest = rest + nxt_flat
                    consumed = 2
            out.append(prose)
            if rest:
                out.append(_rebuild_gatha(seg, rest))
            peels += 1
            i += consumed
            continue

        out.append(seg)
        i += 1

    # Renumber order stably.
    for idx, seg in enumerate(out, start=1):
        if isinstance(seg, dict):
            seg["order"] = idx
    return out, peels


def fix_document(data: dict[str, Any]) -> int:
    segs = [s for s in (data.get("segments") or []) if isinstance(s, dict)]
    new_segs, n = fix_segments(segs)
    if n:
        data["segments"] = new_segs
    return n


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--volume", help="Volume id (e.g. 03Vin03)")
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
            print(f"{path}: peeled {n} false gatha prose intrusion(s)")
            if not args.dry_run:
                save_content(path, data, normalize=True)
        else:
            print(f"{path}: ok")
    print(f"Done ({total} peel(s))" + (" [dry-run]" if args.dry_run else ""))
    if total and not args.dry_run:
        print(
            "Note: segment orders changed; re-run heading assignment + sync, e.g.\n"
            "  python books/cs-roman/scripts/assign_cs_roman_heading_levels.py "
            "<output>/<id>.segments.json <source>/<id>.pdf\n"
            "  python books/cs-roman/scripts/sync_volume_data.py --volume <id>"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
