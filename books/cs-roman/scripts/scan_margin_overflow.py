#!/usr/bin/env python3
"""Scan cs-roman PDFs for body words that overflow the text-block right edge.

A hit is any word whose right edge extends past the text block by more than
about two character widths of that word. Margin folio marks (``ฉ.N``) and
content that sits entirely outside the text block are ignored.

Words are recovered from glyph bboxes (``rawdict``), splitting on horizontal
gaps. CS Roman TeX often spaces Thai/Pāli with kerning only — no space
glyphs — so MuPDF ``get_text("words")`` glues a whole line into one token.

Geometry matches ``shared/style/pagegeometry-printing.tex`` /
``pagegeometry-reading.tex`` (odd/even spine vs outer margins).

Examples:
  python books/cs-roman/scripts/scan_margin_overflow.py
  python books/cs-roman/scripts/scan_margin_overflow.py --all
  python books/cs-roman/scripts/scan_margin_overflow.py --volume 01Vin01
  python books/cs-roman/scripts/scan_margin_overflow.py --volume 01Vin01 --mode reading
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

try:
    import fitz
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyMuPDF (fitz) is required: pip install pymupdf") from exc

ROOT = Path(__file__).resolve().parents[1]
VOLUMES = ROOT / "volumes"
RESEARCH = ROOT / "research"

FOLIO_RE = re.compile(r"^ฉ\.\d+")
# Overflow past the text-block right edge by more than this many character
# widths of the word (estimated from the word's own glyph width).
OVERFLOW_CHARS = 2.0
# Interword gap in TeX PDFs is ~6–9pt; footnote callouts sit ~1–2pt after
# the host word. Split only on gaps larger than this (points).
WORD_GAP_PT = 3.0
# Skip nonspacing marks when estimating character width (same idea as
# scan_long_words.thai_display_len).
_SKIP_WIDTH_CATS = frozenset({"Mn", "Me", "Cf"})


@dataclass(frozen=True)
class PageGeometry:
    """Left/right margins from memoir ``\\setlrmarginsandblock{spine}{outer}``."""

    spine: float
    outer: float
    top: float
    bottom: float


# books/cs-roman/shared/style/pagegeometry-printing.tex
PRINTING_GEOM = PageGeometry(
    spine=73.11, outer=58.113, top=85.014, bottom=67.486
)
# books/cs-roman/shared/style/pagegeometry-reading.tex
READING_GEOM = PageGeometry(spine=78.0, outer=62.0, top=90.7, bottom=72.0)

MODE_GEOM = {
    "printing": PRINTING_GEOM,
    "reading": READING_GEOM,
}


@dataclass
class OverflowHit:
    volume: str
    physical_page: int
    y0: float
    x1: float
    text_right: float
    overflow_pt: float
    overflow_chars: float
    text: str


def display_char_count(text: str) -> int:
    """Spacing glyphs only (skip Thai/Pāli nonspacing marks and soft hyphens)."""
    n = 0
    for ch in text:
        if ch in "-‐‑­":
            continue
        if unicodedata.category(ch) in _SKIP_WIDTH_CATS:
            continue
        n += 1
    return max(n, 1)


def text_block_right(
    page_index: int, page_width: float, geom: PageGeometry
) -> float:
    """Right edge of the text block for a 0-based physical page index."""
    tw = page_width - geom.spine - geom.outer
    odd = page_index % 2 == 0  # page 1 is odd
    left = geom.spine if odd else geom.outer
    return left + tw


def is_body_y(y0: float, page_height: float, geom: PageGeometry) -> bool:
    return geom.top < y0 < (page_height - geom.bottom + 8.0)


@dataclass(frozen=True)
class GlyphWord:
    """One visual word recovered from glyph positions."""

    x0: float
    y0: float
    x1: float
    y1: float
    text: str


def _is_spacing_glyph(ch: str) -> bool:
    if not ch or ch.isspace():
        return False
    return unicodedata.category(ch) not in _SKIP_WIDTH_CATS


def words_from_glyphs(
    chars: list[tuple[str, float, float, float, float]],
    *,
    gap_pt: float = WORD_GAP_PT,
) -> list[GlyphWord]:
    """Cluster glyphs into words by horizontal gap / explicit spaces.

    ``chars`` is ``(text, x0, y0, x1, y1)`` in reading order within one line.
    Nonspacing marks attach to the current word. Explicit space glyphs and
    gaps ``> gap_pt`` between spacing glyphs start a new word.
    """
    words: list[GlyphWord] = []
    buf: list[str] = []
    x0 = y0 = x1 = y1 = 0.0
    have = False
    last_spacing_x1: float | None = None

    def flush() -> None:
        nonlocal have, buf
        text = "".join(buf).strip()
        if text and have:
            words.append(GlyphWord(x0=x0, y0=y0, x1=x1, y1=y1, text=text))
        buf = []
        have = False

    for ch, cx0, cy0, cx1, cy1 in chars:
        if ch.isspace():
            flush()
            last_spacing_x1 = None
            continue
        spacing = _is_spacing_glyph(ch)
        if (
            have
            and spacing
            and last_spacing_x1 is not None
            and (cx0 - last_spacing_x1) > gap_pt
        ):
            flush()
        if not have:
            x0, y0, x1, y1 = cx0, cy0, cx1, cy1
            have = True
            buf = [ch]
        else:
            buf.append(ch)
            x0 = min(x0, cx0)
            y0 = min(y0, cy0)
            x1 = max(x1, cx1)
            y1 = max(y1, cy1)
        if spacing:
            last_spacing_x1 = cx1
    flush()
    return words


def iter_page_words(page: fitz.Page) -> list[GlyphWord]:
    """Yield visual words from ``rawdict`` (gap-split; not MuPDF words)."""
    raw = page.get_text("rawdict")
    out: list[GlyphWord] = []
    for block in raw.get("blocks") or []:
        if block.get("type") != 0:
            continue
        for line in block.get("lines") or []:
            chars: list[tuple[str, float, float, float, float]] = []
            for span in line.get("spans") or []:
                for c in span.get("chars") or []:
                    ch = str(c.get("c") or "")
                    bbox = c.get("bbox") or (0.0, 0.0, 0.0, 0.0)
                    chars.append(
                        (ch, float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3]))
                    )
            out.extend(words_from_glyphs(chars))
    return out


def scan_page(
    page: fitz.Page,
    *,
    page_index: int,
    volume: str,
    geom: PageGeometry,
) -> list[OverflowHit]:
    page_w = float(page.rect.width)
    page_h = float(page.rect.height)
    right = text_block_right(page_index, page_w, geom)
    hits: list[OverflowHit] = []
    for word in iter_page_words(page):
        text = word.text.strip()
        if not text or FOLIO_RE.match(text):
            continue
        if not is_body_y(word.y0, page_h, geom):
            continue
        # Entirely in the outer margin (folio / notes column).
        if word.x0 >= right - 0.5:
            continue
        overflow = word.x1 - right
        if overflow <= 0:
            continue
        char_w = (word.x1 - word.x0) / display_char_count(text)
        if overflow <= OVERFLOW_CHARS * char_w:
            continue
        hits.append(
            OverflowHit(
                volume=volume,
                physical_page=page_index + 1,
                y0=word.y0,
                x1=word.x1,
                text_right=right,
                overflow_pt=overflow,
                overflow_chars=overflow / char_w,
                text=text,
            )
        )
    return hits


def scan_pdf(pdf_path: Path, volume: str, geom: PageGeometry) -> list[OverflowHit]:
    try:
        doc = fitz.open(pdf_path)
    except Exception as exc:  # noqa: BLE001 — report and skip corrupt PDFs
        raise RuntimeError(f"cannot open {pdf_path}: {exc}") from exc
    hits: list[OverflowHit] = []
    try:
        for pi in range(doc.page_count):
            hits.extend(
                scan_page(doc[pi], page_index=pi, volume=volume, geom=geom)
            )
    finally:
        doc.close()
    return hits


def volume_pdf(volume: str, mode: str) -> Path:
    return VOLUMES / volume / "out" / f"{volume}.{mode}.pdf"


def list_volumes() -> list[str]:
    names: list[str] = []
    for p in sorted(VOLUMES.iterdir()):
        if not p.is_dir() or not re.match(r"^\d{2}", p.name):
            continue
        if (p / "data" / "segments.json").is_file():
            names.append(p.name)
    return names


def format_report(mode: str, hits: list[OverflowHit], scanned: list[str]) -> str:
    lines = [
        f"# Margin overflow — {mode}",
        "",
        "Words whose right edge extends past the text block by **more than "
        f"about {OVERFLOW_CHARS:g} character widths** of that word. "
        "Folio marks (`ฉ.N`) ignored.",
        "",
        f"Volumes scanned: {len(scanned)}; hits: {len(hits)}. "
        "Rows ordered by character count (longest first).",
        "",
        "| volume | page | text |",
        "|--------|-----:|------|",
    ]
    ordered = sorted(
        hits,
        key=lambda h: (-len(h.text), h.volume, h.physical_page, h.y0),
    )
    for h in ordered:
        text = h.text.replace("|", "\\|")
        lines.append(f"| {h.volume} | {h.physical_page} | {text} |")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--volume", help="Volume id (e.g. 01Vin01)")
    g.add_argument(
        "--all",
        action="store_true",
        help="All volumes with segments (default)",
    )
    ap.add_argument(
        "--mode",
        choices=sorted(MODE_GEOM),
        default="printing",
        help="PDF mode to scan (default: printing)",
    )
    ap.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Markdown report path (default: research/margin_overflow_<mode>.md)",
    )
    args = ap.parse_args(argv)

    volumes = [args.volume] if args.volume else list_volumes()
    if not volumes:
        print("No volumes to scan", file=sys.stderr)
        return 1

    geom = MODE_GEOM[args.mode]
    all_hits: list[OverflowHit] = []
    scanned: list[str] = []
    missing: list[str] = []

    for vol in volumes:
        pdf = volume_pdf(vol, args.mode)
        if not pdf.is_file():
            missing.append(vol)
            print(f"skip {vol}: missing {pdf}", file=sys.stderr)
            continue
        try:
            hits = scan_pdf(pdf, vol, geom)
        except RuntimeError as exc:
            missing.append(vol)
            print(f"skip {vol}: {exc}", file=sys.stderr)
            continue
        scanned.append(vol)
        all_hits.extend(hits)
        print(f"{vol}: {len(hits)} hit(s)")

    out = args.output or RESEARCH / f"margin_overflow_{args.mode}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    report = format_report(args.mode, all_hits, scanned)
    out.write_text(report, encoding="utf-8")
    print(f"Wrote {out} ({len(all_hits)} hit(s) across {len(scanned)} volume(s))")
    if missing:
        print(f"Missing PDF: {len(missing)} volume(s)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
