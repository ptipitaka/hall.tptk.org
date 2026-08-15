"""
Extract Tipitaka segment candidates from a cs-roman PDF text layer.

Pipeline:
  1. Read PDF text with PyMuPDF (fitz)
  2. Convert VZTime font encoding → Unicode (cs_roman_vztime)
  3. Detect volume-wide running headers (page-top labels across all body pages)
  4. Split into paragraphs, detect item numbers / headings / notes
     (peel running headers glued onto body when PDF omits blank lines;
      peel page-top header + edition folio clusters across blank lines;
      peel uddāna labels glued to verse lines similarly)
  5. Page-anchor segments; geometry upgrades flush page-starts → {kind}_continuation
  6. Attach footnotes to the segment where the callout appears ({{n0}})
  7. Tag uddāna/gāthā runs (title + gāthā-indent geometry); group into บท→บาท→วรรค
  8. Geometry: short centered labels → source_layout='center'
  9. Demote false heading guesses (speech-intro dash; weak+not centered)
  10. Write JSON for study / later import

Encoding note: anusvara uses ṃ (e.g. saṃghena), not ṅ before g.

Example (Docker):
  docker compose exec -T web python books/cs-roman/scripts/extract_cs_roman_pdf.py \\
      books/cs-roman/source/01Vin01.pdf \\
      --content-start 24 \\
      -o books/cs-roman/output/01Vin01.segments.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

try:
    import fitz
except ImportError:  # pragma: no cover
    print(
        "PyMuPDF (pymupdf) is required. Install with: pip install pymupdf",
        file=sys.stderr,
    )
    raise

from paths import OUTPUT_DIR, ensure_import_paths, repo_relative

ensure_import_paths()
from cs_roman_bold import (  # noqa: E402
    BoldSpan,
    bold_ranges_from_geoms,
    bold_span_geoms,
    substantial_bold_ranges,
)
from cs_roman_hanging import (  # noqa: E402
    _is_first_indent,
    _is_gatha_geometry_indent,
    _is_gatha_indent,
    _match_cached_line,
    _seg_pdf_page,
    collect_hanging_groups,
    merge_hanging_into_segments,
    page_body_lines,
    reclassify_page_start_by_indent,
    restore_centered_line_breaks,
    segment_roman_text,
    tag_center_layout_by_geometry,
)
from cs_roman_segments import (  # noqa: E402
    SCHEMA_VERSION,
    layout_path_for,
    load,
    save_document,
)
from cs_roman_text import (  # noqa: E402
    SECTION_RULE_FLAG,
    is_expansion_parenthetical,
    is_section_closer_formula,
    is_section_nama_colophon,
    is_tassuddana_label,
    normalize_printable_dashes,
    normalize_roman_body,
    peel_trailing_expansion_parenthetical,
    peel_trailing_section_closer,
    script_text_entries,
    split_trailing_section_rule,
    strip_sentence_spacers,
    strip_solid_midword_hyphens,
    uses_sentence_spacer,
)
from cs_roman_vztime import unmapped_chars, vztime_to_unicode  # noqa: E402

# Full-width footnote separators in CS Roman text extract (~60 underscores).
# Decorative title / section rules are much shorter (typically 5–9); do not
# treat those as footnote splits or the opening page becomes all-notes
# (seen on 02Vin02 ``________`` under the gambhīra title).
FOOTNOTE_RULE_RE = re.compile(r"^_{20,}$")
FOOTNOTE_SPLIT_RE = re.compile(r"\n[ \t]*_{20,}[ \t]*(?:\n|$)")
# Short/medium centered rules from PDF text (~3–16 underscores).
SECTION_RULE_LINE_RE = re.compile(r"^_{3,16}$")
SECTION_RULE_TAIL = " _____"
ITEM_START_RE = re.compile(r"^(\d+)\s*[-–]\s*(\d+)\.\s*(.*)$")
ITEM_SINGLE_RE = re.compile(r"^(\d+)\.\s*(.*)$")
STAR_BLOCK_RE = re.compile(r"^\*\s+(.*)$")
PLUS_BLOCK_RE = re.compile(r"^\+\s+(.*)$")
# Same-line sibling apparatus note: "...pi. + Dī 3. …"
_INLINE_PLUS_NOTE_RE = re.compile(r"(?<=\.)\s+\+\s+(?=[A-ZĀĪŪÑÉÓ])")
# Mid-paragraph apparatus callouts (e.g. ``Te + evarūpaṃ`` on 01Vin01 p.274).
_INLINE_PLUS_CALLOUT_RE = re.compile(r"(?<=\S)\s+\+\s+(?=\S)")
_INLINE_STAR_CALLOUT_RE = re.compile(r"(?<=\S)\s+\*\s+(?=\S)")
# Bracket apparatus note: ``[  ] Etthantare pāṭhā Syāmapotthake natthi.``
_BRACKET_NOTE_RE = re.compile(r"^\[\s*\]\s*(.+)$", re.DOTALL)
# Empty-paren apparatus: ``(  ) (katthaci natthi)`` (02Vin02 p.317).
_PAREN_NOTE_RE = re.compile(r"^\(\s*\)\s*(.+)$", re.DOTALL)
# Folio / paragraph-range markers like ``(150)`` / ``(55-56)`` — never host
# ``{{()}}`` (01Vin01 p.86 stole note 2 onto ``(150)``).
_FOLIO_PAREN_RE = re.compile(r"^\(\d+(?:-\d+)?\)")
PAGE_NUM_RE = re.compile(r"^\d+$")
# Majjhima-style running heads: ``Potaliyasutta (54)`` / ``4. Potaliyasutta (54)``.
# The trailing ``(folio)`` marks page furniture, not a chapter-open title.
_RUNNING_HEADER_FOLIO_LINE_RE = re.compile(
    r"^(?:\d+\.\s+)?.{1,80}\(\d{1,3}\)$"
)
# Same form glued onto prose (space after the closing paren).
_GLUED_RUNNING_HEADER_FOLIO_PREFIX_RE = re.compile(
    r"^(?:(\d+)\.\s+)?([^\n(]{2,80}?)\s*\((\d{1,3})\)(?:[ \t\u00a0]+)"
)
_FOLIO_HEADER_MAX_LEN = 90
_GENERIC_HEADER_MAX_LEN = 40

# Back-matter indexes (Padānukkama / Nāmānukkama / Gāthāsūci, etc.).
# Match near the top of a page so body mentions do not trigger a false end.
BACK_MATTER_RE = re.compile(
    r"(?:"
    r"Pad[āa]nukkam|"
    r"Pi[ṭt]{1,2}ha[ṅn]k|"
    r"anukkama[ṇn]ik|"
    r"G[āa]th[āa]s[ūu]ci|"
    r"N[āa]m[āa]na[ṃm]\s+anukkam|"
    r"N[āa]n[āa]p[āa][ṭt]h[āa]\s+Pi|"
    r"Sa[ṃm]va[ṇn]{1,2}itapad|"
    r"ปทานุกฺกม|"
    r"ปิฏฺฐงฺก|"
    r"อนุกฺกมณิก|"
    r"คาถาสูจิ|"
    r"นามานํ\s*อนุกฺกม|"
    r"นานาปาฐา"
    r")",
    re.IGNORECASE,
)
VARIANT_NOTE_RE = re.compile(
    r"\((Sī|Syā|Ka|PTS|Sīā|C[sS]|Bj|Mr)\)",
)
STRUCTURAL_HINT_RE = re.compile(
    r"(kaṇḍa|vagga|sikkhāpada|samatha|bhāṇavāra|uddānagāthā|uddāna|gāthā|gatha|"
    r"mātikā|niṭṭhita|namo\s+tassa|piṭaka|pāḷi)\b",
    re.IGNORECASE,
)
# Heading glued to pātimokkha uddesa intro (no blank line in PDF text).
_UDDESA_SPLIT_RE = re.compile(
    r"^(?P<title>.+?)\s+(?P<body>Ime kho\b.+)$",
    re.IGNORECASE | re.DOTALL,
)
# Title must *end* on a structural stem (not merely contain one mid-sentence).
_UDDESA_TITLE_END_RE = re.compile(
    r"(?:sikkhāpada|vagga|samatha|kaṇḍa)\s*$",
    re.IGNORECASE,
)
# Body must be the pātimokkha uddesa formula (rejects ordinary “Ime kho…” lists).
_UDDESA_BODY_RE = re.compile(
    r"^Ime kho\s+(?:panāyasmanto|panāyyāyo)\b.+\buddesaṃ\s+āgacchanti",
    re.IGNORECASE | re.DOTALL,
)
# Titles that open an uddāna / gāthā verse block.
GATHA_TITLE_RE = re.compile(r"uddānagāthā|uddāna|gāthā|\bgatha\b", re.IGNORECASE)
# Short block labels eligible for blank-line peel (not niddesa compounds).
_GATHA_BLOCK_TITLE_RE = re.compile(
    r"^(?:tassuddānaṃ|uddānagāthā(?:yo)?|uddānaṃ|uddāna)$",
    re.IGNORECASE,
)
_GATHA_STOP_KINDS = frozenset(
    {
        "niṭṭhitaṃ",
        "chapter",
        "title",
        "tassuddānaṃ",
        "piṭaka",
        "gambhīra",
        "namakkāraṃ",
        "note",
        "subhead",
        "centered",
    }
)
NAMO_RE = re.compile(r"^namo\s+tassa\b", re.IGNORECASE)
# Footnote callout after a word/quote. PDF superscripts are often glued
# Letters used in Roman Pāli (callout trailers + mid-word page-break repair).
_PALI_LETTER_CLASS = r"A-Za-zĀāĪīŪūṄṅÑñṆṇṬṭḌḍḶḷṂṃŒœ"
# (Bhagavā’1 / anabhāvaṃkatā1) or spaced (paccāsīsitabbā 1). Also mid-compound
# glued marks (Kaṇṭakassa1nāma — 02Vin02 p.181). Groups:
#   1 = optional horizontal space, 2 = mark digits, 3 = trailer char or None.
# Spaced + trailing ``.`` is an outline number (``vagga 1.``), not a callout.
FOOTNOTE_CALLOUT_RE = re.compile(
    rf"(?<=[^\s\d])([ \t]*)(\d+)(?=([\s,;:.!?”’\"'\-–]|[{_PALI_LETTER_CLASS}])|$)"
)
# Sacred-style note markers after attach_notes ({{n0}}, {{n1}}, …).
_NOTE_MARKER_RE = re.compile(r"\{\{n(\d+)\}\}")


def remap_note_markers(text: str, offset: int) -> str:
    """Shift ``{{nK}}`` indices by ``offset`` (0 = unchanged)."""
    if not offset or not text:
        return text

    def _repl(match: re.Match[str]) -> str:
        return "{{" + f"n{int(match.group(1)) + offset}" + "}}"

    return _NOTE_MARKER_RE.sub(_repl, text)


def merge_note_carrying_units(
    units: list[tuple[str, "Segment"]],
    *,
    note_index_base: int = 0,
) -> tuple[list[str], list[str], dict[str, str], list[str]]:
    """Merge per-line notes when folding printed lines into one บท.

    Each unit is ``(roman, segment)``. Segments that share identity (bat_line
    left/right split) contribute notes once. Markers in each roman string are
    remapped so ``{{n0}}`` on a later line becomes ``{{nK}}`` after earlier
    notes. Pieces with empty ``notes`` (glued-line expand) keep marker indices
    relative to ``note_index_base`` (they inherit the parent line's pool).
    """
    notes: list[str] = []
    symbol_notes: dict[str, str] = {}
    flags: list[str] = []
    offsets: dict[int, int] = {}
    romans: list[str] = []
    for roman, seg in units:
        sid = id(seg)
        if sid not in offsets:
            seg_notes = list(seg.notes or [])
            if seg_notes:
                offsets[sid] = note_index_base + len(notes)
                notes.extend(seg_notes)
            else:
                # Marker indices already refer to notes merged at base.
                offsets[sid] = note_index_base
            for key, value in (seg.symbol_notes or {}).items():
                symbol_notes[key] = value
            for fl in seg.flags or []:
                if fl not in flags:
                    flags.append(fl)
        romans.append(remap_note_markers(roman or "", offsets[sid]))
    return romans, notes, symbol_notes, flags
_LEADING_WORD_RE = re.compile(
    rf"^([{_PALI_LETTER_CLASS}]+)(.*)$",
    re.DOTALL,
)
# Hyphen-wrapped markers such as CS Roman peyyāla ``-pa-`` (not soft hyphens).
_HYPHEN_WRAPPED_MARKER_RE = re.compile(
    rf"^-[{_PALI_LETTER_CLASS}]+-$"
)
# False join left by older extract: page-end ``-pa-`` + next-page word → ``-paWORD``.
_FALSE_PA_JOIN_END_RE = re.compile(
    rf"^(?P<head>.*\s)-pa(?P<word>[{_PALI_LETTER_CLASS}]+)$",
    re.DOTALL,
)

# Body kinds that may continue across a printed page break.
_CONTINUABLE_KINDS = frozenset(
    {
        "prose",
        "prose_continuation",
        "gatha",
        "gatha_continuation",
        "verse",
        "verse_continuation",
    }
)


def _base_kind(kind: str) -> str:
    if kind.endswith("_continuation"):
        return kind[: -len("_continuation")]
    return kind


def _continuation_kind(kind: str) -> str:
    """prose→prose_continuation, gatha→gatha_continuation, etc."""
    base = _base_kind(kind)
    return f"{base}_continuation"


def _take_leading_word(text: str) -> tuple[str, str]:
    """Return (leading_word, remainder) from the start of ``text``."""
    m = _LEADING_WORD_RE.match(text.lstrip())
    if not m:
        return "", text
    return m.group(1), m.group(2).lstrip()


def _trailing_token(text: str) -> str:
    """Last whitespace-separated token; soft hyphens normalized to ``-``."""
    text = text.rstrip()
    if not text:
        return ""
    return text.split()[-1].replace("\u00ad", "-")


def _is_hyphen_wrapped_marker(text: str) -> bool:
    """True for ``-pa-`` / similar markers; false for soft-hyphen ``pabbaj-``."""
    return bool(_HYPHEN_WRAPPED_MARKER_RE.fullmatch(_trailing_token(text)))


def _repair_mid_word_split(
    prev_text: str, next_text: str
) -> tuple[str, str, bool]:
    """
    If the page break splits a word, finish the word on the first segment.

    Only hyphenated breaks count: a trailing ``-`` or soft hyphen on the
    previous page. A bare page-end letter (e.g. ``ṭhitā`` / ``hoti.``) is two
    words and must not be joined.

    Hyphen-wrapped markers such as peyyāla ``-pa-`` keep their trailing hyphen
    and must not pull the next page's leading word onto ``prev``.

    Returns (updated_prev_text, updated_next_text, joined).
    ``joined`` is True only when a leading word was moved onto ``prev``.
    """
    prev = prev_text.rstrip()
    nxt = next_text.lstrip()
    if not prev or not nxt:
        return prev_text, next_text, False

    # ``-pa-`` at page end is a marker, not a soft-hyphenated word break.
    if _is_hyphen_wrapped_marker(prev):
        return prev_text, next_text, False

    if prev.endswith("-") or prev.endswith("\u00ad"):
        prev = prev.rstrip("-").rstrip("\u00ad")
        word, rest = _take_leading_word(nxt)
        if word:
            return prev + word, rest, True
        return prev, nxt, False
    return prev_text, next_text, False


def _split_false_pa_join(text: str) -> tuple[str, str] | None:
    """If ``text`` ends with ``-paWORD`` (false page join), return (head+-pa-, WORD)."""
    m = _FALSE_PA_JOIN_END_RE.match(text.rstrip())
    if not m:
        return None
    return f"{m.group('head')}-pa-", m.group("word")


def _roman_entry_from_text_field(text: object) -> dict | None:
    if not isinstance(text, list):
        return None
    for entry in text:
        if isinstance(entry, dict) and entry.get("script") == "roman":
            return entry
    return None


def _set_roman_value(text_field: object, new_value: str) -> object:
    """Set roman ``value``; keep bold runs when the edit is a trailing unglue."""
    if isinstance(text_field, str):
        return new_value
    entry = _roman_entry_from_text_field(text_field)
    if entry is None:
        return text_field
    old_value = str(entry.get("value") or "")
    entry["value"] = new_value
    runs = entry.get("runs")
    if isinstance(runs, list) and runs and old_value != new_value:
        # Prefer patching the last run when it carries the glued tail.
        last = runs[-1]
        if isinstance(last, dict):
            last_val = str(last.get("value") or "")
            if old_value.endswith(last_val):
                head_len = len(old_value) - len(last_val)
                if new_value.startswith(old_value[:head_len]):
                    last["value"] = new_value[head_len:]
                    entry["runs"] = runs
                    return text_field
        # Structural mismatch — drop runs; enrich --force may remap from spans.
        entry.pop("runs", None)
    return text_field


def _prepend_roman_value(text_field: object, word: str) -> object:
    """Prepend ``word`` (+ space when needed) to the roman value / first run."""
    prefix = word if not word else f"{word} "
    if isinstance(text_field, str):
        body = text_field.lstrip()
        return prefix + body if body else word
    entry = _roman_entry_from_text_field(text_field)
    if entry is None:
        return text_field
    body = str(entry.get("value") or "").lstrip()
    entry["value"] = prefix + body if body else word
    runs = entry.get("runs")
    if isinstance(runs, list) and runs:
        first = runs[0]
        if isinstance(first, dict):
            first_body = str(first.get("value") or "").lstrip()
            first["value"] = prefix + first_body if first_body else word
    return text_field


def unglue_false_pa_page_joins(segments: list) -> int:
    """
    Undo false ``-pa-`` + next-word joins at page boundaries in stored JSON.

    When a prior extract treated peyyāla ``-pa-`` as a soft hyphen, the leading
    word of the next page was glued onto the previous segment (e.g.
    ``-paaññaṃ``). Move that word back to the continuation segment.

    Returns the number of joins repaired.
    """
    fixed = 0
    for i in range(len(segments) - 1):
        cur = segments[i]
        nxt = segments[i + 1]
        if not isinstance(cur, dict) or not isinstance(nxt, dict):
            continue
        cur_page = cur.get("page")
        nxt_page = nxt.get("page")
        if not isinstance(cur_page, int) or not isinstance(nxt_page, int):
            continue
        if nxt_page <= cur_page:
            continue
        nxt_kind = str(nxt.get("segment_type") or "")
        if not nxt_kind.endswith("_continuation"):
            continue
        if cur.get("item") != nxt.get("item"):
            continue

        cur_roman = ""
        cur_text = cur.get("text")
        if isinstance(cur_text, str):
            cur_roman = cur_text
        else:
            entry = _roman_entry_from_text_field(cur_text)
            if entry is not None:
                cur_roman = str(entry.get("value") or "")
        split = _split_false_pa_join(cur_roman)
        if split is None:
            continue
        new_prev, word = split
        cur["text"] = _set_roman_value(cur_text, new_prev)
        nxt["text"] = _prepend_roman_value(nxt.get("text"), word)

        # Hanging lines may mirror the glued page-end tail — unglue in place.
        hanging = cur.get("hanging_lines")
        if isinstance(hanging, list) and hanging:
            last_hl = hanging[-1]
            hl_roman = ""
            if isinstance(last_hl, str):
                hl_roman = last_hl
            else:
                hl_entry = _roman_entry_from_text_field(last_hl)
                if hl_entry is not None:
                    hl_roman = str(hl_entry.get("value") or "")
            hl_split = _split_false_pa_join(hl_roman)
            if hl_split is not None and hl_split[1] == word:
                hanging[-1] = _set_roman_value(last_hl, hl_split[0])
                cur["hanging_lines"] = hanging
        fixed += 1
    return fixed


# วรรค roles within a standard 4-wak gāthā บท.
_WAK_ROLES = {1: "sadap", 2: "rap", 3: "rong", 4: "song"}


@dataclass
class Segment:
    page: int
    order: int
    item: int | str | None
    segment_type: str
    text: str
    pdf_page: int | None = None
    flags: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    # Apparatus footnotes marked * / + (not part of numbered {{nN}} sequence).
    symbol_notes: dict[str, str] = field(default_factory=dict)
    needs_review: bool = False
    review_reasons: list[str] = field(default_factory=list)
    # Outline number before a heading title (e.g. 1 in "1. Pārājikakaṇḍa").
    # Distinct from Tipiṭaka ``item``; omit / None when the source has no number.
    section_no: int | str | None = None
    # Nested gāthā: one segment = one บท (or 1 บทครึ่ง with 3 bats).
    # Absent for non-gatha kinds.
    # Also reused for hanging / center: source_layout + optional hanging_lines.
    source_layout: str | None = None  # bat_line | wak_line | hanging | center
    bats: list[dict] | None = None
    # Hanging-paragraph body lines (roman), when source_layout == "hanging".
    hanging_lines: list[str] | None = None


def _normalize_inline(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]*\n[ \t]*", " ", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    # U+23AF → en-dash (printable; see normalize_printable_dashes).
    return normalize_printable_dashes(text.strip())


def _split_blocks(page_text: str, *, notes: bool = False) -> list[str]:
    text = page_text.replace("\r\n", "\n")
    if notes:
        text = re.sub(r"\n(?=\d+\.\s)", "\n\n", text)
        text = re.sub(r"\n(?=\*\s)", "\n\n", text)
        text = re.sub(r"\n(?=\+\s)", "\n\n", text)
    # Expansion paren on its own printed line (no blank line in PDF text).
    # ``…padanti.\n(Appamādavaggo…)`` must not collapse into one paragraph.
    if not notes:
        text = re.sub(
            r"([.!?…][\"'\u201c\u201d]?)\n(?=\()",
            r"\1\n\n",
            text,
        )
    parts = re.split(r"\n\s*\n", text)
    return [p.strip("\n") for p in parts if p.strip()]


def _symbol_note_parts(mark: str, text: str) -> list[tuple[str, str]]:
    """Split a symbol-note line that packs ``* … + …`` on one line."""
    text = text.strip()
    if not text:
        return []
    if mark == "*":
        chunks = _INLINE_PLUS_NOTE_RE.split(text, maxsplit=1)
        if len(chunks) == 2:
            return [("*", chunks[0].strip()), ("+", chunks[1].strip())]
    return [(mark, text)]


def _append_symbol_note_blocks(
    blocks_out: list[dict],
    *,
    mark: str,
    text: str,
    printed_page: int,
    pdf_page: int,
) -> None:
    for sym, body in _symbol_note_parts(mark, text):
        sym_flag = "star" if sym == "*" else "plus"
        blocks_out.append(
            {
                "kind": "note",
                "item": None,
                "text": body,
                "flags": [sym_flag],
                "page": printed_page,
                "pdf_page": pdf_page,
            }
        )


def _is_section_rule_line(block: str) -> bool:
    """True for a short underscore-only end-of-section rule (not footnote sep)."""
    line = _normalize_inline(block).replace(" ", "")
    return bool(SECTION_RULE_LINE_RE.match(line))


def _attach_section_rule_tail(text: str) -> str:
    """Append a trailing ``_____`` if the body does not already end with one."""
    body = text.rstrip()
    if re.search(r"_{3,}\s*$", body):
        return body
    return body + SECTION_RULE_TAIL


def is_running_header_folio_label(text: str) -> bool:
    """True for ``Name (folio)`` / ``N. Name (folio)`` page-furniture labels."""
    s = (text or "").strip()
    if not s or len(s) > _FOLIO_HEADER_MAX_LEN:
        return False
    return bool(_RUNNING_HEADER_FOLIO_LINE_RE.match(s))


def _is_running_header(block: str, headers: set[str]) -> bool:
    line = _normalize_inline(block)
    if not line:
        return True
    if FOOTNOTE_RULE_RE.match(line):
        return True
    if PAGE_NUM_RE.match(line):
        return True
    # Recitation topic-summary label — never page furniture.
    if is_tassuddana_label(line):
        return False
    # ``Potaliyasutta (54)`` is always furniture (folio), never a chapter open.
    if is_running_header_folio_label(line):
        return True
    if line in headers:
        # Numbered ``N. Title`` may be a real chapter open that reuses the
        # running-header wording as its own blank-line-isolated block.
        # Unnumbered furniture (``…pāḷi``) is dropped when alone.
        if ITEM_SINGLE_RE.match(line):
            return False
        return True
    # Short underscore section rules are attached to the previous body block
    # in ``_blocks_from_region`` / ``merge_blocks`` — do not discard them here.
    if _is_section_rule_line(line):
        return False
    if set(line) <= {"_", " ", "–", "-"}:
        return True
    return False


def running_header_bare_name(header: str) -> str:
    """``10. Subhasutta`` → ``Subhasutta``; unnumbered labels unchanged."""
    s = (header or "").strip()
    m = ITEM_SINGLE_RE.match(s)
    if m:
        rest = (m.group(2) or "").strip()
        if rest:
            return rest
    return s


def _is_page_top_header_label(line: str, headers: set[str]) -> bool:
    """True when ``line`` is a detected running header or folio furniture label."""
    s = (line or "").strip()
    if not s:
        return False
    if is_running_header_folio_label(s):
        return True
    return bool(headers) and s in headers


def _looks_like_heading_open_line(line: str) -> bool:
    """True for a short title-like line that follows a chapter running header.

    Used so ``12. Vacchagottasaṃyutta`` + ``1. Rūpa-aññāṇasutta`` is kept as a
    chapter open, while ``12. Vacchagottasaṃyutta`` + edition page + body prose
    is treated as page furniture.
    """
    s = _normalize_inline(line or "")
    if not s or len(s) > 80:
        return False
    if PAGE_NUM_RE.match(s) or FOOTNOTE_RULE_RE.match(s):
        return False
    if is_tassuddana_label(s):
        return False
    # Numbered child titles often fail the weak-heading uppercase gate (``1.``).
    if ITEM_SINGLE_RE.match(s) and len(s) <= 80:
        rest = (ITEM_SINGLE_RE.match(s).group(2) or "").strip()
        if rest and not re.search(r"[.!?…][\"'\u201c\u201d]?\s*$", rest):
            return True
    heading, _reasons = _classify_heading(s)
    return heading is not None


def peel_page_top_running_header_furniture(
    page_text: str, headers: set[str]
) -> str:
    """Drop page-top running header + edition page-number furniture.

    Continuation pages often print a centered ``N. Title`` (same wording as the
    chapter open) with the edition page number on the outer margin, then body.
    Blank lines between them make ``_split_blocks`` isolate the title so the
    numbered-header keep rule would otherwise retain it as a false heading.

    Peel only when the leading cluster contains both a header label (in
    ``headers`` / folio form) and an edition ``PAGE_NUM``, and the first
    non-furniture line is not itself a heading open (child title). Chapter
    opens like ``12. Vacchagottasaṃyutta`` / ``1. Rūpa-…`` are kept.
    """
    if not page_text or not headers:
        return page_text
    text = page_text.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    i = 0
    furniture_end = 0
    saw_header = False
    saw_page_num = False
    while i < len(lines):
        s = lines[i].strip()
        if not s:
            i += 1
            continue
        if PAGE_NUM_RE.match(s):
            saw_page_num = True
            i += 1
            furniture_end = i
            continue
        if FOOTNOTE_RULE_RE.match(s):
            i += 1
            furniture_end = i
            continue
        if _is_page_top_header_label(s, headers):
            saw_header = True
            i += 1
            furniture_end = i
            continue
        break
    if not (saw_header and saw_page_num):
        return page_text
    # First real line after the furniture cluster.
    rest = "\n".join(lines[furniture_end:])
    first = next((ln.strip() for ln in rest.split("\n") if ln.strip()), "")
    if first and _looks_like_heading_open_line(first):
        return page_text
    return rest


def peel_leading_running_headers(raw: str, headers: set[str]) -> str:
    """Drop leading running-header / page-number lines from a multi-line block.

    CS Roman often places ``10. Subhasutta`` / page number / body with no blank
    line between them, so ``_split_blocks`` joins them into one paragraph and
    item-parse turns the sutta number into a false Tipiṭaka ``item``.

    Isolated single-line blocks are left alone — chapter opens use the same
    wording with blank lines around the title (unless they are ``Name (folio)``
    furniture, which ``_is_running_header`` drops separately). Page-top
    header+edition-folio clusters with blank lines are handled by
    ``peel_page_top_running_header_furniture`` before splitting.
    """
    if not raw:
        return raw
    text = raw.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    non_empty = [ln for ln in lines if ln.strip()]
    if len(non_empty) <= 1:
        return raw
    i = 0
    while i < len(lines):
        s = lines[i].strip()
        if not s:
            i += 1
            continue
        if PAGE_NUM_RE.match(s) or FOOTNOTE_RULE_RE.match(s):
            i += 1
            continue
        if (headers and s in headers) or is_running_header_folio_label(s):
            i += 1
            continue
        break
    if i == 0:
        return raw
    return "\n".join(lines[i:])


def peel_glued_running_header_prefix(
    text: str, headers: set[str]
) -> tuple[str, str, int | None] | None:
    """Peel a detected running-header label glued onto prose.

    Returns ``(remainder, peeled_label, header_item_or_None)`` when ``text``
    starts with a header string (or its bare name after ``N. ``) and enough
    body remains. Also peels ``Name (folio)`` / ``N. Name (folio)`` by pattern
    when the label was never frequency-detected. Used by extract repair and
    ``fixup_glued_running_headers``.
    """
    t = (text or "").strip()
    if len(t) < 50:
        return None
    # Longer labels first so ``Mahāsīhanādasutta`` wins over shorter stems.
    for header in sorted(headers or (), key=lambda h: len(h), reverse=True):
        h = header.strip()
        if not h:
            continue
        bare = running_header_bare_name(h)
        item: int | None = None
        m = ITEM_SINGLE_RE.match(h)
        if m:
            try:
                item = int(m.group(1))
            except ValueError:
                item = None
        for label, label_item in ((h, item), (bare, item)):
            if not label or len(label) < 3:
                continue
            if not (
                t.startswith(label + " ")
                or t.startswith(label + "\u00a0")
            ):
                continue
            rest = t[len(label) :].lstrip()
            if len(rest) < 40:
                return None
            return rest, label, label_item

    # Pattern fallback: short suttas may appear at page top only once, so they
    # never entered the frequency set under the old min_pages=3 rule.
    fm = _GLUED_RUNNING_HEADER_FOLIO_PREFIX_RE.match(t)
    if fm:
        rest = t[fm.end() :]
        if len(rest) >= 40:
            item: int | None = None
            if fm.group(1):
                try:
                    item = int(fm.group(1))
                except ValueError:
                    item = None
            label = fm.group(0).strip()
            return rest, label, item
    return None


# En/em dash at line end = speech / verse lead-in (“…abhāsi–”, “…etadavoca–”),
# not a section title. ASCII hyphen is left alone (soft line-join residue).
_SPEECH_INTRO_DASH_RE = re.compile(r"[–—]\s*$")


def ends_with_speech_intro_dash(text: str) -> bool:
    """True when text ends with an en/em dash (quote/verse intro, not a heading)."""
    return bool(_SPEECH_INTRO_DASH_RE.search((text or "").rstrip()))


def _classify_heading(text: str) -> tuple[str | None, list[str]]:
    """
    Return (segment_type or None, review_reasons).

    Heading cues (basics): structural stems / Mātikā later; short guesses need
    center geometry (and preferably bold) — not trailing en/em dash lead-ins.
    Strong matches need no review; weak short-line guesses are flagged and may
    be demoted after the center-layout pass.
    """
    if NAMO_RE.match(text):
        return "namakkāraṃ", []
    # Recitation topic-summary label — not a TOC heading / not an end formula.
    if is_tassuddana_label(text):
        return "tassuddānaṃ", []
    # Only short closing lines — the stem also appears inside body/index prose.
    # Includes gendered samattaṃ / สมตฺโต (not only niṭṭhitaṃ).
    if len(text) <= 90 and is_section_closer_formula(text):
        return "niṭṭhitaṃ", []
    if VARIANT_NOTE_RE.search(text):
        return None, []
    # “…āmantesi–” / “…paṭicodetha–” introduce speech or gāthā, never titles.
    if ends_with_speech_intro_dash(text):
        return None, []
    if STRUCTURAL_HINT_RE.search(text) and len(text) <= 80:
        # Opening volume labels (also reused as running headers later).
        if re.search(r"piṭaka\b", text, re.I):
            return "piṭaka", []
        if re.search(r"pāḷi\b", text, re.I) and len(text) <= 40:
            return "gambhīra", []
        if re.search(r"(kaṇḍa|vagga)\b", text, re.I):
            return "chapter", []
        # uddāna / gāthā compounds are strong titles (not weak heuristics).
        if GATHA_TITLE_RE.search(text):
            return "title", []
        return "title", []
    # Weak heading: short phrase, not a sentence, not verse. Confirmed only if
    # later geometry tags ``source_layout='center'`` (see demote_false_heading_guesses).
    # Verse halves often end with "," or contain a pāda-break comma — never titles.
    if len(text) <= 60 and not re.search(r"[.!?…][\"'\u201c\u201d]?\s*$", text):
        if text.rstrip().endswith(","):
            return None, []
        if "," in text:
            return None, []
        if " " not in text or text[0].isupper():
            return "title", ["weak_heading_heuristic"]
    return None, []


_DEMOTABLE_WEAK_HEADING_TYPES = frozenset({"title", "subhead"})


def demote_false_heading_guesses(segments: list[Segment]) -> dict[str, int]:
    """Demote mistyped titles that fail basic heading cues.

    - Trailing en/em dash → prose (speech/verse lead-in).
    - ``weak_heading_heuristic`` without ``source_layout='center'`` → prose
      (short+uppercase alone is not enough; real short labels are centered).

    Structural stems (chapter / piṭaka / …) are left alone. Returns demote counts.
    """
    dash_n = 0
    weak_n = 0
    for seg in segments:
        if seg.segment_type not in _DEMOTABLE_WEAK_HEADING_TYPES:
            continue
        text = seg.text or ""
        reasons = list(seg.review_reasons or [])
        demote = False
        if ends_with_speech_intro_dash(text):
            demote = True
            dash_n += 1
        elif (
            "weak_heading_heuristic" in reasons
            and seg.source_layout != "center"
        ):
            demote = True
            weak_n += 1
        if not demote:
            continue
        seg.segment_type = "prose"
        seg.review_reasons = [
            r
            for r in reasons
            if r
            not in {
                "weak_heading_heuristic",
                "heading_level_unmatched_matika",
            }
        ]
        seg.needs_review = bool(seg.review_reasons)
    return {"demoted_speech_intro_dash": dash_n, "demoted_weak_uncentered": weak_n}


def peel_glued_uddesa_heading(text: str) -> tuple[str, str] | None:
    """Split ``Title Ime kho…`` into (heading, uddesa body) when title classifies.

    PDF text often joins a short rule/vagga heading to the pātimokkha uddesa
    sentence with no blank line, which otherwise fails the 80-char heading gate
    and is stored as prose with a false Tipiṭaka ``item``.
    """
    cleaned = re.sub(r"\s+", " ", strip_sentence_spacers(text or "").strip())
    if not cleaned:
        return None
    m = _UDDESA_SPLIT_RE.match(cleaned)
    if not m:
        return None
    title = m.group("title").strip()
    body = m.group("body").strip()
    if not title or not body or len(title) > 80:
        return None
    if not _UDDESA_TITLE_END_RE.search(title):
        return None
    # Reject mid-sentence titles (allow outline dots after digits: ``1. Name``).
    if re.search(r"(?<!\d)\.\s+\S", title):
        return None
    if not _UDDESA_BODY_RE.search(body):
        return None
    heading, _reasons = _classify_heading(title)
    if heading is None:
        return None
    return title, body


def _is_peelable_gatha_block_title(text: str) -> bool:
    """True for short uddāna labels that may be glued to following verses."""
    t = (text or "").strip()
    if not _GATHA_BLOCK_TITLE_RE.match(t):
        return False
    heading, _reasons = _classify_heading(t)
    return heading in {"title", "tassuddānaṃ"}


def peel_glued_gatha_title_raw(raw: str) -> tuple[str, list[str]] | None:
    """Split ``Tassuddānaṃ\\nVerse…`` when PDF omitted the blank line after title.

    On most pages blank lines already separate the uddāna label from bat/wak
    verses. When they are missing, ``_split_blocks`` keeps title + verses in one
    paragraph; classification then fails (too long / commas) and center geometry
    paints the whole block as ``\\csromancenter``.
    """
    lines = [
        ln.strip()
        for ln in (raw or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
        if ln.strip()
    ]
    if len(lines) < 2:
        return None
    first = _normalize_inline(lines[0])
    if not _is_peelable_gatha_block_title(first):
        return None
    rest = lines[1:]
    verseish = 0
    for ln in rest:
        if _is_section_rule_line(ln):
            continue
        # Bat line or wak seed only — not every short sentence ending in ``.``.
        if not _looks_like_gatha_seed_line(ln):
            return None
        verseish += 1
    if verseish < 1:
        return None
    return first, rest


def peel_glued_gatha_title_text(text: str) -> tuple[str, list[str]] | None:
    """Peel a normalized prose string ``Title Verse.{{sp1}} Verse.`` → title + lines.

    Used by JSON fixup after extract already collapsed newlines / inserted
    sentence spacers. Rejects long *gāthā*-containing section names whose
    trailers are commentary, not bat/wak verse lines.
    """
    raw = (text or "").strip()
    if not raw:
        return None
    m = re.match(r"^(\S+)\s+(.+)$", raw, flags=re.DOTALL)
    if not m:
        return None
    title, rest = m.group(1), m.group(2).strip()
    if not _is_peelable_gatha_block_title(title):
        return None
    # Drop a trailing section-rule glyph run if present in the string.
    rest_body = re.sub(r"(?:\s|_)+$", "", rest).strip()
    parts = [
        p.strip()
        for p in re.split(r"\{\{sp1\}\}", rest_body)
        if p.strip() and not _is_section_rule_line(p)
    ]
    if not parts:
        # No {{sp1}}: try a single remaining bat/wak line.
        one = strip_sentence_spacers(rest_body).strip()
        parts = [one] if one else []
    if not parts:
        return None
    if not all(_looks_like_gatha_seed_line(p) for p in parts):
        return None
    return title, parts


def _split_body_and_notes(page_text: str) -> tuple[str, str]:
    parts = FOOTNOTE_SPLIT_RE.split(page_text, maxsplit=1)
    if len(parts) == 1:
        return page_text, ""
    return parts[0], parts[1]


def _split_at_namo(text: str) -> tuple[str, str]:
    """Split page body into (before first Namo line, from Namo onward)."""
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if NAMO_RE.match(line.strip()):
            return "\n".join(lines[:i]), "\n".join(lines[i:])
    return "", text


def _strip_running_header_lines(
    text: str,
    headers: set[str],
    *,
    keep_until_namo: bool = False,
) -> str:
    """
    Drop page numbers and footnote separator lines.

    Running-header *strings* are not stripped here: numbered titles
    (``10. Subhasutta``) also appear as real chapter opens. Those are peeled
    from multi-line blocks via ``peel_leading_running_headers`` instead.
    ``headers`` / ``keep_until_namo`` are kept for call-site compatibility.
    """
    del headers, keep_until_namo  # API stable; peeling handles headers.
    kept: list[str] = []
    for line in text.split("\n"):
        s = line.strip()
        if not s:
            kept.append(line)
            continue
        if PAGE_NUM_RE.match(s) or FOOTNOTE_RULE_RE.match(s):
            continue
        kept.append(line)
    return "\n".join(kept)


def _parse_item_prefix(text: str) -> tuple[int | str | None, str, list[str]]:
    flags: list[str] = []
    m = ITEM_START_RE.match(text)
    if m:
        item: int | str = f"{m.group(1)}-{m.group(2)}"
        rest = m.group(3).strip()
    else:
        m = ITEM_SINGLE_RE.match(text)
        if not m:
            return None, text, flags
        item = int(m.group(1))
        rest = m.group(2).strip()

    if rest.startswith("*"):
        flags.append("star")
        rest = rest[1:].strip()
    elif rest.startswith("+"):
        flags.append("plus")
        rest = rest[1:].strip()
    return item, rest, flags


# PDF note region sometimes joins two numbered notes on one line:
# ``2. Dakkhitānaṃ (Syā, I) 3. Idaṃ padaṃ natthi …``
_GLUED_NUMBERED_NOTE_RE = re.compile(
    rf"^(?P<head>.+?)\s+(?P<item>\d+)\.\s+"
    rf"(?P<rest>[{_PALI_LETTER_CLASS}].*)$"
)


def split_glued_numbered_note_body(
    item: int, text: str
) -> list[tuple[int, str]]:
    """Split a note body that embeds a following ``N. …`` note."""
    out: list[tuple[int, str]] = []
    cur_item = item
    cur_text = (text or "").strip()
    while True:
        m = _GLUED_NUMBERED_NOTE_RE.match(cur_text)
        if m is None:
            if cur_text:
                out.append((cur_item, cur_text))
            break
        head = m.group("head").strip()
        if head:
            out.append((cur_item, head))
        cur_item = int(m.group("item"))
        cur_text = m.group("rest").strip()
    return out


def expand_glued_numbered_notes(
    item: int | str | None, text: str, flags: list[str]
) -> list[tuple[int | str | None, str, list[str]]]:
    """Expand one parsed note into one or more ``(item, text, flags)`` rows."""
    if not isinstance(item, int):
        return [(item, text, flags)]
    parts = split_glued_numbered_note_body(item, text)
    if len(parts) <= 1:
        return [(item, text, flags)]
    rows: list[tuple[int | str | None, str, list[str]]] = []
    for i, (note_item, note_text) in enumerate(parts):
        rows.append((note_item, note_text, list(flags) if i == 0 else []))
    return rows


def _blocks_from_region(
    region_text: str,
    *,
    printed_page: int,
    pdf_page: int,
    headers: set[str],
    as_notes: bool,
) -> list[dict]:
    blocks_out: list[dict] = []
    for raw in _split_blocks(region_text, notes=as_notes):
        # Running header + page number + body with no blank line → peel furniture
        # before normalize/item-parse (else ``10. Subhasutta`` becomes item=10).
        if not as_notes and headers:
            raw = peel_leading_running_headers(raw, headers)
            if not str(raw).strip():
                continue
        # Uddāna label glued to verse lines (missing blank line in PDF text).
        if not as_notes:
            peeled_gatha = peel_glued_gatha_title_raw(raw)
            if peeled_gatha is not None:
                title, verse_lines = peeled_gatha
                heading, reasons = _classify_heading(title)
                assert heading in {"title", "tassuddānaṃ"}
                blocks_out.append(
                    {
                        "kind": heading,
                        "item": None,
                        "text": title,
                        "flags": [],
                        "page": printed_page,
                        "pdf_page": pdf_page,
                        "needs_review": bool(reasons),
                        "review_reasons": reasons,
                    }
                )
                for vline in verse_lines:
                    if _is_section_rule_line(vline):
                        if blocks_out:
                            prev = blocks_out[-1]
                            prev["text"] = _attach_section_rule_tail(
                                str(prev.get("text") or "")
                            )
                        continue
                    blocks_out.append(
                        {
                            "kind": "prose",
                            "item": None,
                            "text": _normalize_inline(vline),
                            "flags": [],
                            "page": printed_page,
                            "pdf_page": pdf_page,
                        }
                    )
                continue

        text = _normalize_inline(raw)
        # Underscore-only short rule on its own line → attach to previous body
        # block as trailing ``_____`` (becomes ``section_rule`` at serialize).
        if not as_notes and text and _is_section_rule_line(text):
            if blocks_out:
                prev = blocks_out[-1]
                prev["text"] = _attach_section_rule_tail(str(prev.get("text") or ""))
            continue
        if _is_running_header(raw, headers):
            continue
        if not text or FOOTNOTE_RULE_RE.match(text):
            continue

        if as_notes:
            item, rest, flags = _parse_item_prefix(text)
            if item is None:
                star = STAR_BLOCK_RE.match(text)
                plus = PLUS_BLOCK_RE.match(text)
                if star:
                    _append_symbol_note_blocks(
                        blocks_out,
                        mark="*",
                        text=star.group(1),
                        printed_page=printed_page,
                        pdf_page=pdf_page,
                    )
                elif plus:
                    _append_symbol_note_blocks(
                        blocks_out,
                        mark="+",
                        text=plus.group(1),
                        printed_page=printed_page,
                        pdf_page=pdf_page,
                    )
                else:
                    blocks_out.append(
                        {
                            "kind": "note_continuation",
                            "item": None,
                            "text": text,
                            "flags": [],
                            "page": printed_page,
                            "pdf_page": pdf_page,
                        }
                    )
            else:
                for note_item, note_text, note_flags in expand_glued_numbered_notes(
                    item, rest, flags
                ):
                    blocks_out.append(
                        {
                            "kind": "note",
                            "item": note_item,
                            "text": note_text,
                            "flags": note_flags,
                            "page": printed_page,
                            "pdf_page": pdf_page,
                        }
                    )
            continue

        star = STAR_BLOCK_RE.match(text)
        plus = PLUS_BLOCK_RE.match(text)
        if star and not ITEM_SINGLE_RE.match(text):
            blocks_out.append(
                {
                    "kind": "prose",
                    "item": None,
                    "text": star.group(1).strip(),
                    "flags": ["star"],
                    "page": printed_page,
                    "pdf_page": pdf_page,
                }
            )
            continue
        if plus and not ITEM_SINGLE_RE.match(text):
            blocks_out.append(
                {
                    "kind": "prose",
                    "item": None,
                    "text": plus.group(1).strip(),
                    "flags": ["plus"],
                    "page": printed_page,
                    "pdf_page": pdf_page,
                }
            )
            continue

        item, rest, flags = _parse_item_prefix(text)
        if item is not None:
            peeled = peel_glued_uddesa_heading(rest)
            if peeled is not None:
                title, body = peeled
                heading, reasons = _classify_heading(title)
                assert heading is not None
                blocks_out.append(
                    {
                        "kind": heading,
                        "item": None,
                        "text": title,
                        "flags": flags,
                        "page": printed_page,
                        "pdf_page": pdf_page,
                        "section_no": item,
                        "needs_review": bool(reasons),
                        "review_reasons": reasons,
                    }
                )
                blocks_out.append(
                    {
                        "kind": "prose",
                        "item": None,
                        "text": body,
                        "flags": [],
                        "page": printed_page,
                        "pdf_page": pdf_page,
                    }
                )
                continue
            heading, reasons = _classify_heading(rest)
            if heading and len(rest) <= 80:
                blocks_out.append(
                    {
                        "kind": heading,
                        "item": None,
                        "text": rest,
                        "flags": flags,
                        "page": printed_page,
                        "pdf_page": pdf_page,
                        "section_no": item,
                        "needs_review": bool(reasons),
                        "review_reasons": reasons,
                    }
                )
            else:
                blocks_out.append(
                    {
                        "kind": "prose",
                        "item": item,
                        "text": rest,
                        "flags": flags,
                        "page": printed_page,
                        "pdf_page": pdf_page,
                    }
                )
            continue

        peeled = peel_glued_uddesa_heading(text)
        if peeled is not None:
            title, body = peeled
            heading, reasons = _classify_heading(title)
            assert heading is not None
            blocks_out.append(
                {
                    "kind": heading,
                    "item": None,
                    "text": title,
                    "flags": [],
                    "page": printed_page,
                    "pdf_page": pdf_page,
                    "needs_review": bool(reasons),
                    "review_reasons": reasons,
                }
            )
            blocks_out.append(
                {
                    "kind": "prose",
                    "item": None,
                    "text": body,
                    "flags": [],
                    "page": printed_page,
                    "pdf_page": pdf_page,
                }
            )
            continue

        heading, reasons = _classify_heading(text)
        if heading:
            blocks_out.append(
                {
                    "kind": heading,
                    "item": None,
                    "text": text,
                    "flags": [],
                    "page": printed_page,
                    "pdf_page": pdf_page,
                    "needs_review": bool(reasons),
                    "review_reasons": reasons,
                }
            )
            continue

        # Long expansion ``(…)`` after summary verses — centered prose furniture.
        prose_flags: list[str] = []
        prose_layout = None
        if is_expansion_parenthetical(text):
            prose_layout = "center"
        blocks_out.append(
            {
                "kind": "prose",
                "item": None,
                "text": text,
                "flags": prose_flags,
                "page": printed_page,
                "pdf_page": pdf_page,
                "source_layout": prose_layout,
            }
        )
    return blocks_out


def extract_page_blocks(
    page_text: str,
    *,
    printed_page: int,
    pdf_page: int,
    headers: set[str],
    is_opening_page: bool = False,
) -> list[dict]:
    body, notes = _split_body_and_notes(page_text)
    # Continuation-page furniture: centered ``N. Title`` + edition page number
    # (outer margin) may be blank-line-separated; peel before block split.
    if not is_opening_page:
        body = peel_page_top_running_header_furniture(body, headers)
    body = _strip_running_header_lines(
        body, headers, keep_until_namo=is_opening_page
    )
    notes = _strip_running_header_lines(notes, headers)

    blocks: list[dict] = []
    if is_opening_page:
        pre_namo, from_namo = _split_at_namo(body)
        # Opening titles share strings with later running headers — do not
        # filter them as headers before Namo.
        if pre_namo.strip():
            blocks.extend(
                _blocks_from_region(
                    pre_namo,
                    printed_page=printed_page,
                    pdf_page=pdf_page,
                    headers=set(),
                    as_notes=False,
                )
            )
        body_after = from_namo
    else:
        body_after = body

    if body_after.strip():
        blocks.extend(
            _blocks_from_region(
                body_after,
                printed_page=printed_page,
                pdf_page=pdf_page,
                headers=headers,
                as_notes=False,
            )
        )
    if notes.strip():
        blocks.extend(
            _blocks_from_region(
                notes,
                printed_page=printed_page,
                pdf_page=pdf_page,
                headers=headers,
                as_notes=True,
            )
        )
    return blocks


def merge_blocks(raw_blocks: list[dict]) -> list[Segment]:
    """
    Build page-anchored segments (one printed page per segment).

    Rules:
    - Itemless body under the current item → ``prose`` / base kind (same or
      later page). Geometry later upgrades flush page-starts to
      ``{kind}_continuation``; indented page-starts stay new paragraphs.
    - Mid-word page break → finish the word on the earlier segment.
    - One printed page per segment (no page span field).
    """
    segments: list[Segment] = []
    order = 0
    last_body_idx: int | None = None
    last_note_idx: int | None = None

    def append_new(block: dict) -> Segment:
        nonlocal order, last_body_idx, last_note_idx
        order += 1
        layout = block.get("source_layout")
        if block["kind"] == "tassuddānaṃ" and not layout:
            layout = "center"
        seg = Segment(
            page=block["page"],
            order=order,
            item=block.get("item"),
            segment_type=block["kind"],
            text=block["text"],
            pdf_page=block.get("pdf_page"),
            flags=list(block.get("flags") or []),
            needs_review=bool(block.get("needs_review")),
            review_reasons=list(block.get("review_reasons") or []),
            section_no=block.get("section_no"),
            source_layout=layout,
        )
        segments.append(seg)
        idx = len(segments) - 1
        base = _base_kind(seg.segment_type)
        if base in {"prose", "gatha", "verse"}:
            last_body_idx = idx
        elif seg.segment_type in {
            "namakkāraṃ",
            "piṭaka",
            "gambhīra",
            "nikaya",
            "book",
            "chapter",
            "title",
            "tassuddānaṃ",
            "subhead",
            "niṭṭhitaṃ",
            "centered",
        }:
            # Structural break — do not inherit item across headings.
            last_body_idx = None
        elif seg.segment_type == "note":
            last_note_idx = idx
        return seg

    for block in raw_blocks:
        kind = block["kind"]

        if kind == "note_continuation":
            if last_note_idx is not None and segments[last_note_idx].page == block["page"]:
                prev = segments[last_note_idx]
                prev.text = f"{prev.text} {block['text']}".strip()
            else:
                append_new({**block, "kind": "note"})
            continue

        # Separate underscore-only body line → previous segment (not a new one).
        if (
            kind not in {"note", "note_continuation"}
            and _is_section_rule_line(str(block.get("text") or ""))
        ):
            target_idx = last_body_idx
            if target_idx is None and segments:
                target_idx = len(segments) - 1
            if target_idx is not None:
                prev = segments[target_idx]
                prev.text = _attach_section_rule_tail(prev.text)
            continue

        if (
            kind in {"prose", "gatha", "verse"}
            and block.get("item") is None
            and last_body_idx is not None
            and not block.get("flags")
        ):
            prev = segments[last_body_idx]
            block_page = block["page"]

            # Cross-page: repair mid-word hyphen splits. A joined hyphen means
            # the remainder cannot be a new paragraph → continuation. Otherwise
            # keep base kind; geometry upgrades flush page-starts afterward.
            text = block["text"]
            out_kind = kind if kind != "prose" else "prose"
            if (
                block_page > prev.page
                and prev.segment_type in _CONTINUABLE_KINDS
            ):
                prev_text, next_text, joined = _repair_mid_word_split(
                    prev.text, text
                )
                prev.text = prev_text
                if not next_text.strip():
                    # Entire remainder was only the end of a split word.
                    continue
                text = next_text
                if joined:
                    out_kind = _continuation_kind(kind)

            # Same item, same or later page — base kind until geometry / hyphen
            # repair says this is a continuation.
            append_new(
                {
                    **block,
                    "item": prev.item,
                    "kind": out_kind,
                    "text": text,
                }
            )
            continue

        # Apparatus * / + paragraphs belong under the current item number.
        if (
            kind == "prose"
            and block.get("item") is None
            and last_body_idx is not None
            and set(block.get("flags") or []) & {"star", "plus"}
        ):
            append_new({**block, "item": segments[last_body_idx].item})
            continue

        append_new(block)

    for i, seg in enumerate(segments, start=1):
        seg.order = i
    return segments


def is_spaced_outline_number(spaces: str, trailer: str | None) -> bool:
    """True for ``vagga 1.`` / ``2. Title``-style outline numbers, not callouts."""
    return bool(spaces) and trailer == "."


def apply_numbered_footnote_callouts(
    text: str,
    numbered: dict[int, str],
    *,
    note_index_base: int = 0,
    allow_reuse: bool = False,
) -> tuple[str, list[str], set[int]]:
    """Bind numbered callouts in ``text`` to note bodies keyed by source mark.

    Accepts glued (``word1``) and spaced (``word 1``) marks. Spaced marks
    followed by ``.`` are left unchanged (outline numbers).

    Returns ``(new_text, bound_note_texts, used_item_numbers)``. Markers are
    ``{{nK}}`` with ``K`` starting at ``note_index_base``.

    When ``allow_reuse`` is true, the same source mark may bind more than once
    (shared apparatus on one page); each callout still gets its own note body
    copy in ``notes_out``.
    """
    notes_out: list[str] = []
    used_items: set[int] = set()
    available = dict(numbered)

    def replace_callout(match: re.Match[str]) -> str:
        spaces, num_s, trailer = match.group(1), match.group(2), match.group(3)
        if is_spaced_outline_number(spaces, trailer):
            return match.group(0)
        num = int(num_s)
        note_text = available.get(num)
        if note_text is None:
            return match.group(0)
        idx = note_index_base + len(notes_out)
        notes_out.append(note_text)
        used_items.add(num)
        if not allow_reuse:
            available.pop(num, None)
        return "{{" + f"n{idx}" + "}}"

    return FOOTNOTE_CALLOUT_RE.sub(replace_callout, text), notes_out, used_items


def _insert_empty_paren_marker(text: str) -> str | None:
    """Insert ``{{()}}`` after the first non-folio ``(``; None if none."""
    i = 0
    while True:
        j = text.find("(", i)
        if j < 0:
            return None
        if _FOLIO_PAREN_RE.match(text[j:]):
            i = j + 1
            continue
        return text[: j + 1] + "{{()}}" + text[j + 1 :]


def _is_symbol_apparatus_note(note: Segment) -> bool:
    """True for unnumbered apparatus notes (not ``1.`` / ``2.`` footnotes).

    Numbered note bodies may start with ``( ) …`` / ``[ ] …`` as *text*
    (01Vin01 p.86 note 2); those must stay in the numbered pool.
    """
    return not isinstance(note.item, int)


def _bind_inline_symbol_callouts(
    text: str,
    *,
    mark: str,
    page_notes: list[Segment],
    symbol_notes: dict[str, str],
    shared_symbol_notes: dict[tuple[int, str], str],
    page: int,
    used_note_ids: set[int],
) -> tuple[str, dict[str, str]]:
    """Replace mid-paragraph `` + `` / `` * `` with ``{{+}}`` / ``{{*}}``."""
    marker = "{{" + mark + "}}"
    if marker in text:
        return text, symbol_notes
    callout_re = (
        _INLINE_PLUS_CALLOUT_RE if mark == "+" else _INLINE_STAR_CALLOUT_RE
    )
    if not callout_re.search(text):
        return text, symbol_notes

    key = (page, mark)
    available = [n for n in page_notes if id(n) not in used_note_ids]
    if available:
        note_seg = available[0]
        symbol_notes = dict(symbol_notes)
        symbol_notes[mark] = note_seg.text
        shared_symbol_notes[key] = note_seg.text
        used_note_ids.add(id(note_seg))
    elif key in shared_symbol_notes:
        symbol_notes = dict(symbol_notes)
        symbol_notes[mark] = shared_symbol_notes[key]
    else:
        return text, symbol_notes

    return callout_re.sub(marker, text, count=1), symbol_notes


def attach_notes_sacred_style(segments: list[Segment]) -> list[Segment]:
    """
    Fold page footnotes into body segments (sacred-app style).

    Numbered callouts → ``{{nK}}`` + ``notes[K]``.
    ``*`` / ``+`` apparatus notes → ``{{*}}`` / ``{{+}}`` + ``symbol_notes``
    (do not share the numbered footnote sequence). Mid-paragraph `` + `` /
    `` * `` callouts are bound the same way. Bracket notes ``[  ] …`` bind to
    the body ``[`` on the same page as ``{{[]}}``. Empty-paren notes
    ``(  ) …`` bind to the first non-folio body ``(`` as ``{{()}}``.
    Numbered footnotes whose body starts with ``( )`` / ``[ ]`` stay
    numbered (they are not symbol apparatus). Folio markers like
    ``(150)`` never host ``{{()}}``.
    Unmatched leftover notes remain as segment_type=note with needs_review.
    """
    notes_by_page: dict[int, list[Segment]] = {}
    for seg in segments:
        if seg.segment_type == "note":
            notes_by_page.setdefault(seg.page, []).append(seg)

    used_note_ids: set[int] = set()
    # One foot-note body per mark per page; later * / + callouts share it.
    shared_symbol_notes: dict[tuple[int, str], str] = {}
    # Numbered marks may also repeat on a page (same apparatus, several hosts).
    shared_numbered_notes: dict[tuple[int, int], str] = {}
    out: list[Segment] = []

    for seg in segments:
        if seg.segment_type == "note":
            continue

        # Only notes printed on this segment's page (callout page).
        page_notes = list(notes_by_page.get(seg.page, []))

        numbered = {
            n.item: n
            for n in page_notes
            if isinstance(n.item, int) and id(n) not in used_note_ids
        }
        star_notes = [
            n
            for n in page_notes
            if "star" in n.flags and id(n) not in used_note_ids
        ]
        plus_notes = [
            n
            for n in page_notes
            if "plus" in n.flags and id(n) not in used_note_ids
        ]

        symbol_notes: dict[str, str] = {}

        numbered_texts = {
            item: note_seg.text for item, note_seg in numbered.items()
        }
        for (page, mark), body in shared_numbered_notes.items():
            if page == seg.page and mark not in numbered_texts:
                numbered_texts[mark] = body
        new_text, notes_out, used_items = apply_numbered_footnote_callouts(
            seg.text, numbered_texts, allow_reuse=True
        )
        for item in used_items:
            if item in numbered:
                note_seg = numbered.pop(item)
                used_note_ids.add(id(note_seg))
                shared_numbered_notes[(seg.page, item)] = note_seg.text
            elif (seg.page, item) in shared_numbered_notes:
                pass
            else:
                # Bound via shared copy only.
                shared_numbered_notes[(seg.page, item)] = numbered_texts[item]

        # Body * / + callouts always stay in text. Several callouts may share
        # one foot-note (e.g. two + marks → one "+ …" note at page bottom).
        if "star" in seg.flags:
            key = (seg.page, "*")
            if star_notes:
                note_seg = star_notes[0]
                symbol_notes["*"] = note_seg.text
                shared_symbol_notes[key] = note_seg.text
                used_note_ids.add(id(note_seg))
            elif key in shared_symbol_notes:
                symbol_notes["*"] = shared_symbol_notes[key]
            if "{{*}}" not in new_text:
                new_text = "{{*}}" + new_text

        if "plus" in seg.flags:
            key = (seg.page, "+")
            if plus_notes:
                note_seg = plus_notes[0]
                symbol_notes["+"] = note_seg.text
                shared_symbol_notes[key] = note_seg.text
                used_note_ids.add(id(note_seg))
            elif key in shared_symbol_notes:
                symbol_notes["+"] = shared_symbol_notes[key]
            if "{{+}}" not in new_text:
                new_text = "{{+}}" + new_text

        # Mid-paragraph `` + `` / `` * `` callouts (not only paragraph-initial).
        new_text, symbol_notes = _bind_inline_symbol_callouts(
            new_text,
            mark="+",
            page_notes=plus_notes,
            symbol_notes=symbol_notes,
            shared_symbol_notes=shared_symbol_notes,
            page=seg.page,
            used_note_ids=used_note_ids,
        )
        new_text, symbol_notes = _bind_inline_symbol_callouts(
            new_text,
            mark="*",
            page_notes=star_notes,
            symbol_notes=symbol_notes,
            shared_symbol_notes=shared_symbol_notes,
            page=seg.page,
            used_note_ids=used_note_ids,
        )

        # Bracket apparatus ``[  ] …`` notes → marker next to body ``[``.
        # Skip numbered footnotes whose body merely begins with ``[ ]``.
        bracket_notes = [
            n
            for n in page_notes
            if id(n) not in used_note_ids
            and _is_symbol_apparatus_note(n)
            and _BRACKET_NOTE_RE.match((n.text or "").strip())
        ]
        if bracket_notes and "[" in new_text and "{{[]}}" not in new_text:
            note_seg = bracket_notes[0]
            m = _BRACKET_NOTE_RE.match((note_seg.text or "").strip())
            assert m is not None
            symbol_notes["[]"] = m.group(1).strip()
            used_note_ids.add(id(note_seg))
            new_text = new_text.replace("[", "[{{[]}}", 1)

        # Empty-paren apparatus ``(  ) …`` → marker next to body ``(``.
        # Skip numbered footnotes whose body begins with ``( )`` (common
        # empty-reading formula). Never host the marker on folio ``(150)``.
        paren_notes = [
            n
            for n in page_notes
            if id(n) not in used_note_ids
            and _is_symbol_apparatus_note(n)
            and _PAREN_NOTE_RE.match((n.text or "").strip())
        ]
        if paren_notes and "{{()}}" not in new_text:
            marked = _insert_empty_paren_marker(new_text)
            if marked is not None:
                note_seg = paren_notes[0]
                m = _PAREN_NOTE_RE.match((note_seg.text or "").strip())
                assert m is not None
                symbol_notes["()"] = m.group(1).strip()
                used_note_ids.add(id(note_seg))
                new_text = marked

        seg.text = new_text
        seg.notes = notes_out
        seg.symbol_notes = symbol_notes
        out.append(seg)

    orphans = sorted(
        (
            n
            for page_notes in notes_by_page.values()
            for n in page_notes
            if id(n) not in used_note_ids
        ),
        key=lambda s: (s.page, s.order),
    )
    for note in orphans:
        note.needs_review = True
        if "orphan_note" not in note.review_reasons:
            note.review_reasons.append("orphan_note")
        out.append(note)

    for i, seg in enumerate(out, start=1):
        seg.order = i
    return out


def _gatha_line_body(text: str) -> str:
    """Strip apparatus markers / quotes / section-rule tail for verse-shape checks."""
    t = (text or "").strip()
    t = re.sub(r"^\{\{\*\}\}\s*", "", t)
    t = re.sub(r"^\{\{\+\}\}\s*", "", t)
    t = re.sub(r"^[\*\+]\s*", "", t)
    t, _ = split_trailing_section_rule(t)
    return t.strip(" \t\"'“”«»")


def _note_section_rule_flag(seg: Segment) -> None:
    if SECTION_RULE_FLAG not in seg.flags:
        seg.flags.append(SECTION_RULE_FLAG)


def _peel_gatha_line_section_rule(seg: Segment, text: str) -> str:
    """Strip trailing ``_____`` before bat/wak tests; record ``section_rule``.

    Extract glues the decorative section rule onto the previous body block.
    If fold sees ``A, B. _____``, ``_is_bat_printed_line`` fails (line does not
    end with a stop) and the บาท stays one วรรค — peel first so comma-split
    still runs, and keep the flag for generate.
    """
    body, had_rule = split_trailing_section_rule((text or "").strip())
    if had_rule:
        _note_section_rule_flag(seg)
        seg.text = body
    return body


def _looks_like_bat_gatha_line(text: str) -> bool:
    """True for one printed บาท: two วรรค as ``A, B.`` (comma + final stop).

    Bat-line gāthā repeats this shape on every printed line of the block.
    """
    body = _gatha_line_body(text)
    if not body or len(body) > 160:
        return False
    if _looks_like_prose_not_gatha_wak(body):
        return False
    return _is_bat_printed_line(body)


def _looks_like_prose_not_gatha_wak(text: str) -> bool:
    """True for narrative/speech-intro lines that must not fold as วรรค.

    Catches lead-ins ending in en/em dash, long lines, and quote-close
    ``…ti`` followed by more prose (not verse-final ``…ti.``).
    """
    body = _gatha_line_body(text)
    if not body:
        return True
    if is_section_nama_colophon(body):
        return True
    if ends_with_speech_intro_dash(body):
        return True
    if len(body) > 70:
        return True
    # Quote-close ``…"ti`` then more prose (not verse-final ``…ti.`` / ``…"ti.``).
    if re.search(r"[\"'\u201c\u201d»]ti\b", body, re.IGNORECASE) and not re.search(
        r"[\"'\u201c\u201d»]?ti[.!…]?[\"'\u201c\u201d»]?\s*$",
        body,
        re.IGNORECASE,
    ):
        return True
    # Narrative subject then opening quote: ``Manussā “dhammena…``
    if re.search(r"^[^\"'\u201c\u201d«»]+?\s+[\"'\u201c\u201d«»]", body):
        return True
    return False


def _looks_like_gatha_seed_line(text: str) -> bool:
    """True for a printed line that can start a gāthā run (bat or wak)."""
    body = _gatha_line_body(text)
    if not body or len(body) > 160:
        return False
    if _looks_like_prose_not_gatha_wak(body):
        return False
    if _is_bat_printed_line(body):
        return True
    # wak_line first วรรค
    return body.endswith(",")


def _looks_like_gatha_line(text: str) -> bool:
    """True for bat_line, wak seed, or short wak/bat closing line."""
    if _looks_like_prose_not_gatha_wak(text):
        return False
    if _looks_like_gatha_seed_line(text):
        return True
    body = _gatha_line_body(text)
    if not body or len(body) > 160:
        return False
    # wak_line second วรรค / short verse close
    if not re.search(r"[.!?…][\"'\u201c\u201d]?\s*$", body):
        return False
    return len(body) <= 120


def tag_gatha_segments(segments: list[Segment]) -> list[Segment]:
    """
    After an uddāna/gāthā title, retag short itemless prose lines as ``gatha``.

    Stops at numbered prose, structural headings, or notes. Apparatus (* / +)
    on a verse-shaped line stays inside the run; other * / + exits.
    Each tagged segment is still one *printed* line; ``group_gatha_stanzas``
    then folds lines into บท → บาท → วรรค.

    Embedded quotes (no title) are handled by ``tag_gatha_by_geometry``.
    """
    out: list[Segment] = []
    in_gatha = False
    for seg in segments:
        if seg.segment_type == "tassuddānaṃ" or (
            seg.segment_type == "title" and GATHA_TITLE_RE.search(seg.text)
        ):
            in_gatha = True
            if "weak_heading_heuristic" in seg.review_reasons:
                seg.review_reasons = [
                    r for r in seg.review_reasons if r != "weak_heading_heuristic"
                ]
                if not seg.review_reasons:
                    seg.needs_review = False
            out.append(seg)
            continue

        if not in_gatha:
            out.append(seg)
            continue

        if seg.segment_type in _GATHA_STOP_KINDS:
            # A new summary / gāthā title re-enters; any other structural exits.
            if seg.segment_type == "tassuddānaṃ" or (
                seg.segment_type == "title" and GATHA_TITLE_RE.search(seg.text)
            ):
                in_gatha = True
                out.append(seg)
                continue
            in_gatha = False
            out.append(seg)
            continue

        base = _base_kind(seg.segment_type)
        if base not in {"prose", "gatha"}:
            in_gatha = False
            out.append(seg)
            continue

        # Peel glued expansion ``(…)`` before length checks demote the verse.
        paren_seg: Segment | None = None
        peeled_paren = peel_trailing_expansion_parenthetical(seg.text or "")
        if peeled_paren is not None:
            body, paren = peeled_paren
            seg.text = body
            paren_seg = _expansion_paren_segment_from_template(seg, paren)

        if set(seg.flags) & {"star", "plus"} and not _looks_like_gatha_line(
            seg.text
        ):
            in_gatha = False
            out.append(seg)
            if paren_seg is not None:
                out.append(paren_seg)
            continue

        if seg.item is not None:
            in_gatha = False
            out.append(seg)
            if paren_seg is not None:
                out.append(paren_seg)
            continue

        # Section closers after uddāna (…samatto. / …niṭṭhito.) are not verse.
        if is_section_closer_formula(seg.text):
            in_gatha = False
            out.append(seg)
            if paren_seg is not None:
                out.append(paren_seg)
            continue

        # “…codenti–” / “…paṭicodetha–” introduce the quote; stay prose.
        if ends_with_speech_intro_dash(seg.text):
            in_gatha = False
            out.append(seg)
            if paren_seg is not None:
                out.append(paren_seg)
            continue

        if _looks_like_prose_not_gatha_wak(seg.text):
            in_gatha = False
            out.append(seg)
            if paren_seg is not None:
                out.append(paren_seg)
            continue

        # Verse lines in this edition are short couplet halves.
        if len(seg.text) > 160:
            in_gatha = False
            out.append(seg)
            if paren_seg is not None:
                out.append(paren_seg)
            continue

        if seg.segment_type.endswith("_continuation"):
            seg.segment_type = "gatha_continuation"
        else:
            seg.segment_type = "gatha"
        out.append(seg)
        if paren_seg is not None:
            out.append(paren_seg)

    return out


def tag_gatha_by_geometry(
    doc: fitz.Document,
    segments: list[Segment],
    *,
    content_start: int | None = None,
) -> int:
    """
    Retag prose lines in the verse indent that look like gāthā.

    Bat-line blocks: every printed line is ``วรรค, วรรค.`` (comma + stop).
    Hang / near-hang band accepts bat_line, and also wak_line runs of at
    least two printed lines (one บาท as วรรค pairs — e.g. embedded udāna
    quotes). Deep gāthā column allows wak_line seeds with the usual grow.

    Catches embedded quotes (no uddāna title). Returns how many printed-line
    segments were retagged.
    """
    if fitz is None:
        raise RuntimeError("PyMuPDF (pymupdf) is required")

    line_cache: dict[int, list] = {}
    tagged = 0
    i = 0
    n = len(segments)
    while i < n:
        seg = segments[i]
        base = _base_kind(seg.segment_type)
        seed_is_bat = _looks_like_bat_gatha_line(seg.text) or (
            seg.item is not None and _is_bat_printed_line(seg.text)
        )
        if (
            base != "prose"
            or seg.bats is not None
            or seg.source_layout == "hanging"
            or not (seed_is_bat or _looks_like_gatha_seed_line(seg.text))
        ):
            i += 1
            continue

        pdf_page = _seg_pdf_page(seg, content_start=content_start)
        if pdf_page is None or pdf_page < 1 or pdf_page > doc.page_count:
            i += 1
            continue
        if pdf_page not in line_cache:
            line_cache[pdf_page] = page_body_lines(doc[pdf_page - 1])
        roman = segment_roman_text(seg) or seg.text
        matched = _match_cached_line(line_cache[pdf_page], roman)
        if matched is None:
            i += 1
            continue
        # Deep / hang-band verse, or first-indent numbered bat head (item).
        seed_first_indent = _is_first_indent(matched.x0)
        if not (
            _is_gatha_geometry_indent(matched.x0)
            or (seed_is_bat and seed_first_indent and seg.item is not None)
        ):
            i += 1
            continue

        # Hang / near-hang wak_line (comma-only first วรรค): allow only when
        # the grown run has ≥2 printed lines (one บาท). Deep column wak OK
        # with a single seed line (grow may still add pair lines).
        hang_band_wak = not seed_is_bat and not _is_gatha_indent(matched.x0)

        # Grow a run; bat-line seeds stay bat-shaped on every line.
        run_end = i + 1
        while run_end < n:
            nxt = segments[run_end]
            nxt_base = _base_kind(nxt.segment_type)
            shape_ok = (
                (
                    _looks_like_bat_gatha_line(nxt.text)
                    or _is_bat_printed_line(nxt.text)
                )
                if seed_is_bat
                else _looks_like_gatha_line(nxt.text)
            )
            if (
                nxt_base != "prose"
                or nxt.bats is not None
                or nxt.source_layout == "hanging"
                or ends_with_speech_intro_dash(nxt.text)
                or (
                    not seed_is_bat
                    and _looks_like_prose_not_gatha_wak(nxt.text)
                )
                or not shape_ok
            ):
                break
            nxt_pdf = _seg_pdf_page(nxt, content_start=content_start)
            if nxt_pdf is None or nxt_pdf < 1 or nxt_pdf > doc.page_count:
                break
            if nxt_pdf not in line_cache:
                line_cache[nxt_pdf] = page_body_lines(doc[nxt_pdf - 1])
            nxt_roman = segment_roman_text(nxt) or nxt.text
            nxt_match = _match_cached_line(line_cache[nxt_pdf], nxt_roman)
            if nxt_match is None or not _is_gatha_geometry_indent(nxt_match.x0):
                break
            run_end += 1

        # Bat / deep wak: ≥1 printed line. Hang-band wak: ≥2 (one บาท).
        # First-indent numbered bat head must grow ≥1 hang/geometry child.
        min_run = 2 if hang_band_wak or seed_first_indent else 1
        if run_end - i < min_run:
            i += 1
            continue

        # Keep Tipiṭaka item only on first-indent numbered verse heads;
        # embedded geometry runs clear item so prose numbering is not repeated.
        preserve_item = seed_first_indent and seg.item is not None
        for j in range(i, run_end):
            cur = segments[j]
            if cur.segment_type.endswith("_continuation"):
                cur.segment_type = "gatha_continuation"
            else:
                cur.segment_type = "gatha"
            if not preserve_item or j > i:
                cur.item = None
            tagged += 1
        i = run_end

    return tagged


def _is_bat_printed_line(text: str) -> bool:
    """True when one printed line is one บาท: two วรรค as ``A, B.``.

    Comma separates the วรรค; a final stop closes the บาท. Bat-line gāthā
    uses this shape on every printed line of the block. Trailing section-rule
    underscores (``_____``) are ignored for the shape test.
    """
    t, _ = split_trailing_section_rule((text or "").strip())
    if not re.search(r"[.!?…][\"'\u201c\u201d]?\s*$", t):
        return False
    return bool(re.search(r",\s+\S", t))


def _split_bat_printed_line(text: str) -> tuple[str, str] | None:
    """Split ``A, B.`` into two วรรค strings (comma stays on the first)."""
    t = text.strip()
    m = re.search(r",\s+", t)
    if not m:
        return None
    first = t[: m.start() + 1].strip()  # include comma
    second = t[m.end() :].strip()
    if not first or not second:
        return None
    return first, second


# After a verse stop, ``{{sp1}}`` then more text = next printed line glued by
# ``_split_blocks`` when the PDF text layer omits a blank line.
# Sentence spacer form is ``.{{sp1}} Word`` (space after the marker).
# Space-only ``head. rest`` is glued only when ``head`` is a completed บาท
# (``A, B.``). Abhidhamma Yamaka ``X. Y`` / ``X.  . Y`` stays one line
# (35Abhi07 p.76).
_GLUED_GATHA_SP1_TAIL_RE = re.compile(
    r"^(.+?[.!?…][\"'\u201c\u201d]?)\{\{sp1\}\}+\s+(\S[\s\S]*)$"
)
_GLUED_GATHA_BAT_SPACE_TAIL_RE = re.compile(
    r"^(.+?[.!?…][\"'\u201c\u201d]?)\s+(\S[\s\S]*)$"
)


def split_glued_gatha_printed_line_tail(text: str) -> tuple[str, str] | None:
    """Split ``head.{{sp1}} rest`` or bat-shaped ``A, B. rest`` after the stop.

    Used when PDF block-join collapsed consecutive gāthā printed lines into one
    paragraph. Returns ``None`` when nothing follows the first stop, or when
    a space-only tail is not a completed บาท plus the next verse line.
    """
    t = (text or "").strip()
    if not t:
        return None
    m = _GLUED_GATHA_SP1_TAIL_RE.match(t)
    if m is None:
        m = _GLUED_GATHA_BAT_SPACE_TAIL_RE.match(t)
        if m is None:
            return None
        head = m.group(1).strip()
        rest = m.group(2).strip()
        if not head or not rest:
            return None
        if not _is_bat_printed_line(head):
            return None
        return head, rest
    head = m.group(1).strip()
    rest = m.group(2).strip()
    if not head or not rest:
        return None
    return head, rest


def expand_glued_gatha_printed_lines(text: str) -> list[str]:
    """Expand a block-joined gāthā string into printed-line pieces."""
    t = (text or "").strip()
    if not t:
        return []
    out: list[str] = []
    rest = t
    while rest:
        peeled = split_glued_gatha_printed_line_tail(rest)
        if peeled is None:
            out.append(rest)
            break
        head, more = peeled
        out.append(head)
        rest = more
    return out


def _gatha_line_segment_from_template(template: Segment, roman: str) -> Segment:
    """Clone a printed-line gāthā segment with a different roman body."""
    return Segment(
        page=template.page,
        order=template.order,
        item=template.item,
        segment_type=template.segment_type,
        text=roman,
        pdf_page=template.pdf_page,
        flags=list(template.flags),
        notes=[],
        symbol_notes={},
        needs_review=template.needs_review,
        review_reasons=list(template.review_reasons),
        section_no=template.section_no,
        source_layout=None,
        bats=None,
    )


def _wak_dict(wak_no: int, roman: str) -> dict:
    return {
        "wak": wak_no,
        "role": _WAK_ROLES.get(wak_no, f"wak{wak_no}"),
        "text": roman,
    }


def _bat_dict(bat_no: int, wak_a: str, wak_b: str) -> dict:
    # bat 1 → wak 1–2, bat 2 → 3–4, bat 3 → 5–6 (1 บทครึ่ง / 1.5 stanza).
    base = 2 * (bat_no - 1) + 1
    return {
        "bat": bat_no,
        "waks": [_wak_dict(base, wak_a), _wak_dict(base + 1, wak_b)],
    }


def _one_bat_wak_romans(
    buf: list[tuple[str, str, Segment]],
) -> list[str] | None:
    """
    If ``buf`` is exactly one verse บาท (two วรรค), return those roman strings.

    Accepts either two already-split **bat_line** units or one unsplit
    ``A, B.`` bat line. Wak-line leftovers (often prose intrusion) are
    rejected so they are not glued onto the previous บท as 1 บทครึ่ง.
    """
    if len(buf) == 2 and all(u[1] == "bat_line" for u in buf):
        if any(_looks_like_prose_not_gatha_wak(u[0]) for u in buf):
            return None
        return [buf[0][0], buf[1][0]]
    if (
        len(buf) == 1
        and buf[0][1] == "bat_line"
        and _is_bat_printed_line(buf[0][0])
    ):
        if _looks_like_prose_not_gatha_wak(buf[0][0]):
            return None
        parts = _split_bat_printed_line(buf[0][0])
        if parts:
            return [parts[0], parts[1]]
    return None


def _prose_segment_from_gatha_line(template: Segment, roman: str) -> Segment:
    """Rebuild a prose segment from a mistagged gāthā printed line."""
    return Segment(
        page=template.page,
        order=template.order,
        item=template.item,
        segment_type="prose",
        text=roman,
        pdf_page=template.pdf_page,
        flags=list(template.flags),
        notes=list(template.notes),
        symbol_notes=dict(template.symbol_notes),
        needs_review=False,
        review_reasons=[],
        section_no=template.section_no,
        source_layout=None,
        bats=None,
    )


def _stanza_from_waks(
    wak_romans: list[str],
    *,
    source_layout: str,
    template: Segment,
    pages: list[int],
    pdf_pages: list[int | None],
    notes: list[str] | None = None,
    symbol_notes: dict[str, str] | None = None,
    flags: list[str] | None = None,
) -> Segment:
    """Build one บท segment from exactly four วรรค roman strings."""
    reasons = list(template.review_reasons)
    needs = bool(template.needs_review)
    if len(wak_romans) != 4:
        needs = True
        if "irregular_gatha_stanza" not in reasons:
            reasons.append("irregular_gatha_stanza")
    if len(set(pages)) > 1:
        needs = True
        if "gatha_stanza_page_span" not in reasons:
            reasons.append("gatha_stanza_page_span")

    bats: list[dict] = []
    if len(wak_romans) >= 2:
        bats.append(_bat_dict(1, wak_romans[0], wak_romans[1]))
    if len(wak_romans) >= 4:
        bats.append(_bat_dict(2, wak_romans[2], wak_romans[3]))
    elif len(wak_romans) == 3:
        bats.append(
            {
                "bat": 2,
                "waks": [_wak_dict(3, wak_romans[2])],
            }
        )
    elif len(wak_romans) == 1:
        bats = [{"bat": 1, "waks": [_wak_dict(1, wak_romans[0])]}]

    kind = template.segment_type
    if kind not in {"gatha", "gatha_continuation"}:
        kind = "gatha"

    merged_flags = list(flags) if flags is not None else list(template.flags)
    return Segment(
        page=pages[0],
        order=0,  # renumbered later
        item=template.item,
        segment_type=kind,
        text="",
        pdf_page=pdf_pages[0],
        flags=merged_flags,
        notes=list(notes) if notes is not None else list(template.notes),
        symbol_notes=(
            dict(symbol_notes)
            if symbol_notes is not None
            else dict(template.symbol_notes)
        ),
        needs_review=needs,
        review_reasons=reasons,
        source_layout=source_layout,
        bats=bats,
    )


def _closer_segment_from_template(template: Segment, closer: str) -> Segment:
    """Build a ``niṭṭhitaṃ`` segment for a formula peeled off a verse line."""
    return Segment(
        page=template.page,
        order=0,
        item=None,
        segment_type="niṭṭhitaṃ",
        text=closer,
        pdf_page=template.pdf_page,
        flags=[],
        notes=[],
        symbol_notes={},
        needs_review=False,
        review_reasons=[],
    )


def _expansion_paren_segment_from_template(
    template: Segment, paren: str
) -> Segment:
    """Build centered prose for an expansion ``(…)`` peeled off a verse line."""
    return Segment(
        page=template.page,
        order=0,
        item=None,
        segment_type="prose",
        text=paren,
        pdf_page=template.pdf_page,
        flags=[],
        notes=[],
        symbol_notes={},
        needs_review=False,
        review_reasons=[],
        source_layout="center",
    )


def _nama_colophon_segment_from_template(
    template: Segment, label: str
) -> Segment:
    """Build centered prose for a ``Name nāma.`` section label."""
    return Segment(
        page=template.page,
        order=0,
        item=None,
        segment_type="prose",
        text=label,
        pdf_page=template.pdf_page,
        flags=[],
        notes=[],
        symbol_notes={},
        needs_review=False,
        review_reasons=[],
        source_layout="center",
    )


def _consume_printed_gatha_lines(
    lines: list[Segment],
) -> list[Segment]:
    """
    Fold a run of printed-line ``gatha`` segments into บท segments.

    Each บท has two บาท × two วรรค. ``source_layout`` records whether the
    source printed one บาท per line (``bat_line``) or one วรรค per line
    (``wak_line``).

    Trailing section closers glued after a verse stop
    (``…cāti. Mūlapaṇṇāsako samatto.``) are peeled into ``niṭṭhitaṃ``
    segments emitted after the บท that held them. Trailing expansion
    parentheticals (``…padanti. (Appamādavaggo…)``) become centered prose.
    Standalone ``Name nāma.`` section labels become centered prose.

    Speech-intro / narrative lines mistagged as gāthā are emitted as
    ``prose`` and split the run so neighbouring verse still folds cleanly.
    """
    out: list[Segment] = []
    chunk: list[Segment] = []
    # Work on a mutable list so glued ``verse. (paren)`` can be split in place
    # before length-based prose demotion sees the long string.
    work = list(lines)
    i = 0
    while i < len(work):
        seg = work[i]
        text = _peel_gatha_line_section_rule(seg, seg.text or "")
        if not text or _is_section_rule_line(text):
            # Pure ``_____`` after peel — flag already on seg; do not fold as วรรค.
            i += 1
            continue
        peeled_paren = peel_trailing_expansion_parenthetical(text)
        if peeled_paren is not None:
            body, paren = peeled_paren
            seg.text = body
            text = body
            work.insert(i + 1, _expansion_paren_segment_from_template(seg, paren))
        # Expand block-joined verse lines before length-based prose demotion
        # sees the joined paragraph as one long "prose" วรรค.
        expanded = expand_glued_gatha_printed_lines(text)
        if len(expanded) > 1:
            text = expanded[0]
            seg.text = text
            for j, piece in enumerate(expanded[1:]):
                work.insert(
                    i + 1 + j, _gatha_line_segment_from_template(seg, piece)
                )
        if text and is_expansion_parenthetical(text):
            if chunk:
                out.extend(_fold_gatha_printed_lines(chunk))
                chunk = []
            paren_seg = _prose_segment_from_gatha_line(seg, text)
            paren_seg.source_layout = "center"
            out.append(paren_seg)
            i += 1
            continue
        if text and is_section_nama_colophon(text):
            if chunk:
                out.extend(_fold_gatha_printed_lines(chunk))
                chunk = []
            out.append(_nama_colophon_segment_from_template(seg, text))
            i += 1
            continue
        if (
            text
            and not is_section_closer_formula(text)
            and (
                ends_with_speech_intro_dash(text)
                or _looks_like_prose_not_gatha_wak(text)
            )
        ):
            if chunk:
                out.extend(_fold_gatha_printed_lines(chunk))
                chunk = []
            out.append(_prose_segment_from_gatha_line(seg, text))
        else:
            chunk.append(seg)
        i += 1
    if chunk:
        out.extend(_fold_gatha_printed_lines(chunk))
    return out


def _fold_gatha_printed_lines(
    lines: list[Segment],
) -> list[Segment]:
    """Fold a prose-free run of printed-line gāthā into บท segments."""
    # Collect (roman, layout_hint, seg) for each วรรค in order.
    units: list[tuple[str, str, Segment]] = []
    # Closers keyed by unit index after which they belong (pending until
    # the บท that consumes that unit is flushed).
    closers_after_unit: dict[int, list[Segment]] = {}

    def _note_closer(unit_index: int, template: Segment, closer: str) -> None:
        closers_after_unit.setdefault(unit_index, []).append(
            _closer_segment_from_template(template, closer)
        )

    def _note_paren(unit_index: int, template: Segment, paren: str) -> None:
        closers_after_unit.setdefault(unit_index, []).append(
            _expansion_paren_segment_from_template(template, paren)
        )

    def _strip_trailers(text: str) -> tuple[str, str | None, str | None]:
        """Return (body, expansion_paren or None, closer or None)."""
        paren = None
        closer = None
        peeled_paren = peel_trailing_expansion_parenthetical(text)
        if peeled_paren is not None:
            text, paren = peeled_paren
        peeled = peel_trailing_section_closer(text)
        if peeled is not None:
            text, closer = peeled
        return text, paren, closer

    def _emit_trailers(
        unit_index: int,
        template: Segment,
        paren: str | None,
        closer: str | None,
    ) -> None:
        if paren is not None:
            _note_paren(unit_index, template, paren)
        if closer is not None:
            _note_closer(unit_index, template, closer)

    # Mutable so block-joined ``A, B.{{sp1}} C.`` can be split into printed lines.
    work = list(lines)
    i = 0
    while i < len(work):
        seg = work[i]
        raw = _peel_gatha_line_section_rule(seg, seg.text or "")
        # Standalone closer / expansion paren / pure section rule mistagged as gatha.
        if not raw or _is_section_rule_line(raw):
            if units and SECTION_RULE_FLAG in seg.flags:
                _note_section_rule_flag(units[-1][2])
            i += 1
            continue
        if is_section_closer_formula(raw):
            _note_closer(len(units) - 1 if units else -1, seg, raw)
            i += 1
            continue
        if is_expansion_parenthetical(raw):
            _note_paren(len(units) - 1 if units else -1, seg, raw)
            i += 1
            continue
        if is_section_nama_colophon(raw):
            closers_after_unit.setdefault(
                len(units) - 1 if units else -1, []
            ).append(_nama_colophon_segment_from_template(seg, raw))
            i += 1
            continue
        # Peel trailers before bat/wak shape tests (``A, B. (paren)``).
        text, pending_paren, pending_closer = _strip_trailers(raw)
        # PDF text layer often omits blank lines between verse lines; expand
        # ``bat.{{sp1}} next`` before comma-split so the right วรรค stays one line.
        expanded = expand_glued_gatha_printed_lines(text)
        if len(expanded) > 1:
            text = expanded[0]
            seg.text = text
            for j, piece in enumerate(expanded[1:]):
                piece_text = piece
                if j == len(expanded) - 2:
                    # Re-attach trailers onto the last piece so the next
                    # iteration's ``_strip_trailers`` places them correctly.
                    if pending_paren:
                        piece_text = f"{piece_text} {pending_paren}"
                    if pending_closer:
                        piece_text = f"{piece_text} {pending_closer}"
                    pending_paren = None
                    pending_closer = None
                work.insert(
                    i + 1 + j, _gatha_line_segment_from_template(seg, piece_text)
                )
        if _is_bat_printed_line(text):
            parts = _split_bat_printed_line(text)
            if parts:
                left, right = parts
                # Closer/paren may still glue on the right วรรค only.
                right, r_paren, r_closer = _strip_trailers(right)
                units.append((left, "bat_line", seg))
                units.append((right, "bat_line", seg))
                _emit_trailers(
                    len(units) - 1,
                    seg,
                    pending_paren or r_paren,
                    pending_closer or r_closer,
                )
                i += 1
                continue
        # wak_line pair: line ending with "," + next ending with "."
        if (
            text.endswith(",")
            and i + 1 < len(work)
            and not _is_bat_printed_line(work[i + 1].text)
            and not _looks_like_prose_not_gatha_wak(work[i + 1].text)
            and re.search(r"[.!?…][\"'\u201c\u201d]?\s*$", work[i + 1].text.strip())
        ):
            right_raw = work[i + 1].text.strip()
            if is_section_closer_formula(right_raw):
                units.append((text, "wak_line", seg))
                _emit_trailers(len(units) - 1, seg, pending_paren, pending_closer)
                _note_closer(len(units) - 1, work[i + 1], right_raw)
                i += 2
                continue
            if is_expansion_parenthetical(right_raw):
                units.append((text, "wak_line", seg))
                _emit_trailers(len(units) - 1, seg, pending_paren, pending_closer)
                _note_paren(len(units) - 1, work[i + 1], right_raw)
                i += 2
                continue
            right, r_paren, r_closer = _strip_trailers(right_raw)
            units.append((text, "wak_line", seg))
            units.append((right, "wak_line", work[i + 1]))
            _emit_trailers(
                len(units) - 1,
                work[i + 1],
                pending_paren or r_paren,
                pending_closer or r_closer,
            )
            i += 2
            continue
        # Fallback: one printed line = one วรรค.
        units.append((text, "wak_line", seg))
        _emit_trailers(len(units) - 1, seg, pending_paren, pending_closer)
        i += 1

    stanzas: list[Segment] = []
    buf: list[tuple[str, str, Segment]] = []
    unit_cursor = 0

    def _flush_closers_through(last_unit_index: int) -> None:
        for idx in sorted(closers_after_unit):
            if idx > last_unit_index:
                break
            stanzas.extend(closers_after_unit.pop(idx))

    for unit in units:
        buf.append(unit)
        if len(buf) >= 4:
            chunk = buf[:4]
            buf = buf[4:]
            layouts = {u[1] for u in chunk}
            # Pure bat_line only when every unit came from ``A, B.``.
            # Pure wak_line (comma/stop pairs or all singles) → wak_line.
            # Bat pairs + single-line วรรค → mixed (keep Roman 3-line shape).
            if layouts == {"bat_line"}:
                layout = "bat_line"
            elif layouts == {"wak_line"}:
                layout = "wak_line"
            else:
                layout = "mixed"
            template = chunk[0][2]
            pages = [u[2].page for u in chunk]
            pdf_pages = [u[2].pdf_page for u in chunk]
            romans, notes, symbol_notes, flags = merge_note_carrying_units(
                [(u[0], u[2]) for u in chunk]
            )
            stanza = _stanza_from_waks(
                romans,
                source_layout=layout,
                template=template,
                pages=pages,
                pdf_pages=pdf_pages,
                notes=notes,
                symbol_notes=symbol_notes,
                flags=flags,
            )
            # mixed_gatha_layout: audit-only (no needs_review).
            if len(layouts) > 1 and "mixed_gatha_layout" not in stanza.review_reasons:
                stanza.review_reasons.append("mixed_gatha_layout")
            stanzas.append(stanza)
            unit_cursor += 4
            _flush_closers_through(unit_cursor - 1)

    if buf:
        # One leftover บาท after a full บท → 1 บทครึ่ง (3 บาท); keep in one
        # segment so TeX does not insert \\[\\gathastanzaskip] mid-block.
        # Only bat_line leftovers qualify — wak pairs are often prose.
        half = _one_bat_wak_romans(buf)
        last = stanzas[-1] if stanzas else None
        if (
            half is not None
            and last is not None
            and isinstance(last.bats, list)
            and len(last.bats) == 2
        ):
            romans, new_notes, new_sym, new_flags = merge_note_carrying_units(
                [(u[0], u[2]) for u in buf],
                note_index_base=len(last.notes),
            )
            if len(romans) >= 2:
                left, right = romans[0], romans[1]
            else:
                parts = _split_bat_printed_line(romans[0]) if romans else None
                if parts is None:
                    left, right = half[0], half[1]
                else:
                    left, right = parts
            last.bats.append(_bat_dict(3, left, right))
            last.notes.extend(new_notes)
            last.symbol_notes.update(new_sym)
            for fl in new_flags:
                if fl not in last.flags:
                    last.flags.append(fl)
            unit_cursor += len(buf)
            _flush_closers_through(unit_cursor - 1)
        elif any(_looks_like_prose_not_gatha_wak(u[0]) for u in buf):
            # Demote prose leftovers (one segment per printed-line template).
            seen_ids: set[int] = set()
            for u in buf:
                tid = id(u[2])
                if tid in seen_ids:
                    continue
                seen_ids.add(tid)
                siblings = [x[0] for x in buf if id(x[2]) == tid]
                roman = " ".join(siblings) if len(siblings) > 1 else siblings[0]
                stanzas.append(_prose_segment_from_gatha_line(u[2], roman))
            unit_cursor += len(buf)
            _flush_closers_through(unit_cursor - 1)
        else:
            # Other leftovers — emit irregular stanza for review.
            template = buf[0][2]
            layouts = {u[1] for u in buf}
            if layouts == {"bat_line"}:
                layout = "bat_line"
            elif layouts == {"wak_line"}:
                layout = "wak_line"
            else:
                layout = "mixed"
            romans, notes, symbol_notes, flags = merge_note_carrying_units(
                [(u[0], u[2]) for u in buf]
            )
            stanza = _stanza_from_waks(
                romans,
                source_layout=layout,
                template=template,
                pages=[u[2].page for u in buf],
                pdf_pages=[u[2].pdf_page for u in buf],
                notes=notes,
                symbol_notes=symbol_notes,
                flags=flags,
            )
            stanza.needs_review = True
            if "irregular_gatha_stanza" not in stanza.review_reasons:
                stanza.review_reasons.append("irregular_gatha_stanza")
            stanzas.append(stanza)
            unit_cursor += len(buf)
            _flush_closers_through(unit_cursor - 1)

    # Closers with no preceding unit (run started with a closer) or any
    # leftover keys after flush.
    for idx in sorted(closers_after_unit):
        stanzas.extend(closers_after_unit[idx])

    return stanzas


_BAT_LEFT_STOP_RE = re.compile(r"[.!?…][\"'\u201c\u201d]?\s*$")


def _gatha_wak_roman_bare(text: Any) -> str:
    """Roman (or plain) wak text with note markers stripped for shape checks."""
    if isinstance(text, list):
        roman = ""
        plain = ""
        for entry in text:
            if not isinstance(entry, dict):
                continue
            val = str(entry.get("value") or "")
            if entry.get("script") == "roman":
                roman = val
            elif not plain:
                plain = val
        raw = roman or plain
    else:
        raw = str(text or "")
    bare = re.sub(r"\{\{[^}]+\}\}", "", raw)
    return bare.strip().rstrip("\"'\u201c\u201d")


def _gatha_bat_left_shapes(seg: dict) -> tuple[bool, bool]:
    """``(has_comma_left, has_stop_left)`` across บาท of a gāthā segment."""
    has_comma = False
    has_stop = False
    bats = seg.get("bats") if isinstance(seg, dict) else None
    if not isinstance(bats, list):
        return False, False
    for bat in bats:
        if not isinstance(bat, dict):
            continue
        waks = bat.get("waks") or []
        if not isinstance(waks, list) or len(waks) < 2:
            continue
        left = waks[0] if isinstance(waks[0], dict) else None
        if left is None:
            continue
        bare = _gatha_wak_roman_bare(left.get("text"))
        if not bare:
            continue
        if bare.endswith(","):
            has_comma = True
        elif _BAT_LEFT_STOP_RE.search(bare):
            has_stop = True
    return has_comma, has_stop


def gatha_layout_fix_target(seg: dict) -> str | None:
    """Target ``source_layout`` when a stored บท mirrors CS mixed/long print.

    - comma-left + stop-left บาท → ``mixed`` (Roman: pair line + long singles)
    - stop-left only (all singles folded into bat pairs) → ``wak_line``
    - otherwise None (leave layout alone)
    """
    if not isinstance(seg, dict):
        return None
    if seg.get("segment_type") not in {"gatha", "gatha_continuation"}:
        return None
    layout = seg.get("source_layout")
    if layout not in {"bat_line", "wak_line", "mixed", None}:
        return None
    has_comma, has_stop = _gatha_bat_left_shapes(seg)
    if not has_stop:
        return None
    if has_comma:
        return "mixed"
    # All left วรรค are stop lines — never true bat_line column pairs.
    return "wak_line"


def bat_line_segment_needs_wak_layout(seg: dict) -> bool:
    """Deprecated alias: True when fixup should change layout away from bat_line."""
    target = gatha_layout_fix_target(seg)
    return target is not None and seg.get("source_layout") == "bat_line"


def group_gatha_stanzas(segments: list[Segment]) -> list[Segment]:
    """Replace runs of printed-line gatha segments with nested บท segments."""
    out: list[Segment] = []
    run: list[Segment] = []

    def flush_run() -> None:
        nonlocal run
        if not run:
            return
        out.extend(_consume_printed_gatha_lines(run))
        run = []

    for seg in segments:
        if _base_kind(seg.segment_type) == "gatha" and seg.bats is None:
            run.append(seg)
            continue
        flush_run()
        out.append(seg)
    flush_run()

    for i, seg in enumerate(out, start=1):
        seg.order = i
    return out


def detect_content_start(doc: fitz.Document, *, max_scan: int = 80) -> int | None:
    """
    1-based PDF page where body text begins (first ``Namo tassa…`` / ``Namo Tassa…``).
    """
    limit = min(max_scan, doc.page_count)
    for i in range(limit):
        text = vztime_to_unicode(doc[i].get_text("text"))
        if re.search(r"Namo\s+Tassa\b", text, re.IGNORECASE):
            return i + 1
    return None


def page_looks_like_back_matter(page_text: str, *, head_chars: int = 600) -> bool:
    """True when the page opening looks like a volume index / anukkamaṇikā."""
    head = (page_text or "")[:head_chars]
    return bool(BACK_MATTER_RE.search(head))


def detect_back_matter_start(
    doc: fitz.Document,
    *,
    content_start: int,
) -> int | None:
    """
    First 1-based *printed* page of back-matter indexes, or None if not found.

    Printed page N corresponds to PDF page ``content_start + N - 1``.
    """
    for pdf_page in range(content_start, doc.page_count + 1):
        text = vztime_to_unicode(doc[pdf_page - 1].get_text("text"))
        if page_looks_like_back_matter(text):
            return pdf_page - content_start + 1
    return None


def detect_running_headers(
    doc: fitz.Document,
    content_start_idx: int,
    *,
    content_end_idx: int | None = None,
    top_lines: int = 6,
    min_pages: int = 3,
) -> set[str]:
    """Collect short labels that recur at page tops across the volume.

    Sutta/chapter running headers change through the book (``1. Brahmajālasutta``
    … ``10. Subhasutta`` …). Sampling only the first dozen pages misses later
    titles, which then glue into body prose and pick up ``source_layout=center``.

    ``Name (folio)`` / ``N. Name (folio)`` labels are accepted from a single
    page-top sighting (short suttas may span fewer than ``min_pages`` pages).

    Counts each candidate at most once per page, and only among the first
    ``top_lines`` raw lines (page furniture zone), so repeated body phrases
    mid-page are not treated as headers.
    """
    counts: dict[str, int] = {}
    folio_once: set[str] = set()
    end = doc.page_count if content_end_idx is None else min(doc.page_count, content_end_idx)
    for i in range(content_start_idx, end):
        text = vztime_to_unicode(doc[i].get_text("text"))
        seen_on_page: set[str] = set()
        for line in text.splitlines()[: max(1, top_lines)]:
            s = line.strip()
            if not s or PAGE_NUM_RE.match(s) or FOOTNOTE_RULE_RE.match(s):
                continue
            is_folio = is_running_header_folio_label(s)
            max_len = _FOLIO_HEADER_MAX_LEN if is_folio else _GENERIC_HEADER_MAX_LEN
            if len(s) > max_len:
                continue
            # Recitation topic-summary labels recur mid-volume but are body
            # furniture, not running headers (would wipe every Tassuddānaṃ).
            if is_tassuddana_label(s):
                continue
            if s in seen_on_page:
                continue
            seen_on_page.add(s)
            counts[s] = counts.get(s, 0) + 1
            if is_folio:
                folio_once.add(s)
    out = {line for line, n in counts.items() if n >= min_pages}
    out |= folio_once
    return out


def extract_pdf(
    pdf_path: Path,
    *,
    content_start: int | None = None,
    content_end: int | None = None,
    max_pages: int | None = None,
) -> dict:
    doc = fitz.open(pdf_path)
    if content_start is None:
        detected = detect_content_start(doc)
        if detected is None:
            raise ValueError(
                f"Could not auto-detect content start (Namo tassa) in {pdf_path}"
            )
        content_start = detected
    start_idx = max(0, content_start - 1)
    headers = detect_running_headers(doc, start_idx)

    back_matter_start = detect_back_matter_start(doc, content_start=content_start)
    if content_end is None and back_matter_start is not None:
        # Last printed body page = page before indexes (may be blank).
        content_end = back_matter_start - 1

    end_idx = doc.page_count
    if max_pages is not None:
        end_idx = min(end_idx, start_idx + max_pages)
    if content_end is not None:
        # printed N → PDF index content_start + N - 2 (0-based exclusive end)
        end_idx = min(end_idx, content_start + content_end - 1)

    raw: list[dict] = []
    unmapped: dict[str, int] = {}
    # PDF-page → stroke-overlay (fake-bold) spans with bboxes from texttrace.
    bold_by_pdf_page: dict[int, list[BoldSpan]] = {}
    lines_by_pdf_page: dict[int, list] = {}

    for idx in range(start_idx, end_idx):
        pdf_page = idx + 1
        printed = pdf_page - content_start + 1
        raw_text = doc[idx].get_text("text")
        for ch in unmapped_chars(raw_text):
            unmapped[ch] = unmapped.get(ch, 0) + 1
        page_text = vztime_to_unicode(raw_text)
        if content_end is None and page_looks_like_back_matter(page_text):
            # Safety stop if end was not pre-detected.
            back_matter_start = printed
            content_end = printed - 1
            break
        bold_spans = bold_span_geoms(doc[idx])
        if bold_spans:
            bold_by_pdf_page[pdf_page] = bold_spans
        lines_by_pdf_page[pdf_page] = page_body_lines(doc[idx])
        raw.extend(
            extract_page_blocks(
                page_text,
                printed_page=printed,
                pdf_page=pdf_page,
                headers=headers,
                is_opening_page=(printed == 1),
            )
        )

    segments = tag_gatha_segments(attach_notes_sacred_style(merge_blocks(raw)))
    # Fold hanging paragraphs first so hang-body prose is not mistaken for
    # hang-band embedded gāthā in the next pass.
    pdf_pages = {s.pdf_page for s in segments if s.pdf_page}
    hanging_groups = collect_hanging_groups(doc, pdf_pages=pdf_pages)
    hanging_merged = merge_hanging_into_segments(segments, hanging_groups)
    # Embedded verse: deep column, hang-band bat_line, or hang-band wak runs.
    gatha_geometry_tagged = tag_gatha_by_geometry(
        doc, segments, content_start=content_start
    )
    segments = group_gatha_stanzas(segments)
    # Flush page-start → continuation; indented → keep as new prose.
    page_start_stats = reclassify_page_start_by_indent(
        doc, segments, content_start=content_start
    )
    # Geometry pass: short centered labels → source_layout='center'.
    center_stats = tag_center_layout_by_geometry(
        doc, segments, content_start=content_start
    )
    # Recover typesetter's manual line breaks inside centered multi-line blocks
    # (e.g. pātimokkha-uddesa ``…dhammā`` / ``uddesaṃ āgacchanti.``) that the
    # block-join collapsed to a space. Splices ``{{br}}`` at line boundaries;
    # non-destructive when the PDF-line reconstruction does not match exactly.
    center_break_stats = restore_centered_line_breaks(
        doc, segments, content_start=content_start
    )
    # Drop weak title guesses that are not centered, and speech-intro dashes.
    heading_demote_stats = demote_false_heading_guesses(segments)
    review_count = sum(1 for s in segments if s.needs_review)
    type_counts: dict[str, int] = {}
    for s in segments:
        type_counts[s.segment_type] = type_counts.get(s.segment_type, 0) + 1
    notes_embedded = sum(1 for s in segments if s.notes)
    segments_with_bold = 0
    json_segments: list[dict] = []
    for s in segments:
        payload = _segment_to_json(
            s,
            bold_by_pdf_page=bold_by_pdf_page,
            lines_by_pdf_page=lines_by_pdf_page,
        )
        if _json_has_bold_runs(payload):
            segments_with_bold += 1
        json_segments.append(payload)

    # Lean schema v1 document. Extract stats are ephemeral for CLI/manifest
    # and stripped by normalize_document / save_segments.
    return {
        "schema_version": SCHEMA_VERSION,
        "source": repo_relative(pdf_path),
        "content_start_pdf_page": content_start,
        "content_end_printed_page": content_end,
        "back_matter_start_printed_page": back_matter_start,
        "segments": json_segments,
        "_extract_stats": {
            "running_headers_skipped": sorted(headers),
            "unmapped_char_samples": {
                ch: n
                for ch, n in sorted(unmapped.items(), key=lambda kv: -kv[1])[:30]
            },
            "segment_count": len(segments),
            "segments_needing_review": review_count,
            "segments_with_notes": notes_embedded,
            "segments_with_bold": segments_with_bold,
            "hanging_paragraphs_merged": hanging_merged,
            "gatha_geometry_tagged": gatha_geometry_tagged,
            "page_start_reclassify": page_start_stats,
            "center_layout": center_stats,
            "center_breaks_restored": center_break_stats,
            "heading_demote": heading_demote_stats,
            "segment_type_counts": dict(sorted(type_counts.items())),
        },
    }


def _bold_assets_for_segment(
    seg: Segment,
    bold_by_pdf_page: dict[int, list[BoldSpan]],
    lines_by_pdf_page: dict[int, list],
) -> tuple[list[BoldSpan], list]:
    """Stroke spans + body lines for a segment's PDF page(s)."""
    if not seg.pdf_page:
        return [], []
    spans = list(bold_by_pdf_page.get(seg.pdf_page) or [])
    lines = list(lines_by_pdf_page.get(seg.pdf_page) or [])
    # Rare mid-unit page break: allow geometry from the next PDF page too.
    if seg.segment_type.endswith("_continuation"):
        nxt = seg.pdf_page + 1
        spans.extend(bold_by_pdf_page.get(nxt) or [])
        lines.extend(lines_by_pdf_page.get(nxt) or [])
    return spans, lines


def _bold_ranges_for_roman(
    roman: str,
    *,
    bold_spans: list[BoldSpan] | None = None,
    page_lines: list | None = None,
    normalize_spacing: bool = True,
) -> tuple[list[tuple[int, int]], str, bool]:
    """Prepare Roman and compute bbox-aware bold ranges."""
    spaced, had_rule = normalize_roman_body(
        roman, normalize_spacing=normalize_spacing
    )
    prepared = strip_solid_midword_hyphens(spaced)
    ranges = bold_ranges_from_geoms(
        prepared, bold_spans or [], page_lines or []
    )
    return ranges, prepared, had_rule


def _wak_text_to_json(
    roman: str,
    *,
    bold_spans: list[BoldSpan] | None = None,
    page_lines: list | None = None,
    normalize_spacing: bool = True,
) -> tuple[list[dict], bool]:
    # Spacing first (keep solid hyphens for Thai morpheme breaks); bold on the
    # final Roman after hyphen strip. script_text_entries re-normalizes and
    # strips hyphens for storage.
    ranges, _prepared, had_rule = _bold_ranges_for_roman(
        roman,
        bold_spans=bold_spans,
        page_lines=page_lines,
        normalize_spacing=normalize_spacing,
    )
    entries, _ = script_text_entries(
        roman,
        bold_ranges=ranges or None,
        normalize_spacing=normalize_spacing,
    )
    return entries, had_rule


def _json_has_bold_runs(payload: dict) -> bool:
    text = payload.get("text")
    if isinstance(text, list):
        for entry in text:
            if isinstance(entry, dict) and entry.get("runs"):
                return True
    for bat in payload.get("bats") or []:
        for wak in bat.get("waks") or []:
            wak_text = wak.get("text")
            if isinstance(wak_text, list):
                for entry in wak_text:
                    if isinstance(entry, dict) and entry.get("runs"):
                        return True
    return False


def _segment_to_json(
    seg: Segment,
    *,
    bold_by_pdf_page: dict[int, list[BoldSpan]] | None = None,
    lines_by_pdf_page: dict[int, list] | None = None,
) -> dict:
    """Serialize a Segment; ``text`` becomes multi-script entries (+ optional runs).

    Omits ``pdf_page`` and gāthā ``bat``/``wak``/``role`` (schema v1). Final
    compact form (empty flags/notes, bold-only runs) is applied by
    ``normalize_document`` on save.
    """
    data = asdict(seg)
    data.pop("pdf_page", None)
    if data.get("section_no") is None:
        data.pop("section_no", None)
    flags = [f for f in (data.get("flags") or []) if f != SECTION_RULE_FLAG]
    had_rule = False
    bold_spans, page_lines = _bold_assets_for_segment(
        seg, bold_by_pdf_page or {}, lines_by_pdf_page or {}
    )

    normalize_spacing = uses_sentence_spacer(seg.segment_type)
    if seg.bats is not None:
        # Nested gāthā: no top-level text; serialize each วรรค.
        data.pop("text", None)
        data.pop("hanging_lines", None)
        json_bats: list[dict] = []
        for bat in seg.bats:
            json_waks: list[dict] = []
            for wak in bat.get("waks") or []:
                roman = wak.get("text") or ""
                if isinstance(roman, list):
                    entries = roman
                else:
                    entries, rule = _wak_text_to_json(
                        str(roman),
                        bold_spans=bold_spans,
                        page_lines=page_lines,
                        normalize_spacing=normalize_spacing,
                    )
                    had_rule = had_rule or rule
                json_waks.append({"text": entries})
            json_bats.append({"waks": json_waks})
        data["bats"] = json_bats
        data["source_layout"] = seg.source_layout
    else:
        # Spacing first (keep solid hyphens for Thai); bold on post-strip Roman.
        ranges, prepared, had_rule = _bold_ranges_for_roman(
            seg.text,
            bold_spans=bold_spans,
            page_lines=page_lines,
            normalize_spacing=normalize_spacing,
        )
        # Closers: only keep full-line (major) bold; drop lemma bleed.
        if seg.segment_type == "niṭṭhitaṃ":
            ranges = substantial_bold_ranges(prepared, ranges)
        entries, _ = script_text_entries(
            seg.text,
            bold_ranges=ranges or None,
            normalize_spacing=normalize_spacing,
        )
        data["text"] = entries
        data.pop("bats", None)
        if seg.source_layout == "hanging" and seg.hanging_lines:
            data["source_layout"] = "hanging"
            hl_out: list[list[dict]] = []
            for line in seg.hanging_lines:
                hl_entries, hl_rule = _wak_text_to_json(
                    str(line),
                    bold_spans=bold_spans,
                    page_lines=page_lines,
                    normalize_spacing=normalize_spacing,
                )
                had_rule = had_rule or hl_rule
                hl_out.append(hl_entries)
            data["hanging_lines"] = hl_out
        elif seg.source_layout == "center":
            data["source_layout"] = "center"
            data.pop("hanging_lines", None)
        else:
            data.pop("source_layout", None)
            data.pop("hanging_lines", None)

    if had_rule:
        flags.append(SECTION_RULE_FLAG)
    data["flags"] = flags
    # dataclass may still expose hanging_lines=None / bats=None
    if not data.get("hanging_lines"):
        data.pop("hanging_lines", None)
    if not data.get("bats"):
        data.pop("bats", None)
    if not data.get("source_layout"):
        data.pop("source_layout", None)
    return data


def _resolve_pdfs(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    if path.is_dir():
        return sorted(path.glob("*.pdf"))
    return []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "pdf",
        type=Path,
        help="Path to a cs-roman PDF, or a directory of PDFs",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help=(
            "JSON output path for a single PDF "
            "(default: books/cs-roman/output/<stem>.segments.json). "
            "Ignored when pdf is a directory."
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help="Directory for batch JSON output (default: books/cs-roman/output)",
    )
    parser.add_argument(
        "--content-start",
        type=int,
        default=None,
        help=(
            "1-based PDF page where printed page 1 begins. "
            "Default: auto-detect first Namo tassa / Namo Tassa page."
        ),
    )
    parser.add_argument(
        "--content-end",
        type=int,
        default=None,
        help=(
            "Last 1-based *printed* page to keep (body only). "
            "Default: auto-detect first back-matter index page − 1."
        ),
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Only extract this many PDF pages from content-start (pilot)",
    )
    args = parser.parse_args(argv)

    pdfs = _resolve_pdfs(args.pdf)
    if not pdfs:
        print(f"No PDF found at: {args.pdf}", file=sys.stderr)
        return 1

    args.output_dir.mkdir(parents=True, exist_ok=True)
    failures: list[str] = []
    summary_rows: list[dict] = []

    for pdf_path in pdfs:
        if len(pdfs) == 1 and args.output is not None:
            out = args.output
        else:
            out = args.output_dir / f"{pdf_path.stem}.segments.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        try:
            data = extract_pdf(
                pdf_path,
                content_start=args.content_start,
                content_end=args.content_end,
                max_pages=args.max_pages,
            )
        except Exception as exc:  # noqa: BLE001 — batch should continue
            print(f"FAIL {pdf_path.name}: {exc}", file=sys.stderr)
            failures.append(pdf_path.name)
            continue

        stats = dict(data.pop("_extract_stats", {}) or {})
        # Preserve hand-tuned print config across re-extract.
        layout_out = layout_path_for(out)
        if layout_out.is_file():
            existing = load(layout_out)
            if existing.get("layout") is not None:
                data["layout"] = existing["layout"]
            if existing.get("page_layout_reading_mode") is not None:
                data["page_layout_reading_mode"] = existing[
                    "page_layout_reading_mode"
                ]
            if existing.get("page_breaks_reading_mode") is not None:
                data["page_breaks_reading_mode"] = existing[
                    "page_breaks_reading_mode"
                ]
            for key, value in existing.items():
                if isinstance(key, str) and key.startswith("//"):
                    data[key] = value
        save_document(out, data, layout_path=layout_out, normalize=True)
        seg_count = stats.get("segment_count", len(data.get("segments") or []))
        print(
            f"Wrote {seg_count} segments "
            f"(start={data['content_start_pdf_page']}"
            f", end={data.get('content_end_printed_page')}) -> {out} + {layout_out.name}"
        )
        summary_rows.append(
            {
                "pdf": pdf_path.name,
                "content_start_pdf_page": data["content_start_pdf_page"],
                "content_end_printed_page": data.get("content_end_printed_page"),
                "back_matter_start_printed_page": data.get(
                    "back_matter_start_printed_page"
                ),
                "segment_count": seg_count,
                "segments_with_notes": stats.get("segments_with_notes"),
                "segments_needing_review": stats.get("segments_needing_review"),
                "segment_type_counts": stats.get("segment_type_counts"),
                "output": str(out).replace("\\", "/"),
            }
        )

    if len(summary_rows) > 1:
        manifest = args.output_dir / "manifest.json"
        manifest.write_text(
            json.dumps(
                {
                    "source_dir": str(args.pdf).replace("\\", "/"),
                    "volume_count": len(summary_rows),
                    "failed": failures,
                    "volumes": summary_rows,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"Manifest -> {manifest} ({len(summary_rows)} ok, {len(failures)} failed)")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
