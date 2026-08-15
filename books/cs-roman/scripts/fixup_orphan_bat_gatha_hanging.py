#!/usr/bin/env python3
"""Promote numbered bat/wak hanging (and orphan pairs) to real gāthā.

Numbered KN/SN verses often print as first-indent head + near-hang body and
were stored as ``source_layout: hanging``. They are true บท (bat_line or
wak_line) and must emit ``\\csromangathabat`` so วรรค 2/4 share a column,
with Tipiṭaka ``item`` on the first printed line.

Also repairs the older split:

  prose item=N (bat-shaped verse line) + irregular 1-bat gāthā
  → one ``gatha`` with two บาท and ``item`` kept

Does not merge long comma-prose (Vinaya kammavācā / ñatti) onto a following
1-bat line: that uses extract's ``_looks_like_bat_gatha_line`` guard.

Root-cause extract guards: hang merge skips bat+bat groups; geometry may
seed first-indent numbered bats and preserve ``item`` on the บท.

  python books/cs-roman/scripts/fixup_orphan_bat_gatha_hanging.py --volume 23Khu06
  python books/cs-roman/scripts/fixup_orphan_bat_gatha_hanging.py --all
  python books/cs-roman/scripts/fixup_orphan_bat_gatha_hanging.py --all --dry-run
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
from cs_roman_text import roman_value_from_text_field  # noqa: E402
from extract_cs_roman_pdf import (  # noqa: E402
    _gatha_line_body,
    _is_bat_printed_line,
    _looks_like_bat_gatha_line,
    _split_bat_printed_line,
    ends_with_speech_intro_dash,
)

_GATHA_TYPES = frozenset({"gatha", "gatha_continuation"})
_SCRIPT_ORDER = ("roman", "thai")


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


def _script_value(text: Any, script: str) -> str:
    if isinstance(text, list):
        for e in text:
            if isinstance(e, dict) and e.get("script") == script:
                return str(e.get("value") or "")
    if script == "roman" and isinstance(text, str):
        return text
    return ""


def _multi_script_text(by_script: dict[str, str]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for script in _SCRIPT_ORDER:
        val = (by_script.get(script) or "").strip()
        if val:
            out.append({"script": script, "value": val})
    for script, val in by_script.items():
        if script in _SCRIPT_ORDER:
            continue
        val = (val or "").strip()
        if val:
            out.append({"script": script, "value": val})
    return out


def _wak(by_script: dict[str, str]) -> dict[str, Any]:
    return {"text": _multi_script_text(by_script)}


def _split_line_field_to_waks(text: Any) -> list[dict[str, Any]] | None:
    """Split one printed bat line (multi-script) into two วรรค waks."""
    roman = roman_value_from_text_field(text)
    parts_r = _split_bat_printed_line(roman)
    if not parts_r:
        return None
    left_r, right_r = parts_r
    thai = _script_value(text, "thai")
    parts_t = _split_bat_printed_line(thai) if thai else None
    left: dict[str, str] = {"roman": left_r}
    right: dict[str, str] = {"roman": right_r}
    if parts_t:
        left["thai"] = parts_t[0]
        right["thai"] = parts_t[1]
    elif thai:
        # Fallback: keep full Thai on left only if split fails.
        left["thai"] = thai
    return [_wak(left), _wak(right)]


def _single_line_wak(text: Any) -> dict[str, Any]:
    by_script: dict[str, str] = {}
    if isinstance(text, list):
        for e in text:
            if isinstance(e, dict) and e.get("script") and e.get("value"):
                by_script[str(e["script"])] = str(e["value"])
    else:
        by_script["roman"] = str(text or "")
    return _wak(by_script)


def _hanging_printed_fields(seg: dict[str, Any]) -> list[Any]:
    fields: list[Any] = [seg.get("text")]
    for line in seg.get("hanging_lines") or []:
        fields.append(line)
    return fields


def _is_verse_hang_line(roman: str) -> bool:
    """True for a hang-body line that can belong to a numbered บท."""
    body = _gatha_line_body(roman)
    if not body or ends_with_speech_intro_dash(body):
        return False
    if _is_bat_printed_line(body):
        return len(body) <= 160
    if len(body) > 90:
        return False
    return bool(re.search(r"[.!?…,]\s*$", body))


def _classify_hanging_verse(romans: list[str]) -> str | None:
    if not romans:
        return None
    if all(_is_bat_printed_line(_gatha_line_body(r)) for r in romans):
        return "bat_line"
    if all(_is_verse_hang_line(r) for r in romans):
        return "wak_line"
    return None


def _bats_from_hanging_fields(
    fields: list[Any], *, layout: str
) -> list[dict[str, Any]] | None:
    bats: list[dict[str, Any]] = []
    if layout == "bat_line":
        for field in fields:
            waks = _split_line_field_to_waks(field)
            if not waks:
                return None
            bats.append({"waks": waks})
        return bats
    # wak_line: one วรรค per printed line; pack into bats of up to 2.
    waks: list[dict[str, Any]] = []
    for field in fields:
        waks.append(_single_line_wak(field))
    if not waks:
        return None
    for i in range(0, len(waks), 2):
        chunk = waks[i : i + 2]
        bats.append({"waks": chunk})
    return bats


def _promote_hanging_to_gatha(seg: dict[str, Any]) -> dict[str, Any] | None:
    if seg.get("segment_type") != "prose":
        return None
    if seg.get("source_layout") != "hanging":
        return None
    if seg.get("item") is None:
        return None
    fields = _hanging_printed_fields(seg)
    romans = [roman_value_from_text_field(f) for f in fields]
    layout = _classify_hanging_verse(romans)
    if layout is None:
        return None
    bats = _bats_from_hanging_fields(fields, layout=layout)
    if not bats:
        return None
    out = copy.deepcopy(seg)
    out["segment_type"] = "gatha"
    out["source_layout"] = layout
    out["bats"] = bats
    out.pop("text", None)
    out.pop("hanging_lines", None)
    # Clear hanging-only review noise if present.
    reasons = [
        r
        for r in (out.get("review_reasons") or [])
        if r not in {"irregular_gatha_stanza"}
    ]
    if reasons:
        out["review_reasons"] = reasons
    else:
        out.pop("review_reasons", None)
        out.pop("needs_review", None)
    return out


def _is_orphan_one_bat_gatha(seg: dict[str, Any]) -> bool:
    """True for a leftover second บาท after a numbered bat-shaped prose head.

    Accepts either:
      - ``irregular_gatha_stanza`` (pre-peel leftover), or
      - no ``item`` (continuation half after a section label was peeled off)
    """
    if seg.get("segment_type") not in _GATHA_TYPES:
        return False
    if (seg.get("source_layout") or "bat_line") != "bat_line":
        return False
    bats = seg.get("bats") or []
    if not isinstance(bats, list) or len(bats) != 1:
        return False
    bat = bats[0]
    if not isinstance(bat, dict):
        return False
    waks = bat.get("waks") or []
    if not isinstance(waks, list) or len(waks) != 2:
        return False
    reasons = seg.get("review_reasons") or []
    if "irregular_gatha_stanza" in reasons:
        return True
    # After peeling a trailing centered label (``Name nāma.``), the leftover
    # บาท is clean bat_line with no item — still an orphan second half.
    return seg.get("item") is None


def _prose_is_bat_head(seg: dict[str, Any]) -> bool:
    if seg.get("segment_type") != "prose":
        return False
    if seg.get("source_layout") in {
        "hanging",
        "center",
        "bat_line",
        "wak_line",
        "mixed",
    }:
        return False
    if seg.get("item") is None:
        return False
    roman = roman_value_from_text_field(seg.get("text"))
    # Same verse-shape + prose guard as extract (``_looks_like_bat_gatha_line``).
    # Raw ``_is_bat_printed_line`` (comma + stop) is too wide: Vinaya kammavācā
    # such as ``Sammato saṃghena …, khamati saṃghassa, … dhārayāmī”ti.`` must
    # not merge with a following 1-bat uddāna/catechism line (04Vin04 p.226).
    return _looks_like_bat_gatha_line(roman)


def _merge_notes(head: dict[str, Any], orphan: dict[str, Any]) -> None:
    notes = list(head.get("notes") or [])
    for n in orphan.get("notes") or []:
        if n not in notes:
            notes.append(n)
    if notes:
        head["notes"] = notes
    symbols = dict(head.get("symbol_notes") or {})
    for k, v in (orphan.get("symbol_notes") or {}).items():
        symbols.setdefault(k, v)
    if symbols:
        head["symbol_notes"] = symbols
    flags = list(head.get("flags") or [])
    for f in orphan.get("flags") or []:
        if f not in flags:
            flags.append(f)
    if flags:
        head["flags"] = flags


def _merge_prose_orphan_to_gatha(
    prose: dict[str, Any], orphan: dict[str, Any]
) -> dict[str, Any] | None:
    head_waks = _split_line_field_to_waks(prose.get("text"))
    if not head_waks:
        return None
    bats = orphan.get("bats") or []
    bat = bats[0] if bats else None
    if not isinstance(bat, dict):
        return None
    out = copy.deepcopy(prose)
    out["segment_type"] = "gatha"
    out["source_layout"] = "bat_line"
    out["bats"] = [{"waks": head_waks}, copy.deepcopy(bat)]
    out.pop("text", None)
    out.pop("hanging_lines", None)
    _merge_notes(out, orphan)
    out.pop("needs_review", None)
    out.pop("review_reasons", None)
    return out


def fix_segments(segments: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    """Promote hanging / orphan pairs to numbered gāthā; return (segs, n)."""
    out: list[dict[str, Any]] = []
    changes = 0
    i = 0
    n = len(segments)
    while i < n:
        cur = segments[i]
        nxt = segments[i + 1] if i + 1 < n else None
        if (
            isinstance(cur, dict)
            and isinstance(nxt, dict)
            and _prose_is_bat_head(cur)
            and _is_orphan_one_bat_gatha(nxt)
        ):
            merged = _merge_prose_orphan_to_gatha(cur, nxt)
            if merged is not None:
                out.append(merged)
                changes += 1
                i += 2
                continue
        if isinstance(cur, dict):
            promoted = _promote_hanging_to_gatha(cur)
            if promoted is not None:
                out.append(promoted)
                changes += 1
                i += 1
                continue
        out.append(cur)
        i += 1

    for idx, seg in enumerate(out, start=1):
        if isinstance(seg, dict):
            seg["order"] = idx
    return out, changes


def fix_document(data: dict[str, Any]) -> int:
    segs = [s for s in (data.get("segments") or []) if isinstance(s, dict)]
    new_segs, n = fix_segments(segs)
    if n:
        data["segments"] = new_segs
    return n


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--volume", help="Volume id (e.g. 23Khu06)")
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
            print(f"{path}: promoted {n} numbered verse(s) to gāthā")
            if not args.dry_run:
                save_content(path, data, normalize=True)
        else:
            print(f"{path}: ok")
    print(f"Done ({total} promotion(s))" + (" [dry-run]" if args.dry_run else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
