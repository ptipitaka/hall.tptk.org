#!/usr/bin/env python3
"""Pre-measure CS Roman gāthā กลุ่ม widths to choose bat vs stacked วรรค.

When two วรรค would share one printed line (``\\csromangathabat``) but the
aligned pair exceeds the text block, emit one วรรค per line instead. Decision
is per กลุ่ม: shared left-column width is recomputed from pairs that still fit
so a single long บาท does not inflate the column for shorter neighbours.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

try:
    import fitz
except ImportError:  # pragma: no cover
    fitz = None  # type: ignore

BOOKS = Path(__file__).resolve().parents[1]
_Sarabun = BOOKS / "shared" / "fonts" / "Sarabun-Regular.ttf"

# Matches ``\\csromangathabatgap`` in book-macros.tex (not printing-scaled).
GATHA_BAT_GAP_PT = 20.0
# Body nominal size before Scale in preamble.tex.
_BODY_FONT_PT = 11.0
_PRINTING_FONT_SCALE = 1.031038
_READING_FONT_SCALE = 1.1
# Stack when within this many pt of the edge (callout / glue slack).
_FIT_SLACK_PT = 2.0

# Stock − L − R (bp). Printing margins from pagegeometry-printing.tex.
_TEXTWIDTH_PT = {
    "printing": 165.0 * 72.0 / 25.4 - 73.11 - 58.113,
    "reading": 499.0 - 78.0 - 62.0,
    "sync": 499.0 - 62.6 - 59.4,
}

_MARKER_RE = re.compile(r"\{\{([^}]+)\}\}")


@dataclass(frozen=True)
class GathaBatFitCandidate:
    """One บาท that would otherwise emit ``\\csromangathabat{left}{right}``."""

    seg_index: int
    bat_index: int
    left: str
    right: str


def gatha_fit_textwidth_pt(mode: str) -> float:
    """Text-block width (pt) for generate ``mode``."""
    try:
        return _TEXTWIDTH_PT[mode]
    except KeyError as exc:
        raise ValueError(f"unknown generate mode {mode!r}") from exc


def gatha_fit_fontsize_pt(mode: str) -> float:
    """Body font size (pt) including preamble Scale."""
    scale = _PRINTING_FONT_SCALE if mode == "printing" else _READING_FONT_SCALE
    return _BODY_FONT_PT * scale


def _thai_or_roman_from_text(text: Any) -> str:
    if isinstance(text, list):
        thai = ""
        roman = ""
        for entry in text:
            if not isinstance(entry, dict):
                continue
            val = str(entry.get("value") or "")
            if entry.get("script") == "thai":
                thai = val
            elif entry.get("script") == "roman":
                roman = val
        return thai or roman
    return str(text or "")


def gatha_fit_plain_text(text: Any) -> str:
    """Thai/Roman wak text with markers reduced to approximate print width."""

    def _repl(m: re.Match[str]) -> str:
        key = m.group(1)
        if key == "sb" or key in {"sp1", "sp3"}:
            return ""
        if key.startswith("n") and key[1:].isdigit():
            return "1"  # \\textsuperscript digit proxy
        if key in {"*", "+", "[]", "()"}:
            return "*"
        return ""

    raw = _thai_or_roman_from_text(text)
    return _MARKER_RE.sub(_repl, raw)


@lru_cache(maxsize=1)
def _sarabun_font() -> Any:
    if fitz is None:
        raise RuntimeError("pymupdf is required for gāthā fit measurement")
    if not _Sarabun.is_file():
        raise FileNotFoundError(_Sarabun)
    return fitz.Font(fontfile=str(_Sarabun))


def gatha_fit_string_width_pt(
    text: str,
    *,
    fontsize: float,
    word_space: float,
    preamble_word_space: float = 3.5,
) -> float:
    """Approximate TeX width: glyph advances + WordSpace-scaled interword glue."""
    if not text:
        return 0.0
    _ = preamble_word_space  # reserved: spaceskip factor vs preamble baseline
    font = _sarabun_font()
    native_sp = font.text_length(" ", fontsize=fontsize)
    # fontspec WordSpace multiplies the space glyph; layout.json stores that
    # absolute multiplier (DEFAULT_LAYOUT / volume layout word_space).
    space_pt = native_sp * float(word_space)
    parts = text.split(" ")
    if len(parts) == 1:
        return float(font.text_length(text, fontsize=fontsize))
    glyphs = sum(float(font.text_length(p, fontsize=fontsize)) for p in parts)
    return glyphs + space_pt * (len(parts) - 1)


def resolve_gatha_bat_stack_keys(
    candidates: list[GathaBatFitCandidate],
    *,
    mode: str,
    word_space: float,
    preamble_word_space: float = 3.5,
    bat_gap_pt: float = GATHA_BAT_GAP_PT,
    slack_pt: float = _FIT_SLACK_PT,
) -> frozenset[tuple[int, int]]:
    """Return ``(seg_index, bat_index)`` pairs that must stack (one วรรค/line).

    Iterates: leftcol = max left among still-paired บาท; drop any pair whose
    ``leftcol + gap + right`` exceeds the text block; repeat.
    """
    if not candidates:
        return frozenset()
    tw = gatha_fit_textwidth_pt(mode) - slack_pt
    fs = gatha_fit_fontsize_pt(mode)
    left_w = {
        (c.seg_index, c.bat_index): gatha_fit_string_width_pt(
            c.left,
            fontsize=fs,
            word_space=word_space,
            preamble_word_space=preamble_word_space,
        )
        for c in candidates
    }
    right_w = {
        (c.seg_index, c.bat_index): gatha_fit_string_width_pt(
            c.right,
            fontsize=fs,
            word_space=word_space,
            preamble_word_space=preamble_word_space,
        )
        for c in candidates
    }
    pairing = {(c.seg_index, c.bat_index) for c in candidates}
    stacked: set[tuple[int, int]] = set()
    while pairing:
        leftcol = max(left_w[k] for k in pairing)
        overflow = {
            k
            for k in pairing
            if leftcol + bat_gap_pt + right_w[k] > tw
        }
        if not overflow:
            break
        stacked.update(overflow)
        pairing -= overflow
    return frozenset(stacked)


def collect_gatha_bat_fit_candidates(
    segments: list[dict],
    start: int,
    end: int,
    *,
    wak_is_bat_left,
) -> list[GathaBatFitCandidate]:
    """บาท in ``segments[start:end]`` that generate would emit as bat pairs."""
    out: list[GathaBatFitCandidate] = []
    for si in range(start, end):
        seg = segments[si]
        if not isinstance(seg, dict):
            continue
        kind = seg.get("segment_type") or ""
        if kind not in {"gatha", "gatha_continuation"}:
            continue
        layout = seg.get("source_layout") or "bat_line"
        if layout == "wak_line":
            continue
        bats = seg.get("bats")
        if not isinstance(bats, list):
            continue
        pair_all = layout != "mixed"
        for bi, bat in enumerate(bats):
            if not isinstance(bat, dict):
                continue
            waks = bat.get("waks") or []
            if not isinstance(waks, list) or len(waks) != 2:
                continue
            left_w = waks[0] if isinstance(waks[0], dict) else None
            right_w = waks[1] if isinstance(waks[1], dict) else None
            if left_w is None or right_w is None:
                continue
            if not pair_all and not wak_is_bat_left(left_w.get("text")):
                continue
            left = gatha_fit_plain_text(left_w.get("text"))
            right = gatha_fit_plain_text(right_w.get("text"))
            if not left and not right:
                continue
            out.append(
                GathaBatFitCandidate(
                    seg_index=si,
                    bat_index=bi,
                    left=left,
                    right=right,
                )
            )
    return out


def gatha_group_stack_bat_keys(
    segments: list[dict],
    start: int,
    end: int,
    *,
    mode: str,
    word_space: float,
    wak_is_bat_left,
    preamble_word_space: float = 3.5,
) -> frozenset[tuple[int, int]]:
    """Measure one consecutive gāthā กลุ่ม; return keys that must stack."""
    cands = collect_gatha_bat_fit_candidates(
        segments, start, end, wak_is_bat_left=wak_is_bat_left
    )
    return resolve_gatha_bat_stack_keys(
        cands,
        mode=mode,
        word_space=word_space,
        preamble_word_space=preamble_word_space,
    )
