#!/usr/bin/env python3
"""Reclassify page-start prose vs prose_continuation from PDF geometry.

Does not re-extract text — only adjusts ``segment_type`` on stored JSON.

  python books/cs-roman/scripts/fixup_page_start_continuation.py --volume 01Vin01
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import fitz
except ImportError:  # pragma: no cover
    print("PyMuPDF (pymupdf) is required", file=sys.stderr)
    raise

from paths import BOOKS, REPO, ensure_import_paths

ensure_import_paths()
from cs_roman_hanging import reclassify_page_start_by_indent  # noqa: E402
from cs_roman_segments import load_document, save_content  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--volume", required=True, help="e.g. 01Vin01")
    parser.add_argument(
        "--pdf",
        type=Path,
        default=None,
        help="Override source PDF (default: layout.json source)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report changes without writing segments.json",
    )
    args = parser.parse_args(argv)

    vol = BOOKS / "volumes" / args.volume
    segments_path = vol / "data" / "segments.json"
    if not segments_path.is_file():
        print(f"Missing {segments_path}", file=sys.stderr)
        return 1

    doc_data = load_document(segments_path)
    content_start = int(doc_data.get("content_start_pdf_page") or 0)
    if content_start < 1:
        print("content_start_pdf_page missing/invalid", file=sys.stderr)
        return 1

    pdf_path = args.pdf
    if pdf_path is None:
        source = doc_data.get("source") or ""
        pdf_path = REPO / source if source else None
    if pdf_path is None or not Path(pdf_path).is_file():
        # Fallback: volume-local source copy.
        alt = vol / "source" / f"{args.volume}.pdf"
        if alt.is_file():
            pdf_path = alt
        else:
            print(f"Missing source PDF for {args.volume}", file=sys.stderr)
            return 1

    pdf = fitz.open(pdf_path)
    segments = list(doc_data.get("segments") or [])
    before = {
        i: s.get("segment_type")
        for i, s in enumerate(segments)
        if isinstance(s, dict)
    }
    stats = reclassify_page_start_by_indent(
        pdf, segments, content_start=content_start
    )
    changed = [
        (s.get("page"), s.get("order"), s.get("item"), before[i], s.get("segment_type"))
        for i, s in enumerate(segments)
        if isinstance(s, dict) and before.get(i) != s.get("segment_type")
    ]
    print(
        f"{args.volume}: demoted={stats['demoted_to_prose']} "
        f"upgraded={stats['upgraded_to_continuation']} "
        f"changed={len(changed)}"
    )
    for page, order, item, old, new in changed[:40]:
        print(f"  p{page} o{order} item={item}: {old} -> {new}")
    if len(changed) > 40:
        print(f"  … +{len(changed) - 40} more")

    if args.dry_run:
        return 0

    doc_data["segments"] = segments
    save_content(segments_path, doc_data, normalize=True)
    print(f"Wrote {segments_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
