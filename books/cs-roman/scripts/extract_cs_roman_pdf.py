"""
Extract Tipitaka segment candidates from a cs-roman PDF text layer.

Pipeline:
  1. Read PDF text with PyMuPDF (fitz)
  2. Convert VZTime font encoding → Unicode (cs_roman_vztime)
  3. Split into paragraphs, detect item numbers / headings / notes
  4. Page-anchor segments; unfinished units → {kind}_continuation
  5. Attach footnotes to the segment where the callout appears ({{n0}})
  6. Tag uddāna/gāthā runs; group printed lines into บท→บาท→วรรค
  7. Write JSON for study / later import

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
from cs_roman_bold import bold_ranges_in_text, bold_span_texts  # noqa: E402
from cs_roman_hanging import (  # noqa: E402
    collect_hanging_groups,
    merge_hanging_into_segments,
)
from cs_roman_segments import (  # noqa: E402
    SCHEMA_VERSION,
    layout_path_for,
    load,
    save_document,
)
from cs_roman_text import (  # noqa: E402
    SECTION_RULE_FLAG,
    prepare_roman_body,
    script_text_entries,
)
from cs_roman_vztime import unmapped_chars, vztime_to_unicode  # noqa: E402

FOOTNOTE_RULE_RE = re.compile(r"^_{6,}$")
FOOTNOTE_SPLIT_RE = re.compile(r"\n[ \t]*_{6,}[ \t]*(?:\n|$)")
ITEM_START_RE = re.compile(r"^(\d+)\s*[-–]\s*(\d+)\.\s*(.*)$")
ITEM_SINGLE_RE = re.compile(r"^(\d+)\.\s*(.*)$")
STAR_BLOCK_RE = re.compile(r"^\*\s+(.*)$")
PLUS_BLOCK_RE = re.compile(r"^\+\s+(.*)$")
# Same-line sibling apparatus note: "...pi. + Dī 3. …"
_INLINE_PLUS_NOTE_RE = re.compile(r"(?<=\.)\s+\+\s+(?=[A-ZĀĪŪÑÉÓ])")
PAGE_NUM_RE = re.compile(r"^\d+$")

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
    r"(kaṇḍa|vagga|sikkhāpada|bhāṇavāra|uddānagāthā|uddāna|gāthā|gatha|mātikā|"
    r"niṭṭhita|namo\s+tassa|piṭaka|pāḷi)\b",
    re.IGNORECASE,
)
# Titles that open an uddāna / gāthā verse block.
GATHA_TITLE_RE = re.compile(r"uddānagāthā|uddāna|gāthā|\bgatha\b", re.IGNORECASE)
_GATHA_STOP_KINDS = frozenset(
    {
        "niṭṭhitaṃ",
        "chapter",
        "title",
        "piṭaka",
        "gambhīra",
        "namakkāraṃ",
        "note",
        "subhead",
        "centered",
    }
)
NAMO_RE = re.compile(r"^namo\s+tassa\b", re.IGNORECASE)
NITTHITA_RE = re.compile(r"niṭṭhit", re.IGNORECASE)
# Footnote callout glued to a word/quote: Bhagavā’1 / anabhāvaṃkatā1 / bhikkhave2
FOOTNOTE_CALLOUT_RE = re.compile(
    r"(?<=[^\s\d])(\d+)(?=[\s,;:.!?”’\"'\-–]|$)"
)
# Typical Pāli paragraph endings (…ti. / .”ti. / plain sentence stop).
_PARAGRAPH_COMPLETE_RE = re.compile(
    r"(?:[”’'\"]\s*)?ti\.?\s*$|[.!?…][”’'\"]?\s*$",
    re.IGNORECASE,
)
# Trailing case / print-page refs after a finished sentence: (16) (14-15) (๑๔-๑๕).
_TRAILING_PAREN_REF_RE = re.compile(
    r"\s*\([0-9๐-๙]+(?:\s*[-–]\s*[0-9๐-๙]+)?\)\s*$"
)
# Letters used in Roman Pāli (for mid-word page-break repair).
_LEADING_WORD_RE = re.compile(
    r"^([A-Za-zĀāĪīŪūṄṅÑñṆṇṬṭḌḍḶḷṂṃŒœ]+)(.*)$",
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


def _paragraph_seems_complete(text: str) -> bool:
    """True when text looks like a finished paragraph (not a mid-page cut)."""
    t = re.sub(r"\{\{(?:n\d+|\*|\+)\}\}\s*$", "", text).rstrip()
    if not t:
        return True
    # A finished sentence may still carry a trailing (n) / (n-m) marker.
    t = _TRAILING_PAREN_REF_RE.sub("", t).rstrip()
    if not t:
        return True
    return bool(_PARAGRAPH_COMPLETE_RE.search(t))


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


def _repair_mid_word_split(prev_text: str, next_text: str) -> tuple[str, str]:
    """
    If the page break splits a word, finish the word on the first segment.

    Only hyphenated breaks count: a trailing ``-`` or soft hyphen on the
    previous page. A bare page-end letter (e.g. ``ṭhitā`` / ``hoti.``) is two
    words and must not be joined.

    Returns (updated_prev_text, updated_next_text).
    """
    prev = prev_text.rstrip()
    nxt = next_text.lstrip()
    if not prev or not nxt:
        return prev_text, next_text

    if prev.endswith("-") or prev.endswith("\u00ad"):
        prev = prev.rstrip("-").rstrip("\u00ad")
        word, rest = _take_leading_word(nxt)
        if word:
            return prev + word, rest
        return prev, nxt
    return prev_text, next_text


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
    # Nested gāthā: one segment = one บท (stanza). Absent for non-gatha kinds.
    # Also reused for hanging prose: source_layout="hanging" + hanging_lines.
    source_layout: str | None = None  # "bat_line" | "wak_line" | "hanging"
    bats: list[dict] | None = None
    # Hanging-paragraph body lines (roman), when source_layout == "hanging".
    hanging_lines: list[str] | None = None


def _normalize_inline(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]*\n[ \t]*", " ", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def _split_blocks(page_text: str, *, notes: bool = False) -> list[str]:
    text = page_text.replace("\r\n", "\n")
    if notes:
        text = re.sub(r"\n(?=\d+\.\s)", "\n\n", text)
        text = re.sub(r"\n(?=\*\s)", "\n\n", text)
        text = re.sub(r"\n(?=\+\s)", "\n\n", text)
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


def _is_running_header(block: str, headers: set[str]) -> bool:
    line = _normalize_inline(block)
    if not line:
        return True
    if FOOTNOTE_RULE_RE.match(line):
        return True
    if PAGE_NUM_RE.match(line):
        return True
    if line in headers:
        return True
    if set(line) <= {"_", " ", "–", "-"}:
        return True
    return False


def _classify_heading(text: str) -> tuple[str | None, list[str]]:
    """
    Return (segment_type or None, review_reasons).

    Strong matches need no review; weak short-line guesses are flagged.
    """
    if NAMO_RE.match(text):
        return "namakkāraṃ", []
    # Only short closing lines — the stem also appears inside body/index prose.
    if len(text) <= 80 and NITTHITA_RE.search(text):
        return "niṭṭhitaṃ", []
    if VARIANT_NOTE_RE.search(text):
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
    # Weak heading: short centered-style phrase, not a sentence, not verse.
    # Verse halves often end with "," or contain a pāda-break comma — never titles.
    if len(text) <= 60 and not re.search(r"[.!?…][\"'\u201c\u201d]?\s*$", text):
        if text.rstrip().endswith(","):
            return None, []
        if "," in text:
            return None, []
        if " " not in text or text[0].isupper():
            return "title", ["weak_heading_heuristic"]
    return None, []


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
    Drop running-header lines.

    When ``keep_until_namo`` is True (content-start page), header strings that
    appear *before* the first Namo line are kept — they are the real piṭaka /
    gambhīra titles on the opening page, not headers.
    """
    kept: list[str] = []
    seen_namo = False
    for line in text.split("\n"):
        s = line.strip()
        if not s:
            kept.append(line)
            continue
        if NAMO_RE.match(s):
            seen_namo = True
        if PAGE_NUM_RE.match(s) or FOOTNOTE_RULE_RE.match(s):
            continue
        if s in headers and (seen_namo or not keep_until_namo):
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
        if _is_running_header(raw, headers):
            continue
        text = _normalize_inline(raw)
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
                blocks_out.append(
                    {
                        "kind": "note",
                        "item": item,
                        "text": rest,
                        "flags": flags,
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

        blocks_out.append(
            {
                "kind": "prose",
                "item": None,
                "text": text,
                "flags": [],
                "page": printed_page,
                "pdf_page": pdf_page,
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
    - Unfinished unit continuing on the next page → new segment with
      ``{kind}_continuation`` (prose_continuation, gatha_continuation, …).
    - New paragraph under the same item → ``prose`` (not continuation).
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

        if (
            kind in {"prose", "gatha", "verse"}
            and block.get("item") is None
            and last_body_idx is not None
            and not block.get("flags")
        ):
            prev = segments[last_body_idx]
            block_page = block["page"]

            # Same unit continues on a later printed page.
            if (
                block_page > prev.page
                and prev.segment_type in _CONTINUABLE_KINDS
                and not _paragraph_seems_complete(prev.text)
            ):
                prev_text, next_text = _repair_mid_word_split(
                    prev.text, block["text"]
                )
                prev.text = prev_text
                if not next_text.strip():
                    # Entire remainder was only the end of a split word.
                    continue
                append_new(
                    {
                        **block,
                        "item": prev.item,
                        "kind": _continuation_kind(prev.segment_type),
                        "text": next_text,
                    }
                )
                continue

            # New paragraph under the same item (same or later page).
            inherited = {
                **block,
                "item": prev.item,
                # New paragraph → base kind (prose), not continuation.
                "kind": kind if kind != "prose" else "prose",
            }
            append_new(inherited)
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


def attach_notes_sacred_style(segments: list[Segment]) -> list[Segment]:
    """
    Fold page footnotes into body segments (sacred-app style).

    Numbered callouts → ``{{nK}}`` + ``notes[K]``.
    ``*`` / ``+`` apparatus notes → ``{{*}}`` / ``{{+}}`` + ``symbol_notes``
    (do not share the numbered footnote sequence).
    Unmatched leftover notes remain as segment_type=note with needs_review.
    """
    notes_by_page: dict[int, list[Segment]] = {}
    for seg in segments:
        if seg.segment_type == "note":
            notes_by_page.setdefault(seg.page, []).append(seg)

    used_note_ids: set[int] = set()
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

        notes_out: list[str] = []
        symbol_notes: dict[str, str] = {}

        def replace_callout(match: re.Match[str]) -> str:
            num = int(match.group(1))
            note_seg = numbered.get(num)
            if note_seg is None:
                return match.group(0)
            idx = len(notes_out)
            notes_out.append(note_seg.text)
            used_note_ids.add(id(note_seg))
            numbered.pop(num, None)
            return "{{" + f"n{idx}" + "}}"

        new_text = FOOTNOTE_CALLOUT_RE.sub(replace_callout, seg.text)

        if "star" in seg.flags and star_notes:
            note_seg = star_notes[0]
            symbol_notes["*"] = note_seg.text
            used_note_ids.add(id(note_seg))
            new_text = "{{*}}" + new_text

        if "plus" in seg.flags and plus_notes:
            note_seg = plus_notes[0]
            symbol_notes["+"] = note_seg.text
            used_note_ids.add(id(note_seg))
            new_text = "{{+}}" + new_text

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


def tag_gatha_segments(segments: list[Segment]) -> list[Segment]:
    """
    After an uddāna/gāthā title, retag short itemless prose lines as ``gatha``.

    Stops at numbered prose, structural headings, apparatus (* / +), or notes.
    Each tagged segment is still one *printed* line; ``group_gatha_stanzas``
    then folds lines into บท → บาท → วรรค.
    """
    in_gatha = False
    for seg in segments:
        if seg.segment_type == "title" and GATHA_TITLE_RE.search(seg.text):
            in_gatha = True
            if "weak_heading_heuristic" in seg.review_reasons:
                seg.review_reasons = [
                    r for r in seg.review_reasons if r != "weak_heading_heuristic"
                ]
                if not seg.review_reasons:
                    seg.needs_review = False
            continue

        if not in_gatha:
            continue

        if seg.segment_type in _GATHA_STOP_KINDS:
            # A new gāthā title re-enters; any other structural title exits.
            if seg.segment_type == "title" and GATHA_TITLE_RE.search(seg.text):
                in_gatha = True
                continue
            in_gatha = False
            continue

        base = _base_kind(seg.segment_type)
        if base not in {"prose", "gatha"}:
            in_gatha = False
            continue

        if set(seg.flags) & {"star", "plus"}:
            in_gatha = False
            continue

        if seg.item is not None:
            in_gatha = False
            continue

        # Verse lines in this edition are short couplet halves.
        if len(seg.text) > 160:
            in_gatha = False
            continue

        if seg.segment_type.endswith("_continuation"):
            seg.segment_type = "gatha_continuation"
        else:
            seg.segment_type = "gatha"

    return segments


def _is_bat_printed_line(text: str) -> bool:
    """True when one printed line already holds both วรรค of a บาท (A, B.)."""
    t = text.strip()
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


def _wak_dict(wak_no: int, roman: str) -> dict:
    return {
        "wak": wak_no,
        "role": _WAK_ROLES.get(wak_no, f"wak{wak_no}"),
        "text": roman,
    }


def _bat_dict(bat_no: int, wak_a: str, wak_b: str) -> dict:
    base = 1 if bat_no == 1 else 3
    return {
        "bat": bat_no,
        "waks": [_wak_dict(base, wak_a), _wak_dict(base + 1, wak_b)],
    }


def _stanza_from_waks(
    wak_romans: list[str],
    *,
    source_layout: str,
    template: Segment,
    pages: list[int],
    pdf_pages: list[int | None],
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

    return Segment(
        page=pages[0],
        order=0,  # renumbered later
        item=None,
        segment_type=kind,
        text="",
        pdf_page=pdf_pages[0],
        flags=list(template.flags),
        notes=list(template.notes),
        symbol_notes=dict(template.symbol_notes),
        needs_review=needs,
        review_reasons=reasons,
        source_layout=source_layout,
        bats=bats,
    )


def _consume_printed_gatha_lines(
    lines: list[Segment],
) -> list[Segment]:
    """
    Fold a run of printed-line ``gatha`` segments into บท segments.

    Each บท has two บาท × two วรรค. ``source_layout`` records whether the
    source printed one บาท per line (``bat_line``) or one วรรค per line
    (``wak_line``).
    """
    # Collect (roman, layout_hint, seg) for each วรรค in order.
    units: list[tuple[str, str, Segment]] = []
    i = 0
    while i < len(lines):
        seg = lines[i]
        text = seg.text.strip()
        if _is_bat_printed_line(text):
            parts = _split_bat_printed_line(text)
            if parts:
                units.append((parts[0], "bat_line", seg))
                units.append((parts[1], "bat_line", seg))
                i += 1
                continue
        # wak_line pair: line ending with "," + next ending with "."
        if (
            text.endswith(",")
            and i + 1 < len(lines)
            and not _is_bat_printed_line(lines[i + 1].text)
            and re.search(r"[.!?…][\"'\u201c\u201d]?\s*$", lines[i + 1].text.strip())
        ):
            units.append((text, "wak_line", seg))
            units.append((lines[i + 1].text.strip(), "wak_line", lines[i + 1]))
            i += 2
            continue
        # Fallback: treat as a single wak (may yield irregular stanza).
        hint = "wak_line" if text.endswith(",") else "bat_line"
        units.append((text, hint, seg))
        i += 1

    stanzas: list[Segment] = []
    buf: list[tuple[str, str, Segment]] = []
    for unit in units:
        buf.append(unit)
        if len(buf) >= 4:
            chunk = buf[:4]
            buf = buf[4:]
            layouts = {u[1] for u in chunk}
            if layouts == {"bat_line"}:
                layout = "bat_line"
            elif layouts == {"wak_line"}:
                layout = "wak_line"
            else:
                layout = "wak_line" if "wak_line" in layouts else "bat_line"
            template = chunk[0][2]
            pages = [u[2].page for u in chunk]
            pdf_pages = [u[2].pdf_page for u in chunk]
            stanza = _stanza_from_waks(
                [u[0] for u in chunk],
                source_layout=layout,
                template=template,
                pages=pages,
                pdf_pages=pdf_pages,
            )
            if len(layouts) > 1:
                stanza.needs_review = True
                if "mixed_gatha_layout" not in stanza.review_reasons:
                    stanza.review_reasons.append("mixed_gatha_layout")
            # Merge notes from all printed lines into the บท.
            for u in chunk[1:]:
                stanza.notes.extend(u[2].notes)
                stanza.symbol_notes.update(u[2].symbol_notes)
                for fl in u[2].flags:
                    if fl not in stanza.flags:
                        stanza.flags.append(fl)
            stanzas.append(stanza)

    if buf:
        # Leftover waks — emit irregular stanza for review.
        template = buf[0][2]
        layouts = {u[1] for u in buf}
        layout = "wak_line" if "wak_line" in layouts else "bat_line"
        stanza = _stanza_from_waks(
            [u[0] for u in buf],
            source_layout=layout,
            template=template,
            pages=[u[2].page for u in buf],
            pdf_pages=[u[2].pdf_page for u in buf],
        )
        stanza.needs_review = True
        if "irregular_gatha_stanza" not in stanza.review_reasons:
            stanza.review_reasons.append("irregular_gatha_stanza")
        for u in buf[1:]:
            stanza.notes.extend(u[2].notes)
            stanza.symbol_notes.update(u[2].symbol_notes)
        stanzas.append(stanza)

    return stanzas


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


def detect_running_headers(doc: fitz.Document, content_start_idx: int) -> set[str]:
    counts: dict[str, int] = {}
    end = min(doc.page_count, content_start_idx + 12)
    for i in range(content_start_idx, end):
        text = vztime_to_unicode(doc[i].get_text("text"))
        for line in text.splitlines():
            s = line.strip()
            if not s or PAGE_NUM_RE.match(s) or FOOTNOTE_RULE_RE.match(s):
                continue
            if len(s) <= 40:
                counts[s] = counts.get(s, 0) + 1
    return {line for line, n in counts.items() if n >= 3}


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
    # PDF-page → stroke-overlay (fake-bold) span strings from texttrace.
    bold_by_pdf_page: dict[int, list[str]] = {}

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
        bold_spans = bold_span_texts(doc[idx])
        if bold_spans:
            bold_by_pdf_page[pdf_page] = bold_spans
        raw.extend(
            extract_page_blocks(
                page_text,
                printed_page=printed,
                pdf_page=pdf_page,
                headers=headers,
                is_opening_page=(printed == 1),
            )
        )

    segments = group_gatha_stanzas(
        tag_gatha_segments(attach_notes_sacred_style(merge_blocks(raw)))
    )
    # Geometry pass: fold first-indent head + deeper hang lines into one unit.
    pdf_pages = {s.pdf_page for s in segments if s.pdf_page}
    hanging_groups = collect_hanging_groups(doc, pdf_pages=pdf_pages)
    hanging_merged = merge_hanging_into_segments(segments, hanging_groups)
    review_count = sum(1 for s in segments if s.needs_review)
    type_counts: dict[str, int] = {}
    for s in segments:
        type_counts[s.segment_type] = type_counts.get(s.segment_type, 0) + 1
    notes_embedded = sum(1 for s in segments if s.notes)
    segments_with_bold = 0
    json_segments: list[dict] = []
    for s in segments:
        payload = _segment_to_json(s, bold_by_pdf_page=bold_by_pdf_page)
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
            "segment_type_counts": dict(sorted(type_counts.items())),
        },
    }


def _wak_text_to_json(
    roman: str,
    *,
    bold_spans: list[str] | None = None,
) -> tuple[list[dict], bool]:
    prepared, _ = prepare_roman_body(roman)
    ranges = bold_ranges_in_text(prepared, bold_spans or [])
    return script_text_entries(prepared, bold_ranges=ranges or None)

def _bold_spans_for_segment(
    seg: Segment,
    bold_by_pdf_page: dict[int, list[str]],
) -> list[str]:
    if not seg.pdf_page:
        return []
    spans = list(bold_by_pdf_page.get(seg.pdf_page) or [])
    # Rare mid-unit page break: allow spans from the next PDF page too.
    if seg.segment_type.endswith("_continuation"):
        spans.extend(bold_by_pdf_page.get(seg.pdf_page + 1) or [])
    return spans


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
    bold_by_pdf_page: dict[int, list[str]] | None = None,
) -> dict:
    """Serialize a Segment; ``text`` becomes multi-script entries (+ optional runs).

    Omits ``pdf_page`` and gāthā ``bat``/``wak``/``role`` (schema v1). Final
    compact form (empty flags/notes, bold-only runs) is applied by
    ``normalize_document`` on save.
    """
    data = asdict(seg)
    data.pop("pdf_page", None)
    flags = [f for f in (data.get("flags") or []) if f != SECTION_RULE_FLAG]
    had_rule = False
    bold_spans = _bold_spans_for_segment(seg, bold_by_pdf_page or {})

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
                        str(roman), bold_spans=bold_spans
                    )
                    had_rule = had_rule or rule
                json_waks.append({"text": entries})
            json_bats.append({"waks": json_waks})
        data["bats"] = json_bats
        data["source_layout"] = seg.source_layout
    else:
        prepared, _ = prepare_roman_body(seg.text)
        ranges = bold_ranges_in_text(prepared, bold_spans)
        entries, had_rule = script_text_entries(
            prepared, bold_ranges=ranges or None
        )
        data["text"] = entries
        data.pop("bats", None)
        if seg.source_layout == "hanging" and seg.hanging_lines:
            data["source_layout"] = "hanging"
            hl_out: list[list[dict]] = []
            for line in seg.hanging_lines:
                hl_entries, hl_rule = _wak_text_to_json(
                    str(line), bold_spans=bold_spans
                )
                had_rule = had_rule or hl_rule
                hl_out.append(hl_entries)
            data["hanging_lines"] = hl_out
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
            if existing.get("page_layout") is not None:
                data["page_layout"] = existing["page_layout"]
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
