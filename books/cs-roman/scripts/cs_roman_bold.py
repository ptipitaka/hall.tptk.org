"""Detect CS Roman PDF fake-bold (fill+stroke) and build inline text runs.

Chaṭṭha Saṅgāyana Roman PDFs use a single VZTime face. Visual bold is drawn as
a stroke overlay (PyMuPDF ``get_texttrace()`` item ``type == 1``) on top of the
normal fill (``type == 0``), not via a Bold font flag.

Stroke spans carry a ``bbox``. Extract maps bold onto segment text by
overlapping those boxes with PDF body-line geometry, then locating the span
string inside the covered line's window in the prepared Roman — not by
painting every occurrence of the span string on the page.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

try:
    import fitz
except ImportError:  # pragma: no cover
    fitz = None  # type: ignore

from cs_roman_hanging import (  # noqa: E402
    PageLine,
    _match_cached_line,
    normalize_match_text,
)
from cs_roman_vztime import vztime_to_unicode

# Markers inserted after extraction; absent from PDF stroke text.
_NOTE_MARKER_RE = re.compile(r"\{\{(?:n\d+|\*|\+|sp1|sp3|sb|br)\}\}")

# Vertical / horizontal slack when testing stroke vs body-line overlap (pt).
_LINE_OVERLAP_TOL = 3.0
# Fallback line height when ``PageLine.y1`` is missing.
_DEFAULT_LINE_HEIGHT = 14.0


@dataclass(frozen=True)
class BoldSpan:
    """One stroke-overlay (fake-bold) run with page geometry."""

    text: str
    bbox: tuple[float, float, float, float]  # x0, y0, x1, y1


def marker_ranges(text: str) -> list[tuple[int, int]]:
    """Index ranges of inline ``{{…}}`` markers in ``text``."""
    if not text:
        return []
    return [m.span() for m in _NOTE_MARKER_RE.finditer(text)]


def subtract_marker_ranges(
    text: str,
    ranges: list[tuple[int, int]],
) -> list[tuple[int, int]]:
    """Drop any bold coverage that falls inside inline markers.

    Short PDF stroke spans such as ``1`` must not paint the digit inside
    ``{{sp1}}`` (which would split the marker and corrupt Thai runs).
    """
    markers = marker_ranges(text)
    if not ranges or not markers:
        return _merge_ranges(ranges)
    out: list[tuple[int, int]] = []
    for start, end in ranges:
        pieces = [(start, end)]
        for ms, me in markers:
            next_pieces: list[tuple[int, int]] = []
            for a, b in pieces:
                if b <= ms or a >= me:
                    next_pieces.append((a, b))
                    continue
                if a < ms:
                    next_pieces.append((a, ms))
                if me < b:
                    next_pieces.append((me, b))
            pieces = next_pieces
        out.extend(pieces)
    return _merge_ranges(out)


def bold_span_geoms(page: Any) -> list[BoldSpan]:
    """Stroke (bold) text runs on a PyMuPDF page, with bboxes."""
    if fitz is None:
        raise RuntimeError("PyMuPDF (pymupdf) is required")
    spans: list[BoldSpan] = []
    for item in page.get_texttrace():
        if item.get("type") != 1:
            continue
        chars = item.get("chars") or []
        if not chars:
            continue
        raw = "".join(chr(c[0]) if c[0] < 0x10000 else "" for c in chars)
        text = vztime_to_unicode(raw).strip()
        if not text:
            continue
        bb = item.get("bbox")
        if not bb or len(bb) < 4:
            continue
        spans.append(
            BoldSpan(
                text=text,
                bbox=(float(bb[0]), float(bb[1]), float(bb[2]), float(bb[3])),
            )
        )
    return spans


def bold_span_texts(page: Any) -> list[str]:
    """Unicode strings of stroke (bold) text runs on a PyMuPDF page."""
    return [s.text for s in bold_span_geoms(page)]


def _merge_ranges(ranges: list[tuple[int, int]]) -> list[tuple[int, int]]:
    if not ranges:
        return []
    ordered = sorted(ranges)
    merged: list[list[int]] = [[ordered[0][0], ordered[0][1]]]
    for start, end in ordered[1:]:
        last = merged[-1]
        if start <= last[1]:
            last[1] = max(last[1], end)
        else:
            merged.append([start, end])
    return [(a, b) for a, b in merged]


def _overlaps(start: int, end: int, ranges: list[tuple[int, int]]) -> bool:
    for a, b in ranges:
        if start < b and end > a:
            return True
    return False


def find_span_ranges(
    text: str,
    needle: str,
    *,
    strip_markers: bool = True,
) -> list[tuple[int, int]]:
    """Locate ``needle`` in ``text`` (exact, then whitespace/marker-flexible).

    When ``strip_markers`` is true (default), drop coverage inside ``{{…}}``
    — required so a stroke ``1`` cannot bold the digit in ``{{sp1}}``. Line
    window mapping passes ``strip_markers=False`` so a PDF line that crosses a
    sentence spacer still yields one contiguous window.
    """
    needle = needle.strip()
    if not needle or not text:
        return []

    found: list[tuple[int, int]] = []
    start = 0
    while True:
        i = text.find(needle, start)
        if i < 0:
            break
        found.append((i, i + len(needle)))
        start = i + len(needle)
    if found:
        # Exact ``find`` can hit digits/letters inside ``{{sp1}}`` / ``{{n0}}``.
        return subtract_marker_ranges(text, found) if strip_markers else found

    needle_chars = [c for c in needle if not c.isspace()]
    if not needle_chars:
        return []

    results: list[tuple[int, int]] = []
    i = 0
    n = len(text)
    while i < n:
        marker = _NOTE_MARKER_RE.match(text, i)
        if marker:
            i = marker.end()
            continue
        if text[i].isspace():
            i += 1
            continue

        ti = i
        ni = 0
        match_start: int | None = None
        while ni < len(needle_chars) and ti < n:
            marker = _NOTE_MARKER_RE.match(text, ti)
            if marker:
                ti = marker.end()
                continue
            if text[ti].isspace():
                ti += 1
                continue
            if match_start is None:
                match_start = ti
            if text[ti] != needle_chars[ni]:
                break
            ti += 1
            ni += 1

        if ni == len(needle_chars) and match_start is not None:
            results.append((match_start, ti))
            i = ti
        else:
            i += 1
    return subtract_marker_ranges(text, results) if strip_markers else results


def bold_ranges_in_text(text: str, bold_spans: list[str]) -> list[tuple[int, int]]:
    """Map PDF bold span strings onto ``text``; longer spans win on overlap.

    String-only helper (tests / legacy). Extract prefers
    ``bold_ranges_from_geoms``. Enrich remap uses ``bold_ranges_one_per_span``
    so one stored bold run cannot re-paint every later occurrence.
    """
    if not text or not bold_spans:
        return []
    # Dedupe while preserving longer-first application order.
    unique = sorted(set(bold_spans), key=lambda s: (-len(s.strip()), s))
    accepted: list[tuple[int, int]] = []
    for span in unique:
        for start, end in find_span_ranges(text, span):
            if not _overlaps(start, end, accepted):
                accepted.append((start, end))
    return subtract_marker_ranges(text, _merge_ranges(accepted))


def bold_ranges_one_per_span(
    text: str, spans: list[str]
) -> list[tuple[int, int]]:
    """Map each span string to at most one unused occurrence (list order).

    Used when re-locating stored bold runs after text edits: multiplicity in
    ``spans`` is meaningful, and later plain repeats must stay plain.
    """
    if not text or not spans:
        return []
    accepted: list[tuple[int, int]] = []
    for span in spans:
        needle = (span or "").strip()
        if not needle:
            continue
        for start, end in find_span_ranges(text, needle):
            if not _overlaps(start, end, accepted):
                accepted.append((start, end))
                break
    return subtract_marker_ranges(text, _merge_ranges(accepted))


def _line_y1(line: PageLine) -> float:
    if line.y1 > line.y0:
        return line.y1
    return line.y0 + _DEFAULT_LINE_HEIGHT


def bbox_overlaps_line(
    bbox: tuple[float, float, float, float],
    line: PageLine,
    *,
    tol: float = _LINE_OVERLAP_TOL,
) -> bool:
    """True when a stroke bbox overlaps a body line's rectangle."""
    sx0, sy0, sx1, sy1 = bbox
    ly0 = line.y0
    ly1 = _line_y1(line)
    lx0 = line.x0
    lx1 = line.x1 if line.x1 > line.x0 else line.x0 + 1.0
    if sy1 < ly0 - tol or sy0 > ly1 + tol:
        return False
    if sx1 < lx0 - tol or sx0 > lx1 + tol:
        return False
    return True


