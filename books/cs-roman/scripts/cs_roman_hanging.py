"""Detect CS Roman hanging-paragraph blocks from PDF line geometry.

In the printed edition, a hanging paragraph is one unit whose first line sits at
the normal first-line indent (~84 pt) and whose following lines sit deeper
(~106 pt) — not body wrap (~63 pt) and not gāthā indent (~127 pt).

Example (printed page 216 / PDF 239)::

    84.2  338. Paṭiggaṇhāti vīmaṃsati paccāharati, …
   105.8      Paṭiggaṇhāti vīmaṃsati na paccāharati, …
   105.8      …
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Any

try:
    import fitz
except ImportError:  # pragma: no cover
    fitz = None  # type: ignore

from cs_roman_vztime import vztime_to_unicode

# CS Roman 01Vin01 body columns (measured); keep ranges tight to avoid gāthā.
_FIRST_INDENT_LO = 78.0
_FIRST_INDENT_HI = 92.0
_HANG_INDENT_LO = 100.0
_HANG_INDENT_HI = 116.0

_ITEM_PREFIX_RE = re.compile(r"^\d+\.\s*")
_SPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class PageLine:
    y0: float
    x0: float
    text: str


@dataclass(frozen=True)
class HangingGroup:
    """One hanging paragraph on a PDF page."""

    pdf_page: int
    head: str
    lines: tuple[str, ...]  # hanging body lines (not including head)


def normalize_match_text(text: str) -> str:
    """Normalize for matching PDF lines to extracted segment strings."""
    t = (text or "").replace("\u00ad", "").strip()
    t = _ITEM_PREFIX_RE.sub("", t)
    t = _SPACE_RE.sub(" ", t)
    return t.strip(" \t\"'“”")


def page_body_lines(page: Any) -> list[PageLine]:
    """Return non-empty body lines as (y0, x0, unicode text), top-to-bottom."""
    if fitz is None:
        raise RuntimeError("PyMuPDF (pymupdf) is required")
    rows: list[PageLine] = []
    for block in page.get_text("dict").get("blocks") or []:
        if block.get("type") != 0:
            continue
        for line in block.get("lines") or []:
            spans = line.get("spans") or []
            if not spans:
                continue
            raw = "".join(str(s.get("text") or "") for s in spans)
            text = vztime_to_unicode(raw).strip()
            if not text:
                continue
            x0 = min(float(s["bbox"][0]) for s in spans)
            y0 = float(line["bbox"][1])
            # Skip far-right running heads / folio digits.
            if x0 > 200:
                continue
            rows.append(PageLine(y0=y0, x0=x0, text=text))
    rows.sort(key=lambda r: (r.y0, r.x0))
    return rows


def _is_first_indent(x0: float) -> bool:
    return _FIRST_INDENT_LO <= x0 <= _FIRST_INDENT_HI


def _is_hang_indent(x0: float) -> bool:
    return _HANG_INDENT_LO <= x0 <= _HANG_INDENT_HI


def hanging_groups_on_page(page: Any, *, pdf_page: int) -> list[HangingGroup]:
    """Find hanging paragraph groups on one PDF page via x0 bands."""
    lines = page_body_lines(page)
    groups: list[HangingGroup] = []
    i = 0
    n = len(lines)
    while i < n:
        head = lines[i]
        if not _is_first_indent(head.x0):
            i += 1
            continue
        # Apparatus / footnote markers are not hanging heads.
        if head.text.lstrip().startswith(("*", "+")):
            i += 1
            continue
        j = i + 1
        hang: list[str] = []
        while j < n and _is_hang_indent(lines[j].x0):
            body = lines[j].text.strip()
            # Skip footnote callout lines that share a similar x0.
            if body.startswith(("*", "+")):
                break
            hang.append(body)
            j += 1
        if hang:
            groups.append(
                HangingGroup(
                    pdf_page=pdf_page,
                    head=head.text.strip(),
                    lines=tuple(hang),
                )
            )
            i = j
            continue
        i += 1
    return groups


def collect_hanging_groups(
    doc: Any,
    *,
    pdf_pages: set[int] | None = None,
) -> list[HangingGroup]:
    """Scan PDF pages (1-based) and return all hanging groups."""
    if fitz is None:
        raise RuntimeError("PyMuPDF (pymupdf) is required")
    out: list[HangingGroup] = []
    for idx in range(doc.page_count):
        pdf_page = idx + 1
        if pdf_pages is not None and pdf_page not in pdf_pages:
            continue
        out.extend(hanging_groups_on_page(doc[idx], pdf_page=pdf_page))
    return out


def _texts_equal(a: str, b: str) -> bool:
    return normalize_match_text(a) == normalize_match_text(b)


def merge_hanging_into_segments(segments: list[Any], groups: list[HangingGroup]) -> int:
    """
    Fold hanging child prose segments into their head segment.

    Mutates ``segments`` in place (sets ``source_layout='hanging'`` and
    ``hanging_lines`` on the head; removes absorbed children).

    Returns the number of hanging groups successfully merged.
    """
    if not groups:
        return 0

    # Index groups by pdf page for local search.
    by_page: dict[int, list[HangingGroup]] = {}
    for g in groups:
        by_page.setdefault(g.pdf_page, []).append(g)

    used: set[int] = set()  # id(group)
    out: list[Any] = []
    i = 0
    merged = 0
    while i < len(segments):
        seg = segments[i]
        pdf_page = getattr(seg, "pdf_page", None)
        kind = getattr(seg, "segment_type", "") or ""
        if (
            pdf_page
            and kind in {"prose", "verse"}
            and getattr(seg, "bats", None) is None
        ):
            candidates = by_page.get(int(pdf_page)) or []
            matched: HangingGroup | None = None
            for g in candidates:
                if id(g) in used:
                    continue
                if _texts_equal(seg.text, g.head):
                    matched = g
                    break
            if matched is not None:
                kids = list(matched.lines)
                ok = True
                for k, expected in enumerate(kids):
                    nxt_i = i + 1 + k
                    if nxt_i >= len(segments):
                        ok = False
                        break
                    nxt = segments[nxt_i]
                    if (getattr(nxt, "segment_type", "") or "") not in {
                        "prose",
                        "verse",
                    }:
                        ok = False
                        break
                    if getattr(nxt, "pdf_page", None) != pdf_page:
                        ok = False
                        break
                    if not _texts_equal(nxt.text, expected):
                        ok = False
                        break
                if ok:
                    seg.source_layout = "hanging"
                    seg.hanging_lines = list(kids)
                    used.add(id(matched))
                    out.append(seg)
                    i += 1 + len(kids)
                    merged += 1
                    continue
        out.append(seg)
        i += 1

    segments[:] = out
    for n, seg in enumerate(segments, start=1):
        seg.order = n
    return merged


def hanging_band_histogram(groups: list[HangingGroup]) -> dict[str, int]:
    """Debug helper: count groups / lines."""
    return {
        "groups": len(groups),
        "lines": sum(len(g.lines) for g in groups),
        "pages": len({g.pdf_page for g in groups}),
    }
