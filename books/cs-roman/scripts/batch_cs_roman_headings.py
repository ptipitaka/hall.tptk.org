#!/usr/bin/env python3
"""Assign heading_kind / in_toc for every cs-roman segments JSON.

Example:
  docker compose exec -T web python books/cs-roman/scripts/batch_cs_roman_headings.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from paths import OUTPUT_DIR, SOURCE_DIR, ensure_import_paths

ensure_import_paths()
from assign_cs_roman_heading_levels import process_file  # noqa: E402

DEFAULT_JSON_DIR = OUTPUT_DIR
DEFAULT_PDF_DIR = SOURCE_DIR


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json-dir",
        type=Path,
        default=DEFAULT_JSON_DIR,
        help="Directory of *.segments.json (default: books/cs-roman/output)",
    )
    parser.add_argument(
        "--pdf-dir",
        type=Path,
        default=DEFAULT_PDF_DIR,
        help="Directory of source PDFs (default: books/cs-roman/source)",
    )
    args = parser.parse_args(argv)

    json_files = sorted(args.json_dir.glob("*.segments.json"))
    if not json_files:
        print(f"No segments JSON in {args.json_dir}", file=sys.stderr)
        return 1

    ok = 0
    failures: list[str] = []
    for json_path in json_files:
        stem = json_path.name.replace(".segments.json", "")
        pdf_path = args.pdf_dir / f"{stem}.pdf"
        if not pdf_path.is_file():
            print(f"SKIP {stem}: missing PDF {pdf_path}", file=sys.stderr)
            failures.append(stem)
            continue
        try:
            report = process_file(json_path, pdf_path)
            print(
                f"OK {stem}: matika={report['matika_entries']} "
                f"matched={report['matika_matched_to_segments']} "
                f"in_toc={report['in_toc_count']} "
                f"kinds={report['heading_kind_counts']}"
            )
            ok += 1
        except Exception as exc:  # noqa: BLE001 — batch continues
            print(f"FAIL {stem}: {exc}", file=sys.stderr)
            failures.append(stem)

    print(f"Done: {ok} ok, {len(failures)} failed")
    if failures:
        print("Failed:", ", ".join(failures), file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