def _y_overlap_amount(
    bbox: tuple[float, float, float, float], line: PageLine
) -> float:
    sy0, sy1 = bbox[1], bbox[3]
    ly0, ly1 = line.y0, _line_y1(line)
    return max(0.0, min(sy1, ly1) - max(sy0, ly0))


def _first_match_at_or_after(
    text: str, needle: str, cursor: int
) -> tuple[int, int] | None:
    # Keep markers inside the window so sentence-spacer splits do not truncate
    # a PDF line that continues after ``{{sp1}}``.
    for start, end in find_span_ranges(text, needle, strip_markers=False):
        if start >= cursor:
            return start, end
    return None


def cover_lines_for_text(
    page_lines: list[PageLine], text: str
) -> list[PageLine]:
    """Body lines whose content covers ``text`` in reading order."""
    if not page_lines or not text:
        return []
    first = _match_cached_line(page_lines, text)
    if first is None:
        return []
    try:
        i0 = next(
            i
            for i, ln in enumerate(page_lines)
            if ln.y0 == first.y0
            and ln.x0 == first.x0
            and ln.text == first.text
        )
    except StopIteration:
        return []

    covered: list[PageLine] = []
    cursor = 0
    for line in page_lines[i0:]:
        needle = normalize_match_text(line.text)
        if not needle:
            continue
        hit: tuple[int, int] | None = None
        # Prefer full line; shorten when the PDF line is longer than the
        # remaining prepared text (page-break / next-item spill).
        for size in (
            len(needle),
            max(20, int(len(needle) * 0.7)),
            max(12, int(len(needle) * 0.4)),
        ):
            n = needle[:size]
            if len(n) < 8 and size < len(needle):
                continue
            hit = _first_match_at_or_after(text, n, cursor)
            if hit is not None:
                break
        if hit is None:
            break
        start, end = hit
        if start < cursor - 5:
            break
        covered.append(line)
        cursor = end
        if cursor >= len(text):
            break
    return covered


