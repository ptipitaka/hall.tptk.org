#!/usr/bin/env python3
"""Repair unbound / collided numbered footnote callouts in stored segments.

Covers two failures that ``fixup_orphan_footnote_callouts`` does not catch:

1. **Index collision after gāthā fold** — several printed lines each had
   ``{{n0}}``; notes were concatenated but markers were not remapped, so every
   callout points at ``notes[0]`` (23Khu06 item 6: ``va`` / ``Uṭṭhāna``).
2. **Literal glued digits** — callouts never became ``{{nN}}`` and the note
   bodies are missing from JSON (often dropped by older refolds). Rebound from
   the source PDF note region by printed page + mark number.

Also walks gāthā ``bats`` (orphan fixup historically only saw top-level
``text``).

  python books/cs-roman/scripts/fixup_unbound_footnote_callouts.py --volume 23Khu06
  python books/cs-roman/scripts/fixup_unbound_footnote_callouts.py --all
  python books/cs-roman/scripts/fixup_unbound_footnote_callouts.py --all --dry-run
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any, Callable

from paths import BOOKS, OUTPUT_DIR, VOLUMES_DIR, ensure_import_paths

ensure_import_paths()
from cs_roman_segments import load_document, save_content  # noqa: E402
from cs_roman_text import (  # noqa: E402
    ensure_script_text,
    roman_value_from_text_field,
)
from extract_cs_roman_pdf import (  # noqa: E402
    FOOTNOTE_CALLOUT_RE,
    _NOTE_MARKER_RE,
    apply_numbered_footnote_callouts,
    detect_running_headers,
    extract_page_blocks,
    is_spaced_outline_number,
    merge_blocks,
    vztime_to_unicode,
)

try:
    import fitz
except ImportError:  # pragma: no cover
    fitz = None  # type: ignore

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


def _volume_id_from_path(path: Path) -> str | None:
    parts = path.parts
    if "volumes" in parts:
        i = parts.index("volumes")
        if i + 1 < len(parts):
            return parts[i + 1]
    name = path.name
    if name.endswith(".segments.json"):
        return name[: -len(".segments.json")]
    return None


def _resolve_pdf(volume_id: str) -> Path | None:
    candidates = [
        VOLUMES_DIR / volume_id / "source" / f"{volume_id}.pdf",
        BOOKS / "source" / f"{volume_id}.pdf",
    ]
    for p in candidates:
        if p.is_file():
            return p
    return None


def _load_layout(volume_id: str) -> dict[str, Any]:
    path = VOLUMES_DIR / volume_id / "data" / "layout.json"
    if not path.is_file():
        return {}
    import json

    return json.loads(path.read_text(encoding="utf-8"))


def _rewrite_text_field(field: Any, new_roman: str) -> list[dict[str, Any]]:
    entries, _rule, _bold = ensure_script_text(
        new_roman, force=True, normalize_spacing=True
    )
    return entries


def _segment_roman_sites(
    seg: dict[str, Any],
) -> list[tuple[Callable[[], str], Callable[[str], None]]]:
    """Get/set hooks for every roman body string on a segment."""
    sites: list[tuple[Callable[[], str], Callable[[str], None]]] = []
    st = seg.get("segment_type") or ""
    if st in _GATHA_TYPES:
        for bat in seg.get("bats") or []:
            if not isinstance(bat, dict):
                continue
            for wak in bat.get("waks") or []:
                if not isinstance(wak, dict):
                    continue

                def _make(w: dict[str, Any] = wak) -> tuple[
                    Callable[[], str], Callable[[str], None]
                ]:
                    def getter(ww: dict[str, Any] = w) -> str:
                        return roman_value_from_text_field(ww.get("text"))

                    def setter(new: str, ww: dict[str, Any] = w) -> None:
                        ww["text"] = _rewrite_text_field(ww.get("text"), new)

                    return getter, setter

                sites.append(_make())
        return sites

    def getter() -> str:
        return roman_value_from_text_field(seg.get("text"))

    def setter(new: str) -> None:
        seg["text"] = _rewrite_text_field(seg.get("text"), new)

    sites.append((getter, setter))
    return sites


def remap_collided_note_markers_in_texts(
    texts: list[str], notes: list[str]
) -> list[str] | None:
    """If marker count matches ``notes`` but indices collide, renumber in order."""
    if len(notes) < 2:
        return None
    matches: list[tuple[int, re.Match[str]]] = []
    for i, text in enumerate(texts):
        for m in _NOTE_MARKER_RE.finditer(text or ""):
            matches.append((i, m))
    if len(matches) != len(notes):
        return None
    indices = [int(m.group(1)) for _, m in matches]
    if indices == list(range(len(notes))):
        return None

    # Rebuild each text, remapping markers in document order.
    counters = [0]
    out: list[str] = []

    def _repl(_m: re.Match[str]) -> str:
        idx = counters[0]
        counters[0] += 1
        return "{{" + f"n{idx}" + "}}"

    for text in texts:
        out.append(_NOTE_MARKER_RE.sub(_repl, text or ""))
    return out


def fix_collided_note_indices(seg: dict[str, Any]) -> int:
    """Remap collided ``{{n0}}``… markers when ``len(notes)`` matches count."""
    notes = list(seg.get("notes") or [])
    if len(notes) < 2:
        return 0
    sites = _segment_roman_sites(seg)
    texts = [get() for get, _set in sites]
    remapped = remap_collided_note_markers_in_texts(texts, notes)
    if remapped is None:
        return 0
    for (_get, setter), new in zip(sites, remapped):
        setter(new)
    return 1


def _literal_callout_nums(roman: str) -> list[int]:
    out: list[int] = []
    for m in FOOTNOTE_CALLOUT_RE.finditer(roman or ""):
        spaces, num_s, trailer = m.group(1), m.group(2), m.group(3)
        if is_spaced_outline_number(spaces, trailer):
            continue
        out.append(int(num_s))
    return out


def count_literal_callouts(seg: dict[str, Any]) -> int:
    n = 0
    for get, _set in _segment_roman_sites(seg):
        n += len(_literal_callout_nums(get()))
    return n


def _page_pdf_notes(
    doc: Any,
    *,
    content_start: int,
    printed_page: int,
    headers: set[str],
) -> dict[int, str]:
    pdf_page = content_start + printed_page - 1
    if pdf_page < 1 or pdf_page > doc.page_count:
        return {}
    page_text = vztime_to_unicode(doc[pdf_page - 1].get_text("text"))
    blocks = extract_page_blocks(
        page_text,
        printed_page=printed_page,
        pdf_page=pdf_page,
        headers=headers,
        is_opening_page=(printed_page == 1),
    )
    segs = merge_blocks(blocks)
    numbered: dict[int, str] = {}
    for seg in segs:
        if seg.segment_type != "note":
            continue
        if not isinstance(seg.item, int):
            continue
        text = (seg.text or "").strip()
        if text:
            numbered[int(seg.item)] = text
    return numbered


def bind_literal_callouts_from_notes(
    seg: dict[str, Any], page_notes: dict[int, str]
) -> int:
    """Bind literal callout digits on ``seg`` from ``page_notes`` (mark→body).

    The same source mark may appear more than once on a page (shared apparatus);
    each literal gets its own ``{{nK}}`` + a copy of that note body.
    """
    if not page_notes:
        return 0
    existing = list(seg.get("notes") or [])
    bound_total = 0
    for get, setter in _segment_roman_sites(seg):
        roman = get()
        if not roman or not _literal_callout_nums(roman):
            continue
        offer = {
            num: page_notes[num]
            for num in set(_literal_callout_nums(roman))
            if num in page_notes
        }
        if not offer:
            continue
        new_roman, bound_notes, used = apply_numbered_footnote_callouts(
            roman,
            offer,
            note_index_base=len(existing),
            allow_reuse=True,
        )
        if not used:
            continue
        setter(new_roman)
        existing.extend(bound_notes)
        bound_total += len(used)
    if bound_total:
        seg["notes"] = existing
    return bound_total


def rebind_unbound_footnote_callouts(
    segments: list[dict[str, Any]],
    *,
    pdf_notes_by_page: dict[int, dict[int, str]] | None = None,
) -> tuple[int, int]:
    """Return ``(collisions_fixed, literals_bound)``."""
    collisions = 0
    for seg in segments:
        if not isinstance(seg, dict):
            continue
        if (seg.get("segment_type") or "") not in _BODY_TYPES:
            continue
        collisions += fix_collided_note_indices(seg)

    literals = 0
    if pdf_notes_by_page:
        for page, page_notes in pdf_notes_by_page.items():
            if not page_notes:
                continue
            for seg in segments:
                if not isinstance(seg, dict):
                    continue
                if seg.get("page") != page:
                    continue
                if (seg.get("segment_type") or "") not in _BODY_TYPES:
                    continue
                if count_literal_callouts(seg) == 0:
                    continue
                literals += bind_literal_callouts_from_notes(seg, page_notes)

    # Binding can leave ``{{n0}}``+``{{n0}}`` when older notes were already present
    # with collided markers that failed the equal-count heuristic until new marks
    # were added — remap again after literals.
    for seg in segments:
        if not isinstance(seg, dict):
            continue
        if (seg.get("segment_type") or "") not in _BODY_TYPES:
            continue
        collisions += fix_collided_note_indices(seg)

    return collisions, literals


def _build_pdf_notes_by_page(
    volume_id: str, segments: list[dict[str, Any]]
) -> dict[int, dict[int, str]] | None:
    if fitz is None:
        return None
    pdf_path = _resolve_pdf(volume_id)
    if pdf_path is None:
        return None
    layout = _load_layout(volume_id)
    content_start = int(layout.get("content_start_pdf_page") or 0)
    doc = fitz.open(pdf_path)
    try:
        if content_start < 1:
            from extract_cs_roman_pdf import detect_content_start

            detected = detect_content_start(doc)
            content_start = int(detected or 1)
        headers = detect_running_headers(doc, content_start - 1)
        pages = sorted(
            {
                int(s["page"])
                for s in segments
                if isinstance(s, dict)
                and isinstance(s.get("page"), int)
                and count_literal_callouts(s) > 0
            }
        )
        out: dict[int, dict[int, str]] = {}
        for page in pages:
            out[page] = _page_pdf_notes(
                doc,
                content_start=content_start,
                printed_page=page,
                headers=headers,
            )
        return out
    finally:
        doc.close()


def fix_document(
    data: dict[str, Any],
    *,
    volume_id: str | None,
    use_pdf: bool,
) -> tuple[int, int]:
    segs = [s for s in (data.get("segments") or []) if isinstance(s, dict)]
    pdf_notes = None
    if use_pdf and volume_id:
        pdf_notes = _build_pdf_notes_by_page(volume_id, segs)
    return rebind_unbound_footnote_callouts(segs, pdf_notes_by_page=pdf_notes)


def count_residuals(
    segments: list[dict[str, Any]],
) -> tuple[int, int]:
    """Return ``(collision_segs, literal_callouts)`` still needing repair."""
    collisions = 0
    literals = 0
    for seg in segments:
        if not isinstance(seg, dict):
            continue
        if (seg.get("segment_type") or "") not in _BODY_TYPES:
            continue
        notes = list(seg.get("notes") or [])
        sites = _segment_roman_sites(seg)
        texts = [get() for get, _ in sites]
        if remap_collided_note_markers_in_texts(texts, notes) is not None:
            collisions += 1
        literals += count_literal_callouts(seg)
    return collisions, literals


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--volume", help="e.g. 23Khu06")
    g.add_argument("--all", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--no-pdf",
        action="store_true",
        help="Only remap collided {{nK}} indices (no PDF note rebind)",
    )
    args = ap.parse_args(argv)

    paths = _iter_segment_paths(volume=args.volume, all_volumes=args.all)
    if not paths:
        print("No segments.json found", file=sys.stderr)
        return 1

    total_c = 0
    total_l = 0
    for path in paths:
        data = load_document(path)
        volume_id = _volume_id_from_path(path)
        if args.dry_run:
            import copy

            trial_data = copy.deepcopy(data)
            c, lit = fix_document(
                trial_data, volume_id=volume_id, use_pdf=not args.no_pdf
            )
        else:
            c, lit = fix_document(
                data, volume_id=volume_id, use_pdf=not args.no_pdf
            )
            if c or lit:
                save_content(path, data, normalize=True)
        total_c += c
        total_l += lit
        if c or lit:
            print(f"{path}: remapped={c} bound={lit}")
        else:
            print(f"{path}: ok")

    # Gate residual = would-fix / did-fix count (0 when clean on --dry-run).
    print(
        f"total bound: {total_c + total_l}"
        + (" (dry-run)" if args.dry_run else "")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
