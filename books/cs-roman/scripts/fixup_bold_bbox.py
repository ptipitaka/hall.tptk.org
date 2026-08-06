#!/usr/bin/env python3
"""Re-apply CS Roman fake-bold runs using stroke bbox ↔ body-line geometry.

Older extracts painted every occurrence of a page-level bold span string inside
a segment (e.g. lemma ``Bhūmaṭṭhaṃ`` also bold inside quotes). Extract now uses
``bold_ranges_from_geoms``; this script repairs stored ``segments.json`` without
a full re-extract of text.

  python books/cs-roman/scripts/fixup_bold_bbox.py --volume 01Vin01
  python books/cs-roman/scripts/fixup_bold_bbox.py --all
  python books/cs-roman/scripts/fixup_bold_bbox.py --volume 01Vin01 --dry-run
"""

from __future__ import annotations

import argparse
import json
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
from cs_roman_bold import (  # noqa: E402
    BoldSpan,
    bold_ranges_from_geoms,
    bold_span_geoms,
    ranges_to_runs,
    substantial_bold_ranges,
)
from cs_roman_hanging import page_body_lines  # noqa: E402
from cs_roman_segments import load_document, save_content  # noqa: E402
from cs_roman_text import transliterate_runs  # noqa: E402

def _volume_ids() -> list[str]:
    vols = BOOKS / "volumes"
    if not vols.is_dir():
        return []
    return sorted(
        p.name
        for p in vols.iterdir()
        if p.is_dir() and (p / "data" / "segments.json").is_file()
    )


def _resolve_pdf(volume_id: str, doc_data: dict, override: Path | None) -> Path | None:
    if override is not None and override.is_file():
        return override
    source = doc_data.get("source") or ""
    if source:
        cand = REPO / source
        if cand.is_file():
            return cand
    alt = BOOKS / "volumes" / volume_id / "source" / f"{volume_id}.pdf"
    if alt.is_file():
        return alt
    src = BOOKS / "source" / f"{volume_id}.pdf"
    if src.is_file():
        return src
    return None


def _runs_signature(runs: Any) -> list[tuple[str, bool]]:
    if not isinstance(runs, list):
        return []
    out: list[tuple[str, bool]] = []
    for r in runs:
        if isinstance(r, dict) and r.get("value"):
            out.append((str(r["value"]), bool(r.get("bold"))))
    return out


def _apply_ranges_to_text_field(
    text: Any,
    ranges: list[tuple[int, int]],
) -> bool:
    """Update roman/thai runs from ranges over the roman value. Return changed."""
    if not isinstance(text, list):
        return False
    roman = next(
        (t for t in text if isinstance(t, dict) and t.get("script") == "roman"),
        None,
    )
    thai = next(
        (t for t in text if isinstance(t, dict) and t.get("script") == "thai"),
        None,
    )
    if not isinstance(roman, dict):
        return False
    value = str(roman.get("value") or "")
    if not value:
        return False
    new_runs = ranges_to_runs(value, ranges)
    old_sig = _runs_signature(roman.get("runs"))
    new_sig = _runs_signature(new_runs)
    if old_sig == new_sig:
        # Still refresh Thai bold flags when roman matched but thai drifted.
        if new_runs is None:
            if isinstance(thai, dict) and thai.pop("runs", None) is not None:
                return True
            return False
        if isinstance(thai, dict):
            thai_runs = transliterate_runs(new_runs)
            if _runs_signature(thai.get("runs")) != _runs_signature(thai_runs):
                thai["runs"] = thai_runs
                return True
        return False

    if new_runs is None:
        roman.pop("runs", None)
        if isinstance(thai, dict):
            thai.pop("runs", None)
    else:
        roman["runs"] = new_runs
        if isinstance(thai, dict) and thai.get("value"):
            thai["runs"] = transliterate_runs(new_runs)
    return True


def _page_assets(
    pdf: fitz.Document,
    pdf_page: int,
    cache_bold: dict[int, list[BoldSpan]],
    cache_lines: dict[int, list],
) -> tuple[list[BoldSpan], list]:
    if pdf_page not in cache_bold:
        idx = pdf_page - 1
        if idx < 0 or idx >= pdf.page_count:
            cache_bold[pdf_page] = []
            cache_lines[pdf_page] = []
        else:
            cache_bold[pdf_page] = bold_span_geoms(pdf[idx])
            cache_lines[pdf_page] = page_body_lines(pdf[idx])
    return cache_bold[pdf_page], cache_lines[pdf_page]


