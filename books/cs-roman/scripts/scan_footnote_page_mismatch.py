#!/usr/bin/env python3
"""Scan a cs-roman PDF for footnote bodies on a page without matching callouts.

Compares numbered marks in the body (above the footnote rule) with numbered
marks in the footnote block. Reports pages where a footnote-block mark has no
same-number callout in the body (notes migrated before their marks).

Example:
  python books/cs-roman/scripts/scan_footnote_page_mismatch.py --volume 01Vin01
  python books/cs-roman/scripts/scan_footnote_page_mismatch.py --volume 01Vin01 --mode sync
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

try:
    import fitz
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyMuPDF (fitz) is required: pip install pymupdf") from exc

ROOT = Path(__file__).resolve().parents[1]

# Reading / sync body band (approx); footnote block is smaller type near bottom.
Y_BODY_MIN = 70.0
# footnotesize ≈ 9.86pt in current stack; body ≈ 12pt.
SIZE_NOTE_MAX = 10.2
SIZE_BODY_MIN = 10.5
# \@makefnmark in the note block ≈ 6.6pt; body superscript callout ≈ 8.8pt.
# Do not use y_max*0.55 alone — late body callouts sit in the lower half and
# were misclassified as notes (false "orphan note" hits).
SIZE_NOTE_MARK_MAX = 7.5
SIZE_BODY_CALLOUT_MAX = 9.2
# Note-block marks: "1โลหิตกา" or packed "1foo 2bar" — digit then letter/*/+.
# Reject bare "3." outline crumbs.
NOTE_MARK_RE = re.compile(
    r"(?:^|\s)([1-9]\d{0,2})(?=[^\s\d.A-Za-z]*[\u0E00-\u0E7F*+])"
)
# Body callouts: letter/mark immediately followed by digit (โลหิติกา1).
BODY_CALLOUT_RE = re.compile(
    r"([\u0E00-\u0E7FA-Za-z])([1-9]\d{0,2})(?=\s|$|[^\d])"
)
DIGIT_RE = re.compile(r"[1-9]\d{0,2}")


@dataclass
class Mismatch:
    physical_page: int
    body_marks: list[int]
    note_marks: list[int]
    orphan_note_marks: list[int]
    sample_note: str


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
            size = max(float(s.get("size") or 0) for s in spans)
            rows.append(
                {
                    "text": text,
                    "y0": float(y0),
                    "y1": float(y1),
                    "x0": float(x0),
                    "size": size,
                    "spans": spans,
                }
            )
    rows.sort(key=lambda r: (r["y0"], r["x0"]))
    return rows


def _digit_spans(row: dict, *, size_max: float, size_min: float = 0.0) -> list[int]:
    found: list[int] = []
    for s in row.get("spans") or []:
        st = str(s.get("text") or "").strip()
        sz = float(s.get("size") or 0)
        if size_min < sz <= size_max and DIGIT_RE.fullmatch(st):
            found.append(int(st))
    return found


def split_body_notes(rows: list[dict]) -> tuple[list[dict], list[dict], float]:
    """Split page lines into body vs footnote block; return note_y0."""
    if not rows:
        return [], [], 0.0
    y_max = max(r["y1"] for r in rows)
    # Anchor the note block on true footnote marks (~6.6pt), not body callouts (~8.8).
    mark_rows = [
        r
        for r in rows
        if r["y0"] > y_max * 0.45
        and _digit_spans(r, size_max=SIZE_NOTE_MARK_MAX)
    ]
    if mark_rows:
        note_y0 = min(r["y0"] for r in mark_rows)
    else:
        notes_fallback = [
            r
            for r in rows
            if r["size"] <= SIZE_NOTE_MAX
            and r["y0"] > y_max * 0.70
            and NOTE_MARK_RE.search(r["text"])
        ]
        note_y0 = min((r["y0"] for r in notes_fallback), default=y_max)
    notes = [
        r
        for r in rows
        if r["y0"] >= note_y0 - 0.5 and r["size"] <= SIZE_NOTE_MAX
    ]
    body = [
        r
        for r in rows
        if r["y0"] >= Y_BODY_MIN and r["y0"] < note_y0 - 2.0
    ]
    return body, notes, note_y0


def marks_in_body(body: list[dict]) -> list[int]:
    """Superscript callout digits glued to body text (not ฉ.N folio crumbs)."""
    found: list[int] = []
    for row in body:
        if "ฉ." in row["text"]:
            continue
        # Prefer glued callouts (โลหิติกา1). Bare digit spans are ambiguous
        # (folio / outline) and over-fire as orphan callouts.
        glued = [int(m.group(2)) for m in BODY_CALLOUT_RE.finditer(row["text"])]
        if glued:
            found.extend(glued)
            continue
        span_marks = _digit_spans(
            row, size_max=SIZE_BODY_CALLOUT_MAX, size_min=SIZE_NOTE_MARK_MAX
        )
        # Only keep span digits when the row also has Thai/Latin letters
        # immediately before a same-size mark (callout), not a lone folio digit.
        if span_marks and re.search(r"[\u0E00-\u0E7FA-Za-z]", row["text"]):
            found.extend(span_marks)
    return found


def marks_in_notes(notes: list[dict]) -> tuple[list[int], str]:
    found: list[int] = []
    sample = ""
    for row in notes:
        span_hits = _digit_spans(row, size_max=SIZE_NOTE_MARK_MAX)
        if span_hits:
            found.extend(span_hits)
            if not sample:
                sample = row["text"][:80]
            continue
        hits = list(NOTE_MARK_RE.finditer(row["text"]))
        if not hits:
            continue
        for m in hits:
            found.append(int(m.group(1)))
        if not sample:
            sample = row["text"][:80]
    return found, sample


def scan_pdf(pdf_path: Path) -> list[Mismatch]:
    hits: list[Mismatch] = []
    doc = fitz.open(pdf_path)
    try:
        for pi in range(doc.page_count):
            rows = page_lines(doc[pi])
            body, notes, _note_y0 = split_body_notes(rows)
            if not notes:
                continue
            body_marks = marks_in_body(body)
            note_marks, sample = marks_in_notes(notes)
            if not note_marks:
                continue
            body_c = Counter(body_marks)
            note_c = Counter(note_marks)
            orphan: list[int] = []
            for mark, ncount in sorted(note_c.items()):
                bcount = body_c.get(mark, 0)
                if ncount > bcount:
                    orphan.extend([mark] * (ncount - bcount))
            if orphan:
                hits.append(
                    Mismatch(
                        physical_page=pi + 1,
                        body_marks=body_marks,
                        note_marks=note_marks,
                        orphan_note_marks=orphan,
                        sample_note=sample,
                    )
                )
    finally:
        doc.close()
    return hits


def format_report(volume: str, mode: str, pdf_path: Path, hits: list[Mismatch]) -> str:
    lines = [
        f"# Footnote page mismatch — {volume} ({mode})",
        "",
        f"PDF: `{pdf_path.as_posix()}`",
        f"Hits: {len(hits)}",
        "",
        "A hit means the footnote block has numbered mark(s) with no matching "
        "callout count in the body on that physical page (bodies migrated "
        "before callouts).",
        "",
        "| physical | body marks | note marks | orphan notes | sample |",
        "|---------:|------------|------------|--------------|--------|",
    ]
    for h in hits:
        body = ",".join(str(x) for x in h.body_marks) or "—"
        note = ",".join(str(x) for x in h.note_marks) or "—"
        orphan = ",".join(str(x) for x in h.orphan_note_marks) or "—"
        sample = h.sample_note.replace("|", "\\|")
        lines.append(
            f"| {h.physical_page} | {body} | {note} | {orphan} | {sample} |"
        )
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--volume", required=True, help="Volume id, e.g. 01Vin01")
    p.add_argument(
        "--mode",
        choices=("reading", "sync"),
        default="reading",
        help="Which PDF under volumes/<id>/out/ (default: reading)",
    )
    p.add_argument("--pdf", type=Path, default=None, help="Override PDF path")
    p.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Write markdown report (default: research/footnote_mismatch_<vol>_<mode>.md)",
    )
    p.add_argument(
        "--stdout",
        action="store_true",
        help="Print report to stdout instead of writing the default file",
    )
    args = p.parse_args(argv)

    vol_dir = ROOT / "volumes" / args.volume
    if args.mode == "reading":
        default_pdf = vol_dir / "out" / f"{args.volume}.reading.pdf"
    else:
        default_pdf = vol_dir / "out" / f"{args.volume}.pdf"
    pdf = args.pdf or default_pdf
    if not pdf.is_file():
        print(f"missing PDF: {pdf}", file=sys.stderr)
        return 1

    hits = scan_pdf(pdf)
    report = format_report(args.volume, args.mode, pdf, hits)
    if args.stdout:
        sys.stdout.buffer.write(report.encode("utf-8"))
    else:
        out = args.output or (
            ROOT
            / "research"
            / f"footnote_mismatch_{args.volume}_{args.mode}.md"
        )
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report, encoding="utf-8")
        print(f"wrote {out} ({len(hits)} hits)", file=sys.stderr)
    return 1 if hits else 0


if __name__ == "__main__":
    raise SystemExit(main())
