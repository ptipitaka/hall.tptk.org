#!/usr/bin/env python3
"""
Generate TeX body from cs-roman segments JSON (Thai script).

  python books/cs-roman/scripts/generate_cs_roman_tex.py --volume 01Vin01
  python books/cs-roman/scripts/generate_cs_roman_tex.py --volume 01Vin01 --mode printing
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import NamedTuple

from paths import BOOKS, OUTPUT_DIR, ensure_import_paths

ensure_import_paths()

from cs_roman_segments import (  # noqa: E402
    DEFAULT_LAYOUT,
    doc_layout,
    doc_page_layout_reading,
    doc_reading_break_before_orders,
    effective_layout,
    effective_word_space,
    load_document,
    seg_flags,
    seg_notes,
    seg_symbol_notes,
    seg_word_space,
)
from cs_roman_sandhi_breaks import (  # noqa: E402
    DEFAULT_MIN_THAI_LEN,
    ensure_sandhi_break_cache,
    inject_soft_breaks_in_thai,
    merge_break_maps,
)
from cs_roman_text import (  # noqa: E402
    SECTION_RULE_FLAG,
    roman_to_thai,
    roman_value_from_text_field,
    split_trailing_section_rule,
    thai_digits_to_arabic,
    uses_sentence_spacer,
)
from cs_roman_transforms import (  # noqa: E402
    TransformRule,
    apply_transforms,
    collect_transform_soft_breaks,
    load_volume_transforms,
    segment_context,
)

NOTE_MARKER_RE = re.compile(r"\{\{(n(\d+)|\*|\+|\[\]|\(\)|sp1|sp3|sb)\}\}")

# Sandhi soft-break cache (roman → surface chunks); empty until ensure/load.
# ``_SANDHI_CACHE`` = DPD + curated overrides; ``_SANDHI_BREAKS`` = active map
# (cache merged with soft_breaks from the current volume's transform rules).
_SANDHI_CACHE: dict[str, list[str]] | None = None
_SANDHI_BREAKS: dict[str, list[str]] | None = None
_SANDHI_ENABLED = True


def get_sandhi_breaks() -> dict[str, list[str]]:
    """Lazy-load / auto-build ``shared/sandhi_breaks.json`` for all generate modes."""
    global _SANDHI_BREAKS, _SANDHI_CACHE
    if _SANDHI_BREAKS is not None:
        return _SANDHI_BREAKS
    if _SANDHI_CACHE is None:
        _SANDHI_CACHE = ensure_sandhi_break_cache(quiet=False)
    _SANDHI_BREAKS = _SANDHI_CACHE
    return _SANDHI_BREAKS


def refresh_sandhi_with_transforms(rules: list[TransformRule]) -> None:
    """Merge transform-rule ``soft_breaks`` onto the DPD/overrides cache.

    Call once per generate (and from ``build_body`` so unit tests see the same
    map). Later volume runs replace the extras; they do not accumulate.
    """
    global _SANDHI_BREAKS, _SANDHI_CACHE
    if not _SANDHI_ENABLED:
        return
    if _SANDHI_CACHE is None:
        _SANDHI_CACHE = ensure_sandhi_break_cache(quiet=False)
    extra = collect_transform_soft_breaks(rules)
    _SANDHI_BREAKS = (
        merge_break_maps(_SANDHI_CACHE, extra) if extra else _SANDHI_CACHE
    )


def apply_sandhi_soft_breaks(thai: str, roman: str) -> str:
    """Insert ``{{sb}}`` at DPD sandhi boundaries for long tokens."""
    if not _SANDHI_ENABLED or not thai or not roman:
        return thai
    return inject_soft_breaks_in_thai(
        thai,
        roman,
        get_sandhi_breaks(),
        min_thai_len=DEFAULT_MIN_THAI_LEN,
    )


# Short end-of-section formulas (Thai body): lesser structural band, not prose.
_CLOSER_FORMULA_RE = re.compile(
    r"(?:นิฏฺฐิต[าโตํ]|สมตฺตํ)\s*\.?$"
)
_TEX_FOOTNOTE_RE = re.compile(r"\\footnote\{[^{}]*\}")
_TEX_TEXTBF_RE = re.compile(r"\\textbf\{([^{}]*)\}")
# Paragraph / folio ranges ``(12-13)`` / ``(12- 13)`` — TeX may break after ``-``.
_PAREN_NUM_RANGE_RE = re.compile(r"\(\d+\s*-\s*\d+\)")
_PAREN_NUM_RANGE_SPACE_RE = re.compile(r"\((\d+)\s*-\s*(\d+)\)")

_TEX_ESCAPE = str.maketrans(
    {
        "\\": r"\textbackslash{}",
        "{": r"\{",
        "}": r"\}",
        "%": r"\%",
        "#": r"\#",
        "&": r"\&",
        "_": r"\_",
        "^": r"\^{}",
        "~": r"\textasciitilde{}",
        "$": r"\$",
        # CS Roman en-dash; Sarabun glyph is short — see \csromandash.
        "\u2013": r"\csromandash{}",
        # PDF horizontal line extension (legacy / pre-normalize); same macro.
        "\u23af": r"\csromandash{}",
    }
)


# Font-load WordSpace in shared/style/preamble.tex (fontspec baseline glue).
# Must NOT be tied to DEFAULT_LAYOUT: layout.json / DEFAULT_LAYOUT are absolute
# WordSpace targets that overwrite the preamble via \spaceskip scaling.
_PREAMBLE_WORD_SPACE_RE = re.compile(
    r"^\s*WordSpace\s*=\s*([0-9]+(?:\.[0-9]+)?)\s*,?\s*$",
    re.MULTILINE,
)
_PREAMBLE_TEX = BOOKS / "shared" / "style" / "preamble.tex"


def read_preamble_word_space(path: Path | None = None) -> float:
    """Return ``WordSpace`` from preamble.tex (font-load baseline)."""
    preamble = path if path is not None else _PREAMBLE_TEX
    text = preamble.read_text(encoding="utf-8")
    match = _PREAMBLE_WORD_SPACE_RE.search(text)
    if match is None:
        raise RuntimeError(f"WordSpace not found in {preamble}")
    return float(match.group(1))


PREAMBLE_WORD_SPACE = read_preamble_word_space()


def escape_tex(text: str) -> str:
    """Escape TeX specials; keep ``(N-N)`` ranges on one line via ``\\mbox``.

    Collapse spaces around the range hyphen (``(12- 13)`` → ``(12-13)``) so
    ``\\spaceskip`` does not open a wide word-gap inside the marker.
    """
    escaped = text.translate(_TEX_ESCAPE)

    def _protect_range(m: re.Match[str]) -> str:
        tight = _PAREN_NUM_RANGE_SPACE_RE.sub(r"(\1-\2)", m.group(0))
        return rf"\mbox{{{tight}}}"

    return _PAREN_NUM_RANGE_RE.sub(_protect_range, escaped)


def format_number(value: float | int | str) -> str:
    """TeX-safe numeric factor (no trailing .0 noise)."""
    f = float(value)
    if f == int(f):
        return str(int(f))
    return f"{f:g}"


def format_word_space(value: float | int) -> str:
    return format_number(value)


def word_space_factor(target: float | int) -> str:
    """Scale so ``spaceskip = factor × fontdimen`` matches absolute WordSpace.

    ``target`` is the absolute layout/DEFAULT value; divide by the font-load
    ``WordSpace`` in preamble.tex (not by DEFAULT_LAYOUT).
    """
    return format_number(float(target) / PREAMBLE_WORD_SPACE)


def layout_apply_args(layout: dict) -> str:
    """Seven braced args shared by ``\\csromanlayoutapply`` / reading helpers."""
    ws = layout.get("word_space", DEFAULT_LAYOUT["word_space"])
    return (
        f"{{{word_space_factor(ws)}}}"
        f"{{{format_number(layout.get('line_space', DEFAULT_LAYOUT['line_space']))}}}"
        f"{{{layout.get('par_indent', DEFAULT_LAYOUT['par_indent'])}}}"
        f"{{{layout.get('par_skip', DEFAULT_LAYOUT['par_skip'])}}}"
        f"{{{layout.get('gatha_stanza_skip', DEFAULT_LAYOUT['gatha_stanza_skip'])}}}"
        f"{{{layout.get('gatha_indent', DEFAULT_LAYOUT['gatha_indent'])}}}"
        f"{{{layout.get('emergency_stretch', DEFAULT_LAYOUT['emergency_stretch'])}}}"
    )


def layout_apply_command(layout: dict) -> str:
    """Emit ``\\csromanlayoutapply`` for a full effective layout dict."""
    return rf"\csromanlayoutapply{layout_apply_args(layout)}%"


def reading_page_layout_setup_lines(doc: dict, volume_layout: dict) -> list[str]:
    """TeX setup for ``page_layout_reading_mode`` (physical pages, not ฉ.N)."""
    lines = [
        "% Reading physical-page layout (layout.json ``page_layout_reading_mode``).",
        rf"\csromanreadingpagelayoutvolume{layout_apply_args(volume_layout)}%",
    ]
    for page in sorted(doc_page_layout_reading(doc)):
        eff = effective_layout(doc, page, reading=True)
        lines.append(
            rf"\csromanreadingpagelayoutdef{{{page}}}{layout_apply_args(eff)}%"
        )
    lines.append(r"\csromanreadingpagelayoutenable")
    lines.append("")
    return lines


def wrap_word_space(
    seg: dict,
    tex_lines: list[str],
    *,
    page_word_space: float | int,
    doc: dict | None = None,
    segment_word_space: float | int | None = None,
) -> list[str]:
    """Wrap TeX lines so interword glue matches segment ``word_space``.

    fontspec rejects ``WordSpace`` in ``\\addfontfeatures``, so we scale
    ``\\spaceskip`` relative to the preamble-loaded font glue instead.
    Only emits when the segment override differs from the page/volume value
    already applied by ``\\csromanlayoutapply``.

    Override source: legacy segment ``word_space`` (via ``doc``), or an
    explicit ``segment_word_space`` value.
    """
    if segment_word_space is not None:
        ws = segment_word_space
    elif doc is not None:
        ws = seg_word_space(doc, seg)
    else:
        ws = seg_word_space(seg)
    if ws is None or not tex_lines:
        return tex_lines
    if float(ws) == float(page_word_space):
        return tex_lines
    return [
        rf"\csromanwordspacebegin{{{word_space_factor(ws)}}}%",
        *tex_lines,
        r"\csromanwordspaceend",
    ]


def thai_entry_of_text_field(text: object) -> dict | None:
    """Thai multi-script entry dict, if present."""
    if isinstance(text, list):
        for entry in text:
            if isinstance(entry, dict) and entry.get("script") == "thai":
                return entry
        if text and isinstance(text[0], dict) and "value" in text[0]:
            return text[0]
    return None


def thai_of_text_field(text: object) -> str:
    """Thai string from multi-script list or roman str (stored / legacy)."""
    entry = thai_entry_of_text_field(text)
    if entry is not None:
        return thai_digits_to_arabic(str(entry.get("value") or ""))
    if isinstance(text, str):
        return roman_to_thai(text)
    return ""


def thai_runs_of_text_field(text: object) -> list[dict] | None:
    """Optional Thai ``runs`` from the thai script entry."""
    entry = thai_entry_of_text_field(text)
    if entry is None:
        return None
    runs = entry.get("runs")
    if isinstance(runs, list) and runs:
        return [
            {**r, "value": thai_digits_to_arabic(str(r.get("value") or ""))}
            if isinstance(r, dict)
            else r
            for r in runs
        ]
    return None


def publication_roman_of_text_field(
    text: object,
    rules: list[TransformRule],
    *,
    page: int,
    order: int,
    segment_type: str,
    note_base_index: int = 0,
    emit_footnotes: bool = True,
) -> tuple[str, str, list[str]]:
    """Apply publication transforms once.

    Returns ``(original_roman, new_roman, extra_notes)``.
    """
    roman = roman_value_from_text_field(text)
    new_roman, extra = apply_transforms(
        roman,
        rules,
        page=page,
        order=order,
        segment_type=segment_type,
        note_base_index=note_base_index,
        emit_footnotes=emit_footnotes,
    )
    return roman, new_roman, extra


def publication_thai_of_text_field(
    text: object,
    rules: list[TransformRule],
    *,
    page: int,
    order: int,
    segment_type: str,
    note_base_index: int = 0,
    emit_footnotes: bool = True,
) -> tuple[str, list[dict] | None, str, list[str]]:
    """Thai value (+ optional runs) after publication transforms on Roman.

    When transforms do not change the Roman string, reuse stored Thai / runs.
    When they do, re-derive Thai via ``roman_to_thai`` (bold runs dropped).

    Returns ``(thai, runs_or_none, new_roman, extra_notes)``.
    """
    roman, new_roman, extra = publication_roman_of_text_field(
        text,
        rules,
        page=page,
        order=order,
        segment_type=segment_type,
        note_base_index=note_base_index,
        emit_footnotes=emit_footnotes,
    )
    if new_roman == roman:
        return (
            thai_of_text_field(text),
            thai_runs_of_text_field(text),
            new_roman,
            extra,
        )
    return roman_to_thai(new_roman), None, new_roman, extra


def transform_note_list(
    notes: list,
    rules: list[TransformRule],
    *,
    page: int,
    order: int,
    segment_type: str,
) -> list:
    """Transform note bodies; never inject editorial footnotes into notes."""
    out: list[str] = []
    for n in notes:
        text, _extra = apply_transforms(
            str(n or ""),
            rules,
            page=page,
            order=order,
            segment_type=segment_type,
            emit_footnotes=False,
        )
        out.append(text)
    return out


def transform_symbol_notes(
    symbol_notes: dict,
    rules: list[TransformRule],
    *,
    page: int,
    order: int,
    segment_type: str,
) -> dict:
    out: dict = {}
    for key, value in symbol_notes.items():
        text, _extra = apply_transforms(
            str(value or ""),
            rules,
            page=page,
            order=order,
            segment_type=segment_type,
            emit_footnotes=False,
        )
        out[key] = text
    return out


def note_to_thai(roman: str) -> str:
    """Transliterate note body; keep Arabic digits (catalog-style refs).

    Footnote prose is abbreviation-heavy (``Saṃ 1. 446``); do not inject
    sentence-stop ``{{sp1}}`` spacers — TeX uses ``\\frenchspacing`` instead.
    """
    if not roman:
        return ""
    # Same CS→Thai letter rules as body (incl. -pa- → ฯเปฯ), no stop gaps.
    return roman_to_thai(roman, normalize_spacing=False)


def apply_notes_to_thai(
    thai: str,
    *,
    notes: list,
    symbol_notes: dict,
    emitted_symbol_notes: set[str] | None = None,
    apply_sentence_spacer: bool = True,
) -> tuple[str, bool]:
    """Embed footnotes into Thai body; return (tex, had_section_rule).

    When ``emitted_symbol_notes`` is provided, the first ``{{*}}`` / ``{{+}}``
    with a note body emits ``\\csromansymbolfootnote``; later callouts that
    share the same mark emit ``\\csromansymbolmark`` only.

    ``{{sp1}}`` / ``{{sp3}}`` → ``\\csromanspacer`` only when
    ``apply_sentence_spacer`` is true (body). Headings drop the marker and
    keep ordinary word spacing.
    """
    thai = thai_digits_to_arabic(thai)
    thai, had_rule = split_trailing_section_rule(thai)
    parts: list[str] = []
    last = 0
    for m in NOTE_MARKER_RE.finditer(thai):
        parts.append(escape_tex(thai[last : m.start()]))
        token = m.group(1)
        if token in {"sp1", "sp3"}:
            if apply_sentence_spacer:
                # ``\\csromanspacer`` after visible stop (``{{sp1}}``; pot-ma-gyi uses two).
                # ``{{sp3}}`` kept as legacy alias.
                parts.append(r"\csromanspacer{}")
            elif m.end() < len(thai) and thai[m.end()].isspace():
                parts.append("")
            else:
                parts.append(" ")
        elif token == "sb":
            # Explicit soft hyphen at a sandhi / compound boundary (DPD).
            # Works even with ``hyphenrules=nohyphenation``.
            parts.append(r"\-")
        elif token in {"*", "+", "[]", "()"}:
            note = symbol_notes.get(token)
            already = (
                emitted_symbol_notes is not None and token in emitted_symbol_notes
            )
            # Apparatus marks: ``[ ]`` / ``( )`` for empty bracket/paren notes.
            if token == "[]":
                fn_mark = "[ ]"
            elif token == "()":
                fn_mark = "( )"
            else:
                fn_mark = token
            if note and not already:
                if emitted_symbol_notes is not None:
                    emitted_symbol_notes.add(token)
                body = escape_tex(note_to_thai(note))
                parts.append(rf"\csromansymbolfootnote{{{fn_mark}}}{{{body}}}")
            else:
                # Shared callout (same * / + / [] / () note) or mark without body.
                parts.append(rf"\csromansymbolmark{{{fn_mark}}}")
        else:
            idx = int(m.group(2))
            note = notes[idx] if 0 <= idx < len(notes) else f"[missing note {idx}]"
            parts.append(r"\footnote{" + escape_tex(note_to_thai(note)) + "}")
        last = m.end()
    parts.append(escape_tex(thai[last:]))
    return "".join(parts), had_rule


def apply_notes_to_thai_runs(
    runs: list[dict],
    *,
    notes: list,
    symbol_notes: dict,
    emitted_symbol_notes: set[str] | None = None,
    apply_sentence_spacer: bool = True,
) -> tuple[str, bool]:
    """Like ``apply_notes_to_thai`` but wrap bold runs in ``\\textbf``."""
    parts: list[str] = []
    had_rule = False
    for run in runs:
        piece, rule = apply_notes_to_thai(
            str(run.get("value") or ""),
            notes=notes,
            symbol_notes=symbol_notes,
            emitted_symbol_notes=emitted_symbol_notes,
            apply_sentence_spacer=apply_sentence_spacer,
        )
        had_rule = had_rule or rule
        if not piece:
            continue
        if run.get("bold"):
            parts.append(r"\textbf{" + piece + "}")
        else:
            parts.append(piece)
    return "".join(parts), had_rule


def build_body(
    seg: dict,
    rules: list[TransformRule] | None = None,
    *,
    emitted_symbol_notes: set[str] | None = None,
) -> tuple[str, bool]:
    """Thai body with notes → footnotes; TeX-escaped outside footnotes.

    ``{{nN}}`` → numbered ``\\footnote``; ``{{*}}``/``{{+}}`` → symbol footnotes
    that do not advance the numbered counter; ``{{sp1}}`` / legacy ``{{sp3}}``
    → ``\\csromanspacer`` on body segments only (not titles / chapters).

    Publication transforms (including editorial footnotes) run on Roman before
    Thai transliteration and sandhi soft breaks.

    Also returns whether a CS end-of-section rule should be drawn (from flag or
    leftover ``_____`` tails from PDF extraction).
    """
    rules = rules or []
    refresh_sandhi_with_transforms(rules)
    page, order, kind = segment_context(seg)
    apply_sp = uses_sentence_spacer(kind)
    notes = transform_note_list(
        seg_notes(seg), rules, page=page, order=order, segment_type=kind
    )
    symbol_notes = transform_symbol_notes(
        seg_symbol_notes(seg),
        rules,
        page=page,
        order=order,
        segment_type=kind,
    )
    thai, runs, roman, extra = publication_thai_of_text_field(
        seg.get("text"),
        rules,
        page=page,
        order=order,
        segment_type=kind,
        note_base_index=len(notes),
        emit_footnotes=True,
    )
    notes = [*notes, *extra]
    if runs:
        # Soft-break markers may split bold runs; fall back to plain Thai.
        joined = "".join(str(r.get("value") or "") for r in runs if isinstance(r, dict))
        marked = apply_sandhi_soft_breaks(joined, roman)
        if marked != joined:
            body, had_rule = apply_notes_to_thai(
                marked,
                notes=notes,
                symbol_notes=symbol_notes,
                emitted_symbol_notes=emitted_symbol_notes,
                apply_sentence_spacer=apply_sp,
            )
        else:
            body, had_rule = apply_notes_to_thai_runs(
                runs,
                notes=notes,
                symbol_notes=symbol_notes,
                emitted_symbol_notes=emitted_symbol_notes,
                apply_sentence_spacer=apply_sp,
            )
    else:
        body, had_rule = apply_notes_to_thai(
            apply_sandhi_soft_breaks(thai, roman),
            notes=notes,
            symbol_notes=symbol_notes,
            emitted_symbol_notes=emitted_symbol_notes,
            apply_sentence_spacer=apply_sp,
        )
    if SECTION_RULE_FLAG in seg_flags(seg):
        had_rule = True
    return body, had_rule


def _gatha_wak_thais(
    seg: dict,
    rules: list[TransformRule],
    *,
    note_base_index: int = 0,
) -> tuple[list[str], list[str]]:
    """Ordered วรรค Thai strings from nested bats, or one legacy line.

    Returns ``(lines, extra_notes)`` from editorial transform footnotes.
    """
    page, order, kind = segment_context(seg)
    extras: list[str] = []
    bats = seg.get("bats")
    if isinstance(bats, list) and bats:
        out: list[str] = []
        for bat in bats:
            for wak in bat.get("waks") or []:
                thai, _runs, roman, extra = publication_thai_of_text_field(
                    wak.get("text"),
                    rules,
                    page=page,
                    order=order,
                    segment_type=kind,
                    note_base_index=note_base_index + len(extras),
                    emit_footnotes=True,
                )
                extras.extend(extra)
                out.append(apply_sandhi_soft_breaks(thai, roman))
        return out, extras
    thai, _runs, roman, extra = publication_thai_of_text_field(
        seg.get("text"),
        rules,
        page=page,
        order=order,
        segment_type=kind,
        note_base_index=note_base_index,
        emit_footnotes=True,
    )
    extras.extend(extra)
    marked = apply_sandhi_soft_breaks(thai, roman)
    return ([marked] if marked else []), extras


_GATHA_KINDS = frozenset({"gatha", "gatha_continuation"})
_CONTINUATION_KINDS = frozenset({"prose_continuation", "verse_continuation"})
_PROSE_FLOW_KINDS = frozenset(
    {"prose", "verse", "prose_continuation", "verse_continuation"}
)
# "reading" is retained for internal/test use only (printing shares the same
# reading-flow body via generate_reading_lines); the CLI and build scripts
# expose only sync + printing. See README.
_GENERATE_MODES = frozenset({"sync", "reading", "printing"})
_READING_LIKE_MODES = frozenset({"reading", "printing"})


def is_gatha_segment(seg: dict | None) -> bool:
    if not seg:
        return False
    return (seg.get("segment_type") or "") in _GATHA_KINDS


def folio_tex(page: int) -> str:
    """Reading-mode outer-margin citation for source printed page ``page``."""
    return rf"\csromanfolio{{{page}}}"


def with_folio(body: str, page: int, last_folio_marked: int | None) -> tuple[str, int]:
    """Prefix ``\\csromanfolio`` when ``page`` differs from the last marked folio."""
    if last_folio_marked == page:
        return body, last_folio_marked
    return folio_tex(page) + body, page


def join_reading_flow_bodies(
    chunks: list[tuple[int, str]],
    *,
    last_folio_marked: int | None,
) -> tuple[str, int]:
    """Join prose/continuation bodies; mark folio at each source-page change."""
    parts: list[str] = []
    marked = last_folio_marked
    for page, body in chunks:
        piece, marked = with_folio(body, page, marked)
        if parts:
            parts.append(" ")
        parts.append(piece)
    return "".join(parts), marked


def _strip_note_markers_for_measure(thai: str) -> str:
    """Drop footnote bodies; keep * / + mark chars for approximate width."""

    def repl(m: re.Match[str]) -> str:
        token = m.group(1)
        if token in {"*", "+"}:
            return token
        return ""

    return NOTE_MARKER_RE.sub(repl, thai)


def _thai_with_sandhi(
    text_field: object,
    rules: list[TransformRule],
    *,
    page: int,
    order: int,
    segment_type: str,
    note_base_index: int = 0,
) -> tuple[str, list[dict] | None, list[str]]:
    """Publication Thai (+ runs) with sandhi ``{{sb}}`` markers applied.

    Returns ``(thai_or_marked, runs_or_none, extra_notes)``.
    """
    thai, runs, roman, extra = publication_thai_of_text_field(
        text_field,
        rules,
        page=page,
        order=order,
        segment_type=segment_type,
        note_base_index=note_base_index,
        emit_footnotes=True,
    )
    if runs:
        joined = "".join(
            str(r.get("value") or "") for r in runs if isinstance(r, dict)
        )
        marked = apply_sandhi_soft_breaks(joined, roman)
        if marked != joined:
            return marked, None, extra
        return thai, runs, extra
    return apply_sandhi_soft_breaks(thai, roman), None, extra


class GathaBatPrintedLine(NamedTuple):
    """One bat_line printed บาท: left วรรค (comma) + right วรรค."""

    left: str | list[dict]
    right: str | list[dict]


GathaPrintedLine = str | list[dict] | GathaBatPrintedLine


def _gatha_wak_payload(
    thai: str, runs: list[dict] | None
) -> str | list[dict]:
    return runs if runs is not None else thai


def _gatha_printed_lines(
    seg: dict,
    rules: list[TransformRule],
    *,
    note_base_index: int = 0,
) -> tuple[list[GathaPrintedLine], list[str]]:
    """Raw printed lines for one บท (Thai string, bold runs, or bat pair).

    Returns ``(printed_lines, extra_notes)`` from editorial transform footnotes.
    """
    page, order, kind = segment_context(seg)
    layout = seg.get("source_layout") or "bat_line"
    bats = seg.get("bats")
    printed: list[GathaPrintedLine] = []
    extras: list[str] = []
    if isinstance(bats, list) and bats:
        if layout == "wak_line":
            for bat in bats:
                for wak in bat.get("waks") or []:
                    thai, runs, extra = _thai_with_sandhi(
                        wak.get("text"),
                        rules,
                        page=page,
                        order=order,
                        segment_type=kind,
                        note_base_index=note_base_index + len(extras),
                    )
                    extras.extend(extra)
                    if runs:
                        printed.append(runs)
                    else:
                        printed.append(thai)
        else:
            # bat_line (default): keep วรรค pairs for column align after comma.
            for bat in bats:
                waks = list(bat.get("waks") or [])
                wak_payloads: list[tuple[str, list[dict] | None]] = []
                for w in waks:
                    thai, runs, extra = _thai_with_sandhi(
                        w.get("text"),
                        rules,
                        page=page,
                        order=order,
                        segment_type=kind,
                        note_base_index=note_base_index + len(extras),
                    )
                    extras.extend(extra)
                    wak_payloads.append((thai, runs))
                if len(wak_payloads) == 2:
                    left = _gatha_wak_payload(*wak_payloads[0])
                    right = _gatha_wak_payload(*wak_payloads[1])
                    printed.append(GathaBatPrintedLine(left, right))
                elif waks and all(runs is not None for _, runs in wak_payloads):
                    line_runs: list[dict] = []
                    for _, runs in wak_payloads:
                        assert runs is not None
                        if line_runs:
                            line_runs.append({"value": " ", "bold": False})
                        line_runs.extend(runs)
                    printed.append(line_runs)
                else:
                    parts = [thai for thai, _ in wak_payloads]
                    printed.append(" ".join(p for p in parts if p))
    else:
        lines, extra = _gatha_wak_thais(
            seg, rules, note_base_index=note_base_index + len(extras)
        )
        extras.extend(extra)
        printed = list(lines)
    return printed, extras


def _gatha_payload_to_measure_tex(payload: str | list[dict]) -> str:
    """Plain TeX for width measure (no footnote macros)."""
    if isinstance(payload, list):
        parts: list[str] = []
        for run in payload:
            piece = escape_tex(
                _strip_note_markers_for_measure(str(run.get("value") or ""))
            )
            if not piece:
                continue
            if run.get("bold"):
                parts.append(r"\textbf{" + piece + "}")
            else:
                parts.append(piece)
        return "".join(parts)
    return escape_tex(_strip_note_markers_for_measure(payload))


def _gatha_payload_to_body_tex(
    payload: str | list[dict],
    *,
    notes: list[str],
    symbol_notes: dict[str, str],
    emitted_symbol_notes: set[str] | None,
) -> str:
    """TeX body with note markers expanded."""
    if isinstance(payload, list):
        body, _ = apply_notes_to_thai_runs(
            payload,
            notes=notes,
            symbol_notes=symbol_notes,
            emitted_symbol_notes=emitted_symbol_notes,
        )
        return body
    body, _ = apply_notes_to_thai(
        payload,
        notes=notes,
        symbol_notes=symbol_notes,
        emitted_symbol_notes=emitted_symbol_notes,
    )
    return body


def gatha_bat_tex(left: str, right: str) -> str:
    """``\\csromangathabat{left}{right}`` for aligned bat_line บาท."""
    return rf"\csromangathabat{{{left}}}{{{right}}}"


def gatha_stanza_line_bodies(
    seg: dict,
    rules: list[TransformRule] | None = None,
    *,
    emitted_symbol_notes: set[str] | None = None,
    for_measure: bool = False,
) -> list[str]:
    """TeX bodies for each printed line of one บท.

    ``for_measure``: no footnote macros (safe inside measure macros).
    bat_line pairs emit ``\\csromangathabat{left}{right}``.
    """
    rules = rules or []
    page, order, kind = segment_context(seg)
    notes = transform_note_list(
        seg_notes(seg), rules, page=page, order=order, segment_type=kind
    )
    symbol_notes = transform_symbol_notes(
        seg_symbol_notes(seg),
        rules,
        page=page,
        order=order,
        segment_type=kind,
    )
    printed, extra = _gatha_printed_lines(
        seg, rules, note_base_index=len(notes)
    )
    notes = [*notes, *extra]
    if not printed:
        return []

    bodies: list[str] = []
    for line in printed:
        if isinstance(line, GathaBatPrintedLine):
            if for_measure:
                left = _gatha_payload_to_measure_tex(line.left)
                right = _gatha_payload_to_measure_tex(line.right)
            else:
                left = _gatha_payload_to_body_tex(
                    line.left,
                    notes=notes,
                    symbol_notes=symbol_notes,
                    emitted_symbol_notes=emitted_symbol_notes,
                )
                right = _gatha_payload_to_body_tex(
                    line.right,
                    notes=notes,
                    symbol_notes=symbol_notes,
                    emitted_symbol_notes=emitted_symbol_notes,
                )
            bodies.append(gatha_bat_tex(left, right))
            continue
        if for_measure:
            bodies.append(_gatha_payload_to_measure_tex(line))
            continue
        bodies.append(
            _gatha_payload_to_body_tex(
                line,
                notes=notes,
                symbol_notes=symbol_notes,
                emitted_symbol_notes=emitted_symbol_notes,
            )
        )
    return bodies


def gatha_left_column_bodies(
    seg: dict,
    rules: list[TransformRule] | None = None,
) -> list[str]:
    """Left-วรรค TeX bodies for ``\\csromangathasetleft`` / measuregroup."""
    rules = rules or []
    printed, _ = _gatha_printed_lines(seg, rules)
    lefts: list[str] = []
    for line in printed:
        if isinstance(line, GathaBatPrintedLine):
            lefts.append(_gatha_payload_to_measure_tex(line.left))
    return lefts


def gatha_group_end_index(segments: list[dict], start: int) -> int:
    """Exclusive end of a same-page consecutive gāthā run starting at ``start``."""
    if start < 0 or start >= len(segments) or not is_gatha_segment(segments[start]):
        return start
    page = int(segments[start].get("page") or 0)
    end = start + 1
    while (
        end < len(segments)
        and is_gatha_segment(segments[end])
        and int(segments[end].get("page") or 0) == page
    ):
        end += 1
    return end


def gatha_group_end_index_reading(segments: list[dict], start: int) -> int:
    """Exclusive end of a consecutive gāthā run (may span source folios)."""
    if start < 0 or start >= len(segments) or not is_gatha_segment(segments[start]):
        return start
    end = start + 1
    while end < len(segments) and is_gatha_segment(segments[end]):
        end += 1
    return end


def prose_flow_chain_end(segments: list[dict], start: int) -> int:
    """Exclusive end of prose + following ``*_continuation`` segments."""
    if start < 0 or start >= len(segments):
        return start
    kind = segments[start].get("segment_type") or "prose"
    if kind not in _PROSE_FLOW_KINDS:
        return start + 1
    end = start + 1
    while (
        end < len(segments)
        and (segments[end].get("segment_type") or "") in _CONTINUATION_KINDS
    ):
        end += 1
    return end


_READING_FOLIO_SKIP_KINDS = frozenset(
    {
        "piṭaka",
        "gambhīra",
        "namakkāraṃ",
        "chapter",
        "title",
        "niṭṭhitaṃ",
        "note",
    }
)


def is_ordinary_prose_flow(
    seg: dict,
    kind: str,
    body: str,
    *,
    section_rule: bool,
) -> bool:
    """True when reading mode may merge this segment with continuations."""
    if kind not in _PROSE_FLOW_KINDS:
        return False
    if seg.get("heading_kind") is not None:
        return False
    if seg.get("source_layout") == "hanging":
        return False
    layout = seg.get("source_layout")
    source_layout = str(layout) if layout else None
    if is_layout_center(
        kind,
        body,
        source_layout=source_layout,
        section_no=seg.get("section_no"),
    ):
        return False
    if is_section_closer(
        kind,
        body,
        section_rule=section_rule,
        item=seg.get("item"),
        source_layout=source_layout,
        section_no=seg.get("section_no"),
    ):
        return False
    return True


def is_reading_folio_body(
    seg: dict,
    kind: str,
    body: str,
    *,
    section_rule: bool,
    heading_kind: str | None,
) -> bool:
    """True when ``\\csromanfolio`` may attach (body prose/gāthā/hanging only)."""
    if heading_kind is not None:
        return False
    if kind in _READING_FOLIO_SKIP_KINDS:
        return False
    if kind in _GATHA_KINDS:
        return True
    if seg.get("source_layout") == "hanging":
        return True
    layout = seg.get("source_layout")
    source_layout = str(layout) if layout else None
    if is_layout_center(
        kind,
        body,
        source_layout=source_layout,
        section_no=seg.get("section_no"),
    ):
        return False
    if is_section_closer(
        kind,
        body,
        section_rule=section_rule,
        item=seg.get("item"),
        source_layout=source_layout,
        section_no=seg.get("section_no"),
    ):
        return False
    return kind in _PROSE_FLOW_KINDS


def _is_gatha_one_and_half_pair(
    prev_bodies: list[str],
    next_bodies: list[str],
) -> bool:
    """True for 1 บทครึ่ง: full บท + half บาท with no inter-stanza gap.

    bat_line: 2 printed lines + 1; wak_line: 4 + 2.
    """
    return (len(prev_bodies) == 2 and len(next_bodies) == 1) or (
        len(prev_bodies) == 4 and len(next_bodies) == 2
    )


def format_gatha_group_inner(stanza_bodies: list[list[str]]) -> str:
    """Emit ``\\csromangathastanza{...}`` units for a breakable optical group.

    Each บท is its own unbreakable stanza box; TeX may page-break between
    them. Exception: 3-บาท / 1 บทครึ่ง (full + half) merges into one stanza
    (plain ``\\\\`` only — no break between full and half).
    """
    units: list[list[str]] = []
    i = 0
    while i < len(stanza_bodies):
        bodies = stanza_bodies[i]
        if i + 1 < len(stanza_bodies) and _is_gatha_one_and_half_pair(
            bodies, stanza_bodies[i + 1]
        ):
            units.append([*bodies, *stanza_bodies[i + 1]])
            i += 2
        else:
            units.append(bodies)
            i += 1
    parts: list[str] = []
    for unit in units:
        if not unit:
            continue
        inner = r" \\ ".join(unit)
        parts.append(rf"\csromangathastanza{{{inner}}}")
    return "".join(parts)


def gatha_measure_command(measure_lines: list[str]) -> str:
    """Legacy ``\\csromangathameasure`` from flat printed lines."""
    joined = r" \\ ".join(measure_lines)
    return rf"\csromangathameasure{{{joined}}}"


def gatha_join_lines(lines: list[str]) -> str:
    return r" \\ ".join(lines)


def gatha_measure_group_command(
    left_lines: list[str],
    measure_lines: list[str],
) -> str:
    """``\\csromangathameasuregroup{lefts}{lines}`` — raise page width."""
    return (
        rf"\csromangathameasuregroup{{{gatha_join_lines(left_lines)}}}"
        rf"{{{gatha_join_lines(measure_lines)}}}"
    )


def gatha_set_left_command(left_lines: list[str]) -> str:
    """``\\csromangathasetleft{...}`` before rendering a bat_line กลุ่ม."""
    return rf"\csromangathasetleft{{{gatha_join_lines(left_lines)}}}"


def gatha_group_command(stanza_bodies: list[list[str]]) -> str:
    """One optically centered กลุ่ม (breakable between บท)."""
    return rf"\csromangathagroup{{{format_gatha_group_inner(stanza_bodies)}}}"


def gatha_group_measure_payloads(
    segments: list[dict],
    start: int,
    end: int,
    rules: list[TransformRule] | None = None,
) -> tuple[list[str], list[str]]:
    """``(left_column_lines, full_measure_lines)`` for segments[start:end]."""
    rules = rules or []
    left_lines: list[str] = []
    measure_lines: list[str] = []
    for j in range(start, end):
        seg = segments[j]
        if not is_gatha_segment(seg):
            continue
        left_lines.extend(gatha_left_column_bodies(seg, rules))
        measure_lines.extend(
            gatha_stanza_line_bodies(seg, rules, for_measure=True)
        )
    return left_lines, measure_lines


def append_gatha_page_measures(
    lines: list[str],
    segments: list[dict],
    page: int,
    rules: list[TransformRule] | None = None,
) -> None:
    """Reset page width, then measure each gāthā กลุ่ม on ``page``."""
    rules = rules or []
    lines.append(r"\setlength{\csromangathapagewidth}{0pt}")
    j = 0
    while j < len(segments):
        seg = segments[j]
        if int(seg.get("page") or 0) != page or not is_gatha_segment(seg):
            j += 1
            continue
        end = gatha_group_end_index(segments, j)
        left_lines, measure_lines = gatha_group_measure_payloads(
            segments, j, end, rules
        )
        if measure_lines:
            lines.append(
                gatha_measure_group_command(left_lines, measure_lines)
            )
        j = end


def append_gatha_group_left(
    lines: list[str],
    left_lines: list[str],
) -> None:
    """Set left-column width for the กลุ่ม about to be typeset."""
    if left_lines:
        lines.append(gatha_set_left_command(left_lines))
    else:
        lines.append(r"\setlength{\csromangathaleftcol}{0pt}")


def gatha_stanza_commands(
    seg: dict,
    rules: list[TransformRule] | None = None,
    *,
    emitted_symbol_notes: set[str] | None = None,
) -> list[str]:
    """Emit one บท as a single-stanza optical group (tests / helpers)."""
    bodies = gatha_stanza_line_bodies(
        seg, rules, emitted_symbol_notes=emitted_symbol_notes
    )
    if not bodies:
        return []
    return [gatha_group_command([bodies])]


# Visual macros from heading_kind (preferred over segment_type).
# nik/boo/cha = special stack; h1…h6 = generic section headers (large → small).
_HEADING_KIND_MACRO = {
    "nik": "pitaka",
    "boo": "gambhira",
    "cha": "chapterhead",
}

_HEADER_LEVELS = frozenset({f"h{i}" for i in range(1, 7)})
_STRUCTURAL_HEADING_KINDS = frozenset({"nik", "boo", "cha"}) | _HEADER_LEVELS

# Compound body heading in TeX: ``1. ปตฺตวคฺค 8. อฏฺฐมสิกฺขาปท`` (bold optional).
_COMPOUND_RECTO_HEAD_RE = re.compile(
    r"^((?:\d+\.\s+)?.+?)\s+(\d+\.\s+.+)$",
)
_TEX_TEXTBF_RE = re.compile(r"\\textbf\{([^{}]*)\}")


def split_recto_compound_title(body: str) -> tuple[str, str] | None:
    """Split compound heading text into ``(h1, h2)`` for equal recto gaps.

    Body display stays one line; running head wants two fields separated by
    ``\\csromanheadsep`` (same as cha↔h1), not a narrow word-space inside one
    field. Returns plain titles (``\\textbf`` stripped) or ``None``.
    """
    plain = _TEX_TEXTBF_RE.sub(r"\1", body)
    plain = re.sub(r"\s+", " ", plain).strip()
    match = _COMPOUND_RECTO_HEAD_RE.match(plain)
    if match is None:
        return None
    left, right = match.group(1).strip(), match.group(2).strip()
    if not re.match(r"^\d+\.\s+\S", right):
        return None
    if left == right:
        return None
    return left, right


def heading_command_with_recto_marks(level: str, body: str) -> str:
    """``\\csromanheader`` or compound marks + ``\\csromanheadernomark``."""
    parts = split_recto_compound_title(body)
    if parts is None:
        return rf"\csromanheader{{{level}}}{{{body}}}"
    h1, h2 = parts
    return (
        rf"\csromanmarkh{{{h1}}}"
        rf"\csromanmarkhii{{{h2}}}"
        rf"\csromanheadernomark{{{level}}}{{{body}}}"
    )

# memoir TOC levels written via \csromantocmark when in_toc is true.
# ``cha`` shares chapter with nik/boo so centered numbered parents
# (khandhaka / *kamma / vagga) sit flush-left; left-aligned leaves are
# ``h1`` → section under them.
_TOC_LEVEL = {
    "nik": "chapter",
    "boo": "chapter",
    "cha": "chapter",
    "h1": "section",
    "h2": "subsection",
    "h3": "subsubsection",
    "h4": "paragraph",
    "h5": "subparagraph",
    "h6": "subparagraph",
}

# PDF bookmark depth for deferred \\csromantocmarkat / ref (0 = top).
_BOOKMARK_DEPTH = {
    "chapter": 0,
    "section": 1,
    "subsection": 2,
    "subsubsection": 3,
    "paragraph": 4,
    "subparagraph": 5,
}


def with_section_no(seg: dict, title: str) -> str:
    """Prefix outline ``section_no`` when present (e.g. ``1. Title``)."""
    no = seg.get("section_no")
    if no is None or no == "":
        return title
    return f"{no}. {title}"


def toc_title_of(
    seg: dict,
    rules: list[TransformRule] | None = None,
) -> str:
    """Plain Thai heading for TOC (no footnote markers)."""
    rules = rules or []
    page, order, kind = segment_context(seg)
    thai, _runs, _roman, _extra = publication_thai_of_text_field(
        seg.get("text"),
        rules,
        page=page,
        order=order,
        segment_type=kind,
        emit_footnotes=False,
    )
    # Strip footnote markers for TOC display.
    plain = NOTE_MARKER_RE.sub("", thai)
    return escape_tex(with_section_no(seg, plain))


def toc_mark_command(
    seg: dict,
    rules: list[TransformRule] | None = None,
) -> str | None:
    if not seg.get("in_toc"):
        return None
    level = _TOC_LEVEL.get(str(seg.get("heading_kind") or ""))
    title = toc_title_of(seg, rules)
    if not level or not title.strip():
        return None
    return rf"\csromantocmark{{{level}}}{{{title}}}"


def load_matika(volume_id: str) -> dict | None:
    """Load volume ``data/matika.json``, falling back to ``output/<id>.matika.json``."""
    candidates = [
        BOOKS / "volumes" / volume_id / "data" / "matika.json",
        OUTPUT_DIR / f"{volume_id}.matika.json",
    ]
    for path in candidates:
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
    return None


def matika_entry_toc_title(entry: dict) -> str:
    """Thai TOC title from a Mātikā outline row (not the compound body string)."""
    raw = re.sub(r"\s+", " ", str(entry.get("title") or "").strip())
    if not raw:
        return ""
    thai = roman_to_thai(raw)
    plain = NOTE_MARKER_RE.sub("", thai)
    return escape_tex(with_section_no(entry, plain))


def matika_toc_mark(entry: dict) -> str | None:
    level = _TOC_LEVEL.get(str(entry.get("kind") or ""))
    title = matika_entry_toc_title(entry)
    if not level or not title.strip():
        return None
    return rf"\csromantocmark{{{level}}}{{{title}}}"


def matika_entry_has_printed_page(entry: dict) -> bool:
    """True when the source Mātikā printed a folio for this outline row."""
    page = entry.get("page")
    return page is not None and page != ""


def matika_toc_mark_at(entry: dict, *, page: int, dest: str) -> str | None:
    """TOC row with an explicit printed page (sync deferred emission)."""
    level = _TOC_LEVEL.get(str(entry.get("kind") or ""))
    title = matika_entry_toc_title(entry)
    if not level or not title.strip():
        return None
    depth = _BOOKMARK_DEPTH.get(level, 2)
    # Raw \bookmark line (not wrapped) so optional-arg # tokens stay literal.
    return (
        rf"\csromantocmarkat{{{level}}}{{{title}}}{{{page}}}{{{dest}}}"
        + "\n"
        + rf"\bookmark[dest={{{dest}}},level={depth}]{{{title}}}"
    )


def matika_toc_mark_ref(entry: dict, *, dest: str) -> str | None:
    """TOC row whose page comes from a body ``\\label`` (reading deferred)."""
    level = _TOC_LEVEL.get(str(entry.get("kind") or ""))
    title = matika_entry_toc_title(entry)
    if not level or not title.strip():
        return None
    depth = _BOOKMARK_DEPTH.get(level, 2)
    return (
        rf"\csromantocmarkref{{{level}}}{{{title}}}{{{dest}}}"
        + "\n"
        + rf"\bookmark[dest={{{dest}}},level={depth}]{{{title}}}"
    )


def matika_toc_mark_nopage(entry: dict, *, dest: str) -> str | None:
    """TOC row with no folio — source Mātikā left the page blank."""
    level = _TOC_LEVEL.get(str(entry.get("kind") or ""))
    title = matika_entry_toc_title(entry)
    if not level or not title.strip():
        return None
    depth = _BOOKMARK_DEPTH.get(level, 2)
    return (
        rf"\csromantocmarknopage{{{level}}}{{{title}}}{{{dest}}}"
        + "\n"
        + rf"\bookmark[dest={{{dest}}},level={depth}]{{{title}}}"
    )


def _emit_matika_toc_mark(
    entry: dict,
    *,
    dest: str,
    anchor_page: int | None,
    on_this_anchor: bool = False,
    mode: str = "sync",
) -> str | None:
    """Choose at / ref / nopage / immediate mark from source folio presence.

    Sync prints the source Mātikā folio (ฉ.N) via ``tocmarkat``.
    Reading resolves the physical sheet via ``\\pageref`` to the body dest
    (where ฉ.N was placed), because reflow makes folio ≠ ``\\thepage``.
    """
    if not matika_entry_has_printed_page(entry):
        return matika_toc_mark_nopage(entry, dest=dest)
    # Reading / printing: never print source folio as the TOC page number.
    if mode in _READING_LIKE_MODES:
        return matika_toc_mark_ref(entry, dest=dest)
    if anchor_page is not None:
        return matika_toc_mark_at(entry, page=int(anchor_page), dest=dest)
    if on_this_anchor:
        return matika_toc_mark(entry)
    return matika_toc_mark_ref(entry, dest=dest)


def _matika_dest(index: int) -> str:
    return f"mtk.{index}"



def _seg_is_folio_body_anchor(seg: dict) -> bool:
    """True for segments that can carry ``\\csromanfolio`` (page-landmark dest).

    Page-only Mātikā rows must land here — not on chapter/center headings that
    share the source folio but may sit on an earlier physical sheet in reading.
    """
    if seg.get("heading_kind") is not None:
        return False
    kind = str(seg.get("segment_type") or "")
    if kind in _READING_FOLIO_SKIP_KINDS:
        return False
    if kind in _GATHA_KINDS:
        return True
    if seg.get("source_layout") == "hanging":
        return True
    if seg.get("source_layout") == "center":
        return False
    return kind in _PROSE_FLOW_KINDS


class MatikaTocPlanner:
    """
    Body-anchored TOC marks from ``matika.json``, preserving outline order.

    Each entry gets a stable body anchor (``matched_order`` or first segment on
    ``page``).  Structural rows with neither field inherit the next resolvable
    child's anchor so parents still appear before children.

    On each segment visit:
    1. Place ``\\csromanmatikaanchor`` for entries whose anchor is this segment.
    2. Emit consecutive outline rows whose anchors are already placed.

    Deferred rows (outline order behind body order) use explicit pages (sync)
    or ``\\pageref`` (reading) so late emission never dumps onto the wrong page.
    """

    def __init__(
        self,
        matika_doc: dict,
        segments: list[dict],
        *,
        mode: str = "sync",
    ) -> None:
        self._mode = mode
        self._entries: list[dict] = [
            e for e in (matika_doc.get("entries") or []) if isinstance(e, dict)
        ]
        self._next = 0
        self._placed: set[int] = set()
        self._anchor_order: list[int | None] = [None] * len(self._entries)
        self._anchor_page: list[int | None] = [None] * len(self._entries)
        self._resolve_anchors(segments)
        self._setter_by_order: dict[int, list[str]] = self._build_head_setters()

    def _build_head_setters(self) -> dict[int, list[str]]:
        """Recto running heads come from body TeX marks — not Mātikā.

        Kept as an empty map so ``running_head_lines`` stays a no-op; TOC
        marks still use ``_anchor_order`` / ``marks_for_segment``.
        """
        return {}

    def running_head_lines(self, seg: dict) -> list[str]:
        """No Mātikā recto setters (``\\chapterhead`` / ``\\csromanheader`` set marks)."""
        return []

    def _resolve_anchors(self, segments: list[dict]) -> None:
        by_order: dict[int, dict] = {}
        first_on_page: dict[int, int] = {}
        # Prefer folio-body segments for page-only landmarks (where ฉ.N appears).
        first_folio_body_on_page: dict[int, int] = {}
        for seg in segments:
            order = seg.get("order")
            if order is None:
                continue
            order_i = int(order)
            by_order[order_i] = seg
            page = seg.get("page")
            if isinstance(page, int) and page not in first_on_page:
                first_on_page[page] = order_i
            if (
                isinstance(page, int)
                and page not in first_folio_body_on_page
                and _seg_is_folio_body_anchor(seg)
            ):
                first_folio_body_on_page[page] = order_i

        for i, entry in enumerate(self._entries):
            matched = entry.get("matched_order")
            if matched is not None and matched != "":
                order_i = int(matched)
                self._anchor_order[i] = order_i
                seg = by_order.get(order_i)
                if seg is not None and isinstance(seg.get("page"), int):
                    self._anchor_page[i] = int(seg["page"])
                elif isinstance(entry.get("page"), int):
                    self._anchor_page[i] = int(entry["page"])
                continue
            entry_page = entry.get("page")
            if entry_page is not None and entry_page != "":
                page_i = int(entry_page)
                self._anchor_page[i] = page_i
                # Page-only row: land on first ฉ.N body of that folio, not the
                # leading chapter/center heading (reading reflow may put those
                # on an earlier physical sheet).
                self._anchor_order[i] = first_folio_body_on_page.get(
                    page_i
                ) or first_on_page.get(page_i)
                # Adjacent folio fallback when the exact page has no segment yet.
                if self._anchor_order[i] is None:
                    self._anchor_order[i] = (
                        first_folio_body_on_page.get(page_i - 1)
                        or first_folio_body_on_page.get(page_i + 1)
                        or first_on_page.get(page_i - 1)
                        or first_on_page.get(page_i + 1)
                    )

        # Structural orphans inherit the next resolvable child's anchor.
        for i in range(len(self._entries) - 1, -1, -1):
            if self._anchor_order[i] is not None:
                continue
            for j in range(i + 1, len(self._entries)):
                if self._anchor_order[j] is not None:
                    self._anchor_order[i] = self._anchor_order[j]
                    self._anchor_page[i] = self._anchor_page[j]
                    break

        # Targeted inversion repair: a late spike (matched after all prior
        # anchors) that still precedes earlier-bodied children in the outline.
        # Ignore later anchors that jump backward before max(prior) — those are
        # usually duplicate titles wrongly rematched to an early segment.
        for i in range(len(self._entries)):
            order_i = self._anchor_order[i]
            if order_i is None:
                continue
            prior = [
                self._anchor_order[k]
                for k in range(i)
                if self._anchor_order[k] is not None
            ]
            max_prior = max(prior) if prior else -1
            later = [
                (j, self._anchor_order[j])
                for j in range(i + 1, len(self._entries))
                if self._anchor_order[j] is not None
                and self._anchor_order[j] > max_prior
            ]
            if not later:
                continue
            min_j, min_order = min(later, key=lambda pair: pair[1])
            if order_i > min_order and order_i > max_prior:
                self._anchor_order[i] = min_order
                self._anchor_page[i] = self._anchor_page[min_j]

    def marks_for_page_open(self, page: int) -> list[str]:
        """Place body anchors at folio open so layout spill does not shift dest +1."""
        out: list[str] = []
        for i, anchor_page in enumerate(self._anchor_page):
            if i in self._placed:
                continue
            if anchor_page == page:
                out.append(rf"\csromanmatikaanchor{{{_matika_dest(i)}}}")
                self._placed.add(i)
        # Flush outline rows whose anchors are now available (same rules as
        # segment visits) so deferred parents are not stuck behind page-open
        # placement.
        while self._next < len(self._entries):
            if self._anchor_order[self._next] is None:
                self._next += 1
                continue
            if self._next not in self._placed:
                break
            entry = self._entries[self._next]
            dest = _matika_dest(self._next)
            anchor_page = self._anchor_page[self._next]
            cmd = _emit_matika_toc_mark(
                entry,
                dest=dest,
                anchor_page=anchor_page,
                mode=self._mode,
            )
            if cmd:
                out.append(cmd)
            self._next += 1
        return out

    def marks_for_segment(self, seg: dict) -> list[str]:
        order = seg.get("order")
        if order is None:
            return []
        order_i = int(order)
        out: list[str] = []

        for i, anchor in enumerate(self._anchor_order):
            if anchor == order_i and i not in self._placed:
                out.append(rf"\csromanmatikaanchor{{{_matika_dest(i)}}}")
                self._placed.add(i)
                if self._anchor_page[i] is None and isinstance(seg.get("page"), int):
                    self._anchor_page[i] = int(seg["page"])

        while self._next < len(self._entries):
            # Unanchorable residual rows (no match, page, or inheritable child).
            if self._anchor_order[self._next] is None:
                self._next += 1
                continue
            if self._next not in self._placed:
                break
            entry = self._entries[self._next]
            dest = _matika_dest(self._next)
            anchor_page = self._anchor_page[self._next]
            on_this_anchor = self._anchor_order[self._next] == order_i
            # Sync: print source folio (ฉ.N) via tocmarkat.
            # Reading: print physical sheet via pageref to the body dest.
            # Rows with page:null in the source Mātikā stay unpaged.
            cmd = _emit_matika_toc_mark(
                entry,
                dest=dest,
                anchor_page=anchor_page,
                on_this_anchor=on_this_anchor,
                mode=self._mode,
            )
            if cmd:
                out.append(cmd)
            self._next += 1
        return out


def toc_commands_for_segment(
    seg: dict,
    rules: list[TransformRule] | None = None,
    *,
    planner: MatikaTocPlanner | None = None,
) -> list[str]:
    """Prefer matika planner; fall back to segment ``in_toc`` when absent."""
    if planner is not None:
        return planner.marks_for_segment(seg)
    cmd = toc_mark_command(seg, rules)
    return [cmd] if cmd else []


def append_toc_marks(
    lines: list[str],
    segs: list[dict] | dict,
    rules: list[TransformRule] | None = None,
    *,
    planner: MatikaTocPlanner | None = None,
) -> int:
    """Append ``\\csromantocmark`` lines for one segment or a range; return count."""
    if isinstance(segs, dict):
        batch = [segs]
    else:
        batch = segs
    n = 0
    for seg in batch:
        for toc_cmd in toc_commands_for_segment(seg, rules, planner=planner):
            lines.append(toc_cmd)
            n += 1
        if planner is not None:
            lines.extend(planner.running_head_lines(seg))
    return n


def hanging_line_commands(
    seg: dict,
    rules: list[TransformRule] | None = None,
) -> list[str] | None:
    """Emit TeX for a hanging paragraph, or None if not hanging layout."""
    if seg.get("source_layout") != "hanging":
        return None
    raw_lines = seg.get("hanging_lines")
    if not isinstance(raw_lines, list) or not raw_lines:
        return None

    rules = rules or []
    page, order, kind = segment_context(seg)
    head, _ = build_body(seg, rules)

    body_lines: list[str] = []
    for hl in raw_lines:
        thai, runs, _roman, extra = publication_thai_of_text_field(
            hl,
            rules,
            page=page,
            order=order,
            segment_type=kind,
            note_base_index=0,
            emit_footnotes=True,
        )
        if runs:
            piece, _ = apply_notes_to_thai_runs(
                runs, notes=extra, symbol_notes={}
            )
        else:
            piece, _ = apply_notes_to_thai(thai, notes=extra, symbol_notes={})
        if piece:
            body_lines.append(piece)
    if not body_lines:
        return None

    item = seg.get("item")
    cmds: list[str] = [r"\csromanhangingbegin"]
    if item is not None:
        cmds.append(
            rf"\hangingheaditem{{{escape_tex(str(item))}}}{{{head}}}"
        )
    else:
        cmds.append(rf"\hangingheadline{{{head}}}")
    for line in body_lines:
        cmds.append(rf"\hangingbody{{{line}}}")
    cmds.append(r"\csromanhangingend")
    return cmds


def _plain_closer_body(body: str) -> str:
    """Strip light TeX wrappers so closer-formula detection sees Thai text."""
    plain = _TEX_FOOTNOTE_RE.sub("", body)
    plain = _TEX_TEXTBF_RE.sub(r"\1", plain)
    return plain.strip()


def is_layout_center(
    kind: str,
    body: str,
    *,
    source_layout: str | None = None,
    section_no: object = None,
) -> bool:
    """True when geometry/sandwich ``source_layout='center'`` → ``\\csromancenter``.

    Outline titles (``section_no``, bold ``\\textbf``) keep heading macros —
    geometry records ``center`` but face/size stay title-level.
    """
    if source_layout != "center":
        return False
    if kind not in {
        "prose",
        "prose_continuation",
        "verse",
        "verse_continuation",
        "title",
    }:
        return False
    if kind == "title" and (
        section_no is not None and section_no != "" or r"\textbf{" in body
    ):
        return False
    return True


def is_section_closer(
    kind: str,
    body: str,
    *,
    section_rule: bool = False,
    item: object = None,
    source_layout: str | None = None,
    section_no: object = None,
) -> bool:
    """True when the segment should use the airy ``\\nitthitam`` closer band.

    Includes ``niṭṭhitaṃ``, ``title``+``section_rule`` (e.g. samattaṃ), and
    short end formulas mis-tagged as title/prose. Geometry / sandwich centers
    use ``\\csromancenter`` instead (see ``is_layout_center``). Long prose that
    only carries ``section_rule`` (e.g. Anāpatti formulas) stays body prose +
    rule.

    ``item`` / ``source_layout`` / ``section_no`` kept for call-site compat.
    """
    _ = (item, source_layout, section_no)
    if kind == "niṭṭhitaṃ":
        return True
    if kind == "title" and section_rule:
        return True
    # Short end formulas only (item may be a spurious Tipiṭaka number).
    if kind in {"title", "prose"}:
        plain = _plain_closer_body(body)
        if 0 < len(plain) <= 90 and _CLOSER_FORMULA_RE.search(plain):
            return True
    return False


def segment_command(
    kind: str,
    item: object,
    body: str,
    *,
    last_item: object,
    section_rule: bool = False,
    heading_kind: str | None = None,
    source_layout: str | None = None,
    section_no: object = None,
    chapter_page_start: bool = False,
    reading_mode: bool = False,
) -> tuple[str, object]:
    """Return (tex_line, updated last_item used for numbering)."""
    # Prefer heading_kind for typography (compound chapter+h2 must not stay
    # locked to \\chapterhead just because segment_type is chapter).
    page_macro = "chapterheadpageread" if reading_mode else "chapterheadpage"
    if heading_kind == "cha":
        macro = page_macro if chapter_page_start else "chapterhead"
        return rf"\{macro}{{{body}}}", None
    if heading_kind in _HEADING_KIND_MACRO:
        macro = _HEADING_KIND_MACRO[heading_kind]
        return rf"\{macro}{{{body}}}", None
    if heading_kind in _HEADER_LEVELS:
        level = heading_kind[1]
        return heading_command_with_recto_marks(level, body), None
    if kind == "chapter":
        macro = page_macro if chapter_page_start else "chapterhead"
        return rf"\{macro}{{{body}}}", None
    if kind == "piṭaka":
        return rf"\pitaka{{{body}}}", None
    if kind == "gambhīra":
        return rf"\gambhira{{{body}}}", None
    if kind == "namakkāraṃ":
        return rf"\namakkaram{{{body}}}", None
    # Mid-content centered labels: prose leading (not the niṭṭhitaṃ band).
    # Keep item continuity — a mid-item centered label must not reset
    # last_item, or the next prose under the same Tipiṭaka number reprints N.
    if is_layout_center(
        kind, body, source_layout=source_layout, section_no=section_no
    ):
        kept = item if item is not None else last_item
        return rf"\csromancenter{{{body}}}", kept
    # End-of-section band (lesser than a heading): before title/prose macros.
    if is_section_closer(
        kind,
        body,
        section_rule=section_rule,
        item=item,
        source_layout=source_layout,
        section_no=section_no,
    ):
        kept = item if item is not None else last_item
        if section_rule:
            return rf"\nitthitamruled{{{body}}}", kept
        return rf"\nitthitam{{{body}}}", kept
    if kind == "title":
        return rf"\titlehead{{{body}}}", None
    if kind == "note":
        return rf"\orphannote{{{body}}}", None
    if kind in {"prose_continuation", "verse_continuation"}:
        # Mid-unit across a page break: no new number, no indent.
        return rf"\prosecont{{{body}}}", last_item
    if kind in {"prose", "verse"} and item is not None:
        # New paragraph under the same item → indent only, do not repeat N.
        if item == last_item:
            return rf"\prose{{{body}}}", last_item
        return rf"\proseitem{{{escape_tex(str(item))}}}{{{body}}}", item
    return rf"\prose{{{body}}}", None


_CLOSER_PAIR_KINDS = frozenset(
    {"prose", "prose_continuation", "verse", "verse_continuation"}
)
_PROSE_CLOSER_CMD_PREFIXES = (
    r"\prosewithcloser{",
    r"\prosewithcloserruled{",
    r"\proseitemwithcloser{",
    r"\proseitemwithcloserruled{",
    r"\prosecontwithcloser{",
    r"\prosecontwithcloserruled{",
)


def is_prose_closer_command(cmd: str) -> bool:
    return cmd.startswith(_PROSE_CLOSER_CMD_PREFIXES)


def prose_macro_name(kind: str, item: object, last_item: object) -> str:
    if kind in _CONTINUATION_KINDS:
        return "prosecont"
    if kind in {"prose", "verse"} and item is not None and item != last_item:
        return "proseitem"
    return "prose"


def last_item_after_prose_closer_pair(
    kind: str,
    item: object,
    last_item: object,
    *,
    closer_item: object,
) -> object:
    """Update ``last_item`` as if prose then closer were emitted separately.

    Mirrors ``segment_command`` for body prose / continuation, then keeps or
    replaces from the closer's Tipiṭaka ``item`` (closers usually have none).
    """
    if kind in _CONTINUATION_KINDS:
        updated = last_item
    elif kind in {"prose", "verse"} and item is not None:
        updated = item
    else:
        updated = None
    if closer_item is not None:
        return closer_item
    return updated


def pairable_closer_segment(
    seg: dict,
    rules: list[TransformRule],
    *,
    emitted_symbol_notes: set[str],
) -> tuple[str, bool] | None:
    """Return ``(closer_body, section_rule)`` when ``seg`` is a section closer.

    Builds the closer body once; callers must not call this twice for the same
    segment with a shared ``emitted_symbol_notes`` set.
    """
    kind = seg.get("segment_type") or "prose"
    if seg.get("heading_kind") is not None:
        return None
    layout = seg.get("source_layout")
    source_layout = str(layout) if layout else None
    body, section_rule = build_body(
        seg, rules, emitted_symbol_notes=emitted_symbol_notes
    )
    body = with_section_no(seg, body)
    if not is_section_closer(
        kind,
        body,
        section_rule=section_rule,
        item=seg.get("item"),
        source_layout=source_layout,
        section_no=seg.get("section_no"),
    ):
        return None
    return body, section_rule


def take_following_pairable_closer(
    segments: list[dict],
    index: int,
    rules: list[TransformRule],
    *,
    emitted_symbol_notes: set[str],
) -> tuple[dict, str, bool] | None:
    """If ``segments[index + 1]`` is a pairable closer, build it once.

    Returns ``(closer_seg, closer_body, section_rule)`` or ``None``.
    """
    if index + 1 >= len(segments):
        return None
    nxt = segments[index + 1]
    next_kind = nxt.get("segment_type") or ""
    if next_kind in _CONTINUATION_KINDS:
        return None
    pair = pairable_closer_segment(
        nxt, rules, emitted_symbol_notes=emitted_symbol_notes
    )
    if pair is None:
        return None
    closer_body, closer_rule = pair
    return nxt, closer_body, closer_rule


def prose_with_closer_command(
    macro: str,
    prose_body: str,
    closer_body: str,
    *,
    item: object = None,
    section_rule: bool = False,
) -> str:
    if macro == "proseitem":
        item_tex = escape_tex(str(item))
        name = (
            "proseitemwithcloserruled" if section_rule else "proseitemwithcloser"
        )
        return rf"\{name}{{{item_tex}}}{{{prose_body}}}{{{closer_body}}}"
    if macro == "prosecont":
        name = "prosecontwithcloserruled" if section_rule else "prosecontwithcloser"
        return rf"\{name}{{{prose_body}}}{{{closer_body}}}"
    name = "prosewithcloserruled" if section_rule else "prosewithcloser"
    return rf"\{name}{{{prose_body}}}{{{closer_body}}}"


def section_rule_commands(
    cmd: str,
    *,
    kind: str,
    section_rule: bool,
) -> list[str]:
    """Body command plus ``\\csromansectionrule`` when the flag requires it.

    ``\\nitthitamruled`` already embeds the rule. ``\\gambhira`` already draws
    its title underline (the same short PDF mark), so do not emit a second.
    """
    if not section_rule:
        return [cmd]
    if kind == "gambhīra" or cmd.startswith(r"\nitthitamruled"):
        return [cmd]
    if cmd.startswith(
        (
            r"\prosewithcloserruled{",
            r"\proseitemwithcloserruled{",
            r"\prosecontwithcloserruled{",
        )
    ):
        return [cmd]
    return [cmd, r"\csromansectionrule"]


def _body_header_lines(
    volume_id: str,
    *,
    mode: str,
    segment_count: int,
    rule_count: int,
    volume_layout: dict,
) -> list[str]:
    return [
        "% Auto-generated from data/segments.json + layout.json"
        " (+ transforms) — do not edit by hand.",
        f"% volume: {volume_id}",
        f"% mode: {mode}",
        f"% segments: {segment_count}",
        f"% transform_rules: {rule_count}",
        "",
        "% Volume layout defaults (layout.json ``layout``).",
        layout_apply_command(volume_layout),
        "",
    ]


def _annotate_toc_marks(lines: list[str], toc_marks: int) -> None:
    for i, line in enumerate(lines):
        if line.startswith("% transform_rules:"):
            lines.insert(i + 1, f"% toc_marks: {toc_marks}")
            return
    for i, line in enumerate(lines):
        if line.startswith("% segments:"):
            lines.insert(i + 1, f"% toc_marks: {toc_marks}")
            return


# Suttanta volumes (Di/Ma/Sam/An/Khu) have no ``piṭaka`` segment in
# segments.json — inject the piṭaka name for the left running head.
_SUTTANTA_PITAKA = "สุตฺตนฺตปิฏก"


def opening_running_head_lines(
    segments: list[dict],
    rules: list[TransformRule] | None = None,
) -> list[str]:
    """Volume-opening running-head setters.

    Vinaya / Abhidhamma volumes carry their own ``piṭaka`` segment (whose
    ``\\pitaka`` macro sets the head field), so nothing is injected there.
    For Suttanta volumes the piṭaka name comes from here, and the nikāya name
    is the opening ``title`` segment (e.g. ทีฆนิกาย).
    """
    out: list[str] = []
    if not any(
        str(seg.get("segment_type") or "") == "piṭaka" for seg in segments
    ):
        out.append(rf"\setcsromanpitaka{{{_SUTTANTA_PITAKA}}}")
    first = segments[0] if segments else None
    if first is not None and str(first.get("segment_type") or "") == "title":
        title = toc_title_of(first, rules)
        if title:
            out.append(rf"\setcsromannikaya{{{title}}}")
    return out


def _sorted_segments(doc: dict) -> list[dict]:
    """Return segments in extraction order (``order``), not by printed page.

    Printed ``page`` can restart mid-volume (second Namo / back-matter). Sorting
    by page would scramble the body stream and stall ``MatikaTocPlanner``.
    """
    segments = list(doc.get("segments") or [])
    segments.sort(key=lambda seg: int(seg.get("order") or 0))
    return segments


def generate_sync_lines(
    doc: dict,
    rules: list[TransformRule],
    volume_id: str,
    segments: list[dict],
    volume_layout: dict,
    *,
    toc_planner: MatikaTocPlanner | None = None,
) -> tuple[list[str], int]:
    """Page-synced body: ``\\csromanpage``; volume ``layout`` only (no per-page)."""
    toc_marks = 0
    lines = _body_header_lines(
        volume_id,
        mode="sync",
        segment_count=len(segments),
        rule_count=len(rules),
        volume_layout=volume_layout,
    )
    lines.extend(opening_running_head_lines(segments, rules))
    current_page: int | None = None
    last_item: object = None
    last_was_layout_center = False
    emitted_symbol_notes: set[str] = set()
    gatha_measured_pages: set[int] = set()
    page_ws = float(volume_layout.get("word_space") or DEFAULT_LAYOUT["word_space"])
    i = 0
    while i < len(segments):
        seg = segments[i]
        page = int(seg.get("page") or 1)
        if current_page is None:
            lines.append(rf"\setcounter{{page}}{{{page}}}")
            current_page = page
            emitted_symbol_notes = set()
            if toc_planner is not None:
                for cmd in toc_planner.marks_for_page_open(page):
                    lines.append(cmd)
                    toc_marks += 1
        elif page != current_page:
            lines.append(rf"\csromanpage{{{page}}}")
            current_page = page
            emitted_symbol_notes = set()
            if toc_planner is not None:
                for cmd in toc_planner.marks_for_page_open(page):
                    lines.append(cmd)
                    toc_marks += 1
        seg_ws = seg_word_space(doc, seg)
        kind = seg.get("segment_type") or "prose"
        prev_seg = segments[i - 1] if i > 0 else None
        next_seg = segments[i + 1] if i + 1 < len(segments) else None
        if is_gatha_segment(seg):
            end = gatha_group_end_index(segments, i)
            toc_marks += append_toc_marks(
                lines, segments[i:end], rules, planner=toc_planner
            )
            if page not in gatha_measured_pages:
                append_gatha_page_measures(lines, segments, page, rules)
                gatha_measured_pages.add(page)
            left_lines, _ = gatha_group_measure_payloads(
                segments, i, end, rules
            )
            append_gatha_group_left(lines, left_lines)
            stanza_bodies: list[list[str]] = []
            group_ws: float | int | None = None
            mixed_ws = False
            for j in range(i, end):
                gseg = segments[j]
                bodies = gatha_stanza_line_bodies(
                    gseg,
                    rules,
                    emitted_symbol_notes=emitted_symbol_notes,
                )
                if bodies:
                    stanza_bodies.append(bodies)
                ws_j = seg_word_space(doc, gseg)
                if group_ws is None:
                    group_ws = ws_j
                elif ws_j is not None and float(ws_j) != float(group_ws or page_ws):
                    mixed_ws = True
            if stanza_bodies:
                cmd = gatha_group_command(stanza_bodies)
                wrap_seg = seg if not mixed_ws else seg
                wrap_ws = group_ws if not mixed_ws else None
                for out in wrap_word_space(
                    wrap_seg,
                    [cmd],
                    page_word_space=page_ws,
                    segment_word_space=wrap_ws,
                ):
                    lines.append(out)
                lines.append("")
            last_was_layout_center = False
            i = end
            continue
        hang_cmds = hanging_line_commands(seg, rules)
        if hang_cmds:
            toc_marks += append_toc_marks(
                lines, seg, rules, planner=toc_planner
            )
            for cmd in wrap_word_space(
                seg,
                hang_cmds,
                page_word_space=page_ws,
                segment_word_space=seg_ws,
            ):
                lines.append(cmd)
            lines.append("")
            item = seg.get("item")
            if item is not None:
                last_item = item
            last_was_layout_center = False
            i += 1
            continue
        body, section_rule = build_body(
            seg, rules, emitted_symbol_notes=emitted_symbol_notes
        )
        body = with_section_no(seg, body)
        toc_marks += append_toc_marks(
            lines, seg, rules, planner=toc_planner
        )
        heading_kind = seg.get("heading_kind")
        if heading_kind is not None:
            heading_kind = str(heading_kind)
        layout = seg.get("source_layout")
        prev_page = int(prev_seg.get("page") or 0) if prev_seg else None
        chapter_page_start = prev_page is None or prev_page != page
        paired_closer: dict | None = None
        closer_body = ""
        closer_rule = False
        source_layout = str(layout) if layout else None
        if (
            kind in _CLOSER_PAIR_KINDS
            and heading_kind is None
            and not is_layout_center(
                kind,
                body,
                source_layout=source_layout,
                section_no=seg.get("section_no"),
            )
        ):
            taken = take_following_pairable_closer(
                segments,
                i,
                rules,
                emitted_symbol_notes=emitted_symbol_notes,
            )
            if taken is not None:
                paired_closer, closer_body, closer_rule = taken
        if paired_closer is not None:
            macro = prose_macro_name(kind, seg.get("item"), last_item)
            cmd = prose_with_closer_command(
                macro,
                body,
                closer_body,
                item=seg.get("item") if macro == "proseitem" else None,
                section_rule=closer_rule,
            )
            last_item = last_item_after_prose_closer_pair(
                kind,
                seg.get("item"),
                last_item,
                closer_item=paired_closer.get("item"),
            )
            toc_marks += append_toc_marks(
                lines, paired_closer, rules, planner=toc_planner
            )
            emit_section_rule = closer_rule
        else:
            cmd, last_item = segment_command(
                kind,
                seg.get("item"),
                body,
                last_item=last_item,
                section_rule=section_rule,
                heading_kind=heading_kind,
                source_layout=source_layout,
                section_no=seg.get("section_no"),
                chapter_page_start=chapter_page_start,
            )
            emit_section_rule = section_rule
        is_center_cmd = cmd.startswith(r"\csromancenter")
        if is_center_cmd and not last_was_layout_center:
            lines.append(r"\vspace{\tipitakaparskip}")
        for line in wrap_word_space(
            seg,
            section_rule_commands(
                cmd, kind=kind, section_rule=emit_section_rule
            ),
            page_word_space=page_ws,
            segment_word_space=seg_ws,
        ):
            lines.append(line)
        next_kind = (next_seg or {}).get("segment_type") or ""
        if is_center_cmd and next_kind in _GATHA_KINDS:
            lines.append(r"\vspace{0.5\baselineskip}")
        last_was_layout_center = is_center_cmd
        structural = {
            "piṭaka",
            "gambhīra",
            "namakkāraṃ",
            "chapter",
            "title",
            "niṭṭhitaṃ",
        }
        if (
            kind not in structural
            and heading_kind not in _STRUCTURAL_HEADING_KINDS
            and not cmd.startswith(r"\nitthitam")
            and not is_prose_closer_command(cmd)
            and not is_center_cmd
        ):
            lines.append("")
        i += 2 if paired_closer is not None else 1
    return lines, toc_marks


def generate_reading_lines(
    doc: dict,
    rules: list[TransformRule],
    volume_id: str,
    segments: list[dict],
    volume_layout: dict,
    *,
    toc_planner: MatikaTocPlanner | None = None,
    mode: str = "reading",
) -> tuple[list[str], int]:
    """Continuous body: merge continuations; ``\\csromanfolio`` at folio changes.

    ``mode`` is ``reading`` or ``printing`` (same flow). Printing omits
    ``page_layout_reading_mode`` hooks — those keys are physical reading pages.
    """
    if mode not in _READING_LIKE_MODES:
        raise ValueError(f"generate_reading_lines mode must be reading/printing, got {mode!r}")
    toc_marks = 0
    lines = _body_header_lines(
        volume_id,
        mode=mode,
        segment_count=len(segments),
        rule_count=len(rules),
        volume_layout=volume_layout,
    )
    # Physical-page overrides: reading only (printing reflows to different pages).
    if mode == "reading":
        lines.extend(reading_page_layout_setup_lines(doc, volume_layout))
    lines.extend(opening_running_head_lines(segments, rules))
    page_ws = float(volume_layout.get("word_space") or DEFAULT_LAYOUT["word_space"])
    break_before = doc_reading_break_before_orders(doc)
    last_item: object = None
    last_was_layout_center = False
    last_folio_marked: int | None = None
    emitted_symbol_notes: set[str] = set()
    i = 0
    while i < len(segments):
        seg = segments[i]
        order = int(seg.get("order") or 0)
        if order in break_before:
            lines.append(r"\clearpage")
        page = int(seg.get("page") or 1)
        if last_folio_marked is not None and page != last_folio_marked:
            emitted_symbol_notes = set()
        seg_ws = seg_word_space(doc, seg)
        kind = seg.get("segment_type") or "prose"
        prev_seg = segments[i - 1] if i > 0 else None
        next_seg = segments[i + 1] if i + 1 < len(segments) else None

        if is_gatha_segment(seg):
            end = gatha_group_end_index_reading(segments, i)
            toc_marks += append_toc_marks(
                lines, segments[i:end], rules, planner=toc_planner
            )
            left_lines, measure_lines = gatha_group_measure_payloads(
                segments, i, end, rules
            )
            if measure_lines:
                lines.append(r"\setlength{\csromangathapagewidth}{0pt}")
                lines.append(
                    gatha_measure_group_command(left_lines, measure_lines)
                )
                append_gatha_group_left(lines, left_lines)
            stanza_bodies: list[list[str]] = []
            group_ws: float | int | None = None
            mixed_ws = False
            for j in range(i, end):
                gseg = segments[j]
                gpage = int(gseg.get("page") or 0)
                if last_folio_marked is not None and gpage != last_folio_marked:
                    emitted_symbol_notes = set()
                bodies = gatha_stanza_line_bodies(
                    gseg,
                    rules,
                    emitted_symbol_notes=emitted_symbol_notes,
                )
                if bodies:
                    bodies[0], last_folio_marked = with_folio(
                        bodies[0], gpage, last_folio_marked
                    )
                    stanza_bodies.append(bodies)
                ws_j = seg_word_space(doc, gseg)
                if group_ws is None:
                    group_ws = ws_j
                elif ws_j is not None and float(ws_j) != float(group_ws or page_ws):
                    mixed_ws = True
            if stanza_bodies:
                cmd = gatha_group_command(stanza_bodies)
                wrap_ws = group_ws if not mixed_ws else None
                for out in wrap_word_space(
                    seg,
                    [cmd],
                    page_word_space=page_ws,
                    segment_word_space=wrap_ws,
                ):
                    lines.append(out)
                lines.append("")
            last_was_layout_center = False
            i = end
            continue

        hang_cmds = hanging_line_commands(seg, rules)
        if hang_cmds:
            toc_marks += append_toc_marks(
                lines, seg, rules, planner=toc_planner
            )
            hang_cmds = list(hang_cmds)
            for hi, hcmd in enumerate(hang_cmds):
                if hcmd.startswith(r"\hangingheaditem{"):
                    rest = hcmd[len(r"\hangingheaditem{") :]
                    label, _, body_part = rest.partition("}{")
                    if body_part.endswith("}"):
                        body_inner = body_part[:-1]
                        body_inner, last_folio_marked = with_folio(
                            body_inner, page, last_folio_marked
                        )
                        hang_cmds[hi] = (
                            rf"\hangingheaditem{{{label}}}{{{body_inner}}}"
                        )
                    break
                if hcmd.startswith(r"\hangingheadline{"):
                    inner = hcmd[len(r"\hangingheadline{") : -1]
                    inner, last_folio_marked = with_folio(
                        inner, page, last_folio_marked
                    )
                    hang_cmds[hi] = rf"\hangingheadline{{{inner}}}"
                    break
            for cmd in wrap_word_space(
                seg,
                hang_cmds,
                page_word_space=page_ws,
                segment_word_space=seg_ws,
            ):
                lines.append(cmd)
            lines.append("")
            item = seg.get("item")
            if item is not None:
                last_item = item
            last_was_layout_center = False
            i += 1
            continue

        body, section_rule = build_body(
            seg, rules, emitted_symbol_notes=emitted_symbol_notes
        )
        body = with_section_no(seg, body)
        heading_kind = seg.get("heading_kind")
        if heading_kind is not None:
            heading_kind = str(heading_kind)
        layout = seg.get("source_layout")
        source_layout = str(layout) if layout else None

        if is_ordinary_prose_flow(seg, kind, body, section_rule=section_rule):
            end = prose_flow_chain_end(segments, i)
            closer_seg: dict | None = None
            closer_pair: tuple[str, bool] | None = None
            if end < len(segments):
                closer_seg = segments[end]
                closer_pair = pairable_closer_segment(
                    closer_seg,
                    rules,
                    emitted_symbol_notes=emitted_symbol_notes,
                )
            # Visit every row in the merge (including page-opening
            # continuations) so page-anchored Mātikā landmarks are not dropped.
            toc_marks += append_toc_marks(
                lines,
                segments[i : end + (1 if closer_pair else 0)],
                rules,
                planner=toc_planner,
            )
            chunks: list[tuple[int, str]] = [(page, body)]
            for j in range(i + 1, end):
                cseg = segments[j]
                cpage = int(cseg.get("page") or 1)
                if cpage != int(chunks[-1][0]):
                    emitted_symbol_notes = set()
                cbody, _ = build_body(
                    cseg, rules, emitted_symbol_notes=emitted_symbol_notes
                )
                chunks.append((cpage, cbody))
            merged, last_folio_marked = join_reading_flow_bodies(
                chunks, last_folio_marked=last_folio_marked
            )
            if closer_pair is not None and closer_seg is not None:
                closer_body, closer_rule = closer_pair
                macro = prose_macro_name(kind, seg.get("item"), last_item)
                cmd = prose_with_closer_command(
                    macro,
                    merged,
                    closer_body,
                    item=seg.get("item") if macro == "proseitem" else None,
                    section_rule=closer_rule,
                )
                last_item = last_item_after_prose_closer_pair(
                    kind,
                    seg.get("item"),
                    last_item,
                    closer_item=closer_seg.get("item"),
                )
                emit_section_rule = closer_rule
                next_i = end + 1
            else:
                cmd, last_item = segment_command(
                    kind,
                    seg.get("item"),
                    merged,
                    last_item=last_item,
                    section_rule=section_rule,
                    heading_kind=None,
                    source_layout=source_layout,
                    section_no=seg.get("section_no"),
                    chapter_page_start=False,
                    reading_mode=True,
                )
                emit_section_rule = section_rule
                next_i = end
            for line in wrap_word_space(
                seg,
                section_rule_commands(
                    cmd, kind=kind, section_rule=emit_section_rule
                ),
                page_word_space=page_ws,
                segment_word_space=seg_ws,
            ):
                lines.append(line)
            if not is_prose_closer_command(cmd):
                lines.append("")
            last_was_layout_center = False
            i = next_i
            continue

        toc_marks += append_toc_marks(
            lines, seg, rules, planner=toc_planner
        )
        # Folio marks only on body prose/gāthā/hanging — never on headings
        # (including TOC-anchored structural titles).
        if is_reading_folio_body(
            seg,
            kind,
            body,
            section_rule=section_rule,
            heading_kind=heading_kind,
        ):
            body, last_folio_marked = with_folio(body, page, last_folio_marked)
        # Same rule as sync: cha / chapter that opens a source folio uses
        # chapterheadpageread (optional recto). Opening-stack cha on the
        # same folio as pitaka/gambhīra stays \chapterhead.
        prev_page = int(prev_seg.get("page") or 0) if prev_seg else None
        chapter_page_start = prev_page is None or prev_page != page
        cmd, last_item = segment_command(
            kind,
            seg.get("item"),
            body,
            last_item=last_item,
            section_rule=section_rule,
            heading_kind=heading_kind,
            source_layout=source_layout,
            section_no=seg.get("section_no"),
            chapter_page_start=chapter_page_start,
            reading_mode=True,
        )
        is_center_cmd = cmd.startswith(r"\csromancenter")
        if is_center_cmd and not last_was_layout_center:
            lines.append(r"\vspace{\tipitakaparskip}")
        for line in wrap_word_space(
            seg,
            section_rule_commands(cmd, kind=kind, section_rule=section_rule),
            page_word_space=page_ws,
            segment_word_space=seg_ws,
        ):
            lines.append(line)
        next_kind = (next_seg or {}).get("segment_type") or ""
        if is_center_cmd and next_kind in _GATHA_KINDS:
            lines.append(r"\vspace{0.5\baselineskip}")
        last_was_layout_center = is_center_cmd
        structural = {
            "piṭaka",
            "gambhīra",
            "namakkāraṃ",
            "chapter",
            "title",
            "niṭṭhitaṃ",
        }
        if (
            kind not in structural
            and heading_kind not in _STRUCTURAL_HEADING_KINDS
            and not cmd.startswith(r"\nitthitam")
            and not is_center_cmd
        ):
            lines.append("")
        i += 1
    return lines, toc_marks


def generate(volume_id: str, *, mode: str = "sync") -> Path:
    if mode not in _GENERATE_MODES:
        raise ValueError(f"mode must be one of {sorted(_GENERATE_MODES)}, got {mode!r}")
    vol = BOOKS / "volumes" / volume_id
    data_path = vol / "data" / "segments.json"
    if mode == "reading":
        out_path = vol / "tex" / "body.reading.generated.tex"
    elif mode == "printing":
        out_path = vol / "tex" / "body.printing.generated.tex"
    else:
        out_path = vol / "tex" / "body.generated.tex"
    if not data_path.is_file():
        raise FileNotFoundError(data_path)

    doc = load_document(data_path)
    rules = load_volume_transforms(volume_id)
    # DPD/overrides cache + soft_breaks from this volume's transform rules.
    if _SANDHI_ENABLED:
        refresh_sandhi_with_transforms(rules)
    volume_layout = doc_layout(doc)
    segments = _sorted_segments(doc)
    matika_doc = load_matika(volume_id)
    toc_planner = (
        MatikaTocPlanner(matika_doc, segments, mode=mode) if matika_doc else None
    )
    if mode in _READING_LIKE_MODES:
        lines, toc_marks = generate_reading_lines(
            doc,
            rules,
            volume_id,
            segments,
            volume_layout,
            toc_planner=toc_planner,
            mode=mode,
        )
    else:
        lines, toc_marks = generate_sync_lines(
            doc,
            rules,
            volume_id,
            segments,
            volume_layout,
            toc_planner=toc_planner,
        )
    _annotate_toc_marks(lines, toc_marks)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join(lines) + "\n"
    out_path.write_text(body, encoding="utf-8")
    # region agent log
    try:
        import json
        import time
        from pathlib import Path as _P

        _log = _P(__file__).resolve().parents[3] / "debug-ab7022.log"
        _n_at = body.count("\\csromantocmarkat")
        _n_ref = body.count("\\csromantocmarkref")
        _n_nop = body.count("\\csromantocmarknopage")
        _samples = []
        for _ln in lines:
            if "\\csromantocmark" in _ln and len(_samples) < 8:
                _samples.append(_ln[:160])
        _folio294 = next((i for i, _ln in enumerate(lines) if "\\csromanfolio{294}" in _ln), -1)
        _mtk115 = next((i for i, _ln in enumerate(lines) if "\\csromanmatikaanchor{mtk.115}" in _ln), -1)
        _cab = next((i for i, _ln in enumerate(lines) if "จพฺพคฺคิยภิกฺขุวตฺถุ" in _ln and "tocmark" in _ln), -1)
        with _log.open("a", encoding="utf-8") as _f:
            _f.write(
                json.dumps(
                    {
                        "sessionId": "ab7022",
                        "runId": "post-fix",
                        "hypothesisId": "D",
                        "location": "generate_cs_roman_tex.py:generate",
                        "message": "TOC mark counts after generate",
                        "data": {
                            "mode": mode,
                            "volume_id": volume_id,
                            "n_at": _n_at,
                            "n_ref": _n_ref,
                            "n_nopage": _n_nop,
                            "samples": _samples,
                            "folio294_line": _folio294 + 1 if _folio294 >= 0 else None,
                            "mtk115_anchor_line": _mtk115 + 1 if _mtk115 >= 0 else None,
                            "cabbaggiya_toc_line": _cab + 1 if _cab >= 0 else None,
                            "mtk115_at_or_after_folio294": (
                                _mtk115 >= 0 and _folio294 >= 0 and _mtk115 >= _folio294 - 5
                            ),
                        },
                        "timestamp": int(time.time() * 1000),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    except Exception:
        pass
    # endregion
    return out_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--volume", default="01Vin01")
    parser.add_argument(
        "--mode",
        choices=["printing", "sync"],
        default="sync",
        help="sync: page-faithful; printing: continuous reading flow at 165×230 mm",
    )
    parser.add_argument(
        "--forbid-orphan-notes",
        action="store_true",
        help=(
            "Exit 1 if body emits \\orphannote (unbound note segments dumped at "
            "end of book). Clear with extract + fixup_orphan_footnote_callouts; "
            "audit with scan_orphan_notes.py."
        ),
    )
    parser.add_argument(
        "--no-sandhi-breaks",
        action="store_true",
        help="Disable DPD sandhi soft hyphens (shared/sandhi_breaks.json).",
    )
    args = parser.parse_args(argv)
    global _SANDHI_ENABLED
    _SANDHI_ENABLED = not args.no_sandhi_breaks
    path = generate(args.volume, mode=args.mode)
    body = path.read_text(encoding="utf-8")
    orphan_n = body.count(r"\orphannote")
    print(f"Wrote {path}")
    if orphan_n:
        print(
            f"warning: {orphan_n} \\orphannote in {path.name} "
            "(unbound footnotes → last-page dump); "
            "run fixup_orphan_footnote_callouts.py / scan_orphan_notes.py",
            file=sys.stderr,
        )
        if args.forbid_orphan_notes:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
