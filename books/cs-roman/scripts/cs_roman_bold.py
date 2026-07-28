"""Detect CS Roman PDF fake-bold (fill+stroke) and build inline text runs.

Chaṭṭha Saṅgāyana Roman PDFs use a single VZTime face. Visual bold is drawn as
a stroke overlay (PyMuPDF ``get_texttrace()`` item ``type == 1``) on top of the
normal fill (``type == 0``), not via a Bold font flag.
"""

from __future__ import annotations

import re
from typing import Any

try:
    import fitz
except ImportError:  # pragma: no cover
    fitz = None  # type: ignore

from cs_roman_vztime import vztime_to_unicode

# Markers inserted after extraction; absent from PDF stroke text.
_NOTE_MARKER_RE = re.compile(r"\{\{(?:n\d+|\*|\+|sp1|sp3)\}\}")


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


def bold_span_texts(page: Any) -> list[str]:
    """Unicode strings of stroke (bold) text runs on a PyMuPDF page."""
    if fitz is None:
        raise RuntimeError("PyMuPDF (pymupdf) is required")
    spans: list[str] = []
    for item in page.get_texttrace():
        if item.get("type") != 1:
            continue
        chars = item.get("chars") or []
        if not chars:
            continue
        raw = "".join(chr(c[0]) if c[0] < 0x10000 else "" for c in chars)
        text = vztime_to_unicode(raw).strip()
        if text:
            spans.append(text)
    return spans


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


def find_span_ranges(text: str, needle: str) -> list[tuple[int, int]]:
    """Locate ``needle`` in ``text`` (exact, then whitespace/marker-flexible)."""
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
        return subtract_marker_ranges(text, found)

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
    return subtract_marker_ranges(text, results)


def bold_ranges_in_text(text: str, bold_spans: list[str]) -> list[tuple[int, int]]:
    """Map PDF bold span strings onto ``text``; longer spans win on overlap."""
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
