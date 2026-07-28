#!/usr/bin/env python3
"""
Generate TeX body from cs-roman segments JSON (Thai script).

  python books/cs-roman/scripts/generate_cs_roman_tex.py --volume 01Vin01
  python books/cs-roman/scripts/generate_cs_roman_tex.py --volume 01Vin01 --mode reading
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from paths import BOOKS, OUTPUT_DIR, ensure_import_paths

ensure_import_paths()

from cs_roman_segments import (  # noqa: E402
    DEFAULT_LAYOUT,
    doc_layout,
    doc_page_layout_reading,
    effective_layout,
    effective_word_space,
    load_document,
    seg_flags,
    seg_notes,
    seg_symbol_notes,
    seg_word_space,
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
    load_volume_transforms,
    segment_context,
)

NOTE_MARKER_RE = re.compile(r"\{\{(n(\d+)|\*|\+|sp1|sp3)\}\}")
# Short end-of-section formulas (Thai body): lesser structural band, not prose.
_CLOSER_FORMULA_RE = re.compile(
    r"(?:นิฏฺฐิต[าโตํ]|สมตฺตํ)\s*\.?$"
)
_TEX_FOOTNOTE_RE = re.compile(r"\\footnote\{[^{}]*\}")
_TEX_TEXTBF_RE = re.compile(r"\\textbf\{([^{}]*)\}")

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
    }
)


# Match preamble.tex babelfont WordSpace (absolute multiplier on Sarabun).
# Font glue already includes this; layout/segment targets scale against it.
PREAMBLE_WORD_SPACE = float(DEFAULT_LAYOUT["word_space"])


def escape_tex(text: str) -> str:
    return text.translate(_TEX_ESCAPE)


def format_number(value: float | int | str) -> str:
    """TeX-safe numeric factor (no trailing .0 noise)."""
    f = float(value)
    if f == int(f):
        return str(int(f))
    return f"{f:g}"


def format_word_space(value: float | int) -> str:
    return format_number(value)


def word_space_factor(target: float | int) -> str:
    """Scale so ``spaceskip = factor × fontdimen`` matches absolute WordSpace."""
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

    Override source: ``page_layout[page].segments[n]`` (via ``doc``), or an
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


def publication_thai_of_text_field(
    text: object,
    rules: list[TransformRule],
    *,
    page: int,
    order: int,
    segment_type: str,
) -> tuple[str, list[dict] | None]:
    """Thai value (+ optional runs) after publication transforms on Roman.

    When transforms do not change the Roman string, reuse stored Thai / runs.
    When they do, re-derive Thai via ``roman_to_thai`` (bold runs dropped).
    """
    roman = roman_value_from_text_field(text)
    new_roman = apply_transforms(
        roman,
        rules,
        page=page,
        order=order,
        segment_type=segment_type,
    )
    if new_roman == roman:
        return thai_of_text_field(text), thai_runs_of_text_field(text)
    return roman_to_thai(new_roman), None


def transform_note_list(
    notes: list,
    rules: list[TransformRule],
    *,
    page: int,
    order: int,
    segment_type: str,
) -> list:
    return [
        apply_transforms(
            str(n or ""),
            rules,
            page=page,
            order=order,
            segment_type=segment_type,
        )
        for n in notes
    ]


def transform_symbol_notes(
    symbol_notes: dict,
    rules: list[TransformRule],
    *,
    page: int,
    order: int,
    segment_type: str,
) -> dict:
    return {
        key: apply_transforms(
            str(value or ""),
            rules,
            page=page,
            order=order,
            segment_type=segment_type,
        )
        for key, value in symbol_notes.items()
    }


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
                # 0.5em after visible stop (``{{sp1}}``; pot-ma-gyi uses two).
                # ``{{sp3}}`` kept as legacy alias.
                parts.append(r"\csromanspacer{}")
            elif m.end() < len(thai) and thai[m.end()].isspace():
                parts.append("")
            else:
                parts.append(" ")
        elif token in {"*", "+"}:
            note = symbol_notes.get(token)
            already = (
                emitted_symbol_notes is not None and token in emitted_symbol_notes
            )
            if note and not already:
                if emitted_symbol_notes is not None:
                    emitted_symbol_notes.add(token)
                body = escape_tex(note_to_thai(note))
                parts.append(rf"\csromansymbolfootnote{{{token}}}{{{body}}}")
            else:
                # Shared callout (same * / + note) or mark without body yet.
                parts.append(rf"\csromansymbolmark{{{token}}}")
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

    Also returns whether a CS end-of-section rule should be drawn (from flag or
    leftover ``_____`` tails from PDF extraction).
    """
    rules = rules or []
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
    thai, runs = publication_thai_of_text_field(
        seg.get("text"),
        rules,
        page=page,
        order=order,
        segment_type=kind,
    )
    if runs:
        body, had_rule = apply_notes_to_thai_runs(
            runs,
            notes=notes,
            symbol_notes=symbol_notes,
            emitted_symbol_notes=emitted_symbol_notes,
            apply_sentence_spacer=apply_sp,
        )
    else:
        body, had_rule = apply_notes_to_thai(
            thai,
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
) -> list[str]:
    """Ordered วรรค Thai strings from nested bats, or one legacy line."""
    page, order, kind = segment_context(seg)
    bats = seg.get("bats")
    if isinstance(bats, list) and bats:
        out: list[str] = []
        for bat in bats:
            for wak in bat.get("waks") or []:
                thai, _ = publication_thai_of_text_field(
                    wak.get("text"),
                    rules,
                    page=page,
                    order=order,
                    segment_type=kind,
                )
                out.append(thai)
        return out
    thai, _ = publication_thai_of_text_field(
        seg.get("text"),
        rules,
        page=page,
        order=order,
        segment_type=kind,
    )
    return [thai] if thai else []