def line_windows_in_text(
    prepared: str, lines: list[PageLine]
) -> list[tuple[PageLine, int, int]]:
    """Map covered lines to ``[start, end)`` windows inside ``prepared``."""
    windows: list[tuple[PageLine, int, int]] = []
    cursor = 0
    for line in lines:
        needle = normalize_match_text(line.text)
        if not needle:
            continue
        hit: tuple[int, int] | None = None
        for size in (
            len(needle),
            max(20, int(len(needle) * 0.7)),
            max(12, int(len(needle) * 0.4)),
        ):
            n = needle[:size]
            if len(n) < 8 and size < len(needle):
                continue
            hit = _first_match_at_or_after(prepared, n, cursor)
            if hit is not None:
                break
        if hit is None:
            break
        start, end = hit
        windows.append((line, start, end))
        cursor = end
    return windows


def _pick_match_by_x(
    matches: list[tuple[int, int]],
    line: PageLine,
    bbox: tuple[float, float, float, float],
) -> tuple[int, int]:
    """Choose the match whose relative x best fits the stroke bbox center."""
    if len(matches) == 1:
        return matches[0]
    span_cx = (bbox[0] + bbox[2]) / 2.0
    line_w = max((line.x1 if line.x1 > line.x0 else line.x0 + 1.0) - line.x0, 1.0)
    target_frac = (span_cx - line.x0) / line_w
    win_start = matches[0][0]
    win_end = matches[-1][1]
    win_w = max(win_end - win_start, 1)

    def score(m: tuple[int, int]) -> float:
        mid = (m[0] + m[1]) / 2.0
        frac = (mid - win_start) / win_w
        return abs(frac - target_frac)

    return min(matches, key=score)


