#!/usr/bin/env python3
"""Scan a reading-mode PDF for headings left alone at the bottom of a page.

Reports physical page (\\thepage), source folio, heading_kind, segment order,
and display text — suitable for ``page_breaks_reading_mode.before_orders``.

Example:
  python books/cs-roman/scripts/scan_orphan_headings.py --volume 01Vin01
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    import fitz
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyMuPDF (fitz) is required: pip install pymupdf") from exc

ROOT = Path(__file__).resolve().parents[1]  # books/cs-roman
THAI_DIGITS = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")

# Reading geometry (pagegeometry-reading.tex): body roughly below head, above foot.
Y_BODY_MIN = 85.0
Y_BODY_MAX = 640.0
# Footnote blocks often sit lower / smaller; treat digit-led lines as notes.
NOTE_LINE_RE = re.compile(r"^\d+\s")
SIZE_NOTE_MAX = 9.5


def thai_text_of(field: object) -> str:
    if isinstance(field, str):
        return field
    if not isinstance(field, list):
        return ""
    parts: list[str] = []
    for entry in field:
        if isinstance(entry, dict) and entry.get("script") == "thai":
            parts.append(str(entry.get("value") or ""))
    return "".join(parts)


def display_heading(seg: dict) -> str:
    title = thai_text_of(seg.get("text")).strip()
    no = seg.get("section_no")
    if no is None or no == "":
        return title
    return f"{no}. {title}"


def norm_key(text: str) -> str:
    s = text.translate(THAI_DIGITS)
    s = re.sub(r"\s+", "", s)
    s = s.replace("ฺ", "")
    return s


@dataclass
class Heading:
    order: int
    kind: str
    source_page: int | None
    display: str
    key: str


@dataclass
class OrphanHit:
    physical_page: int
    y0: float
    heading: Heading
    last_line: str


def load_headings(segments_path: Path) -> list[Heading]:
    data = json.loads(segments_path.read_text(encoding="utf-8"))
    segs = data["segments"] if isinstance(data, dict) else data
    out: list[Heading] = []
    for seg in segs:
        if seg.get("heading_kind") is None:
            continue
        display = display_heading(seg)
        key = norm_key(display)
        if not key:
            continue
        out.append(
            Heading(
                order=int(seg["order"]),
                kind=str(seg["heading_kind"]),
                source_page=int(seg["page"]) if seg.get("page") is not None else None,
                display=display,
                key=key,
            )
        )
    return out


def page_lines(page: fitz.Page) -> list[dict]:
    rows: list[dict] = []
    for block in page.get_text("dict")["blocks"]:
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            spans = line.get("spans") or []
            if not spans:
                continue
            text = "".join(s["text"] for s in spans).strip()
            if not text:
                continue
            x0, y0, x1, y1 = line["bbox"]
            size = float(spans[0].get("size") or 0)
            rows.append(
                {
                    "text": text,
                    "y0": float(y0),
                    "y1": float(y1),
                    "x0": float(x0),
                    "size": size,
                }
            )
    rows.sort(key=lambda r: (r["y0"], r["x0"]))
    return rows


def body_content_lines(rows: list[dict]) -> list[dict]:
    body = [r for r in rows if Y_BODY_MIN < r["y0"] < Y_BODY_MAX]
    # Drop trailing footnote-like lines so a heading above a note still counts.
    while body:
        last = body[-1]
        if NOTE_LINE_RE.match(last["text"]) or last["size"] <= SIZE_NOTE_MAX:
            body.pop()
            continue
        break
    return body


def match_heading(
    line_text: str,
    unused: list[Heading],
) -> Heading | None:
    """Exact normalized match only (avoids prose/title suffix false hits)."""
    key = norm_key(line_text)
    if not key:
        return None
    for i, h in enumerate(unused):
        if h.key == key:
            return unused.pop(i)
    return None


def scan_pdf(pdf_path: Path, headings: list[Heading]) -> list[OrphanHit]:
    unused = list(headings)
    hits: list[OrphanHit] = []
    doc = fitz.open(pdf_path)
    try:
        for pi in range(doc.page_count):
            rows = page_lines(doc[pi])
            body = body_content_lines(rows)
            if not body:
                continue
            last = body[-1]
            # Consume all heading matches on this page (in y order) so later
            # duplicates stay aligned; only the final body line can be orphan.
            page_heads: list[tuple[dict, Heading]] = []
            for row in body:
                hit = match_heading(row["text"], unused)
                if hit is not None:
                    page_heads.append((row, hit))
            if not page_heads:
                continue
            last_row, last_head = page_heads[-1]
            if last_row is not last:
                # Heading matched earlier on the page; body (or another block)
                # follows — not an orphan.
                continue
            # Orphan = heading is the last content line on the page.
            hits.append(
                OrphanHit(
                    physical_page=pi + 1,
                    y0=last_row["y0"],
                    heading=last_head,
                    last_line=last_row["text"],
                )
            )
    finally:
        doc.close()
    return hits


def format_report(volume: str, pdf_path: Path, hits: list[OrphanHit]) -> str:
    lines = [
        f"# Orphan headings — {volume} (reading)",
        "",
        f"PDF: `{pdf_path.as_posix()}`",
        f"Hits: {len(hits)}",
        "",
        "Physical page = `\\thepage` / key for visual check; "
        "**order** goes in `page_breaks_reading_mode.before_orders`.",
        "",
        "| physical | y0 | order | kind | src folio | text |",
        "|---------:|---:|------:|------|----------:|------|",
    ]
    for h in hits:
        src = h.heading.source_page if h.heading.source_page is not None else ""
        text = h.heading.display.replace("|", "\\|")
        lines.append(
            f"| {h.physical_page} | {h.y0:.1f} | {h.heading.order} | "
            f"{h.heading.kind} | {src} | {text} |"
        )
    if hits:
        orders = ", ".join(str(h.heading.order) for h in hits)
        lines.extend(
            [
                "",
                "## Suggested `before_orders`",
                "",
                "```json",
                '"page_breaks_reading_mode": {',
                f'  "before_orders": [{orders}]',
                "}",
                "```",
            ]
        )
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--volume", required=True, help="Volume id, e.g. 01Vin01")
    p.add_argument(
        "--pdf",
        type=Path,
        default=None,
        help="Override reading PDF path",
    )
    p.add_argument(
        "--segments",
        type=Path,
        default=None,
        help="Override segments.json path",
    )
    p.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Write markdown report (default: stdout)",
    )
    args = p.parse_args(argv)

    vol_dir = ROOT / "volumes" / args.volume
    pdf = args.pdf or vol_dir / "out" / f"{args.volume}.reading.pdf"
    segments = args.segments or vol_dir / "data" / "segments.json"
    if not pdf.is_file():
        print(f"missing PDF: {pdf}", file=sys.stderr)
        return 1
    if not segments.is_file():
        print(f"missing segments: {segments}", file=sys.stderr)
        return 1

    headings = load_headings(segments)
    hits = scan_pdf(pdf, headings)
    report = format_report(args.volume, pdf, hits)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
        print(f"wrote {args.output} ({len(hits)} hits)", file=sys.stderr)
    else:
        sys.stdout.buffer.write(report.encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