_GATHA_KINDS = frozenset({"gatha", "gatha_continuation"})
_CONTINUATION_KINDS = frozenset({"prose_continuation", "verse_continuation"})
_PROSE_FLOW_KINDS = frozenset(
    {"prose", "verse", "prose_continuation", "verse_continuation"}
)
_GENERATE_MODES = frozenset({"sync", "reading"})


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


def _gatha_printed_lines(
    seg: dict,
    rules: list[TransformRule],
) -> list[str | list[dict]]:
    """Raw printed lines for one บท (Thai string or bold runs per line)."""
    page, order, kind = segment_context(seg)
    layout = seg.get("source_layout") or "bat_line"
    bats = seg.get("bats")
    printed: list[str | list[dict]] = []
    if isinstance(bats, list) and bats:
        if layout == "wak_line":
            for bat in bats:
                for wak in bat.get("waks") or []:
                    thai, runs = publication_thai_of_text_field(
                        wak.get("text"),
                        rules,
                        page=page,
                        order=order,
                        segment_type=kind,
                    )
                    if runs:
                        printed.append(runs)
                    else:
                        printed.append(thai)
        else:
            # bat_line (default): join วรรค within each บาท with a space.
            for bat in bats:
                waks = list(bat.get("waks") or [])
                wak_payloads: list[tuple[str, list[dict] | None]] = []
                for w in waks:
                    wak_payloads.append(
                        publication_thai_of_text_field(
                            w.get("text"),
                            rules,
                            page=page,
                            order=order,
                            segment_type=kind,
                        )
                    )
                if waks and all(runs is not None for _, runs in wak_payloads):
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
        printed = list(_gatha_wak_thais(seg, rules))
    return printed