def _safe_unique_bold_ranges(
    text: str, span_texts: list[str]
) -> list[tuple[int, int]]:
    """Fallback when line cover fails: only spans that occur once in ``text``."""
    if not text or not span_texts:
        return []
    unique = sorted(set(span_texts), key=lambda s: (-len(s.strip()), s))
    accepted: list[tuple[int, int]] = []
    for span in unique:
        matches = find_span_ranges(text, span)
        if len(matches) != 1:
            continue
        start, end = matches[0]
        if not _overlaps(start, end, accepted):
            accepted.append((start, end))
    return subtract_marker_ranges(text, _merge_ranges(accepted))


def _stroke_covers_line_width(
    span: BoldSpan,
    line: PageLine,
    *,
    min_frac: float = 0.5,
) -> bool:
    """True when the stroke covers most of the body line's horizontal span."""
    sx0, sx1 = span.bbox[0], span.bbox[2]
    lx0 = line.x0
    lx1 = line.x1 if line.x1 > line.x0 else line.x0 + 1.0
    line_w = max(lx1 - lx0, 1.0)
    overlap = max(0.0, min(sx1, lx1) - max(sx0, lx0))
    return overlap / line_w >= min_frac


def bold_ranges_from_geoms(
    prepared: str,
    spans: list[BoldSpan],
    page_lines: list[PageLine],
) -> list[tuple[int, int]]:
    """Map stroke spans onto ``prepared`` using body-line bbox overlap.

    A stroke may only paint occurrences that fall in the union of overlapping
    line windows — so a bold lemma does not paint a later plain repeat on a
    non-overlapping wrap line. The union (not a single line) is required
    because texttrace often emits multi-line stroke strings with a tall bbox
    that straddles wraps (e.g. full-line sikkhāpada rules).
    """
    if not prepared or not spans:
        return []
    covered = cover_lines_for_text(page_lines, prepared)
    if not covered:
        return _safe_unique_bold_ranges(prepared, [s.text for s in spans])

    windows = line_windows_in_text(prepared, covered)
    if not windows:
        return _safe_unique_bold_ranges(prepared, [s.text for s in spans])

    accepted: list[tuple[int, int]] = []
    ordered = sorted(spans, key=lambda s: (s.bbox[1], s.bbox[0], -len(s.text)))
    for span in ordered:
        needle = span.text.strip()
        if not needle:
            continue
        cands = [
            (ln, a, b)
            for ln, a, b in windows
            if bbox_overlaps_line(span.bbox, ln)
        ]
        if not cands:
            continue
        union_a = min(a for _, a, _b in cands)
        union_b = max(b for _, _a, b in cands)
        primary_ln = max(
            cands, key=lambda w: (_y_overlap_amount(span.bbox, w[0]), w[2] - w[1])
        )[0]
        slack = 4
        matches = [
            (s, e)
            for s, e in find_span_ranges(prepared, needle)
            if s < union_b + slack and e > union_a - slack
        ]
        if not matches:
            # Full-line strokes can disagree with prepared text (glued
            # footnote digits, quote normalization). If the stroke covers
            # most of a line's width, bold those overlapping windows.
            for ln, a, b in cands:
                if not _stroke_covers_line_width(span, ln):
                    continue
                if not _overlaps(a, b, accepted):
                    accepted.append((a, b))
            continue
        inside = [
            m
            for m in matches
            if m[0] >= union_a - slack and m[1] <= union_b + slack
        ]
        chosen = _pick_match_by_x(inside or matches, primary_ln, span.bbox)
        if _overlaps(chosen[0], chosen[1], accepted):
            continue
        accepted.append(chosen)
    return subtract_marker_ranges(prepared, _merge_ranges(accepted))


