#!/usr/bin/env python3
"""
Generate TeX body from cs-roman segments JSON (Thai script).

  python books/cs-roman/scripts/generate_cs_roman_tex.py --volume 01Vin01
  python books/cs-roman/scripts/generate_cs_roman_tex.py --volume 01Vin01 --mode printing
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import AbstractSet, Any, NamedTuple

from paths import BOOKS, OUTPUT_DIR, ensure_import_paths

ensure_import_paths()

from cs_roman_gatha_fit import gatha_group_stack_bat_keys  # noqa: E402
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
    DEFAULT_MIN_ROMAN_LEN,
    ensure_sandhi_break_cache,
    inject_soft_breaks_in_thai,
    merge_break_maps,
)
from cs_roman_text import (  # noqa: E402
    SECTION_RULE_FLAG,
    classify_section_closer_tier,
    ensure_ordinal_closer_section_rule,
    is_bare_category_closer_label,
    is_section_closer_formula,
    join_two_line_category_closer,
    remap_runs_through_edit,
    roman_runs_from_text_field,
    roman_to_thai,
    roman_value_from_text_field,
    split_trailing_section_rule,
    thai_digits_to_arabic,
    transliterate_runs,
    uses_sentence_spacer,
)
from cs_roman_transforms import (  # noqa: E402
    TransformRule,
    apply_transforms,
    apply_unbold_to_runs,
    collect_transform_soft_breaks,
    compile_transforms,
    load_shared_transforms,
    segment_context,
    select_rules_for_volume,
)

NOTE_MARKER_RE = re.compile(r"\{\{(n(\d+)|\*|\+|\[\]|\(\)|sp1|sp3|sb|br)\}\}")

# Sandhi soft-break cache (roman → surface chunks); empty until ensure/load.
# ``_SANDHI_CACHE`` = DPD + curated overrides; ``_SANDHI_BREAKS`` = active map
# (cache merged with soft_breaks from shared transform rules).
_SANDHI_CACHE: dict[str, list[str]] | None = None
_SANDHI_BREAKS: dict[str, list[str]] | None = None
_SANDHI_ENABLED = True
_SANDHI_TRANSFORM_RULES_ID: int | None = None


def get_sandhi_breaks() -> dict[str, list[str]]:
    """Lazy-load / auto-build ``shared/sandhi_breaks.json`` for all generate modes."""
    global _SANDHI_BREAKS, _SANDHI_CACHE
    if _SANDHI_BREAKS is not None:
        return _SANDHI_BREAKS
    if _SANDHI_CACHE is None:
        _SANDHI_CACHE = ensure_sandhi_break_cache(quiet=False)
    _SANDHI_BREAKS = _SANDHI_CACHE
    return _SANDHI_BREAKS


def refresh_sandhi_with_transforms(rules: Sequence[TransformRule]) -> None:
    """Merge transform-rule ``soft_breaks`` onto the DPD/overrides cache.

    Call once per generate (and from ``build_body`` so unit tests see the same
    map). Later volume runs replace the extras; they do not accumulate.
    Skips work when ``rules`` is the same object already merged (generate
    calls this from ``build_body`` per segment).
    """
    global _SANDHI_BREAKS, _SANDHI_CACHE, _SANDHI_TRANSFORM_RULES_ID
    if not _SANDHI_ENABLED:
        return
    rules_id = id(rules)
    if (
        rules_id == _SANDHI_TRANSFORM_RULES_ID
        and _SANDHI_BREAKS is not None
    ):
        return
    if _SANDHI_CACHE is None:
        _SANDHI_CACHE = ensure_sandhi_break_cache(quiet=False)
    extra = collect_transform_soft_breaks(rules)
    _SANDHI_BREAKS = (
        merge_break_maps(_SANDHI_CACHE, extra) if extra else _SANDHI_CACHE
    )
    _SANDHI_TRANSFORM_RULES_ID = rules_id


def apply_sandhi_soft_breaks(thai: str, roman: str) -> str:
    """Insert ``{{sb}}`` at DPD sandhi boundaries for long tokens."""
    if not _SANDHI_ENABLED or not thai or not roman:
        return thai
    return inject_soft_breaks_in_thai(
        thai,
        roman,
        get_sandhi_breaks(),
        min_roman_len=DEFAULT_MIN_ROMAN_LEN,
    )


_TEX_FOOTNOTE_RE = re.compile(
    r"\\footnote\{[^{}]*\}|\\csromansharedfootnote\{[^{}]*\}\{[^{}]*\}"
)
_TEX_SYMBOL_FOOTNOTE_RE = re.compile(
    r"\\csromansymbolfootnote\{[^{}]*\}\{[^{}]*\}"
)
_TEX_TEXTBF_RE = re.compile(r"\\textbf\{([^{}]*)\}")
# Paragraph / folio ranges ``(12-13)`` / ``(12- 13)`` — TeX may break after ``-``.
_PAREN_NUM_RANGE_RE = re.compile(r"\(\d+\s*-\s*\d+\)")
_PAREN_NUM_RANGE_SPACE_RE = re.compile(r"\((\d+)\s*-\s*(\d+)\)")
# Dual refs ``(4, 24)`` / ``(4,24)`` — TeX may break after the comma space.
_PAREN_NUM_COMMA_RE = re.compile(r"\(\d+\s*,\s*\d+\)")
_PAREN_NUM_COMMA_SPACE_RE = re.compile(r"\((\d+)\s*,\s*(\d+)\)")

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
    """Escape TeX specials; keep paren number markers on one line via ``\\mbox``.

    Collapse spaces around the range hyphen (``(12- 13)`` → ``(12-13)``) so
    ``\\spaceskip`` does not open a wide word-gap inside the marker.
    Normalize dual comma refs (``(4,24)`` → ``(4, 24)``) and protect them
    the same way — TeX may otherwise break after the comma.
    """
    escaped = text.translate(_TEX_ESCAPE)

    def _protect_range(m: re.Match[str]) -> str:
        tight = _PAREN_NUM_RANGE_SPACE_RE.sub(r"(\1-\2)", m.group(0))
        return rf"\mbox{{{tight}}}"

    def _protect_comma(m: re.Match[str]) -> str:
        spaced = _PAREN_NUM_COMMA_SPACE_RE.sub(r"(\1, \2)", m.group(0))
        return rf"\mbox{{{spaced}}}"

    out = _PAREN_NUM_RANGE_RE.sub(_protect_range, escaped)
    return _PAREN_NUM_COMMA_RE.sub(_protect_comma, out)


def footnote_share_id(thai_body: str) -> str:
    """Stable ascii id for ``\\csromansharedfootnote`` (sha1 prefix)."""
    return hashlib.sha1(thai_body.encode("utf-8")).hexdigest()[:16]


def tex_numbered_footnote(thai_body: str) -> str:
    """Numbered footnote TeX; identical bodies share one mark per page."""
    escaped = escape_tex(thai_body)
    return (
        rf"\csromansharedfootnote{{{footnote_share_id(thai_body)}}}"
        rf"{{{escaped}}}"
    )


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
    rules: Sequence[TransformRule],
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
    rules: Sequence[TransformRule],
    *,
    page: int,
    order: int,
    segment_type: str,
    note_base_index: int = 0,
    emit_footnotes: bool = True,
) -> tuple[str, list[dict] | None, str, list[str]]:
    """Thai value (+ optional runs) after publication transforms on Roman.

    When transforms do not change the Roman string, reuse stored Thai / runs
    unless an ``unbold`` rule hits — then remap flags on Roman runs and
    re-derive Thai runs. When the Roman string changes, re-derive Thai via
    ``roman_to_thai`` and remap stored Roman bold runs through the same edit
    (then ``transliterate_runs``). Runs are dropped only when they cannot be
    aligned (join mismatch / no remaining bold).

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
    roman_runs = roman_runs_from_text_field(text)
    if new_roman != roman:
        roman_runs = remap_runs_through_edit(roman, new_roman, roman_runs)
        roman_runs = apply_unbold_to_runs(
            new_roman,
            roman_runs,
            rules,
            page=page,
            order=order,
            segment_type=segment_type,
        )
        thai_runs = transliterate_runs(roman_runs) if roman_runs else None
        return roman_to_thai(new_roman), thai_runs, new_roman, extra
    unbolded = apply_unbold_to_runs(
        roman,
        roman_runs,
        rules,
        page=page,
        order=order,
        segment_type=segment_type,
    )
    if unbolded is roman_runs:
        return (
            thai_of_text_field(text),
            thai_runs_of_text_field(text),
            new_roman,
            extra,
        )
    thai_runs = transliterate_runs(unbolded) if unbolded else None
    return thai_of_text_field(text), thai_runs, new_roman, extra