def gatha_stanza_line_bodies(
    seg: dict,
    rules: list[TransformRule] | None = None,
    *,
    emitted_symbol_notes: set[str] | None = None,
    for_measure: bool = False,
) -> list[str]:
    """TeX bodies for each printed line of one บท.

    ``for_measure``: no footnote macros (safe inside ``\\csromangathameasure``).
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
    printed = _gatha_printed_lines(seg, rules)
    if not printed:
        return []

    bodies: list[str] = []
    for line in printed:
        if for_measure:
            if isinstance(line, list):
                parts: list[str] = []
                for run in line:
                    piece = escape_tex(
                        _strip_note_markers_for_measure(str(run.get("value") or ""))
                    )
                    if not piece:
                        continue
                    if run.get("bold"):
                        parts.append(r"\textbf{" + piece + "}")
                    else:
                        parts.append(piece)
                bodies.append("".join(parts))
            else:
                bodies.append(escape_tex(_strip_note_markers_for_measure(line)))
            continue
        # Note markers ({{nN}} / {{*}} / {{+}}) may sit on any วรรค/บาท line.
        if isinstance(line, list):
            body, _ = apply_notes_to_thai_runs(
                line,
                notes=notes,
                symbol_notes=symbol_notes,
                emitted_symbol_notes=emitted_symbol_notes,
            )
        else:
            body, _ = apply_notes_to_thai(
                line,
                notes=notes,
                symbol_notes=symbol_notes,
                emitted_symbol_notes=emitted_symbol_notes,
            )
        bodies.append(body)
    return bodies


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
    """Join บท lines with ``\\\\``; between บท use ``\\\\[\\gathastanzaskip]``.

    Exception: 3-บาท / 1 บทครึ่ง (full + half) stays a continuous block —
    plain ``\\\\`` only, no ``\\\\[\\gathastanzaskip]``.
    """
    parts: list[str] = []
    for i, bodies in enumerate(stanza_bodies):
        for j, body in enumerate(bodies):
            parts.append(body)
            if j < len(bodies) - 1:
                parts.append(r" \\ ")
            elif i < len(stanza_bodies) - 1:
                nxt = stanza_bodies[i + 1]
                if _is_gatha_one_and_half_pair(bodies, nxt):
                    parts.append(r" \\ ")
                else:
                    parts.append(r" \\[\gathastanzaskip] ")
    return "".join(parts)


def gatha_measure_command(measure_lines: list[str]) -> str:
    """``\\csromangathameasure`` from all printed lines on a page."""
    joined = r" \\ ".join(measure_lines)
    return rf"\csromangathameasure{{{joined}}}"


def gatha_group_command(stanza_bodies: list[list[str]]) -> str:
    """One optically centered กลุ่ม (``\\csromangathagroup``)."""
    return rf"\csromangathagroup{{{format_gatha_group_inner(stanza_bodies)}}}"


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

# memoir TOC levels written via \csromantocmark when in_toc is true.
_TOC_LEVEL = {
    "nik": "chapter",
    "boo": "chapter",
    "cha": "section",
    "h1": "subsection",
    "h2": "subsubsection",
    "h3": "paragraph",
    "h4": "subparagraph",
    "h5": "subparagraph",
    "h6": "subparagraph",
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
    thai, _ = publication_thai_of_text_field(
        seg.get("text"),
        rules,
        page=page,
        order=order,
        segment_type=kind,
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


class MatikaTocPlanner:
    """
    Body-anchored TOC marks from ``matika.json``, preserving outline order.

    Entries emit in ``matika.json`` sequence (not body visit order):

    - ``matched_order`` → when that segment is visited
    - unmatched with ``page`` → after prior outline rows, once any segment on
      that printed page has been visited (including ``*_continuation``)

    This keeps parents (book / kaṇḍa) before page-anchored children that share
    an early folio (e.g. Verañjakaṇḍa before Bhagavato paribhavakathā).
    """

    def __init__(self, matika_doc: dict, segments: list[dict]) -> None:
        del segments  # API stable; anchors come from entry fields + visit stream
        self._entries: list[dict] = [
            e for e in (matika_doc.get("entries") or []) if isinstance(e, dict)
        ]
        self._next = 0
        self._visited_pages: set[int] = set()

    def marks_for_segment(self, seg: dict) -> list[str]:
        order = seg.get("order")
        page = seg.get("page")
        if order is None:
            return []
        order_i = int(order)
        if page is not None and page != "":
            self._visited_pages.add(int(page))

        out: list[str] = []
        while self._next < len(self._entries):
            entry = self._entries[self._next]
            matched = entry.get("matched_order")
            if matched is not None and matched != "":
                matched_i = int(matched)
                if matched_i < order_i:
                    # Anchor already passed (outline/match inversion, e.g. a
                    # late book title rematched to an early gambhīra
                    # segment). We can no longer emit it at its own segment,
                    # but still surface it here rather than dropping it
                    # silently, so no matched entry ever vanishes from the
                    # PDF outline.
                    cmd = matika_toc_mark(entry)
                    if cmd:
                        out.append(cmd)
                    self._next += 1
                    continue
                if matched_i != order_i:
                    break
                cmd = matika_toc_mark(entry)
                if cmd:
                    out.append(cmd)
                self._next += 1
                continue

            entry_page = entry.get("page")
            if entry_page is not None and entry_page != "":
                if int(entry_page) not in self._visited_pages:
                    break
                cmd = matika_toc_mark(entry)
                if cmd:
                    out.append(cmd)
                self._next += 1
                continue

            # Structural row with neither match nor page: skip (cannot anchor).
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
        thai, runs = publication_thai_of_text_field(
            hl,
            rules,
            page=page,
            order=order,
            segment_type=kind,
        )
        if runs:
            piece, _ = apply_notes_to_thai_runs(
                runs, notes=[], symbol_notes={}
            )
        else:
            piece, _ = apply_notes_to_thai(thai, notes=[], symbol_notes={})
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
) -> tuple[str, object]:
    """Return (tex_line, updated last_item used for numbering)."""
    # Prefer heading_kind for typography (compound chapter+h2 must not stay
    # locked to \\chapterhead just because segment_type is chapter).
    if heading_kind == "cha":
        macro = "chapterheadpage" if chapter_page_start else "chapterhead"
        return rf"\{macro}{{{body}}}", None
    if heading_kind in _HEADING_KIND_MACRO:
        macro = _HEADING_KIND_MACRO[heading_kind]
        return rf"\{macro}{{{body}}}", None
    if heading_kind in _HEADER_LEVELS:
        level = heading_kind[1]
        return rf"\csromanheader{{{level}}}{{{body}}}", None
    if kind == "chapter":
        macro = "chapterheadpage" if chapter_page_start else "chapterhead"
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
    """Page-synced body: ``\\csromanpage`` + optional ``page_layout``."""
    toc_marks = 0
    lines = _body_header_lines(
        volume_id,
        mode="sync",
        segment_count=len(segments),
        rule_count=len(rules),
        volume_layout=volume_layout,
    )
    current_page: int | None = None
    current_layout = volume_layout
    last_item: object = None
    last_was_layout_center = False
    emitted_symbol_notes: set[str] = set()
    gatha_measured_pages: set[int] = set()
    i = 0
    while i < len(segments):
        seg = segments[i]
        page = int(seg.get("page") or 1)
        page_layout = effective_layout(doc, page)
        if current_page is None:
            lines.append(rf"\setcounter{{page}}{{{page}}}")
            if page_layout != current_layout:
                lines.append(layout_apply_command(page_layout))
                current_layout = page_layout
            current_page = page
            emitted_symbol_notes = set()
        elif page != current_page:
            lines.append(rf"\csromanpage{{{page}}}")
            if page_layout != current_layout:
                lines.append(layout_apply_command(page_layout))
                current_layout = page_layout
            current_page = page
            emitted_symbol_notes = set()
        page_ws = effective_word_space(doc, {}, page=page)
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
                measure_lines: list[str] = []
                for s in segments:
                    if int(s.get("page") or 0) != page or not is_gatha_segment(s):
                        continue
                    measure_lines.extend(
                        gatha_stanza_line_bodies(s, rules, for_measure=True)
                    )
                if measure_lines:
                    lines.append(gatha_measure_command(measure_lines))
                gatha_measured_pages.add(page)
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
        cmd, last_item = segment_command(
            kind,
            seg.get("item"),
            body,
            last_item=last_item,
            section_rule=section_rule,
            heading_kind=heading_kind,
            source_layout=str(layout) if layout else None,
            section_no=seg.get("section_no"),
            chapter_page_start=chapter_page_start,
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


def generate_reading_lines(
    doc: dict,
    rules: list[TransformRule],
    volume_id: str,
    segments: list[dict],
    volume_layout: dict,
    *,
    toc_planner: MatikaTocPlanner | None = None,
) -> tuple[list[str], int]:
    """Continuous body: merge continuations; ``\\csromanfolio`` at folio changes."""
    toc_marks = 0
    lines = _body_header_lines(
        volume_id,
        mode="reading",
        segment_count=len(segments),
        rule_count=len(rules),
        volume_layout=volume_layout,
    )
    # Sync page_layout is ignored; physical-page overrides via reading_mode map.
    lines.extend(reading_page_layout_setup_lines(doc, volume_layout))
    page_ws = float(volume_layout.get("word_space") or DEFAULT_LAYOUT["word_space"])
    last_item: object = None
    last_was_layout_center = False
    last_folio_marked: int | None = None
    emitted_symbol_notes: set[str] = set()
    i = 0
    while i < len(segments):
        seg = segments[i]
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
            measure_lines: list[str] = []
            for j in range(i, end):
                measure_lines.extend(
                    gatha_stanza_line_bodies(
                        segments[j], rules, for_measure=True
                    )
                )
            if measure_lines:
                lines.append(gatha_measure_command(measure_lines))
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
            # Visit every row in the merge (including page-opening
            # continuations) so page-anchored Mātikā landmarks are not dropped.
            toc_marks += append_toc_marks(
                lines, segments[i:end], rules, planner=toc_planner
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
            )
            for line in wrap_word_space(
                seg,
                section_rule_commands(
                    cmd, kind=kind, section_rule=section_rule
                ),
                page_word_space=page_ws,
                segment_word_space=seg_ws,
            ):
                lines.append(line)
            lines.append("")
            last_was_layout_center = False
            i = end
            continue

        toc_marks += append_toc_marks(
            lines, seg, rules, planner=toc_planner
        )
        # Headings / closers / centers: no margin folio (defer to next body).
        if is_reading_folio_body(
            seg,
            kind,
            body,
            section_rule=section_rule,
            heading_kind=heading_kind,
        ):
            body, last_folio_marked = with_folio(body, page, last_folio_marked)
        # Same rule as sync: cha / chapter that opens a source folio uses
        # \chapterheadpage (recto, plain, top pad). Opening-stack cha on the
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
    else:
        out_path = vol / "tex" / "body.generated.tex"
    if not data_path.is_file():
        raise FileNotFoundError(data_path)

    doc = load_document(data_path)
    rules = load_volume_transforms(volume_id)
    volume_layout = doc_layout(doc)
    segments = _sorted_segments(doc)
    matika_doc = load_matika(volume_id)
    toc_planner = (
        MatikaTocPlanner(matika_doc, segments) if matika_doc else None
    )
    if mode == "reading":
        lines, toc_marks = generate_reading_lines(
            doc,
            rules,
            volume_id,
            segments,
            volume_layout,
            toc_planner=toc_planner,
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
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--volume", default="01Vin01")
    parser.add_argument(
        "--mode",
        choices=sorted(_GENERATE_MODES),
        default="sync",
        help="sync: page-faithful sheets; reading: continuous + margin folios",
    )
    args = parser.parse_args(argv)
    path = generate(args.volume, mode=args.mode)
    print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
