#!/usr/bin/env python3
"""Trim CS Roman segments.json to body pages only (drop back-matter indexes).

Keeps Thai enrichment and heading fields. Use this on already-enriched JSON
instead of re-extracting.

Detection: first segment page whose opening text matches Padānukkama /
Piṭṭhaṅka / Gāthāsūci / anukkamaṇikā (same rules as extract_cs_roman_pdf).

Example:
  python books/cs-roman/scripts/trim_cs_roman_back_matter.py books/cs-roman/output/01Vin01.segments.json
  python books/cs-roman/scripts/trim_cs_roman_back_matter.py books/cs-roman/output --all
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

from paths import ensure_import_paths

ensure_import_paths()
from cs_roman_segments import load_document, save as save_segments  # noqa: E402
from extract_cs_roman_pdf import BACK_MATTER_RE, page_looks_like_back_matter  # noqa: E402


def segment_plain_text(seg: dict) -> str:
    parts: list[str] = []
    text = seg.get("text")
    if isinstance(text, list):
        for item in text:
            if isinstance(item, dict) and item.get("value"):
                parts.append(str(item["value"]))
    elif isinstance(text, str):
        parts.append(text)
    for bat in seg.get("bats") or []:
        if not isinstance(bat, dict):
            continue
        for wak in bat.get("waks") or []:
            if not isinstance(wak, dict):
                continue
            wak_text = wak.get("text")
            if isinstance(wak_text, list):
                for item in wak_text:
                    if isinstance(item, dict) and item.get("value"):
                        parts.append(str(item["value"]))
            elif isinstance(wak_text, str):
                parts.append(wak_text)
    title = seg.get("title")
    if isinstance(title, str):
        parts.append(title)
    return " ".join(parts)


def detect_back_matter_start_from_segments(segments: list[dict]) -> int | None:
    by_page: dict[int, list[dict]] = {}
    for seg in segments:
        page = seg.get("page")
        if not isinstance(page, int):
            continue
        by_page.setdefault(page, []).append(seg)
    for page in sorted(by_page):
        head = " ".join(segment_plain_text(seg) for seg in by_page[page][:4])
        if page_looks_like_back_matter(head) or BACK_MATTER_RE.search(head[:600]):
            return page
    return None


def trim_document(
    data: dict,
    *,
    content_end: int | None = None,
    back_matter_start: int | None = None,
) -> tuple[dict, dict]:
    segments = list(data.get("segments") or [])
    if back_matter_start is None and content_end is None:
        back_matter_start = detect_back_matter_start_from_segments(segments)
    if content_end is None:
        if back_matter_start is None:
            raise ValueError(
                "Could not detect back-matter start; pass --content-end explicitly"
            )
        # Keep pages strictly before indexes (blank interstitial pages drop out).
        kept = [
            seg
            for seg in segments
            if isinstance(seg.get("page"), int) and seg["page"] < back_matter_start
        ]
        content_end = max((seg["page"] for seg in kept), default=back_matter_start - 1)
    else:
        kept = [
            seg
            for seg in segments
            if isinstance(seg.get("page"), int) and seg["page"] <= content_end
        ]
        if back_matter_start is None:
            back_matter_start = content_end + 1
    # Re-number order if present.
    for i, seg in enumerate(kept, start=1):
        if "order" in seg:
            seg["order"] = i

    out = dict(data)
    out["segments"] = kept
    out["content_end_printed_page"] = content_end
    out["back_matter_start_printed_page"] = back_matter_start

    stats = {
        "before": len(segments),
        "after": len(kept),
        "removed": len(segments) - len(kept),
        "content_end_printed_page": content_end,
        "back_matter_start_printed_page": back_matter_start,
        "max_page_kept": max((seg["page"] for seg in kept), default=None),
        "segment_type_counts": dict(
            sorted(Counter(str(s.get("segment_type") or "?") for s in kept).items())
        ),
    }
    return out, stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "path",
        type=Path,
        help="segments.json file, or directory with *.segments.json",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="When path is a directory, trim every *.segments.json",
    )
    parser.add_argument(
        "--content-end",
        type=int,
        default=None,
        help="Last printed page to keep (default: auto back-matter start − 1)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report only; do not write files",
    )
    args = parser.parse_args(argv)

    paths: list[Path]
    if args.path.is_dir():
        if not args.all:
            print("Directory given; pass --all to trim every *.segments.json", file=sys.stderr)
            return 2
        paths = sorted(args.path.glob("*.segments.json"))
    else:
        paths = [args.path]

    if not paths:
        print(f"No segments JSON at {args.path}", file=sys.stderr)
        return 1

    for path in paths:
        data = load_document(path)
        try:
            out, stats = trim_document(data, content_end=args.content_end)
        except ValueError as exc:
            print(f"SKIP {path.name}: {exc}", file=sys.stderr)
            continue
        print(
            f"{path.name}: {stats['before']} -> {stats['after']} "
            f"(removed {stats['removed']}; end={stats['content_end_printed_page']}; "
            f"back_matter={stats['back_matter_start_printed_page']}; "
            f"max_page={stats['max_page_kept']})"
        )
        if not args.dry_run:
            save_segments(path, out, normalize=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
