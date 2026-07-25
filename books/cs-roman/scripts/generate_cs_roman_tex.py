#!/usr/bin/env python3
"""
Generate TeX body from cs-roman segments JSON (Thai script).

  python books/cs-roman/scripts/generate_cs_roman_tex.py --volume 01Vin01
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from paths import BOOKS, ensure_import_paths

ensure_import_paths()

from pali_script import Script, convert  # noqa: E402
from cs_roman_segments import (  # noqa: E402
    DEFAULT_LAYOUT,
    doc_layout,
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
)
from cs_roman_transforms import (  # noqa: E402
    TransformRule,
    apply_transforms,
    load_volume_transforms,
    segment_context,
)

NOTE_MARKER_RE = re.compile(r"\{\{(n(\d+)|\*|\+|sp1|sp3)\}\}")

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


def layout_apply_command(layout: dict) -> str:
    """Emit ``\\csromanlayoutapply`` for a full effective layout dict."""
    ws = layout.get("word_space", DEFAULT_LAYOUT["word_space"])
    return (
        r"\csromanlayoutapply"
        f"{{{word_space_factor(ws)}}}"
        f"{{{format_number(layout.get('line_space', DEFAULT_LAYOUT['line_space']))}}}"
        f"{{{layout.get('par_indent', DEFAULT_LAYOUT['par_indent'])}}}"
        f"{{{layout.get('par_skip', DEFAULT_LAYOUT['par_skip'])}}}"
        f"{{{layout.get('gatha_stanza_skip', DEFAULT_LAYOUT['gatha_stanza_skip'])}}}"
        f"{{{layout.get('gatha_indent', DEFAULT_LAYOUT['gatha_indent'])}}}"
        f"{{{layout.get('emergency_stretch', DEFAULT_LAYOUT['emergency_stretch'])}}}%"
    )


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
        return str(entry.get("value") or "")
    if isinstance(text, str):
        return convert(text, Script.ROMAN, Script.THAI)
    return ""


def thai_runs_of_text_field(text: object) -> list[dict] | None:
    """Optional Thai ``runs`` from the thai script entry."""
    entry = thai_entry_of_text_field(text)
    if entry is None:
        return None
    runs = entry.get("runs")
    if isinstance(runs, list) and runs:
        return runs
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


_THAI_DIGITS = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")


def note_to_thai(roman: str) -> str:
    """Transliterate note body; keep Arabic digits (catalog-style refs)."""
    if not roman:
        return ""
    # Same CS→Thai rules as body (incl. -pa- → ฯเปฯ).
    return roman_to_thai(roman).translate(_THAI_DIGITS)


def apply_notes_to_thai(
    thai: str,
    *,
    notes: list,
    symbol_notes: dict,
) -> tuple[str, bool]:
    """Embed footnotes into Thai body; return (tex, had_section_rule)."""
    thai, had_rule = split_trailing_section_rule(thai)
    parts: list[str] = []
    last = 0
    for m in NOTE_MARKER_RE.finditer(thai):
        parts.append(escape_tex(thai[last : m.start()]))
        token = m.group(1)
        if token in {"sp1", "sp3"}:
            # 1em after visible stop (``{{sp1}}``; pot-ma-gyi uses two).
            # ``{{sp3}}`` kept as legacy alias.
            parts.append(r"\csromanspacer{}")
        elif token in {"*", "+"}:
            note = symbol_notes.get(token) or f"[missing {token} note]"
            body = escape_tex(note_to_thai(note))
            parts.append(rf"\csromansymbolfootnote{{{token}}}{{{body}}}")
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
) -> tuple[str, bool]:
    """Like ``apply_notes_to_thai`` but wrap bold runs in ``\\textbf``."""
    parts: list[str] = []
    had_rule = False
    for run in runs:
        piece, rule = apply_notes_to_thai(
            str(run.get("value") or ""),
            notes=notes,
            symbol_notes=symbol_notes,
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
) -> tuple[str, bool]:
    """Thai body with notes → footnotes; TeX-escaped outside footnotes.

    ``{{nN}}`` → numbered ``\\footnote``; ``{{*}}``/``{{+}}`` → symbol footnotes
    that do not advance the numbered counter; ``{{sp1}}`` / legacy ``{{sp3}}``
    → ``\\csromanspacer``.

    Also returns whether a CS end-of-section rule should be drawn (from flag or
    leftover ``_____`` tails from PDF extraction).
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
    thai, runs = publication_thai_of_text_field(
        seg.get("text"),
        rules,
        page=page,
        order=order,
        segment_type=kind,
    )
    if runs:
        body, had_rule = apply_notes_to_thai_runs(
            runs, notes=notes, symbol_notes=symbol_notes
        )
    else:
        body, had_rule = apply_notes_to_thai(
            thai, notes=notes, symbol_notes=symbol_notes
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


def gatha_stanza_commands(
    seg: dict,
    rules: list[TransformRule] | None = None,
) -> list[str]:
    """
    Emit TeX lines for one บท from nested bats + source_layout.

    - bat_line: recombine each บาท's two วรรค onto one printed line (2 lines/บท)
    - wak_line: one วรรค per line (4 lines/บท); vspace only after the last
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
    layout = seg.get("source_layout") or "bat_line"
    bats = seg.get("bats")

    # Each printed line is either a plain Thai string or a runs list.
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

    if not printed:
        return []

    cmds: list[str] = []
    for i, line in enumerate(printed):
        # Segment-level notes only on the first printed line of the บท.
        line_notes = notes if i == 0 else []
        line_symbol = symbol_notes if i == 0 else {}
        if isinstance(line, list):
            body, _ = apply_notes_to_thai_runs(
                line, notes=line_notes, symbol_notes=line_symbol
            )
        else:
            body, _ = apply_notes_to_thai(
                line, notes=line_notes, symbol_notes=line_symbol
            )
        if i < len(printed) - 1:
            cmds.append(rf"\gatha{{{body}}}")
        else:
            cmds.append(rf"\gathaclose{{{body}}}")
    return cmds


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
    return escape_tex(plain)


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


def segment_command(
    kind: str,
    item: object,
    body: str,
    *,
    last_item: object,
    section_rule: bool = False,
    heading_kind: str | None = None,
) -> tuple[str, object]:
    """Return (tex_line, updated last_item used for numbering)."""
    if heading_kind in _HEADING_KIND_MACRO:
        macro = _HEADING_KIND_MACRO[heading_kind]
        return rf"\{macro}{{{body}}}", None
    if heading_kind in _HEADER_LEVELS:
        level = heading_kind[1]
        return rf"\csromanheader{{{level}}}{{{body}}}", None
    if kind == "piṭaka":
        return rf"\pitaka{{{body}}}", None
    if kind == "gambhīra":
        return rf"\gambhira{{{body}}}", None
    if kind == "namakkāraṃ":
        return rf"\namakkaram{{{body}}}", None
    if kind == "chapter":
        return rf"\chapterhead{{{body}}}", None
    if kind == "title":
        return rf"\titlehead{{{body}}}", None
    if kind == "niṭṭhitaṃ":
        if section_rule:
            return rf"\nitthitamruled{{{body}}}", None
        return rf"\nitthitam{{{body}}}", None
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


def generate(volume_id: str) -> Path:
    vol = BOOKS / "volumes" / volume_id
    data_path = vol / "data" / "segments.json"
    out_path = vol / "tex" / "body.generated.tex"
    if not data_path.is_file():
        raise FileNotFoundError(data_path)

    doc = load_document(data_path)
    rules = load_volume_transforms(volume_id)
    volume_layout = doc_layout(doc)
    segments = list(doc.get("segments") or [])
    # Keep page order stable even if a few note segments were appended late.
    segments.sort(
        key=lambda seg: (
            int(seg.get("page") or 0),
            int(seg.get("order") or 0),
        )
    )
    toc_marks = 0
    lines: list[str] = [
        "% Auto-generated from data/segments.json + layout.json"
        " (+ transforms) — do not edit by hand.",
        f"% volume: {volume_id}",
        f"% segments: {len(segments)}",
        f"% transform_rules: {len(rules)}",
        "",
        "% Volume layout defaults (layout.json ``layout``).",
        layout_apply_command(volume_layout),
        "",
    ]
    current_page: int | None = None
    current_layout = volume_layout
    last_item: object = None
    for seg in segments:
        page = int(seg.get("page") or 1)
        page_layout = effective_layout(doc, page)
        if current_page is None:
            lines.append(rf"\setcounter{{page}}{{{page}}}")
            if page_layout != current_layout:
                lines.append(layout_apply_command(page_layout))
                current_layout = page_layout
            current_page = page
        elif page != current_page:
            lines.append(rf"\csromanpage{{{page}}}")
            if page_layout != current_layout:
                lines.append(layout_apply_command(page_layout))
                current_layout = page_layout
            current_page = page
        page_ws = effective_word_space(doc, {}, page=page)
        seg_ws = seg_word_space(doc, seg)
        kind = seg.get("segment_type") or "prose"
        if kind in {"gatha", "gatha_continuation"}:
            for cmd in wrap_word_space(
                seg,
                gatha_stanza_commands(seg, rules),
                page_word_space=page_ws,
                segment_word_space=seg_ws,
            ):
                lines.append(cmd)
            lines.append("")
            last_item = None
            continue
        hang_cmds = hanging_line_commands(seg, rules)
        if hang_cmds:
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
            continue
        body, section_rule = build_body(seg, rules)
        toc_cmd = toc_mark_command(seg, rules)
        if toc_cmd:
            lines.append(toc_cmd)
            toc_marks += 1
        heading_kind = seg.get("heading_kind")
        if heading_kind is not None:
            heading_kind = str(heading_kind)
        cmd, last_item = segment_command(
            kind,
            seg.get("item"),
            body,
            last_item=last_item,
            section_rule=section_rule,
            heading_kind=heading_kind,
        )
        for line in wrap_word_space(
            seg,
            [cmd],
            page_word_space=page_ws,
            segment_word_space=seg_ws,
        ):
            lines.append(line)
        # No blank line after title-stack / structural heads — a blank line
        # becomes \par + \parskip and inflates the measured CS Roman gaps.
        structural = {
            "piṭaka",
            "gambhīra",
            "namakkāraṃ",
            "chapter",
            "title",
            "niṭṭhitaṃ",
        }
        if kind not in structural and heading_kind not in _STRUCTURAL_HEADING_KINDS:
            lines.append("")

    # Annotate header after counting TOC marks.
    for i, line in enumerate(lines):
        if line.startswith("% transform_rules:"):
            lines.insert(i + 1, f"% toc_marks: {toc_marks}")
            break
    else:
        if len(lines) > 2 and lines[2].startswith("% segments:"):
            lines.insert(3, f"% toc_marks: {toc_marks}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--volume", default="01Vin01")
    args = parser.parse_args(argv)
    path = generate(args.volume)
    print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
