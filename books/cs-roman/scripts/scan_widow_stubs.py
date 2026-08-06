#!/usr/bin/env python3
"""Scan a reading-mode PDF for short stubs stranded at the top of a page.

Detects:
  - widow_stub: short non-heading continuation at page head, then a new
    paragraph (numbered / indented) — classic last-line-of-paragraph alone
  - closer_stub: short end-of-section formula (นิฏฺฐิตํ / สมตฺตํ / …) alone
    at page head with no prior body of the same paragraph on that page

Example:
  python books/cs-roman/scripts/scan_widow_stubs.py --volume 02Vin02
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    import fitz
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyMuPDF (fitz) is required: pip install pymupdf") from exc

ROOT = Path(__file__).resolve().parents[1]  # books/cs-roman

# Reading geometry (pagegeometry-reading.tex): body roughly below head, above foot.
Y_BODY_MIN = 85.0
Y_BODY_MAX = 640.0
NOTE_LINE_RE = re.compile(r"^\d+\s")
SIZE_NOTE_MAX = 9.5

# Full text-block width ≈ 360 bp in this edition; stubs are much narrower.
W_STUB_MAX = 200.0
# First body line near the top of the text block.
Y_TOP_MAX = 130.0

NEW_PARA_RE = re.compile(r"^\d+\.")
# Allow glued ordinals: นิฏฺฐิตํสตฺตมํ. / นิฏฺฐิตํปฐมํ.
CLOSER_RE = re.compile(
    r"(?:นิฏฺฐิต[าโตํ]\S*|สมตฺตํ)\s*\.?$"
)
# Dotted TOC leaders / page-number-only lines — skip front-matter noise.
TOC_DOTS_RE = re.compile(r"\.{3,}")
FOLIO_RE = re.compile(r"^ฉ\.\d+")


@dataclass
class Line:
    text: str
    y0: float
    x0: float
    w: float
    size: float


@dataclass
class StubHit:
    kind: str  # widow_stub | closer_stub
    physical_page: int
    stub: str
    next_line: str
    stub_w: float
    stub_y0: float


def page_lines(page: fitz.Page) -> list[Line]:
    rows: list[Line] = []
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
            x0, y0, x1, _y1 = line["bbox"]
            rows.append(
                Line(
                    text=text,
                    y0=float(y0),
                    x0=float(x0),
                    w=float(x1 - x0),
                    size=float(spans[0].get("size") or 0),
                )
            )
    rows.sort(key=lambda r: (r.y0, r.x0))
    return rows


def body_content_lines(rows: list[Line]) -> list[Line]:
    body = [
        r
        for r in rows
        if Y_BODY_MIN < r.y0 < Y_BODY_MAX
        and not FOLIO_RE.match(r.text)
        and not TOC_DOTS_RE.search(r.text)
    ]
    while body:
        last = body[-1]
        if NOTE_LINE_RE.match(last.text) or last.size <= SIZE_NOTE_MAX:
            body.pop()
            continue
        break
    return body


def merge_same_band(rows: list[Line], tol: float = 3.0) -> list[Line]:
    """Join fragments that share roughly the same baseline (multi-span lines)."""
    if not rows:
        return []
    out: list[Line] = []
    cur = rows[0]
    for nxt in rows[1:]:
        if abs(nxt.y0 - cur.y0) <= tol:
            # Same visual line — keep leftmost start, sum width approx, join text.
            joined = f"{cur.text} {nxt.text}".strip()
            x0 = min(cur.x0, nxt.x0)
            x1 = max(cur.x0 + cur.w, nxt.x0 + nxt.w)
            cur = Line(
                text=joined,
                y0=min(cur.y0, nxt.y0),
                x0=x0,
                w=x1 - x0,
                size=max(cur.size, nxt.size),
            )
        else:
            out.append(cur)
            cur = nxt
    out.append(cur)
    return out


def is_short_stub(line: Line) -> bool:
    words = line.text.split()
    return len(words) <= 6 and line.w <= W_STUB_MAX


def looks_like_heading(line: Line) -> bool:
    # Numbered section titles are short but intentional page openers.
    if NEW_PARA_RE.match(line.text) and line.w < 220 and not line.text.rstrip().endswith("."):
        return True
    return False


def is_closer(text: str) -> bool:
    """End-of-section formulas only (นิฏฺฐิตํ / สมตฺตํ) — not arbitrary short prose."""
    return bool(CLOSER_RE.search(text.strip()))


def scan_pdf(pdf_path: Path) -> list[StubHit]:
    hits: list[StubHit] = []
    doc = fitz.open(pdf_path)
    try:
        for pi in range(doc.page_count):
            body = merge_same_band(body_content_lines(page_lines(doc[pi])))
            if len(body) < 1:
                continue
            first = body[0]
            if first.y0 > Y_TOP_MAX:
                continue
            if not is_short_stub(first):
                continue
            if looks_like_heading(first):
                continue

            nxt = body[1] if len(body) >= 2 else None
            # Closer formula alone at page head (with or without following heading).
            if is_closer(first.text):
                hits.append(
                    StubHit(
                        kind="closer_stub",
                        physical_page=pi + 1,
                        stub=first.text,
                        next_line=nxt.text if nxt else "",
                        stub_w=first.w,
                        stub_y0=first.y0,
                    )
                )
                continue

            # Widow: short non-new-para line, then a clear new numbered paragraph.
            # Require numbered next line to avoid gāthā / title false positives.
            if (
                not NEW_PARA_RE.match(first.text)
                and nxt is not None
                and NEW_PARA_RE.match(nxt.text)
                and is_short_stub(first)
            ):
                hits.append(
                    StubHit(
                        kind="widow_stub",
                        physical_page=pi + 1,
                        stub=first.text,
                        next_line=nxt.text,
                        stub_w=first.w,
                        stub_y0=first.y0,
                    )
                )
    finally:
        doc.close()
    return hits


def format_report(volume: str, pdf_path: Path, hits: list[StubHit]) -> str:
    closers = [h for h in hits if h.kind == "closer_stub"]
    widows = [h for h in hits if h.kind == "widow_stub"]
    lines = [
        f"# Widow / closer stubs — {volume} (reading)",
        "",
        f"PDF: `{pdf_path.as_posix()}`",
        f"Hits: {len(hits)} (closer_stub={len(closers)}, widow_stub={len(widows)})",
        "",
        "Physical page = PDF page index / visual check key.",
        "",
        "| kind | physical | y0 | w | stub | next |",
        "|------|---------:|---:|--:|------|------|",
    ]
    for h in hits:
        stub = h.stub.replace("|", "\\|")
        nxt = h.next_line.replace("|", "\\|")[:70]
        lines.append(
            f"| {h.kind} | {h.physical_page} | {h.stub_y0:.1f} | "
            f"{h.stub_w:.0f} | {stub} | {nxt} |"
        )
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--volume", required=True, help="Volume id, e.g. 02Vin02")
    p.add_argument("--pdf", type=Path, default=None, help="Override reading PDF path")
    p.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Write markdown report (default: research/widow_stubs_<vol>_reading.md)",
    )
    args = p.parse_args(argv)

    vol_dir = ROOT / "volumes" / args.volume
    pdf = args.pdf or vol_dir / "out" / f"{args.volume}.reading.pdf"
    if not pdf.is_file():
        print(f"missing PDF: {pdf}", file=sys.stderr)
        return 1

    hits = scan_pdf(pdf)
    report = format_report(args.volume, pdf, hits)
    out = args.output
    if out is None:
        out = ROOT / "research" / f"widow_stubs_{args.volume}_reading.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report, encoding="utf-8")
    print(f"wrote {out} ({len(hits)} hits)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
