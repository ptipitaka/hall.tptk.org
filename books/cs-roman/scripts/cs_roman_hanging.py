"""Detect CS Roman hanging-paragraph / center-line blocks from PDF geometry.

In the printed edition, a hanging paragraph is one unit whose first line sits at
the normal first-line indent (~84 pt) and whose following lines sit deeper
(~106 pt) — not body wrap (~63 pt) and not gāthā indent (~127–149 pt).

Example (printed page 216 / PDF 239)::

    84.2  338. Paṭiggaṇhāti vīmaṃsati paccāharati, …
   105.8      Paṭiggaṇhāti vīmaṃsati na paccāharati, …
   105.8      …

Gāthā column (measured 01Vin01)::

   119.3  dialogue bat_line with leading * / + (just above hang band)
   127.4  uddāna / wak_line / bat_line verse
   138.7  embedded verse with leading * / +
   149.0  embedded verse continuation (text aligned after marker)

Embedded verse in hang / near-hang band (not hanging paragraphs)::

    98.3  * Manāpameva… (02Vin02 p.8; apparatus on first bat)
   108.0  following bat lines of the same 1 บทครึ่ง
    97–103  many SN/KN bat_line body verses

Centered short labels (measured 01Vin01 p.129+)::

   mid ≈ page_mid (±12); width ≲ 0.55×page — e.g. ``Baddhacakkaṃ.``,
   ``Idaṃ saṃkhittaṃ.``, ``Idaṃ sabbamūlakaṃ``. Full-width first-indent
   prose is not geometry-center, but a short segment (≲2 sentences)
   sandwiched between two already-centered neighbors is promoted to
   center as well (e.g. ``Evaṃ ekekaṃ mūlaṃ kātuna…`` between
   ``Baddhacakkaṃ.`` and ``Idaṃ saṃkhittaṃ.``).

Page-start prose vs continuation uses the same flush / first-indent bands:
flush first line → ``prose_continuation``; indented → new ``prose``.
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
_BODY_FLUSH_LO = 55.0
_BODY_FLUSH_HI = 72.0
_FIRST_INDENT_LO = 78.0
_FIRST_INDENT_HI = 92.0
_HANG_INDENT_LO = 100.0
_HANG_INDENT_HI = 116.0
# Gāthā verse column (deeper than hang; shallower than short centered labels).
# LO 117: dialogue * lines on 01Vin01 p.223 sit ~119.3 (gap above hang ≤116).
_GATHA_INDENT_LO = 117.0
_GATHA_INDENT_HI = 155.0
# Embedded / book-body verse often sits in or just below the hang band
# (02Vin02 p.8 Manāpameva ~98–108; many SN/KN bat lines ~97–103), not only
# the deep column ≥117. Used by geometry tagging after hanging paragraphs
# have already claimed first-indent head + hang children.
_GATHA_GEOMETRY_INDENT_LO = 97.0
# Far-right folio / margin (not body). Centered labels sit ~140–220 x0.
_FOLIO_X0_SKIP = 350.0
# Centered short line: midpoint near page center, not full text width.
_CENTER_MID_TOL = 12.0
_CENTER_MAX_WIDTH_FRAC = 0.55
_CENTER_LAYOUT = "center"
_CENTER_KINDS = frozenset(
    {
        "prose",
        "prose_continuation",
        "verse",
        "verse_continuation",
        "title",
        "niṭṭhitaṃ",
    }
)
# Short prose between two centers (not geometry-centered itself).
_CENTER_SANDWICH_MAX_CHARS = 80
_CENTER_SANDWICH_MAX_SENTENCES = 2
_CENTER_SKIP_LAYOUTS = frozenset({"hanging", "bat_line", "wak_line"})
_SENTENCE_SPLIT_RE = re.compile(r"\.+")

_ITEM_PREFIX_RE = re.compile(r"^\d+\.\s*")
_SPACE_RE = re.compile(r"\s+")
_MARKER_RE = re.compile(r"\{\{[^}]+\}\}")
_APPARATUS_PREFIX_RE = re.compile(r"^[\*\+]\s*")
# PDF apparatus callouts are often glued digits (Videsso1); segment JSON uses
# {{n0}} which normalize strips — align both sides by dropping those digits.
_GLUED_FOOTNOTE_DIGIT_RE = re.compile(
    r"(?<=\w)[0-9]{1,2}(?=(?:\s|[.,;:!?\"'“”…]|$))"
)
_MATCH_PREFIX_LEN = 28

_BODY_KINDS = frozenset(
    {
        "prose",
        "prose_continuation",
        "verse",
        "verse_continuation",
        "gatha",
        "gatha_continuation",
    }
)


@dataclass(frozen=True)
class PageLine:
    y0: float
    x0: float
    text: str
    x1: float = 0.0
    y1: float = 0.0


@dataclass(frozen=True)
class HangingGroup:
    """One hanging paragraph on a PDF page."""

    pdf_page: int
    head: str
    lines: tuple[str, ...]  # hanging body lines (not including head)


def normalize_match_text(text: str) -> str:
    """Normalize for matching PDF lines to extracted segment strings."""
    t = (text or "").replace("\u00ad", "").strip()
    t = _MARKER_RE.sub("", t)
    t = _APPARATUS_PREFIX_RE.sub("", t)
    t = _ITEM_PREFIX_RE.sub("", t)
    t = _GLUED_FOOTNOTE_DIGIT_RE.sub("", t)
    t = _SPACE_RE.sub(" ", t)
    return t.strip(" \t\"'“”«»")


def segment_roman_text(seg: Any) -> str:
    """Roman body string from a Segment object or schema-v1 JSON segment."""
    if isinstance(seg, dict):
        text = seg.get("text")
        if isinstance(text, str):
            return text
        if isinstance(text, list):
            for entry in text:
                if isinstance(entry, dict) and entry.get("script") == "roman":
                    return str(entry.get("value") or "")
            for entry in text:
                if isinstance(entry, dict) and entry.get("script") != "thai":
                    return str(entry.get("value") or "")
        return ""
    text = getattr(seg, "text", None)
    if isinstance(text, str):
        return text
    return ""


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
            x1 = max(float(s["bbox"][2]) for s in spans)
            y0 = float(line["bbox"][1])
            y1 = float(line["bbox"][3])
            # Skip far-right folio digits (keep centered labels ~x0 140–220).
            if x0 > _FOLIO_X0_SKIP:
                continue
            rows.append(PageLine(y0=y0, x0=x0, x1=x1, y1=y1, text=text))
    rows.sort(key=lambda r: (r.y0, r.x0))
    return rows


def _is_first_indent(x0: float) -> bool:
    return _FIRST_INDENT_LO <= x0 <= _FIRST_INDENT_HI


def _is_body_flush(x0: float) -> bool:
    return _BODY_FLUSH_LO <= x0 <= _BODY_FLUSH_HI


def _is_hang_indent(x0: float) -> bool:
    return _HANG_INDENT_LO <= x0 <= _HANG_INDENT_HI


def _is_gatha_indent(x0: float) -> bool:
    """True for the deep verse column (not hang indent, not centered titles)."""
    return _GATHA_INDENT_LO <= x0 <= _GATHA_INDENT_HI


def _is_gatha_geometry_indent(x0: float) -> bool:
    """True for indents eligible for embedded-gāthā geometry tagging.

    Includes the deep gāthā column and the hang / near-hang band used for
    many bat_line verses and embedded wak_line udāna quotes. Call only after
    hanging paragraphs are merged so true hang-body prose is no longer a
    separate segment.
    """
    return _GATHA_GEOMETRY_INDENT_LO <= x0 <= _GATHA_INDENT_HI


def _is_center_line(line: PageLine, page_width: float) -> bool:
    """True when a PDF line is a short centered label (not full-width prose)."""
    if page_width <= 0:
        return False
    # Left-column bands are never center labels.
    if (
        _is_body_flush(line.x0)
        or _is_first_indent(line.x0)
        or _is_hang_indent(line.x0)
    ):
        return False
    x1 = line.x1 if line.x1 > line.x0 else line.x0
    mid = (line.x0 + x1) / 2.0
    page_mid = page_width / 2.0
    wfrac = (x1 - line.x0) / page_width
    return abs(mid - page_mid) <= _CENTER_MID_TOL and wfrac <= _CENTER_MAX_WIDTH_FRAC


def find_matching_body_line(page: Any, text: str) -> PageLine | None:
    """Return the first body line whose text matches the start of ``text``."""
    return _match_cached_line(page_body_lines(page), text)


def _seg_pdf_page(seg: Any, *, content_start: int | None = None) -> int | None:
    pdf_page = getattr(seg, "pdf_page", None)
    if pdf_page is None and isinstance(seg, dict):
        pdf_page = seg.get("pdf_page")
    if isinstance(pdf_page, int) and pdf_page > 0:
        return pdf_page
    if content_start is None:
        return None
    page = getattr(seg, "page", None)
    if page is None and isinstance(seg, dict):
        page = seg.get("page")
    if isinstance(page, int) and page > 0:
        return int(content_start) + page - 1
    return None


def _set_segment_type(seg: Any, kind: str) -> None:
    if isinstance(seg, dict):
        seg["segment_type"] = kind
    else:
        seg.segment_type = kind


def _get_segment_type(seg: Any) -> str:
    if isinstance(seg, dict):
        return str(seg.get("segment_type") or "")
    return str(getattr(seg, "segment_type", "") or "")


def _get_source_layout(seg: Any) -> str | None:
    if isinstance(seg, dict):
        layout = seg.get("source_layout")
    else:
        layout = getattr(seg, "source_layout", None)
    if layout is None or layout == "":
        return None
    return str(layout)


def _set_source_layout(seg: Any, layout: str | None) -> None:
    if isinstance(seg, dict):
        if layout is None:
            seg.pop("source_layout", None)
        else:
            seg["source_layout"] = layout
    else:
        seg.source_layout = layout


def _match_after_leading_tokens(nt: str, needle: str, prefix: str) -> bool:
    """Match when PDF line still has a hyphen-tail token before ``needle``.

    Extract repairs ``aneka-`` / ``pariyāyena …`` by moving the leading word
    onto the previous segment, so the stored page-start may begin at the
    following word while the PDF line still starts with ``pariyāyena``.
    """
    parts = nt.split()
    for i in range(1, min(3, len(parts))):
        rest = " ".join(parts[i:])
        if not rest:
            continue
        rest_prefix = rest[:_MATCH_PREFIX_LEN]
        if needle.startswith(rest_prefix) or rest.startswith(prefix):
            return True
    return False


def _match_cached_line(
    lines: list[PageLine], text: str
) -> PageLine | None:
    needle = normalize_match_text(text)
    if not needle:
        return None
    prefix = needle[:_MATCH_PREFIX_LEN]
    for line in lines:
        nt = normalize_match_text(line.text)
        if not nt:
            continue
        line_prefix = nt[:_MATCH_PREFIX_LEN]
        if needle.startswith(line_prefix) or nt.startswith(prefix):
            return line
        if _match_after_leading_tokens(nt, needle, prefix):
            return line
    return None


def _seg_page(seg: Any) -> int:
    if isinstance(seg, dict):
        return int(seg.get("page") or 0)
    return int(getattr(seg, "page", 0) or 0)


def _seg_item(seg: Any) -> Any:
    if isinstance(seg, dict):
        return seg.get("item")
    return getattr(seg, "item", None)


def reclassify_continuations_by_indent(
    doc: Any,
    segments: list[Any],
    *,
    content_start: int | None = None,
) -> int:
    """Demote ``prose_continuation`` to ``prose`` when the page-start line is indented.

    Flush-left page starts stay as continuation. Unmatched lines are left alone
    (prefer no false indent). Returns the number of demotions.
    """
    if fitz is None:
        raise RuntimeError("PyMuPDF (pymupdf) is required")
    changed = 0
    line_cache: dict[int, list[PageLine]] = {}
    for seg in segments:
        if _get_segment_type(seg) != "prose_continuation":
            continue
        pdf_page = _seg_pdf_page(seg, content_start=content_start)
        if pdf_page is None or pdf_page < 1 or pdf_page > doc.page_count:
            continue
        roman = segment_roman_text(seg)
        if not roman.strip():
            continue
        if pdf_page not in line_cache:
            line_cache[pdf_page] = page_body_lines(doc[pdf_page - 1])
        matched = _match_cached_line(line_cache[pdf_page], roman)
        if matched is not None and _is_first_indent(matched.x0):
            _set_segment_type(seg, "prose")
            changed += 1
    return changed


def reclassify_page_start_by_indent(
    doc: Any,
    segments: list[Any],
    *,
    content_start: int,
) -> dict[str, int]:
    """Classify page-starts from PDF geometry (extract + stored-JSON fixup).

    - cross-page same-item ``prose`` + flush first line → ``*_continuation``
    - ``*_continuation`` + indented first line → ``prose`` (new paragraph)
    """
    if fitz is None:
        raise RuntimeError("PyMuPDF (pymupdf) is required")

    demoted = reclassify_continuations_by_indent(
        doc, segments, content_start=content_start
    )
    upgraded = 0
    line_cache: dict[int, list[PageLine]] = {}

    for seg in segments:
        if _get_segment_type(seg) != "prose":
            continue
        item = _seg_item(seg)
        if item is None:
            continue
        page = _seg_page(seg)
        has_prior = any(
            _seg_page(s) < page
            and _seg_item(s) == item
            and _get_segment_type(s) in _BODY_KINDS
            for s in segments
        )
        if not has_prior:
            continue
        pdf_page = _seg_pdf_page(seg, content_start=content_start)
        if pdf_page is None or pdf_page < 1 or pdf_page > doc.page_count:
            continue
        roman = segment_roman_text(seg)
        if not roman.strip():
            continue
        if pdf_page not in line_cache:
            line_cache[pdf_page] = page_body_lines(doc[pdf_page - 1])
        matched = _match_cached_line(line_cache[pdf_page], roman)
        if matched is not None and _is_body_flush(matched.x0):
            base = _get_segment_type(seg)
            if base.endswith("_continuation"):
                cont = base
            else:
                cont = f"{base}_continuation"
            _set_segment_type(seg, cont)
            upgraded += 1

    return {"demoted_to_prose": demoted, "upgraded_to_continuation": upgraded}


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


def _plain_center_text(seg: Any) -> str:
    """Roman text with extract markers removed — for sandwich length checks."""
    return _MARKER_RE.sub("", segment_roman_text(seg) or "").strip()


def _sentence_count(text: str) -> int:
    """Count sentence-like chunks split on ASCII periods."""
    parts = [p.strip() for p in _SENTENCE_SPLIT_RE.split(text or "") if p.strip()]
    return len(parts)


def _is_short_center_sandwich_text(text: str) -> bool:
    """True for short (≲1–2 sentence) text eligible for sandwich centering."""
    t = (text or "").strip()
    if not t:
        return False
    if len(t) > _CENTER_SANDWICH_MAX_CHARS:
        return False
    return _sentence_count(t) <= _CENTER_SANDWICH_MAX_SENTENCES


def tag_center_layout_by_sandwich(segments: list[Any]) -> dict[str, int]:
    """Promote a short segment to ``center`` when both neighbors are centered.

    Pattern (01Vin01 p.129)::

        Baddhacakkaṃ.                              (center)
        Evaṃ ekekaṃ mūlaṃ kātuna … kattabbaṃ.      → center
        Idaṃ saṃkhittaṃ.                           (center)

    Only a single intervening segment is considered. Skips hanging / gāthā
    layouts and kinds outside the center vocabulary. Does not change
    ``segment_type``.
    """
    tagged = 0
    n = len(segments)
    for i in range(1, n - 1):
        prev_seg = segments[i - 1]
        seg = segments[i]
        next_seg = segments[i + 1]
        if _get_source_layout(prev_seg) != _CENTER_LAYOUT:
            continue
        if _get_source_layout(next_seg) != _CENTER_LAYOUT:
            continue
        layout = _get_source_layout(seg)
        if layout == _CENTER_LAYOUT or layout in _CENTER_SKIP_LAYOUTS:
            continue
        if _get_segment_type(seg) not in _CENTER_KINDS:
            continue
        if not _is_short_center_sandwich_text(_plain_center_text(seg)):
            continue
        _set_source_layout(seg, _CENTER_LAYOUT)
        tagged += 1
    return {"tagged_center_sandwich": tagged}


def tag_center_layout_by_geometry(
    doc: Any,
    segments: list[Any],
    *,
    content_start: int,
) -> dict[str, int]:
    """Set ``source_layout='center'`` when the segment's first PDF line is centered.

    Geometry (midpoint + short width), then sandwich promotion for a short
    segment between two centers. Does not change ``segment_type``.
    Skips hanging / gāthā layouts. Clears a stale ``center`` when the line no
    longer matches geometry (sandwich tags are re-applied afterward).
    Returns counts for CLI / extract stats.
    """
    if fitz is None:
        raise RuntimeError("PyMuPDF (pymupdf) is required")

    tagged = 0
    cleared = 0
    unmatched = 0
    line_cache: dict[int, list[PageLine]] = {}
    width_cache: dict[int, float] = {}

    for seg in segments:
        kind = _get_segment_type(seg)
        layout = _get_source_layout(seg)
        if layout in _CENTER_SKIP_LAYOUTS:
            continue
        if kind not in _CENTER_KINDS:
            if layout == _CENTER_LAYOUT:
                _set_source_layout(seg, None)
                cleared += 1
            continue
        pdf_page = _seg_pdf_page(seg, content_start=content_start)
        if pdf_page is None or pdf_page < 1 or pdf_page > doc.page_count:
            continue
        roman = segment_roman_text(seg)
        if not roman.strip():
            continue
        if pdf_page not in line_cache:
            page = doc[pdf_page - 1]
            line_cache[pdf_page] = page_body_lines(page)
            width_cache[pdf_page] = float(page.rect.width)
        matched = _match_cached_line(line_cache[pdf_page], roman)
        if matched is None:
            unmatched += 1
            if layout == _CENTER_LAYOUT:
                _set_source_layout(seg, None)
                cleared += 1
            continue
        if _is_center_line(matched, width_cache[pdf_page]):
            if layout != _CENTER_LAYOUT:
                _set_source_layout(seg, _CENTER_LAYOUT)
                tagged += 1
        elif layout == _CENTER_LAYOUT:
            _set_source_layout(seg, None)
            cleared += 1

    sandwich = tag_center_layout_by_sandwich(segments)
    return {
        "tagged_center": tagged,
        "cleared_center": cleared,
        "unmatched": unmatched,
        **sandwich,
    }