def _ranges_for_roman(
    roman: str,
    *,
    segment_type: str,
    pdf_page: int,
    pdf: fitz.Document,
    cache_bold: dict[int, list[BoldSpan]],
    cache_lines: dict[int, list],
) -> list[tuple[int, int]]:
    spans, lines = _page_assets(pdf, pdf_page, cache_bold, cache_lines)
    span_list = list(spans)
    line_list = list(lines)
    if segment_type.endswith("_continuation"):
        s2, l2 = _page_assets(pdf, pdf_page + 1, cache_bold, cache_lines)
        span_list.extend(s2)
        line_list.extend(l2)
    ranges = bold_ranges_from_geoms(roman, span_list, line_list)
    if segment_type == "niṭṭhitaṃ":
        ranges = substantial_bold_ranges(roman, ranges)
    return ranges


def _fix_text_field(
    text: Any,
    *,
    segment_type: str,
    pdf_page: int,
    pdf: fitz.Document,
    cache_bold: dict[int, list[BoldSpan]],
    cache_lines: dict[int, list],
) -> bool:
    if not isinstance(text, list):
        return False
    roman = next(
        (t for t in text if isinstance(t, dict) and t.get("script") == "roman"),
        None,
    )
    if not isinstance(roman, dict):
        return False
    value = str(roman.get("value") or "")
    if not value:
        return False
    ranges = _ranges_for_roman(
        value,
        segment_type=segment_type,
        pdf_page=pdf_page,
        pdf=pdf,
        cache_bold=cache_bold,
        cache_lines=cache_lines,
    )
    return _apply_ranges_to_text_field(text, ranges)


def fix_document(
    data: dict,
    pdf: fitz.Document,
    *,
    content_start: int,
) -> int:
    cache_bold: dict[int, list[BoldSpan]] = {}
    cache_lines: dict[int, list] = {}
    changed = 0
    for seg in data.get("segments") or []:
        if not isinstance(seg, dict):
            continue
        printed = int(seg.get("page") or 0)
        if printed <= 0:
            continue
        pdf_page = content_start + printed - 1
        segment_type = str(seg.get("segment_type") or "prose")

        if isinstance(seg.get("bats"), list):
            for bat in seg["bats"]:
                if not isinstance(bat, dict):
                    continue
                for wak in bat.get("waks") or []:
                    if not isinstance(wak, dict):
                        continue
                    if _fix_text_field(
                        wak.get("text"),
                        segment_type=segment_type,
                        pdf_page=pdf_page,
                        pdf=pdf,
                        cache_bold=cache_bold,
                        cache_lines=cache_lines,
                    ):
                        changed += 1
            continue

        if _fix_text_field(
            seg.get("text"),
            segment_type=segment_type,
            pdf_page=pdf_page,
            pdf=pdf,
            cache_bold=cache_bold,
            cache_lines=cache_lines,
        ):
            changed += 1

        for hl in seg.get("hanging_lines") or []:
            if _fix_text_field(
                hl,
                segment_type=segment_type,
                pdf_page=pdf_page,
                pdf=pdf,
                cache_bold=cache_bold,
                cache_lines=cache_lines,
            ):
                changed += 1
    return changed


def _iter_segment_paths(
    *, volume: str | None, all_volumes: bool
) -> list[tuple[str, Path]]:
    out: list[tuple[str, Path]] = []
    if volume:
        out.append((volume, BOOKS / "volumes" / volume / "data" / "segments.json"))
        alt = OUTPUT_DIR / f"{volume}.segments.json"
        if alt.is_file():
            out.append((volume, alt))
    elif all_volumes:
        for vid in _volume_ids():
            out.append((vid, BOOKS / "volumes" / vid / "data" / "segments.json"))
            alt = OUTPUT_DIR / f"{vid}.segments.json"
            if alt.is_file():
                out.append((vid, alt))
    return [(v, p) for v, p in out if p.is_file()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--volume", default="")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--pdf", type=Path, default=None)
    args = parser.parse_args(argv)
    if not args.volume and not args.all:
        parser.error("pass --volume ID or --all")

    total = 0
    for vol_id, path in _iter_segment_paths(
        volume=args.volume or None, all_volumes=args.all
    ):
        data = load_document(path)
        content_start = int(data.get("content_start_pdf_page") or 0)
        if content_start <= 0:
            layout_path = BOOKS / "volumes" / vol_id / "data" / "layout.json"
            if layout_path.is_file():
                layout = json.loads(layout_path.read_text(encoding="utf-8"))
                content_start = int(layout.get("content_start_pdf_page") or 0)
        if content_start <= 0:
            print(f"SKIP {path}: missing content_start_pdf_page", file=sys.stderr)
            continue
        pdf_path = _resolve_pdf(vol_id, data, args.pdf)
        if pdf_path is None:
            print(f"SKIP {path}: PDF not found", file=sys.stderr)
            continue
        pdf = fitz.open(pdf_path)
        try:
            n = fix_document(data, pdf, content_start=content_start)
        finally:
            pdf.close()
        total += n
        action = "would update" if args.dry_run else "updated"
        print(f"{action} {n} text field(s) in {path}")
        if n and not args.dry_run:
            save_content(path, data)
    print(f"total text fields changed: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
