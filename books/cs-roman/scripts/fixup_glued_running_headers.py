#!/usr/bin/env python3
"""Peel running-header labels glued onto prose in stored segments JSON.

Older extracts only sampled the first ~12 pages for running headers, so later
sutta titles (``10. Subhasutta``) stayed in the text layer, joined the first
body paragraph, became a false Tipiṭaka ``item``, and picked up
``source_layout=center`` from the centered header line.

Majjhima-style ``Name (folio)`` / ``N. Name (folio)`` labels are now detected
from a single page-top sighting and peeled by pattern even when frequency
detection missed them. Isolated ``Potaliyasutta (54)`` title blocks are
dropped as furniture (chapter opens omit the folio paren).

Saṃyutta-style continuation pages print a centered ``N. Title`` with the
edition page number on the outer margin; blank lines isolate that title so it
became a false ``title`` segment. This repair drops non-structural title
segments that match a detected running header when the next substantive
segment is body (not a child title), then dedupes remaining bare-name repeats.
Repeated ``gambhīra`` / ``boo`` pāḷi titles (the same book name reprinted as
page-top furniture) are dropped after the first occurrence of each distinct
title.

Repair (does not re-extract):
  - detect headers from the volume PDF (full-volume page-top scan)
  - peel matching prefixes from long prose / prose_continuation
  - drop isolated ``title`` / ``subhead`` segments that are folio furniture
  - drop continuation-page running-header title repeats (see above)
  - drop repeated gambhīra pāḷi titles (keep first of each distinct name)
  - clear false ``item`` when it equals the header's ``N.``
  - drop stale ``source_layout=center`` on the repaired long prose
  - regenerate Thai from Roman
  - reclassify flush page-starts → ``prose_continuation`` (peeling often
    exposes a mid-sentence body line that geometry can now match)

  python books/cs-roman/scripts/fixup_glued_running_headers.py --volume 06Di01
  python books/cs-roman/scripts/fixup_glued_running_headers.py --all
  python books/cs-roman/scripts/fixup_glued_running_headers.py --all --dry-run
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

try:
    import fitz
except ImportError:  # pragma: no cover
    print("PyMuPDF (pymupdf) is required", file=sys.stderr)
    raise

from paths import BOOKS, OUTPUT_DIR, REPO, ensure_import_paths

ensure_import_paths()
from cs_roman_hanging import reclassify_page_start_by_indent  # noqa: E402
from cs_roman_segments import load_document, save_content  # noqa: E402
from cs_roman_text import (  # noqa: E402
    roman_value_from_text_field,
    script_text_entries,
)
from extract_cs_roman_pdf import (  # noqa: E402
    ITEM_SINGLE_RE,
    detect_running_headers,
    is_running_header_folio_label,
    peel_glued_running_header_prefix,
    running_header_bare_name,
)

_PEELABLE_TYPES = frozenset({"prose", "prose_continuation"})
_FOLIO_TITLE_TYPES = frozenset({"title", "subhead"})
# Matched chapter/book opens — never drop as continuation furniture.
_STRUCTURAL_HEADING_KINDS = frozenset(
    {"cha", "boo", "nik", "piṭaka", "pitaka", "gambhīra", "gambhira", "chapter"}
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


def _resolve_pdf(doc_data: dict[str, Any], segments_path: Path) -> Path | None:
    source = doc_data.get("source") or ""
    if source:
        cand = REPO / source
        if cand.is_file():
            return cand
    vol_dir = segments_path.parent.parent
    vol_id = vol_dir.name
    alt = vol_dir / "source" / f"{vol_id}.pdf"
    if alt.is_file():
        return alt
    shared = BOOKS / "source" / f"{vol_id}.pdf"
    if shared.is_file():
        return shared
    return None


def _last_body_item(segments: list[Any], index: int) -> int | str | None:
    for j in range(index - 1, -1, -1):
        prev = segments[j]
        if not isinstance(prev, dict):
            continue
        if prev.get("segment_type") not in _PEELABLE_TYPES:
            continue
        item = prev.get("item")
        if item is not None:
            return item
    return None


def _header_item_names(headers: set[str]) -> dict[int, str]:
    out: dict[int, str] = {}
    for header in headers:
        m = ITEM_SINGLE_RE.match(header.strip())
        if not m:
            continue
        try:
            num = int(m.group(1))
        except ValueError:
            continue
        out[num] = running_header_bare_name(header)
    return out


def _cascade_same_page_item(
    segments: list[Any],
    *,
    start_i: int,
    header_item: int,
    corrected: int | str | None,
) -> int:
    """Reassign same-page followers that still carry the false header item."""
    fixed = 0
    page = segments[start_i].get("page") if isinstance(segments[start_i], dict) else None
    for j in range(start_i + 1, len(segments)):
        nxt = segments[j]
        if not isinstance(nxt, dict):
            break
        if nxt.get("page") != page:
            break
        if nxt.get("segment_type") not in _PEELABLE_TYPES:
            break
        if nxt.get("item") != header_item:
            break
        if corrected is None:
            nxt.pop("item", None)
        else:
            nxt["item"] = corrected
        fixed += 1
    return fixed


def repair_residual_header_items(
    segments: list[Any],
    headers: set[str],
) -> int:
    """Fix same-page followers left with ``item=N`` after a prior peel.

    Detects a same-page leader that starts mid-word (lowercase) under a
    different Tipiṭaka item — the usual shape after peeling ``N. Sutta`` from
    a page-start continuation.
    """
    header_names = _header_item_names(headers)
    if not header_names:
        return 0
    fixed = 0
    for i, seg in enumerate(segments):
        if not isinstance(seg, dict):
            continue
        if seg.get("segment_type") not in _PEELABLE_TYPES:
            continue
        item = seg.get("item")
        if not isinstance(item, int) or item not in header_names:
            continue
        bare = header_names[item]
        roman = roman_value_from_text_field(seg.get("text")) or ""
        if roman.startswith(bare + " ") or roman.startswith(bare + "\u00a0"):
            continue  # still glued — main peel pass handles
        page = seg.get("page")
        leader_item: int | str | None = None
        for j in range(i):
            prev = segments[j]
            if not isinstance(prev, dict):
                continue
            if prev.get("page") != page:
                continue
            if prev.get("segment_type") not in _PEELABLE_TYPES:
                continue
            prev_roman = roman_value_from_text_field(prev.get("text")) or ""
            if not prev_roman or not prev_roman[0].islower():
                continue
            prev_item = prev.get("item")
            if prev_item is None or prev_item == item:
                continue
            leader_item = prev_item
        if leader_item is None:
            continue
        seg["item"] = leader_item
        fixed += 1
        fixed += _cascade_same_page_item(
            segments,
            start_i=i,
            header_item=item,
            corrected=leader_item,
        )
    return fixed


def drop_folio_running_header_titles(segments: list[Any]) -> int:
    """Remove isolated ``Name (folio)`` title/subhead furniture in-place."""
    kept: list[Any] = []
    dropped = 0
    for seg in segments:
        if not isinstance(seg, dict):
            kept.append(seg)
            continue
        if seg.get("segment_type") not in _FOLIO_TITLE_TYPES:
            kept.append(seg)
            continue
        roman = roman_value_from_text_field(seg.get("text")) or ""
        if is_running_header_folio_label(roman):
            dropped += 1
            continue
        kept.append(seg)
    if dropped:
        segments[:] = kept
    return dropped


def running_header_match_keys(headers: set[str]) -> set[str]:
    """Full header strings plus bare names (``12. X`` → ``X``)."""
    keys: set[str] = set()
    for h in headers or ():
        s = (h or "").strip()
        if not s:
            continue
        keys.add(s)
        bare = running_header_bare_name(s)
        if bare:
            keys.add(bare)
    return keys


def segment_matches_running_header(roman: str, keys: set[str]) -> bool:
    s = (roman or "").strip()
    if not s or not keys:
        return False
    if s in keys:
        return True
    bare = running_header_bare_name(s)
    return bool(bare) and bare in keys


def _next_substantive_segment(
    segments: list[Any], start_i: int
) -> dict[str, Any] | None:
    for j in range(start_i + 1, len(segments)):
        seg = segments[j]
        if not isinstance(seg, dict):
            continue
        st = seg.get("segment_type")
        if st in _FOLIO_TITLE_TYPES or st in _PEELABLE_TYPES:
            return seg
        if st in {
            "gatha",
            "gatha_continuation",
            "niṭṭhitaṃ",
            "nitthitam",
            "chapter",
            "tassuddānaṃ",
        }:
            return seg
    return None


def drop_continuation_gambhira_headers(segments: list[Any]) -> int:
    """Drop repeated ``gambhīra`` / ``boo`` titles (source running-head furniture).

    Saṃyutta volumes reprint the pāḷi name at the top of continuation pages;
    extract tags those as ``gambhīra``. Keep the first occurrence of each
    distinct title (the true book open); drop later exact repeats.
    """
    drop_idx: set[int] = set()
    seen: set[str] = set()
    for i, seg in enumerate(segments):
        if not isinstance(seg, dict):
            continue
        kind = str(seg.get("segment_type") or "")
        hk = seg.get("heading_kind")
        hk_s = str(hk) if hk is not None else None
        if kind != "gambhīra" and hk_s != "boo":
            continue
        roman = roman_value_from_text_field(seg.get("text")) or ""
        thai = ""
        for entry in seg.get("text") or []:
            if isinstance(entry, dict) and entry.get("script") == "thai":
                thai = str(entry.get("value") or "")
                break
        raw = thai or roman
        key = re.sub(r"\s+", "", raw)
        if not key:
            continue
        if key in seen:
            drop_idx.add(i)
        else:
            seen.add(key)
    if not drop_idx:
        return 0
    segments[:] = [
        seg for i, seg in enumerate(segments) if i not in drop_idx
    ]
    return len(drop_idx)


def drop_continuation_running_header_titles(
    segments: list[Any], headers: set[str]
) -> int:
    """Drop isolated running-header titles on continuation pages.

    Signature (proxy after extract stripped the outer edition folio): title
    matches a detected running header, is not a structural matika match
    (``cha`` / ``boo`` / …), and the next substantive segment is body — not a
    child title. Then drop remaining duplicate bare-name titles, keeping one
    structural (or earliest) occurrence.
    """
    keys = running_header_match_keys(headers)
    if not keys:
        return 0

    drop_idx: set[int] = set()
    for i, seg in enumerate(segments):
        if not isinstance(seg, dict):
            continue
        if seg.get("segment_type") not in _FOLIO_TITLE_TYPES:
            continue
        if seg.get("heading_kind") in _STRUCTURAL_HEADING_KINDS:
            continue
        roman = roman_value_from_text_field(seg.get("text")) or ""
        if not segment_matches_running_header(roman, keys):
            continue
        nxt = _next_substantive_segment(segments, i)
        if nxt is None:
            continue
        if nxt.get("segment_type") in _FOLIO_TITLE_TYPES:
            continue
        if nxt.get("heading_kind") in _STRUCTURAL_HEADING_KINDS:
            continue
        drop_idx.add(i)

    # Duplicate net: same bare header label kept more than once.
    by_bare: dict[str, list[int]] = {}
    for i, seg in enumerate(segments):
        if i in drop_idx or not isinstance(seg, dict):
            continue
        if seg.get("segment_type") not in _FOLIO_TITLE_TYPES:
            continue
        roman = roman_value_from_text_field(seg.get("text")) or ""
        if not segment_matches_running_header(roman, keys):
            continue
        bare = running_header_bare_name(roman.strip()) or roman.strip()
        by_bare.setdefault(bare, []).append(i)
    for idxs in by_bare.values():
        if len(idxs) < 2:
            continue
        keep_i = idxs[0]
        for i in idxs:
            kind = segments[i].get("heading_kind")
            if kind in _STRUCTURAL_HEADING_KINDS:
                keep_i = i
                break
        for i in idxs:
            if i != keep_i:
                drop_idx.add(i)

    if not drop_idx:
        return 0
    segments[:] = [
        seg for i, seg in enumerate(segments) if i not in drop_idx
    ]
    return len(drop_idx)


def repair_glued_running_headers(
    segments: list[Any],
    headers: set[str],
) -> dict[str, int]:
    """Peel glued headers in-place. Returns counts."""
    peeled = 0
    cleared_center = 0
    fixed_item = 0
    dropped_titles = drop_folio_running_header_titles(segments)
    dropped_titles += drop_continuation_running_header_titles(segments, headers)
    dropped_titles += drop_continuation_gambhira_headers(segments)

    for i, seg in enumerate(segments):
        if not isinstance(seg, dict):
            continue
        if seg.get("segment_type") not in _PEELABLE_TYPES:
            continue
        roman = roman_value_from_text_field(seg.get("text")) or ""
        result = peel_glued_running_header_prefix(roman, headers)
        if result is None:
            continue
        rest, _label, header_item = result
        entries, _has_rule = script_text_entries(rest, normalize_spacing=True)
        seg["text"] = entries
        peeled += 1

        if seg.get("source_layout") == "center" and len(rest) > 80:
            seg.pop("source_layout", None)
            cleared_center += 1

        if header_item is not None and seg.get("item") == header_item:
            prev_item = _last_body_item(segments, i)
            if prev_item is not None and prev_item != header_item:
                seg["item"] = prev_item
                corrected: int | str | None = prev_item
                fixed_item += 1
            elif prev_item is None:
                seg.pop("item", None)
                corrected = None
                fixed_item += 1
            else:
                corrected = header_item

            if corrected != header_item:
                fixed_item += _cascade_same_page_item(
                    segments,
                    start_i=i,
                    header_item=header_item,
                    corrected=corrected,
                )

    fixed_item += repair_residual_header_items(segments, headers)

    return {
        "peeled": peeled,
        "cleared_center": cleared_center,
        "fixed_item": fixed_item,
        "dropped_titles": dropped_titles,
    }


def fixup_path(path: Path, *, dry_run: bool) -> dict[str, int]:
    doc_data = load_document(path)
    content_start = int(doc_data.get("content_start_pdf_page") or 0)
    if content_start < 1:
        print(f"skip {path}: content_start_pdf_page missing", file=sys.stderr)
        return {
            "peeled": 0,
            "cleared_center": 0,
            "fixed_item": 0,
            "upgraded_continuation": 0,
            "skipped": 1,
        }

    pdf_path = _resolve_pdf(doc_data, path)
    if pdf_path is None:
        print(f"skip {path}: missing source PDF", file=sys.stderr)
        return {
            "peeled": 0,
            "cleared_center": 0,
            "fixed_item": 0,
            "upgraded_continuation": 0,
            "skipped": 1,
        }

    pdf = fitz.open(pdf_path)
    headers = detect_running_headers(pdf, content_start - 1)
    segments = list(doc_data.get("segments") or [])
    stats = repair_glued_running_headers(segments, headers)
    # After peeling, the page-start line is often flush body (continuation).
    # Geometry could not match while the centered header prefix was still glued.
    page_stats = reclassify_page_start_by_indent(
        pdf, segments, content_start=content_start
    )
    stats["upgraded_continuation"] = int(
        page_stats.get("upgraded_to_continuation") or 0
    )
    stats["demoted_continuation"] = int(page_stats.get("demoted_to_prose") or 0)
    stats["headers"] = len(headers)
    label = path.parent.parent.name if path.parent.name == "data" else path.stem
    print(
        f"{label}: peeled={stats['peeled']} "
        f"cleared_center={stats['cleared_center']} "
        f"fixed_item={stats['fixed_item']} "
        f"dropped_titles={stats.get('dropped_titles', 0)} "
        f"cont+={stats['upgraded_continuation']} "
        f"headers={stats['headers']}"
    )
    if dry_run:
        return stats
    if (
        stats["peeled"] == 0
        and stats["cleared_center"] == 0
        and stats["fixed_item"] == 0
        and stats.get("dropped_titles", 0) == 0
        and stats["upgraded_continuation"] == 0
        and stats.get("demoted_continuation", 0) == 0
    ):
        return stats

    doc_data["segments"] = segments
    save_content(path, doc_data, normalize=True)
    print(f"Wrote {path}")
    return stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--volume", help="e.g. 06Di01")
    g.add_argument("--all", action="store_true", help="All volumes + output/")
    g.add_argument(
        "--output-only",
        action="store_true",
        help="Only books/cs-roman/output/*.segments.json",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report without writing",
    )
    args = parser.parse_args(argv)

    paths = _iter_segment_paths(
        volume=args.volume,
        all_volumes=args.all,
        output_only=args.output_only,
    )
    if not paths:
        print("No segments.json found", file=sys.stderr)
        return 1

    total = {
        "peeled": 0,
        "cleared_center": 0,
        "fixed_item": 0,
        "dropped_titles": 0,
        "upgraded_continuation": 0,
    }
    for path in paths:
        if not path.is_file():
            print(f"Missing {path}", file=sys.stderr)
            continue
        stats = fixup_path(path, dry_run=args.dry_run)
        for k in total:
            total[k] += int(stats.get(k) or 0)

    print(
        f"total: peeled={total['peeled']} "
        f"cleared_center={total['cleared_center']} "
        f"fixed_item={total['fixed_item']} "
        f"dropped_titles={total['dropped_titles']} "
        f"cont+={total['upgraded_continuation']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