def transform_note_list(
    notes: list,
    rules: Sequence[TransformRule],
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
    rules: Sequence[TransformRule],
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

    Footnote prose is abbreviation-heavy (``Saṃ 1. 446``); do not run body
    pot-ma-gyi normalize — TeX uses ``\\frenchspacing`` instead.
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
    share the same mark emit ``\\csromansymbolmark`` only. ``{{[]}}`` /
    ``{{()}}`` emit ``\\csromansymbolfoottext`` (footer label, no body glyph)
    because the editorial ``[`` / ``(`` already marks the span.

    Legacy ``{{sp1}}`` / ``{{sp3}}`` are dropped (retired sentence spacers).
    ``apply_sentence_spacer`` is kept for call-site compatibility and ignored.
    """
    del apply_sentence_spacer  # retired; markers are always stripped
    thai = thai_digits_to_arabic(thai)
    thai, had_rule = split_trailing_section_rule(thai)
    parts: list[str] = []
    last = 0
    for m in NOTE_MARKER_RE.finditer(thai):
        parts.append(escape_tex(thai[last : m.start()]))
        token = m.group(1)
        if token in {"sp1", "sp3"}:
            # Retired: drop marker; keep following word space if present.
            if m.end() < len(thai) and thai[m.end()].isspace():
                parts.append("")
            else:
                parts.append(" ")
        elif token == "sb":
            # Explicit soft hyphen at a sandhi / compound boundary (DPD).
            # Works even with ``hyphenrules=nohyphenation``.
            parts.append(r"\-")
        elif token == "br":
            # Typesetter's manual line break inside a centered block (e.g.
            # pātimokkha-uddesa ``…dhammā`` / ``uddesaṃ āgacchanti.``). Under
            # ``\centering`` (``\csromancenter``) this starts a new centered
            # line; the surrounding spaces keep word separation on each line.
            parts.append(r"\\")
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
                if token in {"[]", "()"}:
                    # Body already has editorial ``[`` / ``(``; no second glyph.
                    parts.append(
                        rf"\csromansymbolfoottext{{{fn_mark}}}{{{body}}}"
                    )
                else:
                    parts.append(
                        rf"\csromansymbolfootnote{{{fn_mark}}}{{{body}}}"
                    )
            elif token in {"[]", "()"}:
                # Shared / missing: editorial brackets are the callout.
                parts.append("")
            else:
                # Shared callout (same * / + note) or mark without body.
                parts.append(rf"\csromansymbolmark{{{fn_mark}}}")
        else:
            idx = int(m.group(2))
            note = notes[idx] if 0 <= idx < len(notes) else f"[missing note {idx}]"
            parts.append(tex_numbered_footnote(note_to_thai(note)))
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
    rules: Sequence[TransformRule] | None = None,
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
        marked, sandhi_runs = _runs_after_sandhi(runs, roman)
        if sandhi_runs:
            body, had_rule = apply_notes_to_thai_runs(
                sandhi_runs,
                notes=notes,
                symbol_notes=symbol_notes,
                emitted_symbol_notes=emitted_symbol_notes,
                apply_sentence_spacer=apply_sp,
            )
        else:
            body, had_rule = apply_notes_to_thai(
                marked,
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
    # Editorial: …วคฺโค ปฐโม. always ends with the section rule (CS may omit
    # it when crowded against a footnote separator at the page foot).
    probe = roman or thai or _plain_closer_body(body)
    had_rule = ensure_ordinal_closer_section_rule(probe, had_rule)
    return body, had_rule


def _gatha_wak_thais(
    seg: dict,
    rules: Sequence[TransformRule],
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
    """Drop note *bodies*; keep callout width proxies for measure.

    Numbered / symbol markers become plain stand-ins (``1``, ``*``, ``+``).
    Prefer ``_gatha_string_to_measure_tex`` when emitting TeX — that uses
    ``\\textsuperscript`` so leftcol / pagewidth match body callouts.
    """

    def repl(m: re.Match[str]) -> str:
        token = m.group(1)
        if token in {"*", "+"}:
            return token
        if m.group(2) is not None:
            return "1"
        return ""

    return NOTE_MARKER_RE.sub(repl, thai)


def _gatha_string_to_measure_tex(thai: str) -> str:
    """Escape Thai for width measure; keep superscript callout proxies.

    Body lines use ``\\footnote`` / ``\\csromansymbolfootnote`` marks that add
    width. Measure must not drop them entirely or ``\\csromangathapagewidth`` /
    ``\\csromangathaleftcol`` run short and bat lines wrap (e.g. 03Vin03 p.55
    ``วิชานตนฺ”ติ.`` after ``อุสูยา`` + mark).
    """
    parts: list[str] = []
    last = 0
    for m in NOTE_MARKER_RE.finditer(thai or ""):
        parts.append(escape_tex((thai or "")[last : m.start()]))
        token = m.group(1)
        if token in {"*", "+"}:
            parts.append(rf"\textsuperscript{{{token}}}")
        elif m.group(2) is not None:
            parts.append(r"\textsuperscript{1}")
        # sp1 / sp3 / sb / [] / () — no letter width for verse measure
        last = m.end()
    parts.append(escape_tex((thai or "")[last:]))
    return "".join(parts)


def _runs_after_sandhi(
    runs: list[dict], roman: str
) -> tuple[str, list[dict] | None]:
    """Insert sandhi ``{{sb}}`` into Thai runs; remap bold through the edit.

    Returns ``(marked_thai, runs_or_none)``. Runs drop only when they cannot
    be aligned after the markers are inserted.
    """
    joined = "".join(str(r.get("value") or "") for r in runs if isinstance(r, dict))
    marked = apply_sandhi_soft_breaks(joined, roman)
    if marked == joined:
        return marked, runs
    return marked, remap_runs_through_edit(joined, marked, runs)


def _thai_with_sandhi(
    text_field: object,
    rules: Sequence[TransformRule],
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
        marked, sandhi_runs = _runs_after_sandhi(runs, roman)
        return marked, sandhi_runs, extra
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


def _gatha_text_field_bare(text: Any) -> str:
    """Prefer Thai then Roman value from a multi-script wak ``text`` field."""
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
        raw = thai or roman
    else:
        raw = str(text or "")
    bare = re.sub(r"\{\{[^}]+\}\}", "", raw)
    return bare.strip().rstrip("\"'\u201c\u201d")


def _gatha_wak_is_bat_left(text: Any) -> bool:
    """True when this left วรรค came from a ``A, B.`` printed pair (ends with ,)."""
    bare = _gatha_text_field_bare(text)
    return bool(bare) and bare.endswith(",")


def _gatha_printed_lines(
    seg: dict,
    rules: Sequence[TransformRule],
    *,
    note_base_index: int = 0,
    stack_bat_indices: AbstractSet[int] | None = None,
) -> tuple[list[GathaPrintedLine], list[str]]:
    """Raw printed lines for one บท (Thai string, bold runs, or bat pair).

    Returns ``(printed_lines, extra_notes)`` from editorial transform footnotes.

    ``stack_bat_indices``: บาท indexes that must print one วรรค per line because
    the pre-measured กลุ่ม pair would overflow the text block (see
    ``cs_roman_gatha_fit``).
    """
    page, order, kind = segment_context(seg)
    layout = seg.get("source_layout") or "bat_line"
    bats = seg.get("bats")
    stack = stack_bat_indices or frozenset()
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
            # bat_line / mixed: pair only when left วรรค ends with a comma.
            # mixed (and repair of false bat_line): stop-left บาท → one line
            # per วรรค so long singles are not forced into \csromangathabat.
            # Overflowing comma-left pairs are also stacked (group fit).
            pair_all = layout != "mixed"
            for bi, bat in enumerate(bats):
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
                    use_pair = pair_all or _gatha_wak_is_bat_left(
                        waks[0].get("text") if isinstance(waks[0], dict) else None
                    )
                    if use_pair and bi not in stack:
                        printed.append(GathaBatPrintedLine(left, right))
                    else:
                        printed.append(left)
                        printed.append(right)
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
    """TeX for width measure: no footnote *bodies*, but callout mark width."""
    if isinstance(payload, list):
        parts: list[str] = []
        for run in payload:
            piece = _gatha_string_to_measure_tex(str(run.get("value") or ""))
            if not piece:
                continue
            if run.get("bold"):
                parts.append(r"\textbf{" + piece + "}")
            else:
                parts.append(piece)
        return "".join(parts)
    return _gatha_string_to_measure_tex(payload)


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


def gatha_bat_tex(
    left: str,
    right: str,
    *,
    item: object | None = None,
    item_continuation: bool = False,
) -> str:
    """``\\csromangathabat{left}{right}`` for aligned bat_line บาท.

    With ``item``, emit ``\\csromangathaitembat{N}{left}{right}`` on the first
    printed line; later lines of the same บท use ``\\csromangathacontbat``.
    """
    if item is not None:
        return (
            rf"\csromangathaitembat{{{escape_tex(str(item))}}}"
            rf"{{{left}}}{{{right}}}"
        )
    if item_continuation:
        return rf"\csromangathacontbat{{{left}}}{{{right}}}"
    return rf"\csromangathabat{{{left}}}{{{right}}}"


def gatha_single_line_tex(
    body: str,
    *,
    item: object | None = None,
    item_continuation: bool = False,
) -> str:
    """Wak / stacked single line, optionally numbered like bat_line บท."""
    if item is not None:
        return rf"\csromangathaitemline{{{escape_tex(str(item))}}}{{{body}}}"
    if item_continuation:
        return rf"\csromangathacontline{{{body}}}"
    return body


def gatha_stanza_line_bodies(
    seg: dict,
    rules: Sequence[TransformRule] | None = None,
    *,
    emitted_symbol_notes: set[str] | None = None,
    for_measure: bool = False,
    stack_bat_indices: AbstractSet[int] | None = None,
) -> list[str]:
    """TeX bodies for each printed line of one บท.

    ``for_measure``: no footnote *bodies* (safe inside measure macros), but
    keeps superscript callout width so bat columns do not wrap short.
    Measure payloads also omit ``item`` labels — optical page/wak width is the
    verse body only; TeX pins numbers at the fixed ``\\proseitem`` column.
    bat_line pairs emit ``\\csromangathabat{left}{right}``.
    Numbered บท (``item``) use ``\\csromangathaitembat`` /
    ``\\csromangathacontbat`` (or wak ``…itemline`` / ``…contline``) so the
    label sits outside the shared left-วรรค column and does not shift with
    optical centering.
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
        seg,
        rules,
        note_base_index=len(notes),
        stack_bat_indices=stack_bat_indices,
    )
    notes = [*notes, *extra]
    if not printed:
        return []

    item = None if for_measure else seg.get("item")
    bodies: list[str] = []
    for i, line in enumerate(printed):
        line_item = item if i == 0 and item is not None else None
        line_cont = bool(item is not None and i > 0)
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
            bodies.append(
                gatha_bat_tex(
                    left,
                    right,
                    item=line_item,
                    item_continuation=line_cont,
                )
            )
            continue
        if for_measure:
            body = _gatha_payload_to_measure_tex(line)
        else:
            body = _gatha_payload_to_body_tex(
                line,
                notes=notes,
                symbol_notes=symbol_notes,
                emitted_symbol_notes=emitted_symbol_notes,
            )
        bodies.append(
            gatha_single_line_tex(
                body,
                item=line_item,
                item_continuation=line_cont,
            )
        )
    return bodies


def gatha_left_column_bodies(
    seg: dict,
    rules: Sequence[TransformRule] | None = None,
    *,
    stack_bat_indices: AbstractSet[int] | None = None,
) -> list[str]:
    """Left-วรรค TeX bodies for ``\\csromangathasetleft`` / measuregroup."""
    rules = rules or []
    printed, _ = _gatha_printed_lines(
        seg, rules, stack_bat_indices=stack_bat_indices
    )
    lefts: list[str] = []
    for line in printed:
        if isinstance(line, GathaBatPrintedLine):
            lefts.append(_gatha_payload_to_measure_tex(line.left))
    return lefts


def gatha_stack_indices_for_seg(
    stack_keys: AbstractSet[tuple[int, int]],
    seg_index: int,
) -> frozenset[int]:
    """Bat indexes to stack for one segment within a measured กลุ่ม."""
    return frozenset(bi for si, bi in stack_keys if si == seg_index)


def measure_gatha_group_stack_keys(
    segments: list[dict],
    start: int,
    end: int,
    *,
    mode: str,
    word_space: float | int,
) -> frozenset[tuple[int, int]]:
    """Pre-measure one กลุ่ม; keys are ``(seg_index, bat_index)`` to stack."""
    return gatha_group_stack_bat_keys(
        segments,
        start,
        end,
        mode=mode,
        word_space=float(word_space),
        wak_is_bat_left=_gatha_wak_is_bat_left,
        preamble_word_space=PREAMBLE_WORD_SPACE,
    )

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
        "tassuddānaṃ",
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


def _gatha_layout_name(layout: str | None) -> str:
    if layout in {"bat_line", "wak_line", "mixed"}:
        return layout
    return "bat_line"


def _is_gatha_one_and_half_pair(
    prev_bodies: list[str],
    next_bodies: list[str],
    *,
    prev_layout: str = "bat_line",
    next_layout: str = "bat_line",
) -> bool:
    """True for legacy 1 บทครึ่ง: full บท + half, same ``source_layout`` only.

    bat_line: 2 printed lines + 1; wak_line: 4 + 2; mixed: never merge.
    Never merge across styles (e.g. wak_line 4 + bat_line 2) — that is two
    บท and must keep ``\\gathastanzaskip``.
    """
    if _gatha_layout_name(prev_layout) != _gatha_layout_name(next_layout):
        return False
    layout = _gatha_layout_name(prev_layout)
    if layout == "mixed":
        return False
    if layout == "bat_line":
        return len(prev_bodies) == 2 and len(next_bodies) == 1
    return len(prev_bodies) == 4 and len(next_bodies) == 2


def format_gatha_group_inner(
    stanza_bodies: list[list[str]],
    stanza_layouts: list[str] | None = None,
) -> str:
    """Emit ``\\csromangathastanza{...}`` units for a breakable optical group.

    Each บท is its own unbreakable stanza box; TeX may page-break between
    them. Exception: 3-บาท / 1 บทครึ่ง (full + half, same layout) merges into
    one stanza (plain ``\\\\`` only — no break between full and half).

    ``wak_line`` bodies are wrapped in ``\\csromangathawak`` so the บท block is
    optically centered inside the shared page box (lines stay left-aligned in
    the wak-width box; all wak บท on the page share one axis). ``mixed`` keeps
    bat pairs + single-line วรรค in one stanza without the wak wrapper.
    """
    layouts = [
        _gatha_layout_name(
            stanza_layouts[i] if stanza_layouts and i < len(stanza_layouts) else None
        )
        for i in range(len(stanza_bodies))
    ]
    units: list[tuple[list[str], str]] = []
    i = 0
    while i < len(stanza_bodies):
        bodies = stanza_bodies[i]
        layout = layouts[i]
        if i + 1 < len(stanza_bodies) and _is_gatha_one_and_half_pair(
            bodies,
            stanza_bodies[i + 1],
            prev_layout=layout,
            next_layout=layouts[i + 1],
        ):
            units.append(([*bodies, *stanza_bodies[i + 1]], layout))
            i += 2
        else:
            units.append((bodies, layout))
            i += 1
    parts: list[str] = []
    for unit, layout in units:
        if not unit:
            continue
        inner = r" \\ ".join(unit)
        if layout == "wak_line":
            inner = rf"\csromangathawak{{{inner}}}"
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


def gatha_measure_wak_command(wak_lines: list[str]) -> str:
    """``\\csromangathameasurewak{lines}`` — raise shared wak block width."""
    return rf"\csromangathameasurewak{{{gatha_join_lines(wak_lines)}}}"


def gatha_set_left_command(left_lines: list[str]) -> str:
    """``\\csromangathasetleft{...}`` before rendering a bat_line กลุ่ม."""
    return rf"\csromangathasetleft{{{gatha_join_lines(left_lines)}}}"


def gatha_group_command(
    stanza_bodies: list[list[str]],
    stanza_layouts: list[str] | None = None,
) -> str:
    """One optically centered กลุ่ม (breakable between บท)."""
    return (
        rf"\csromangathagroup{{"
        rf"{format_gatha_group_inner(stanza_bodies, stanza_layouts)}}}"
    )


def gatha_group_with_closer_command(
    stanza_bodies: list[list[str]],
    closer_body: str,
    *,
    section_rule: bool = False,
    closer_tier: str = "leaf",
    stanza_layouts: list[str] | None = None,
) -> str:
    """Gāthā กลุ่ม + section closer (keep-with-previous; no orphan นิฏฺฐิตํ)."""
    name = _closer_macro_name(
        "csromangathagroupwithcloser",
        section_rule=section_rule,
        tier=closer_tier,
    )
    inner = format_gatha_group_inner(stanza_bodies, stanza_layouts)
    return rf"\{name}{{{inner}}}{{{closer_body}}}"


def gatha_group_measure_payloads(
    segments: list[dict],
    start: int,
    end: int,
    rules: Sequence[TransformRule] | None = None,
    *,
    stack_keys: AbstractSet[tuple[int, int]] | None = None,
) -> tuple[list[str], list[str], list[str]]:
    """``(left_column_lines, full_measure_lines, wak_measure_lines)``.

    ``wak_measure_lines`` are printed lines from ``wak_line`` บท only — used to
    size the shared centered wak block on the page.
    ``stack_keys``: ``(seg_index, bat_index)`` pairs that print one วรรค/line.
    """
    rules = rules or []
    keys = stack_keys or frozenset()
    left_lines: list[str] = []
    measure_lines: list[str] = []
    wak_lines: list[str] = []
    for j in range(start, end):
        seg = segments[j]
        if not is_gatha_segment(seg):
            continue
        stack = gatha_stack_indices_for_seg(keys, j)
        left_lines.extend(
            gatha_left_column_bodies(seg, rules, stack_bat_indices=stack)
        )
        bodies = gatha_stanza_line_bodies(
            seg, rules, for_measure=True, stack_bat_indices=stack
        )
        measure_lines.extend(bodies)
        if _gatha_layout_name(seg.get("source_layout")) == "wak_line":
            wak_lines.extend(bodies)
    return left_lines, measure_lines, wak_lines


def append_gatha_page_measures(
    lines: list[str],
    segments: list[dict],
    page: int,
    rules: Sequence[TransformRule] | None = None,
    *,
    mode: str = "sync",
    word_space: float | int | None = None,
) -> None:
    """Reset page/wak widths, then measure each gāthā กลุ่ม on ``page``."""
    rules = rules or []
    ws = float(
        word_space
        if word_space is not None
        else DEFAULT_LAYOUT["word_space"]
    )
    lines.append(r"\setlength{\csromangathapagewidth}{0pt}")
    lines.append(r"\setlength{\csromangathawakwidth}{0pt}")
    j = 0
    while j < len(segments):
        seg = segments[j]
        if int(seg.get("page") or 0) != page or not is_gatha_segment(seg):
            j += 1
            continue
        end = gatha_group_end_index(segments, j)
        stack_keys = measure_gatha_group_stack_keys(
            segments, j, end, mode=mode, word_space=ws
        )
        left_lines, measure_lines, wak_lines = gatha_group_measure_payloads(
            segments, j, end, rules, stack_keys=stack_keys
        )
        if measure_lines:
            lines.append(
                gatha_measure_group_command(left_lines, measure_lines)
            )
        if wak_lines:
            lines.append(gatha_measure_wak_command(wak_lines))
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
    rules: Sequence[TransformRule] | None = None,
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
_TEX_SOFT_HYPHEN_RE = re.compile(r"\\-")
_NIKAYA_PRELUDE_RE = re.compile(
    r"(?:นิกาย|nikāya)\s*$",
    re.IGNORECASE,
)


def is_gambhira_segment(kind: str | None, heading_kind: str | None) -> bool:
    """True for book / pāḷi title segments (``gambhīra`` / ``boo``)."""
    if str(kind or "") == "gambhīra":
        return True
    return str(heading_kind or "") == "boo"


def gambhira_identity_key(text: str) -> str:
    """Normalize a pāḷi title for dedupe / change detection.

    Soft hyphens, ``\\textbf``, footnotes, and whitespace are stripped so
    TeX body and raw Thai compare equal.
    """
    plain = _TEX_TEXTBF_RE.sub(r"\1", text or "")
    plain = strip_tex_footnotes(plain)
    plain = _TEX_SOFT_HYPHEN_RE.sub("", plain)
    plain = NOTE_MARKER_RE.sub("", plain)
    return re.sub(r"\s+", "", plain)


def segment_gambhira_key(
    seg: dict,
    rules: Sequence[TransformRule] | None = None,
) -> str | None:
    """Identity key for a gambhīra segment, or ``None`` if not gambhīra."""
    kind = str(seg.get("segment_type") or "")
    heading_kind = seg.get("heading_kind")
    heading_kind_s = str(heading_kind) if heading_kind is not None else None
    if not is_gambhira_segment(kind, heading_kind_s):
        return None
    # Prefer publication Thai (matches TeX body); fall back to Roman.
    title = toc_title_of(seg, rules)
    key = gambhira_identity_key(title)
    if key:
        return key
    roman = roman_value_from_text_field(seg.get("text")) or ""
    return gambhira_identity_key(roman) or None


def is_pali_open_prelude(kind: str | None, heading_kind: str | None, body: str) -> bool:
    """Nikāya / piṭaka label reprinted immediately before a new gambhīra."""
    kind_s = str(kind or "")
    hk = str(heading_kind or "")
    if kind_s == "piṭaka" or hk == "nik":
        return True
    plain = gambhira_identity_key(body)
    # Restore word boundaries lightly for the suffix check.
    plain_spaced = _TEX_TEXTBF_RE.sub(r"\1", body or "")
    plain_spaced = strip_tex_footnotes(plain_spaced)
    plain_spaced = _TEX_SOFT_HYPHEN_RE.sub("", plain_spaced)
    plain_spaced = NOTE_MARKER_RE.sub("", plain_spaced)
    plain_spaced = re.sub(r"\s+", " ", plain_spaced).strip()
    return bool(_NIKAYA_PRELUDE_RE.search(plain_spaced)) or bool(
        _NIKAYA_PRELUDE_RE.search(plain)
    )


def peek_next_gambhira_key(
    segments: list[dict],
    index: int,
    rules: Sequence[TransformRule] | None = None,
) -> str | None:
    """Next gambhīra identity within a short opening-stack window, else ``None``."""
    for j in range(index + 1, min(index + 6, len(segments))):
        seg = segments[j]
        if not isinstance(seg, dict):
            continue
        key = segment_gambhira_key(seg, rules)
        if key:
            return key
        kind = str(seg.get("segment_type") or "")
        # Stop at body / other structure so a distant gambhīra is not linked.
        if kind in {
            "prose",
            "prose_continuation",
            "verse",
            "verse_continuation",
            "gatha",
            "niṭṭhitaṃ",
            "chapter",
            "namakkāraṃ",
        }:
            return None
    return None


class PaliOpenTracker:
    """Track distinct pāḷi titles; open subsequent ones on a recto sheet.

    Printing/reading emit ``\\csromanpalirecto`` before a *new* gambhīra (and
    before its nikāya prelude). Exact gambhīra text repeats (source running
    headers mistagged as ``gambhīra``) are skipped in every mode.
    """

    def __init__(self, *, reading_like: bool) -> None:
        self.reading_like = reading_like
        self.last_key: str | None = None
        self._recto_pending = False

    def should_skip_gambhira(self, key: str) -> bool:
        return self.last_key is not None and key == self.last_key

    def maybe_recto_before_prelude(
        self,
        lines: list[str],
        *,
        kind: str | None,
        heading_kind: str | None,
        body: str,
        next_gambhira_key: str | None,
    ) -> None:
        if not self.reading_like or self._recto_pending:
            return
        if self.last_key is None:
            return
        if not next_gambhira_key or next_gambhira_key == self.last_key:
            return
        if not is_pali_open_prelude(kind, heading_kind, body):
            return
        lines.append(r"\csromanpalirecto")
        self._recto_pending = True

    def maybe_recto_before_gambhira(self, lines: list[str], key: str) -> None:
        if not self.reading_like:
            self.last_key = key
            self._recto_pending = False
            return
        if self.last_key is not None and not self._recto_pending:
            lines.append(r"\csromanpalirecto")
        self.last_key = key
        self._recto_pending = False


def apply_pali_open_tracking(
    tracker: PaliOpenTracker,
    lines: list[str],
    *,
    segments: list[dict],
    index: int,
    kind: str | None,
    heading_kind: str | None,
    body: str,
    rules: Sequence[TransformRule] | None = None,
) -> bool:
    """Emit recto opens / detect duplicate gambhīra.

    Returns True when this gambhīra should be skipped (same pāḷi already open).
    """
    if is_gambhira_segment(kind, heading_kind):
        key = gambhira_identity_key(body) or segment_gambhira_key(
            segments[index], rules
        )
        if not key:
            return False
        if tracker.should_skip_gambhira(key):
            return True
        tracker.maybe_recto_before_gambhira(lines, key)
        return False
    nxt = peek_next_gambhira_key(segments, index, rules)
    tracker.maybe_recto_before_prelude(
        lines,
        kind=kind,
        heading_kind=heading_kind,
        body=body,
        next_gambhira_key=nxt,
    )
    return False


def strip_tex_footnotes(text: str) -> str:
    """Drop numbered / symbol footnote commands for mark/split safety."""
    text = _TEX_SYMBOL_FOOTNOTE_RE.sub("", text)
    return _TEX_FOOTNOTE_RE.sub("", text)


def split_recto_compound_title(body: str) -> tuple[str, str] | None:
    """Split compound heading text into ``(h1, h2)`` for equal recto gaps.

    Body display stays one line; running head wants two fields separated by
    ``\\csromanheadsep`` (same as cha↔h1), not a narrow word-space inside one
    field. Returns plain titles (``\\textbf`` / footnotes stripped) or ``None``.

    Footnote bodies often contain edition refs like ``3. …`` / ``ขุ 4. 413``;
    those must not trigger a compound split (brace-tears marks → TeX fatal).
    """
    plain = _TEX_TEXTBF_RE.sub(r"\1", body)
    plain = strip_tex_footnotes(plain)
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
    """``\\csromanheader`` or compound marks + ``\\csromanheadernomark``.

    Mark fields are always footnote-free; body display keeps callouts.
    """
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
    rules: Sequence[TransformRule] | None = None,
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
    rules: Sequence[TransformRule] | None = None,
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
    rules: Sequence[TransformRule] | None = None,
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
    rules: Sequence[TransformRule] | None = None,
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
    rules: Sequence[TransformRule] | None = None,
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
    plain = _TEX_FOOTNOTE_RE.sub("", body or "")
    plain = _TEX_TEXTBF_RE.sub(r"\1", plain)
    return plain.strip()


def closer_tier_for_body(body: str) -> str:
    """Visual closer tier from closer body text (Thai or Roman)."""
    return classify_section_closer_tier(_plain_closer_body(body))


def _closer_macro_name(base: str, *, section_rule: bool, tier: str) -> str:
    """Build ``nitthitam`` / ``prosewithcloser`` family names for a tier."""
    t = tier if tier in {"leaf", "mid", "major"} else "leaf"
    if t == "leaf":
        name = base
    else:
        name = f"{base}{t}"
    if section_rule:
        name += "ruled"
    return name


def nitthitam_command(body: str, *, section_rule: bool = False, tier: str = "leaf") -> str:
    """Emit ``\\nitthitam`` / mid / major (+ ruled)."""
    name = _closer_macro_name("nitthitam", section_rule=section_rule, tier=tier)
    return rf"\{name}{{{body}}}"


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


_IDAM_CENTER_LABEL_RE = re.compile(
    r"^(?:Idaṃ|อิทํ)\s+\S+\.?$",
    re.IGNORECASE,
)


def is_idam_center_label(body: str) -> bool:
    """True for plain ``Idaṃ sabbamūlakaṃ`` / ``อิทํ ทสมูลกํ`` body labels."""
    plain = _TEX_TEXTBF_RE.sub(r"\1", body or "")
    plain = strip_tex_footnotes(plain)
    plain = re.sub(r"\s+", " ", plain).strip()
    return bool(_IDAM_CENTER_LABEL_RE.match(plain))


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

    Includes ``niṭṭhitaṃ``, ``title``+``section_rule`` (e.g. samattaṃ), short
    end formulas (นิฏฺฐิตํ / สมตฺตํ / สมตฺโต), and ordinal section closers
    (``…วคฺโค ปฐโม.`` — same stem as the open category head). Geometry /
    sandwich centers use ``\\csromancenter`` instead (see ``is_layout_center``).
    Long prose that only carries ``section_rule`` (e.g. Anāpatti formulas)
    stays body prose + rule.

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
        if is_section_closer_formula(plain):
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
    # Section closers win over mistagged ``heading_kind`` / center layout
    # (ordinal ``…วคฺโค ปฐโม.`` must not become ``\\csromanheader``).
    if is_section_closer(
        kind,
        body,
        section_rule=section_rule,
        item=item,
        source_layout=source_layout,
        section_no=section_no,
    ):
        kept = item if item is not None else last_item
        # Restore end rule for ordinal category closers (CS may omit it).
        if ensure_ordinal_closer_section_rule(_plain_closer_body(body), section_rule):
            section_rule = True
        tier = closer_tier_for_body(body)
        return nitthitam_command(body, section_rule=section_rule, tier=tier), kept
    # Prefer heading_kind for typography (compound chapter+h2 must not stay
    # locked to \\chapterhead just because segment_type is chapter).
    # Exception: plain ``Idaṃ …`` / ``อิทํ …`` centered labels stay
    # ``\\csromancenter`` even when fallback mistagged ``heading_kind``.
    page_macro = "chapterheadpageread" if reading_mode else "chapterheadpage"
    if heading_kind == "cha":
        macro = page_macro if chapter_page_start else "chapterhead"
        return rf"\{macro}{{{body}}}", None
    if heading_kind in _HEADING_KIND_MACRO:
        macro = _HEADING_KIND_MACRO[heading_kind]
        return rf"\{macro}{{{body}}}", None
    if heading_kind in _HEADER_LEVELS:
        if is_layout_center(
            kind, body, source_layout=source_layout, section_no=section_no
        ) and is_idam_center_label(body):
            kept = item if item is not None else last_item
            return rf"\csromancenter{{{body}}}", kept
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
    # Recitation topic-summary label (not a heading; allow bold).
    if kind == "tassuddānaṃ":
        kept = item if item is not None else last_item
        return rf"\csromancenter{{{body}}}", kept
    # Mid-content centered labels: prose leading (not the niṭṭhitaṃ band).
    # Keep item continuity — a mid-item centered label must not reset
    # last_item, or the next prose under the same Tipiṭaka number reprints N.
    if is_layout_center(
        kind, body, source_layout=source_layout, section_no=section_no
    ):
        kept = item if item is not None else last_item
        return rf"\csromancenter{{{body}}}", kept
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
_PAIRED_CLOSER_CMD_PREFIXES = (
    r"\prosewithcloser{",
    r"\prosewithcloserruled{",
    r"\prosewithclosermid{",
    r"\prosewithclosermidruled{",
    r"\prosewithclosermajor{",
    r"\prosewithclosermajorruled{",
    r"\proseitemwithcloser{",
    r"\proseitemwithcloserruled{",
    r"\proseitemwithclosermid{",
    r"\proseitemwithclosermidruled{",
    r"\proseitemwithclosermajor{",
    r"\proseitemwithclosermajorruled{",
    r"\prosecontwithcloser{",
    r"\prosecontwithcloserruled{",
    r"\prosecontwithclosermid{",
    r"\prosecontwithclosermidruled{",
    r"\prosecontwithclosermajor{",
    r"\prosecontwithclosermajorruled{",
    r"\csromangathagroupwithcloser{",
    r"\csromangathagroupwithcloserruled{",
    r"\csromangathagroupwithclosermid{",
    r"\csromangathagroupwithclosermidruled{",
    r"\csromangathagroupwithclosermajor{",
    r"\csromangathagroupwithclosermajorruled{",
)
# Back-compat alias (prose was the first paired-closer family).
_PROSE_CLOSER_CMD_PREFIXES = _PAIRED_CLOSER_CMD_PREFIXES


def is_prose_closer_command(cmd: str) -> bool:
    """True for body+closer paired macros (prose or gāthā กลุ่ม)."""
    return cmd.startswith(_PAIRED_CLOSER_CMD_PREFIXES)


def is_closer_tex_command(cmd: str) -> bool:
    """True for ``\\nitthitam*`` / body+closer units (deferred bottom air)."""
    return cmd.startswith(r"\nitthitam") or is_prose_closer_command(cmd)


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
    rules: Sequence[TransformRule],
    *,
    emitted_symbol_notes: set[str],
) -> tuple[str, bool] | None:
    """Return ``(closer_body, section_rule)`` when ``seg`` is a section closer.

    Builds the closer body once; callers must not call this twice for the same
    segment with a shared ``emitted_symbol_notes`` set. Mistagged
    ``heading_kind`` on ordinal / formula closers does not block pairing —
    ``is_section_closer`` is the gate. Ordinal category closers always report
    ``section_rule=True`` (editorial restoration when CS omitted the rule).

    Speculative probes must not pollute ``emitted_symbol_notes``: the next
    segment after a prose chain is often ordinary prose with ``{{[]}}`` /
    ``{{*}}`` (e.g. 01Vin01 §219 after §218). Building it as a closer
    candidate would mark the symbol emitted and starve the real body of its
    footnote (mark-only or empty).
    """
    kind = seg.get("segment_type") or "prose"
    layout = seg.get("source_layout")
    source_layout = str(layout) if layout else None
    probe = set(emitted_symbol_notes)
    body, section_rule = build_body(
        seg, rules, emitted_symbol_notes=probe
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
    emitted_symbol_notes.update(probe)
    section_rule = ensure_ordinal_closer_section_rule(
        _plain_closer_body(body), section_rule
    )
    return body, section_rule


def take_following_pairable_closer(
    segments: list[dict],
    index: int,
    rules: Sequence[TransformRule],
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


def take_two_line_category_closer(
    segments: list[dict],
    index: int,
    rules: Sequence[TransformRule],
    *,
    emitted_symbol_notes: set[str],
) -> tuple[dict, str, bool] | None:
    """Merge bare ``…วคฺโค.`` + following niṭṭhitaṃ into one mid closer.

    Example (13Sam02): ``โสตาปตฺติวคฺโค.`` + ``อฏฺฐารสเวยฺยากรณํ นิฏฺฐิตํ.``
    → one ``\\nitthitammid`` band (vagga tier). Returns
    ``(trailer_seg, merged_body, section_rule)`` or ``None``.
    """
    if index + 1 >= len(segments):
        return None
    label_seg = segments[index]
    trailer_seg = segments[index + 1]
    label_kind = label_seg.get("segment_type") or "prose"
    if label_kind in _CONTINUATION_KINDS:
        return None
    label_probe_notes: set[str] = set(emitted_symbol_notes)
    label_body, _label_rule = build_body(
        label_seg, rules, emitted_symbol_notes=label_probe_notes
    )
    label_body = with_section_no(label_seg, label_body)
    if not is_bare_category_closer_label(_plain_closer_body(label_body)):
        return None
    trailer_kind = trailer_seg.get("segment_type") or ""
    if trailer_kind in _CONTINUATION_KINDS:
        return None
    trailer_probe_notes: set[str] = set(emitted_symbol_notes)
    trailer_body, trailer_rule = build_body(
        trailer_seg, rules, emitted_symbol_notes=trailer_probe_notes
    )
    trailer_body = with_section_no(trailer_seg, trailer_body)
    plain_trailer = _plain_closer_body(trailer_body)
    if not (
        trailer_kind == "niṭṭhitaṃ"
        or is_section_closer_formula(plain_trailer)
    ):
        return None
    if (
        join_two_line_category_closer(
            _plain_closer_body(label_body), plain_trailer
        )
        is None
    ):
        return None
    emitted_symbol_notes.update(label_probe_notes)
    emitted_symbol_notes.update(trailer_probe_notes)
    merged = f"{label_body}\\\\{trailer_body}"
    trailer_rule = ensure_ordinal_closer_section_rule(plain_trailer, trailer_rule)
    return trailer_seg, merged, trailer_rule


def prose_with_closer_command(
    macro: str,
    prose_body: str,
    closer_body: str,
    *,
    item: object = None,
    section_rule: bool = False,
    closer_tier: str = "leaf",
) -> str:
    tier = closer_tier if closer_tier in {"leaf", "mid", "major"} else "leaf"
    if macro == "proseitem":
        item_tex = escape_tex(str(item))
        name = _closer_macro_name(
            "proseitemwithcloser", section_rule=section_rule, tier=tier
        )
        return rf"\{name}{{{item_tex}}}{{{prose_body}}}{{{closer_body}}}"
    if macro == "prosecont":
        name = _closer_macro_name(
            "prosecontwithcloser", section_rule=section_rule, tier=tier
        )
        return rf"\{name}{{{prose_body}}}{{{closer_body}}}"
    name = _closer_macro_name(
        "prosewithcloser", section_rule=section_rule, tier=tier
    )
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
    if kind == "gambhīra" or cmd.startswith(
        (
            r"\nitthitamruled{",
            r"\nitthitammidruled{",
            r"\nitthitammajorruled{",
        )
    ):
        return [cmd]
    if cmd.startswith(
        (
            r"\prosewithcloserruled{",
            r"\prosewithclosermidruled{",
            r"\prosewithclosermajorruled{",
            r"\proseitemwithcloserruled{",
            r"\proseitemwithclosermidruled{",
            r"\proseitemwithclosermajorruled{",
            r"\prosecontwithcloserruled{",
            r"\prosecontwithclosermidruled{",
            r"\prosecontwithclosermajorruled{",
            r"\csromangathagroupwithcloserruled{",
            r"\csromangathagroupwithclosermidruled{",
            r"\csromangathagroupwithclosermajorruled{",
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
    rules: Sequence[TransformRule] | None = None,
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
    rules: Sequence[TransformRule],
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
    last_was_closer = False
    emitted_symbol_notes: set[str] = set()
    gatha_measured_pages: set[int] = set()
    pali_tracker = PaliOpenTracker(reading_like=False)
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
        if is_gatha_segment(seg):
            end = gatha_group_end_index(segments, i)
            toc_marks += append_toc_marks(
                lines, segments[i:end], rules, planner=toc_planner
            )
            if page not in gatha_measured_pages:
                append_gatha_page_measures(
                    lines,
                    segments,
                    page,
                    rules,
                    mode="sync",
                    word_space=page_ws,
                )
                gatha_measured_pages.add(page)
            stack_keys = measure_gatha_group_stack_keys(
                segments, i, end, mode="sync", word_space=page_ws
            )
            left_lines, _, _ = gatha_group_measure_payloads(
                segments, i, end, rules, stack_keys=stack_keys
            )
            append_gatha_group_left(lines, left_lines)
            stanza_bodies: list[list[str]] = []
            stanza_layouts: list[str] = []
            group_ws: float | int | None = None
            mixed_ws = False
            for j in range(i, end):
                gseg = segments[j]
                bodies = gatha_stanza_line_bodies(
                    gseg,
                    rules,
                    emitted_symbol_notes=emitted_symbol_notes,
                    stack_bat_indices=gatha_stack_indices_for_seg(
                        stack_keys, j
                    ),
                )
                if bodies:
                    stanza_bodies.append(bodies)
                    stanza_layouts.append(
                        _gatha_layout_name(gseg.get("source_layout"))
                    )
                ws_j = seg_word_space(doc, gseg)
                if group_ws is None:
                    group_ws = ws_j
                elif ws_j is not None and float(ws_j) != float(group_ws or page_ws):
                    mixed_ws = True
            if stanza_bodies:
                paired_closer: dict | None = None
                closer_body = ""
                closer_rule = False
                taken = take_following_pairable_closer(
                    segments,
                    end - 1,
                    rules,
                    emitted_symbol_notes=emitted_symbol_notes,
                )
                if taken is not None:
                    paired_closer, closer_body, closer_rule = taken
                if paired_closer is not None:
                    cmd = gatha_group_with_closer_command(
                        stanza_bodies,
                        closer_body,
                        section_rule=closer_rule,
                        closer_tier=closer_tier_for_body(closer_body),
                        stanza_layouts=stanza_layouts,
                    )
                    toc_marks += append_toc_marks(
                        lines, paired_closer, rules, planner=toc_planner
                    )
                else:
                    cmd = gatha_group_command(stanza_bodies, stanza_layouts)
                wrap_seg = seg if not mixed_ws else seg
                wrap_ws = group_ws if not mixed_ws else None
                for out in wrap_word_space(
                    wrap_seg,
                    section_rule_commands(
                        cmd,
                        kind="gatha",
                        section_rule=closer_rule if paired_closer else False,
                    ),
                    page_word_space=page_ws,
                    segment_word_space=wrap_ws,
                ):
                    lines.append(out)
                if paired_closer is None:
                    lines.append("")
                for j in range(i, end):
                    g_item = segments[j].get("item")
                    if g_item is not None:
                        last_item = g_item
                last_was_layout_center = False
                last_was_closer = paired_closer is not None
                i = end + (1 if paired_closer is not None else 0)
                continue
            last_was_layout_center = False
            last_was_closer = False
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
            last_was_closer = False
            i += 1
            continue
        body, section_rule = build_body(
            seg, rules, emitted_symbol_notes=emitted_symbol_notes
        )
        body = with_section_no(seg, body)
        heading_kind = seg.get("heading_kind")
        if heading_kind is not None:
            heading_kind = str(heading_kind)
        if apply_pali_open_tracking(
            pali_tracker,
            lines,
            segments=segments,
            index=i,
            kind=kind,
            heading_kind=heading_kind,
            body=body,
            rules=rules,
        ):
            i += 1
            continue
        toc_marks += append_toc_marks(
            lines, seg, rules, planner=toc_planner
        )
        layout = seg.get("source_layout")
        prev_page = int(prev_seg.get("page") or 0) if prev_seg else None
        chapter_page_start = prev_page is None or prev_page != page
        paired_closer: dict | None = None
        closer_body = ""
        closer_rule = False
        two_line_closer: dict | None = None
        source_layout = str(layout) if layout else None
        two = take_two_line_category_closer(
            segments,
            i,
            rules,
            emitted_symbol_notes=emitted_symbol_notes,
        )
        if two is not None:
            two_line_closer, closer_body, closer_rule = two
            cmd = nitthitam_command(
                closer_body,
                section_rule=closer_rule,
                tier=closer_tier_for_body(closer_body),
            )
            if two_line_closer.get("item") is not None:
                last_item = two_line_closer.get("item")
            toc_marks += append_toc_marks(
                lines, two_line_closer, rules, planner=toc_planner
            )
            emit_section_rule = closer_rule
        elif (
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
                    closer_tier=closer_tier_for_body(closer_body),
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
        # Closer macros already defer ~parskip bottom air; do not stack
        # another \\tipitakaparskip before the following center label.
        if (
            is_center_cmd
            and not last_was_layout_center
            and not last_was_closer
        ):
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
        # Center / ตสฺสุทฺทานํ → gāthā: one paragraph gap only (gatha group
        # top \\addvspace{\\tipitakaparskip}). Do not stack 0.5\\baselineskip.
        last_was_layout_center = is_center_cmd
        last_was_closer = is_closer_tex_command(cmd)
        structural = {
            "piṭaka",
            "gambhīra",
            "namakkāraṃ",
            "chapter",
            "title",
            "tassuddānaṃ",
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
        i += 2 if (paired_closer is not None or two_line_closer is not None) else 1
    return lines, toc_marks


def generate_reading_lines(
    doc: dict,
    rules: Sequence[TransformRule],
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
    last_was_closer = False
    last_folio_marked: int | None = None
    emitted_symbol_notes: set[str] = set()
    pali_tracker = PaliOpenTracker(reading_like=True)
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

        if is_gatha_segment(seg):
            end = gatha_group_end_index_reading(segments, i)
            toc_marks += append_toc_marks(
                lines, segments[i:end], rules, planner=toc_planner
            )
            stack_keys = measure_gatha_group_stack_keys(
                segments, i, end, mode=mode, word_space=page_ws
            )
            left_lines, measure_lines, wak_lines = gatha_group_measure_payloads(
                segments, i, end, rules, stack_keys=stack_keys
            )
            if measure_lines:
                lines.append(r"\setlength{\csromangathapagewidth}{0pt}")
                lines.append(r"\setlength{\csromangathawakwidth}{0pt}")
                lines.append(
                    gatha_measure_group_command(left_lines, measure_lines)
                )
                if wak_lines:
                    lines.append(gatha_measure_wak_command(wak_lines))
                append_gatha_group_left(lines, left_lines)
            stanza_bodies: list[list[str]] = []
            stanza_layouts: list[str] = []
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
                    stack_bat_indices=gatha_stack_indices_for_seg(
                        stack_keys, j
                    ),
                )
                if bodies:
                    bodies[0], last_folio_marked = with_folio(
                        bodies[0], gpage, last_folio_marked
                    )
                    stanza_bodies.append(bodies)
                    stanza_layouts.append(
                        _gatha_layout_name(gseg.get("source_layout"))
                    )
                ws_j = seg_word_space(doc, gseg)
                if group_ws is None:
                    group_ws = ws_j
                elif ws_j is not None and float(ws_j) != float(group_ws or page_ws):
                    mixed_ws = True
            if stanza_bodies:
                paired_closer: dict | None = None
                closer_body = ""
                closer_rule = False
                taken = take_following_pairable_closer(
                    segments,
                    end - 1,
                    rules,
                    emitted_symbol_notes=emitted_symbol_notes,
                )
                if taken is not None:
                    paired_closer, closer_body, closer_rule = taken
                if paired_closer is not None:
                    cmd = gatha_group_with_closer_command(
                        stanza_bodies,
                        closer_body,
                        section_rule=closer_rule,
                        closer_tier=closer_tier_for_body(closer_body),
                        stanza_layouts=stanza_layouts,
                    )
                    toc_marks += append_toc_marks(
                        lines, paired_closer, rules, planner=toc_planner
                    )
                else:
                    cmd = gatha_group_command(stanza_bodies, stanza_layouts)
                wrap_ws = group_ws if not mixed_ws else None
                for out in wrap_word_space(
                    seg,
                    section_rule_commands(
                        cmd,
                        kind="gatha",
                        section_rule=closer_rule if paired_closer else False,
                    ),
                    page_word_space=page_ws,
                    segment_word_space=wrap_ws,
                ):
                    lines.append(out)
                if paired_closer is None:
                    lines.append("")
                for j in range(i, end):
                    g_item = segments[j].get("item")
                    if g_item is not None:
                        last_item = g_item
                last_was_layout_center = False
                last_was_closer = paired_closer is not None
                i = end + (1 if paired_closer is not None else 0)
                continue

            last_was_layout_center = False
            last_was_closer = False
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
            last_was_closer = False
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
        if apply_pali_open_tracking(
            pali_tracker,
            lines,
            segments=segments,
            index=i,
            kind=kind,
            heading_kind=heading_kind,
            body=body,
            rules=rules,
        ):
            i += 1
            continue

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
                    closer_tier=closer_tier_for_body(closer_body),
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
            last_was_closer = is_closer_tex_command(cmd)
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
        two = take_two_line_category_closer(
            segments,
            i,
            rules,
            emitted_symbol_notes=emitted_symbol_notes,
        )
        if two is not None:
            trailer_seg, merged_body, closer_rule = two
            cmd = nitthitam_command(
                merged_body,
                section_rule=closer_rule,
                tier=closer_tier_for_body(merged_body),
            )
            if trailer_seg.get("item") is not None:
                last_item = trailer_seg.get("item")
            toc_marks += append_toc_marks(
                lines, trailer_seg, rules, planner=toc_planner
            )
            emit_section_rule = closer_rule
            skip_next = True
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
                reading_mode=True,
            )
            emit_section_rule = section_rule
            skip_next = False
        is_center_cmd = cmd.startswith(r"\csromancenter")
        if (
            is_center_cmd
            and not last_was_layout_center
            and not last_was_closer
        ):
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
        # Center / ตสฺสุทฺทานํ → gāthā: one paragraph gap only (gatha group
        # top \\addvspace{\\tipitakaparskip}). Do not stack 0.5\\baselineskip.
        last_was_layout_center = is_center_cmd
        last_was_closer = is_closer_tex_command(cmd)
        structural = {
            "piṭaka",
            "gambhīra",
            "namakkāraṃ",
            "chapter",
            "title",
            "tassuddānaṃ",
            "niṭṭhitaṃ",
        }
        if (
            kind not in structural
            and heading_kind not in _STRUCTURAL_HEADING_KINDS
            and not cmd.startswith(r"\nitthitam")
            and not is_center_cmd
        ):
            lines.append("")
        i += 2 if skip_next else 1
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
    all_rules = load_shared_transforms()
    rules = compile_transforms(select_rules_for_volume(all_rules, volume_id))
    # DPD/overrides cache + soft_breaks from shared transform rules.
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