def substantial_bold_ranges(
    text: str,
    ranges: list[tuple[int, int]],
    *,
    min_coverage: float = 0.6,
) -> list[tuple[int, int]]:
    """Keep bold ranges only when they cover most of ``text``.

    Used for ``niṭṭhitaṃ`` closers: major ends are full-line stroke-bold in
    the source PDF. Short bold lemmas from nearby rule text must not paint
    a fragment of a plain closer (e.g. ``Vehāsakuṭi`` inside
    ``Vehāsakuṭisikkhāpadaṃ niṭṭhitaṃ…``).
    """
    if not text or not ranges:
        return []
    # Ignore extract markers / whitespace when measuring coverage.
    plain = _NOTE_MARKER_RE.sub("", text)
    plain_len = sum(1 for c in plain if not c.isspace())
    if plain_len <= 0:
        return []
    bold_chars = 0
    for start, end in ranges:
        chunk = text[start:end]
        chunk = _NOTE_MARKER_RE.sub("", chunk)
        bold_chars += sum(1 for c in chunk if not c.isspace())
    if bold_chars / plain_len < min_coverage:
        return []
    return ranges


def unbold_ranges_in_runs(
    runs: list[dict[str, Any]] | None,
    ranges: list[tuple[int, int]],
) -> list[dict[str, Any]] | None:
    """Clear bold on character ranges; collapse adjacent same-flag runs.

    ``ranges`` are ``[start, end)`` into ``join(runs[].value)``. Idempotent
    when those spans are already unbold. Returns ``None`` when no bold remains.
    """
    if not runs or not ranges:
        return runs
    pieces: list[tuple[str, bool]] = []
    for run in runs:
        if not isinstance(run, dict):
            continue
        value = str(run.get("value") or "")
        if value:
            pieces.append((value, bool(run.get("bold"))))
    if not pieces:
        return runs
    joined = "".join(value for value, _ in pieces)
    flags: list[bool] = []
    for value, bold in pieces:
        flags.extend([bold] * len(value))
    changed = False
    n = len(joined)
    for start, end in ranges:
        a = max(0, min(start, n))
        b = max(a, min(end, n))
        for i in range(a, b):
            if flags[i]:
                flags[i] = False
                changed = True
    if not changed:
        return runs
    out: list[dict[str, Any]] = []
    pos = 0
    while pos < n:
        bold = flags[pos]
        end = pos + 1
        while end < n and flags[end] == bold:
            end += 1
        out.append({"value": joined[pos:end], "bold": bold})
        pos = end
    if not any(r["bold"] for r in out):
        return None
    return out


def ranges_to_runs(text: str, ranges: list[tuple[int, int]]) -> list[dict[str, Any]] | None:
    """Collapse bold ranges into runs; ``None`` when there is no bold."""
    merged = subtract_marker_ranges(text, ranges)
    if not merged or not text:
        return None
    runs: list[dict[str, Any]] = []
    pos = 0
    for start, end in merged:
        start = max(0, min(start, len(text)))
        end = max(start, min(end, len(text)))
        if pos < start:
            runs.append({"value": text[pos:start], "bold": False})
        if start < end:
            runs.append({"value": text[start:end], "bold": True})
        pos = end
    if pos < len(text):
        runs.append({"value": text[pos:], "bold": False})
    if not any(r["bold"] for r in runs):
        return None
    joined = "".join(r["value"] for r in runs)
    if joined != text:
        return None
    return runs


def clip_ranges(
    ranges: list[tuple[int, int]],
    *,
    length: int,
) -> list[tuple[int, int]]:
    """Keep ranges inside ``[0, length)``."""
    out: list[tuple[int, int]] = []
    for start, end in ranges:
        start = max(0, start)
        end = min(length, end)
        if start < end:
            out.append((start, end))
    return _merge_ranges(out)
