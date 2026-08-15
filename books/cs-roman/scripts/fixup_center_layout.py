#!/usr/bin/env python3
"""Tag ``source_layout='center'`` from PDF geometry on stored segments JSON.

Does not re-extract text — only adjusts ``source_layout``.

  python books/cs-roman/scripts/fixup_center_layout.py --volume 01Vin01
  python books/cs-roman/scripts/fixup_center_layout.py --all
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

from paths import BOOKS, OUTPUT_DIR, REPO, ensure_import_paths

ensure_import_paths()
from cs_roman_hanging import (  # noqa: E402
    segment_roman_text,
    tag_center_layout_by_geometry,
)
from cs_roman_segments import load_document, save_content  # noqa: E402


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


def fixup_volume(
    volume_id: str,
    *,
    pdf: Path | None = None,
    dry_run: bool = False,
    sync_output: bool = True,
) -> int:
    vol = BOOKS / "volumes" / volume_id
    segments_path = vol / "data" / "segments.json"
    if not segments_path.is_file():
        print(f"Missing {segments_path}", file=sys.stderr)
        return 1

    doc_data = load_document(segments_path)
    content_start = int(doc_data.get("content_start_pdf_page") or 0)
    if content_start < 1:
        print(f"{volume_id}: content_start_pdf_page missing/invalid", file=sys.stderr)
        return 1

    pdf_path = _resolve_pdf(volume_id, doc_data, pdf)
    if pdf_path is None:
        print(f"Missing source PDF for {volume_id}", file=sys.stderr)
        return 1

    pdf_doc = fitz.open(pdf_path)
    segments = list(doc_data.get("segments") or [])
    before = {
        i: s.get("source_layout")
        for i, s in enumerate(segments)
        if isinstance(s, dict)
    }
    stats = tag_center_layout_by_geometry(
        pdf_doc, segments, content_start=content_start
    )
    changed = [
        (
            s.get("page"),
            s.get("order"),
            before.get(i),
            s.get("source_layout"),
            (segment_roman_text(s) or "")[:60],
        )
        for i, s in enumerate(segments)
        if isinstance(s, dict) and before.get(i) != s.get("source_layout")
    ]
    print(
        f"{volume_id}: tagged={stats['tagged_center']} "
        f"sandwich={stats.get('tagged_center_sandwich', 0)} "
        f"cleared={stats['cleared_center']} "
        f"changed={len(changed)}"
    )
    for page, order, old, new, preview in changed[:40]:
        safe = preview.encode("ascii", "replace").decode("ascii")
        print(f"  p{page} o{order}: {old!r} -> {new!r} | {safe}")
    if len(changed) > 40:
        print(f"  … +{len(changed) - 40} more")

    if dry_run:
        return 0

    doc_data["segments"] = segments
    save_content(segments_path, doc_data, normalize=True)
    print(f"Wrote {segments_path}")

    if sync_output:
        out_path = OUTPUT_DIR / f"{volume_id}.segments.json"
        if out_path.is_file():
            save_content(out_path, doc_data, normalize=True)
            print(f"Wrote {out_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--volume", help="e.g. 01Vin01")
    parser.add_argument("--all", action="store_true", help="All volumes with segments")
    parser.add_argument(
        "--pdf",
        type=Path,
        default=None,
        help="Override source PDF (single --volume only)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report changes without writing segments.json",
    )
    parser.add_argument(
        "--no-sync-output",
        action="store_true",
        help="Do not also write books/cs-roman/output/<id>.segments.json",
    )
    args = parser.parse_args(argv)

    if bool(args.volume) == bool(args.all):
        print("Specify exactly one of --volume or --all", file=sys.stderr)
        return 2

    ids = [args.volume] if args.volume else _volume_ids()
    if not ids:
        print("No volumes found", file=sys.stderr)
        return 1

    rc = 0
    for vid in ids:
        rc = max(
            rc,
            fixup_volume(
                vid,
                pdf=args.pdf if args.volume else None,
                dry_run=args.dry_run,
                sync_output=not args.no_sync_output,
            ),
        )
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
