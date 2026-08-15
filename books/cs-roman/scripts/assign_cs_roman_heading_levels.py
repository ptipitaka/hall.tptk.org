"""
Assign heading_kind / in_toc to cs-roman segment JSON from the volume Mātikā.

Uses the printed Mātikā in the CS Roman PDF as the structural skeleton for
heading_kind (and which body headings enter the TOC). Also writes
``*.matika.json`` — a separate outline used when generating memoir TOC marks
(body-anchored, structure-expanded; compound headings stay one segment).

Kinds: nik | boo | cha | h1 | h2 | h3 | h4 | h5 | h6.

Example:
  python books/cs-roman/scripts/assign_cs_roman_heading_levels.py \\
      books/cs-roman/output/01Vin01.segments.json \\
      --pdf books/cs-roman/source/01Vin01.pdf
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path

import fitz

from paths import OUTPUT_DIR, SOURCE_DIR, ensure_import_paths

ensure_import_paths()
from cs_roman_segments import save as save_segments  # noqa: E402
from cs_roman_text import is_ordinal_section_closer  # noqa: E402
from cs_roman_vztime import vztime_to_unicode  # noqa: E402
from extract_cs_roman_pdf import (  # noqa: E402
    detect_content_start,
    ends_with_speech_intro_dash,
)

HEADING_TYPES = frozenset(
    {
        "piṭaka",
        "gambhīra",
        "namakkāraṃ",
        "chapter",
        "title",
        "niṭṭhitaṃ",
        "subhead",
        "centered",
    }
)

# Skip these Mātikā page chrome lines.
# Page anchors may be a single page, a range (``1-4``), or a disjoint list
# (Paṭṭhāna ``21-30-38``).  Leaders may sit on the same extracted line
# (``... 21-30-38``).
_SKIP_LINE_RE = re.compile(
    r"^(?:"
    r"mātikā|piṭṭhaṅka|piṭṭhaṃka|"
    r"_{3,}|"
    r"[ivxlcdm]+\.?|"  # roman folio
    r"\.{2,}|"
    r"(?:\.{2,}\s*)?\d+(?:-\d+)*"  # 21 / 1-4 / ... 21-30-38 / 21-30-38
    r")$",
    re.IGNORECASE,
)
# Start page of ``N``, ``N-M``, or ``N-M-O-…``.
_PAGE_NUM_RE = re.compile(r"^(\d+)(?:-\d+)*$")
# Combined leader + page list on one extracted line.
_INLINE_LEADER_PAGE_RE = re.compile(
    r"^(?:\.{2,}\s*)(\d+(?:-\d+)*)\s*$"
)
# Book running headers: bare ``…pāḷi`` or ``…pāḷi paṭhamabhāga`` etc.
# Also accept ASCII ``pali`` (some volumes lack the underdot in extract).
_BOOK_RUNNING_RE = re.compile(
    r"^.+pā[ḷl]i(?:\s+(?:paṭhama|dutiya|tatiya|catuttha|pañcama)bhāga)?$",
    re.IGNORECASE,
)
_BHAGA_RUNNING_RE = re.compile(
    r"^.+pā[ḷl]i\s+(?:paṭhama|dutiya|tatiya|catuttha|pañcama)bhāga$",
    re.IGNORECASE,
)
_MATIKA_END_RE = re.compile(r"mātikā\s+niṭṭhit", re.IGNORECASE)
_NUMBERED_RE = re.compile(r"^(\d+)\.\s*(.+)$")
# Single ``N.`` or range ``N-M.`` / ``N–M.`` prefixes (hanging-number guard).
_SECTION_PREFIX_RE = re.compile(r"^\d+(?:\s*[-–]\s*\d+)?\.\s*")
_KANDA_RE = re.compile(r"kaṇḍa\b", re.IGNORECASE)
# Mahāvagga / Cūlavagga chapter heads (same TOC depth as *kaṇḍa).
_KHANDHAKA_RE = re.compile(r"khandhaka\b", re.IGNORECASE)
# Numbered peers of kaṇḍa in Vinaya Mātikā (same TOC depth as *kaṇḍa).
_KANDA_PEER_RE = re.compile(r"adhikaraṇasamatha\b", re.IGNORECASE)
# Whole vibhaṅga books/parts (not rule-internal “…vibhaṅga” analysis).
_MAJOR_VIBHANGA_RE = re.compile(
    r"^(?:bhikkhu|bhikkhunī)vibhaṅga$",
    re.IGNORECASE,
)
_VAGGA_RE = re.compile(r"vagga\b", re.IGNORECASE)
_RULE_RE = re.compile(
    r"(?:pārājika|sikkhāpada|saṃghādisesa|aniyata|nissaggiya)\b",
    re.IGNORECASE,
)
_SUB_HINT_RE = re.compile(
    r"(?:vatthu|bhāṇavāra|uddāna|gāthā|paññatti|anupaññatti|"
    r"vibhaṅga|padabhājanīya|kathā)\b",
    re.IGNORECASE,
)
_CLOSER_RE = re.compile(
    r"(?:niṭṭhit|samattaṃ|samatta\b|tassuddāna)",
    re.IGNORECASE,
)
# Centered deictic labels (Idaṃ sabbamūlakaṃ / อิทํ ทสมูลกํ) — not outline heads.
_IDAM_LABEL_RE = re.compile(
    r"^(?:Idaṃ|อิทํ)\s+\S+\.?$",
    re.IGNORECASE,
)
# Body compound: "Kosiyavagga 5. Nisīdanasanthatasikkhāpada"
_COMPOUND_CHILD_RE = re.compile(
    r"^(.+?)\s+(\d+)\.\s+(.+)$",
)
# CS Roman Mātikā: leaves sit in a left column (x0/width ≈ 0.13).  Centered
# parents — including long titles whose left edge drifts left of the page
# midpoint — are anything above that leaf band.  Do not require x0 ≳ 0.28:
# ``7. Pāpikāya diṭṭhiyā …`` is centered but only ≈ 0.23.
_LEFT_LEAF_X_RATIO = 0.18
# Kept for tests / callers that still pass a “center-ish” threshold.
_CENTER_X_RATIO = 0.28
# Distinct left-column indent steps (e.g. 62.6 → 85.0) are ~16–22pt.
# Smaller Δx0 is usually hanging-number width (``1.`` vs ``9-10.``), not nesting.
_LEFT_INDENT_EPS = 12.0

_KIND_DEPTH = {
    "nik": 0,
    "boo": 1,
    "cha": 2,
    "h1": 3,
    "h2": 4,
    "h3": 5,
    "h4": 6,
    "h5": 7,
    "h6": 8,
}
_KIND_BY_DEPTH = {depth: kind for kind, depth in _KIND_DEPTH.items()}

# Section-closing titles: after indent nesting, outdent to peer the numbered
# heads they follow — not as children of the last nested leaf alone.  They
# still stay below the open chapter/vagga.  Append more bare titles here as
# they are identified (Thai: อุทฺทานคาถา, …).
_SECTION_CLOSER_TITLES = frozenset(
    {
        "uddānagāthā",
        "uddānagāthāyo",
    }
)


@dataclass
class MatikaEntry:
    title: str
    page: int | None
    kind: str
    source_page: int  # 1-based PDF page in the Mātikā block
    section_no: int | None = None


@dataclass
class MatikaLine:
    """One extracted Mātikā text line, optionally with layout geometry."""

    pdf_page: int
    text: str
    x0: float | None = None
    page_width: float | None = None


def split_outline_title(title: str) -> tuple[int | None, str]:
    """Split ``N. Title`` into ``(N, Title)``; unnumbered → ``(None, title)``."""
    text = re.sub(r"\s+", " ", (title or "").strip())
    m = _NUMBERED_RE.match(text)
    if not m:
        return None, text
    return int(m.group(1)), m.group(2).strip()


def has_section_prefix(title: str) -> bool:
    """True for ``N.`` or range ``N-M.`` outline prefixes."""
    return bool(_SECTION_PREFIX_RE.match(re.sub(r"\s+", " ", (title or "").strip())))


def is_matika_centered(x0: float | None, page_width: float | None) -> bool | None:
    """Return True/False from geometry, or None when layout is unknown.

    Left-column leaves (``x0/width ≤ _LEFT_LEAF_X_RATIO``) are not centered.
    All other placed titles count as centered — long mid-heads start left of
    short ones when the printer centers the whole line.
    """
    if x0 is None or page_width is None or page_width <= 0:
        return None
    return (x0 / page_width) > _LEFT_LEAF_X_RATIO


def _is_structural_title(bare: str) -> bool:
    return bool(
        _KANDA_RE.search(bare)
        or _KHANDHAKA_RE.search(bare)
        or _KANDA_PEER_RE.search(bare)
        or _MAJOR_VIBHANGA_RE.match(bare)
    )


def _matika_entry(
    title: str,
    *,
    page: int | None,
    kind: str,
    source_page: int,
) -> MatikaEntry:
    section_no, bare = split_outline_title(title)
    return MatikaEntry(
        title=bare,
        page=page,
        kind=kind,
        source_page=source_page,
        section_no=section_no,
    )


def _roman_text(seg: dict) -> str:
    text = seg.get("text")
    if isinstance(text, list):
        for entry in text:
            if isinstance(entry, dict) and entry.get("script") == "roman":
                return str(entry.get("value") or "")
        if text and isinstance(text[0], dict):
            return str(text[0].get("value") or "")
        return ""
    return str(text or "")


def normalize_title(text: str) -> str:
    """Normalize for fuzzy match (strip numbers, punctuation, length marks)."""
    text = unicodedata.normalize("NFC", text or "")
    text = text.replace("{{n0}}", "").replace("{{*}}", "").replace("{{+}}", "")
    text = (
        text.replace("{{sp1}}", " ")
        .replace("{{sp3}}", " ")
        .replace("{{sp}}", " ")
        .replace("{{br}}", " ")
    )
    text = _NUMBERED_RE.sub(r"\2", text.strip())
    text = text.lower()
    # Fold common anusvāra / niggahīta variants.
    text = text.replace("ṁ", "ṃ")
    # Fold underdot / nasal pairs that often differ between Mātikā and body
    # (e.g. Surāpāṇavagga vs Surāpānavagga, Pācittiyapāli vs …pāḷi).
    text = (
        text.replace("ḷ", "l")
        .replace("ṇ", "n")
        .replace("ṭ", "t")
        .replace("ḍ", "d")
    )
    text = re.sub(r"[’'`´]", "", text)
    text = re.sub(r"[,:;.–—\-]+", " ", text)
    text = re.sub(r"[.!?]+$", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _title_tokens(norm: str) -> set[str]:
    return {t for t in re.split(r"\s+", norm) if len(t) >= 3}


def compound_parts(seg: dict) -> tuple[str | None, int | None, str | None]:
    """
    Split a compound body heading into (parent_name, child_no, child_name).

    Example: section_no=2, text ``Kosiyavagga 5. Nisīdanasanthatasikkhāpada``
    → (``Kosiyavagga``, 5, ``Nisīdanasanthatasikkhāpada``).
    """
    text = _roman_text(seg).strip()
    m = _COMPOUND_CHILD_RE.match(text)
    if not m:
        return None, None, None
    return m.group(1).strip(), int(m.group(2)), m.group(3).strip()


def classify_matika_title(
    title: str,
    *,
    has_page: bool,
    under_vagga: bool = False,
    centered: bool | None = None,
) -> str:
    """Infer heading_kind from Mātikā layout when known, else title morphology.

    Layout (preferred): CS Roman centers structural parents (kaṇḍa / khandhaka)
    and mid-level numbered heads (*kamma / vagga / …), and left-aligns paged
    leaves.  Consecutive centered numbered titles nest via a number stack in
    ``parse_matika`` (restart at 1 = child); this helper only classifies a
    single row (geometry + morphology), so centered non-structural numbered
    titles default to ``h1``.
    """
    bare = _NUMBERED_RE.sub(r"\2", title.strip())
    numbered = bool(_NUMBERED_RE.match(title.strip()))

    if _MAJOR_VIBHANGA_RE.match(bare):
        return "boo"

    # --- Layout-first path -------------------------------------------------
    if centered is True:
        if _is_structural_title(bare) and not _VAGGA_RE.search(bare):
            return "cha"
        if _KANDA_PEER_RE.search(bare):
            return "cha"
        if numbered and _RULE_RE.search(bare):
            return "h2" if under_vagga else "h1"
        if _VAGGA_RE.search(bare) and not _RULE_RE.search(bare):
            return "h1"
        # Centered numbered mid-heads (*kamma, pārājika, …): h1 here;
        # parse_matika may promote/demote via the consecutive-number stack.
        if numbered:
            return "h1"
        if not has_page:
            return "cha" if _is_structural_title(bare) else "h1"
        return "h1"

    if centered is False:
        # Single-row helper: left leaves default to one depth.  Relative
        # deeper-indent nesting among consecutive left rows is applied in
        # ``parse_matika``.
        if under_vagga:
            return "h2"
        return "h1"

    # --- Morphology fallback (no geometry) ---------------------------------
    if _KANDA_RE.search(bare) or _KHANDHAKA_RE.search(bare) or _KANDA_PEER_RE.search(
        bare
    ):
        return "cha"
    if _VAGGA_RE.search(bare) and not _RULE_RE.search(bare):
        return "h1"
    if numbered and _RULE_RE.search(bare):
        return "h2" if under_vagga else "h1"
    if numbered and not _SUB_HINT_RE.search(bare) and len(bare) <= 60:
        # e.g. "1. Paṭhamapārājika"
        return "h1"
    if has_page or _SUB_HINT_RE.search(bare):
        return "h3" if under_vagga else "h2"
    if _RULE_RE.search(bare):
        return "h2" if under_vagga else "h1"
    return "h2"


def _centered_number_depth(stack: list[int], n: int, *, structural: bool) -> int:
    """Update ``stack`` of open centered section numbers; return 1-based depth.

    Structural titles (kaṇḍa / khandhaka) always sit at depth 1 and reset the
    stack.  Other centered numbered titles nest: a restart at ``1`` pushes a
    child level; ``2, 3, …`` replace the sibling whose number is ``n - 1``
    after popping completed deeper numbers (``while top >= n``).
    """
    if structural:
        stack[:] = [n]
        return 1
    if n == 1:
        stack.append(1)
    else:
        while stack and stack[-1] >= n:
            stack.pop()
        if stack and stack[-1] == n - 1:
            stack[-1] = n
        else:
            stack.append(n)
    return len(stack)


def _kind_at_centered_depth(depth: int) -> str:
    """Map consecutive-centered depth → heading_kind."""
    if depth <= 1:
        return "cha"
    if depth == 2:
        return "h1"
    if depth == 3:
        return "h2"
    return f"h{min(depth, 6)}"


def _kind_plus(base: str, rel: int) -> str:
    """Return ``base`` deepened by ``rel`` outline steps (clamped at h6)."""
    if rel <= 0:
        return base
    depth = min(_KIND_DEPTH.get(base, 3) + rel, _KIND_DEPTH["h6"])
    return _KIND_BY_DEPTH.get(depth, "h6")


def _kind_minus(kind: str, steps: int = 1, *, floor: str) -> str:
    """Return ``kind`` raised by ``steps`` outline levels, not above ``floor``."""
    if steps <= 0:
        return kind
    depth = max(
        _KIND_DEPTH.get(kind, 3) - steps,
        _KIND_DEPTH.get(floor, 3),
    )
    return _KIND_BY_DEPTH.get(depth, floor)


def is_section_closer_title(title: str) -> bool:
    """True for known section-closing titles (e.g. Uddānagāthā)."""
    _, bare = split_outline_title(title)
    return normalize_title(bare) in _SECTION_CLOSER_TITLES


def _left_indent_kind(
    stack: list[tuple[float, bool]],
    x0: float,
    *,
    has_prefix: bool,
    base_kind: str,
) -> str:
    """Nest left-column rows by relative indent; return heading_kind.

    A row with ``x0`` deeper than the open left parent becomes a child.
    Prefixed→prefixed “deeper” steps are ignored: in Sam/An that Δx0 is
    hanging-number width (``1.`` vs ``1-2.``), not hierarchy.  True Vinaya
    sub-items are unprefixed at the deeper band (``Appaṭicchannamānatta``
    under ``1. Sukkavissaṭṭhi``).
    """
    while stack and x0 < stack[-1][0] - _LEFT_INDENT_EPS:
        stack.pop()
    if not stack:
        stack.append((x0, has_prefix))
        return base_kind
    parent_x0, parent_prefixed = stack[-1]
    if x0 > parent_x0 + _LEFT_INDENT_EPS:
        if has_prefix and parent_prefixed:
            # Hanging-number sibling — stay at parent depth.
            return _kind_plus(base_kind, len(stack) - 1)
        stack.append((x0, has_prefix))
    else:
        # Same indent band: sibling; keep the band's first x0.
        stack[-1] = (parent_x0, has_prefix)
    return _kind_plus(base_kind, len(stack) - 1)


def _matika_page_range(doc: fitz.Document, *, content_start: int) -> list[int]:
    """1-based PDF page numbers that belong to the Mātikā block."""
    start = max(1, content_start - 12)
    end = content_start
    pages: list[int] = []
    for pdf_page in range(start, end):
        text = vztime_to_unicode(doc[pdf_page - 1].get_text("text"))
        if re.search(r"\bmātikā\b", text, re.IGNORECASE) or (
            pages and re.search(r"\bpiṭṭhaṅka\b", text, re.IGNORECASE)
        ):
            pages.append(pdf_page)
        elif pages:
            pages.append(pdf_page)
    if not pages:
        for pdf_page in range(1, content_start):
            text = vztime_to_unicode(doc[pdf_page - 1].get_text("text"))
            if text.count("...") >= 8 and re.search(r"pāḷi", text, re.I):
                pages.append(pdf_page)
    return pages


def extract_matika_pages(
    doc: fitz.Document, *, content_start: int
) -> list[tuple[int, str]]:
    """Return [(pdf_page_1based, unicode_text), ...] for Mātikā pages."""
    return [
        (pdf_page, vztime_to_unicode(doc[pdf_page - 1].get_text("text")))
        for pdf_page in _matika_page_range(doc, content_start=content_start)
    ]


def extract_matika_lines(
    doc: fitz.Document, *, content_start: int
) -> list[MatikaLine]:
    """Extract Mātikā lines with left-edge geometry for layout classification."""
    lines: list[MatikaLine] = []
    for pdf_page in _matika_page_range(doc, content_start=content_start):
        page = doc[pdf_page - 1]
        page_width = float(page.rect.width)
        for block in page.get_text("dict").get("blocks") or []:
            if block.get("type") != 0:
                continue
            for line in block.get("lines") or []:
                spans = line.get("spans") or []
                if not spans:
                    continue
                raw = "".join(str(span.get("text") or "") for span in spans)
                text = vztime_to_unicode(raw).strip()
                if not text:
                    continue
                x0 = min(float(span["bbox"][0]) for span in spans)
                lines.append(
                    MatikaLine(
                        pdf_page=pdf_page,
                        text=text,
                        x0=x0,
                        page_width=page_width,
                    )
                )
    return lines


def _coerce_matika_lines(
    pages: list[tuple[int, str]] | list[MatikaLine],
) -> list[MatikaLine]:
    if not pages:
        return []
    if isinstance(pages[0], MatikaLine):
        return list(pages)  # type: ignore[arg-type]
    out: list[MatikaLine] = []
    for pdf_page, text in pages:  # type: ignore[misc]
        for raw_line in str(text).splitlines():
            line = raw_line.strip()
            if line:
                out.append(MatikaLine(pdf_page=int(pdf_page), text=line))
    return out


def parse_matika(
    pages: list[tuple[int, str]] | list[MatikaLine],
) -> list[MatikaEntry]:
    """Parse Mātikā pages/lines into ordered TOC entries.

    When lines carry ``x0`` / ``page_width``, kinds follow printed layout
    (centered parents vs left-aligned leaves).  Within the left column,
    deeper indent than the previous left row nests as a child (e.g.
    ``Appaṭicchannamānatta`` under ``1. Sukkavissaṭṭhi``).  Text-only input
    falls back to title morphology.
    """
    entries: list[MatikaEntry] = []
    book_title: str | None = None
    pending_title: str | None = None
    pending_source = 0
    pending_x0: float | None = None
    pending_width: float | None = None
    dot_run = 0
    under_vagga = False
    # True while left-aligned leaves nest under a centered mid-level parent
    # (depth ≥ 2 from the consecutive-number stack).
    under_mid = False
    # Last centered kind below cha (h1/h2/…); left leaves nest one deeper.
    # Needed when a centered rule under vagga is already h2 — a flat
    # under_vagga→h2 base would make Cabbaggiyabhikkhuvatthu a sibling of
    # Paṭhamakathinasikkhāpada instead of a child.
    last_mid_kind: str | None = None
    # Open centered section numbers (depth = len); structural titles reset.
    num_stack: list[int] = []
    # Open left-column indent bands: (x0, numbered).
    left_indent_stack: list[tuple[float, bool]] = []
    seen_bhaga_running: set[str] = set()
    seen_book_running: set[str] = set()

    def _reset_left_indent() -> None:
        left_indent_stack.clear()

    def _kind_for(
        title: str,
        *,
        has_page: bool,
        x0: float | None = None,
        page_width: float | None = None,
    ) -> str:
        nonlocal under_vagga, under_mid, last_mid_kind, num_stack
        centered = is_matika_centered(x0, page_width)
        section_no, bare = split_outline_title(title)
        numbered = section_no is not None
        structural = bool(
            (
                _is_structural_title(bare)
                and not _VAGGA_RE.search(bare)
            )
            or _KANDA_PEER_RE.search(bare)
        )

        if centered is True:
            _reset_left_indent()
            if structural:
                if numbered:
                    _centered_number_depth(
                        num_stack, section_no, structural=True
                    )
                else:
                    num_stack.clear()
                under_mid = False
                under_vagga = False
                last_mid_kind = None
                return "cha"
            if numbered and _RULE_RE.search(bare) and under_vagga:
                last_mid_kind = "h2"
                under_mid = True
                return "h2"
            if numbered:
                depth = _centered_number_depth(
                    num_stack, section_no, structural=False
                )
                kind = _kind_at_centered_depth(depth)
                under_mid = kind != "cha"
                under_vagga = bool(
                    _VAGGA_RE.search(bare) and not _RULE_RE.search(bare)
                )
                last_mid_kind = kind if kind != "cha" else None
                return kind
            kind = classify_matika_title(
                title,
                has_page=has_page,
                under_vagga=under_vagga,
                centered=True,
            )
            if kind in {"boo", "cha", "nik"}:
                under_mid = False
                under_vagga = False
                last_mid_kind = None
                num_stack.clear()
            elif _VAGGA_RE.search(bare) and not _RULE_RE.search(bare):
                under_vagga = True
                under_mid = True
                last_mid_kind = kind
            else:
                last_mid_kind = kind if kind not in {"boo", "cha", "nik"} else None
            return kind

        if centered is False:
            # Left-aligned leaves under a centered mid-parent (or vagga),
            # with optional deeper indent nesting among left rows.
            # Nest one level under the last centered mid-head when known
            # (vagga→sikkhāpada h2 → left leaves h3).
            if last_mid_kind is not None:
                base = _kind_plus(last_mid_kind, 1)
            else:
                base = "h2" if (under_mid or under_vagga) else "h1"
            if x0 is not None:
                kind = _left_indent_kind(
                    left_indent_stack,
                    x0,
                    has_prefix=has_section_prefix(title),
                    base_kind=base,
                )
            else:
                kind = base
            # Closers (Uddānagāthā, …): peer of the numbered heads they follow,
            # not a child of the last nested leaf alone.  Stay below cha/vagga.
            if is_section_closer_title(title):
                if len(left_indent_stack) > 1:
                    left_indent_stack.pop()
                # Peer the last centered mid-head when known (sikkhāpada h2
                # under vagga; numbered kamma h1 under kaṇḍa).  Else keep the
                # old under_mid / base floors.
                if last_mid_kind is not None:
                    floor = last_mid_kind
                elif under_mid and not under_vagga:
                    floor = "h1"
                else:
                    floor = base
                kind = _kind_minus(kind, 1, floor=floor)
                if left_indent_stack:
                    left_indent_stack[-1] = (
                        left_indent_stack[-1][0],
                        False,
                    )
            return kind

        kind = classify_matika_title(
            title,
            has_page=has_page,
            under_vagga=under_vagga,
            centered=None,
        )
        if (
            kind in {"boo", "cha", "nik"}
            or _is_structural_title(bare)
        ):
            under_vagga = False
            under_mid = False
            last_mid_kind = None
            num_stack.clear()
            _reset_left_indent()
        elif _VAGGA_RE.search(bare) and not _RULE_RE.search(bare):
            under_vagga = True
            under_mid = True
            last_mid_kind = kind
        else:
            last_mid_kind = kind if kind not in {"boo", "cha", "nik"} else None
        return kind

    def flush_structural(title: str, source_page: int) -> None:
        entries.append(
            _matika_entry(
                title,
                page=None,
                kind=_kind_for(
                    title,
                    has_page=False,
                    x0=pending_x0,
                    page_width=pending_width,
                ),
                source_page=source_page,
            )
        )

    def flush_paged(title: str, page: int, source_page: int) -> None:
        nonlocal pending_title, pending_x0, pending_width, dot_run
        entries.append(
            _matika_entry(
                title,
                page=page,
                kind=_kind_for(
                    title,
                    has_page=True,
                    x0=pending_x0,
                    page_width=pending_width,
                ),
                source_page=source_page,
            )
        )
        pending_title = None
        pending_x0 = None
        pending_width = None
        dot_run = 0

    for row in _coerce_matika_lines(pages):
        line = row.text.strip()
        if not line:
            continue
        if _MATIKA_END_RE.search(line):
            pending_title = None
            pending_x0 = None
            pending_width = None
            dot_run = 0
            continue

        # Leader + page list on one line: ``... 21-30-38``.
        inline = _INLINE_LEADER_PAGE_RE.match(line)
        if inline and pending_title:
            flush_paged(
                pending_title,
                int(inline.group(1).split("-", 1)[0]),
                pending_source,
            )
            continue
        if inline:
            continue

        # Pure leader dots, bare page, or multi-page list.
        if _SKIP_LINE_RE.match(line):
            if line.startswith("...") and not any(ch.isdigit() for ch in line):
                if pending_title:
                    dot_run += 1
            elif (m := _PAGE_NUM_RE.match(line)) and pending_title and dot_run:
                flush_paged(pending_title, int(m.group(1)), pending_source)
            # Bare page number on its own line after a title (common in
            # geometry extracts where leaders are separate drawing ops).
            elif (
                (m := _PAGE_NUM_RE.match(line))
                and pending_title
                and row.x0 is not None
                and row.page_width
                and row.x0 > row.page_width * 0.7
            ):
                flush_paged(pending_title, int(m.group(1)), pending_source)
            continue

        if _BOOK_RUNNING_RE.match(line) and not _NUMBERED_RE.match(line):
            folded = normalize_title(line)
            if _BHAGA_RUNNING_RE.match(line):
                if folded in seen_bhaga_running or book_title is not None:
                    pending_title = None
                    pending_x0 = None
                    pending_width = None
                    dot_run = 0
                    continue
                seen_bhaga_running.add(folded)
            # Repeated bare / compound ``…pāḷi`` lines are page chrome
            # (common in Paṭṭhāna part 5), not new outline rows.
            if folded in seen_book_running:
                pending_title = None
                pending_x0 = None
                pending_width = None
                dot_run = 0
                continue
            seen_book_running.add(folded)
            if book_title is None:
                book_title = line
            _reset_left_indent()
            under_mid = False
            under_vagga = False
            last_mid_kind = None
            num_stack.clear()
            entries.append(
                _matika_entry(
                    line,
                    page=None,
                    kind="boo",
                    source_page=row.pdf_page,
                )
            )
            pending_title = None
            pending_x0 = None
            pending_width = None
            dot_run = 0
            continue

        # New candidate title line.
        if pending_title and not dot_run:
            flush_structural(pending_title, pending_source)
        pending_title = line
        pending_source = row.pdf_page
        pending_x0 = row.x0
        pending_width = row.page_width
        dot_run = 0

    if pending_title and not dot_run:
        flush_structural(pending_title, pending_source)

    return entries


def is_plain_centered_label(seg: dict, text: str) -> bool:
    """True for mid-body ``Idaṃ …`` / ``อิทํ …`` labels (not outline heads).

    These are body centers (``\\csromancenter``), never ``heading_kind``.
    Other centered titles keep morphology / Mātikā assignment (often bold).
    """
    _ = seg
    return bool(_IDAM_LABEL_RE.match((text or "").strip()))


def fallback_kind(seg: dict, text: str) -> tuple[str | None, bool]:
    """
    Return (heading_kind, in_toc) when no Mātikā match applies.

    ``in_toc`` is True only for edition title stack (nik/boo) so front-matter
    titles still enter the memoir TOC when absent from the Mātikā block.
    """
    st = seg.get("segment_type") or ""
    if (
        st in {"namakkāraṃ", "niṭṭhitaṃ"}
        or _CLOSER_RE.search(text)
        or is_ordinal_section_closer(text)
        or is_plain_centered_label(seg, text)
    ):
        return None, False
    if st == "piṭaka":
        return "nik", True
    if st == "gambhīra":
        return "boo", True
    if st == "chapter":
        if _MAJOR_VIBHANGA_RE.match(text.strip()):
            return "boo", False
        if (
            _KANDA_RE.search(text)
            or _KHANDHAKA_RE.search(text)
            or _KANDA_PEER_RE.search(text)
        ) and not re.search(r"sikkhāpada\b", text, re.I):
            return "cha", False
        if _RULE_RE.search(text) or re.search(r"sikkhāpada\b", text, re.I):
            return "h1", False
        return "cha", False
    if st == "title":
        if ends_with_speech_intro_dash(text):
            return None, False
        if _CLOSER_RE.search(text) or is_ordinal_section_closer(text):
            return None, False
        if _MAJOR_VIBHANGA_RE.match(text.strip()):
            return "boo", False
        if _KANDA_PEER_RE.search(text):
            return "cha", False
        if _RULE_RE.search(text) and not _SUB_HINT_RE.search(text):
            return "h1", False
        if re.search(
            r"(?:paṭhama|dutiya|tatiya|catuttha).+pārājika\b", text, re.I
        ):
            if "samatta" not in text.lower():
                return "h1", False
        if re.search(r"sikkhāpada\b", text, re.I):
            return "h1", False
        return "h2", False
    return None, False


def _score_match(entry_norm: str, seg_norm: str) -> float:
    if not entry_norm or not seg_norm:
        return 0.0
    if entry_norm == seg_norm:
        return 100.0
    # Primary title before comma in Mātikā compound lines.
    entry_primary = entry_norm.split(",")[0].strip()
    # First whitespace-separated chunk often carries the heading stem
    # (e.g. Sudinnabhāṇavāra in "Sudinnabhāṇavāra Sudinnabhikkhuvatthu").
    entry_stem = (entry_primary or entry_norm).split(" ", 1)[0]
    if entry_primary and (
        entry_primary == seg_norm
        or entry_primary in seg_norm
        or seg_norm in entry_primary
    ):
        return 80.0 + min(len(entry_primary), 20) / 20.0
    if entry_stem and len(entry_stem) >= 6 and entry_stem in seg_norm:
        return 75.0 + min(len(entry_stem), 20) / 20.0
    if entry_norm in seg_norm or seg_norm in entry_norm:
        return 70.0 + min(len(entry_norm), len(seg_norm)) / 40.0
    et = _title_tokens(entry_primary or entry_norm)
    st = _title_tokens(seg_norm)
    if not et or not st:
        return 0.0
    overlap = et & st
    if not overlap:
        return 0.0
    return 40.0 * len(overlap) / max(len(et), 1) + 10.0 * len(overlap) / max(
        len(st), 1
    )


def _score_entry_against_segment(entry: MatikaEntry, seg: dict, seg_norm: str) -> float:
    """Score including compound parent/child parts (one body segment, two outline rows)."""
    en = normalize_title(entry.title)
    score = _score_match(en, seg_norm)
    parent, child_no, child_name = compound_parts(seg)
    if parent:
        parent_norm = normalize_title(parent)
        parent_score = _score_match(en, parent_norm)
        if parent_score:
            # Prefer vagga-like entries for the parent half.
            if _VAGGA_RE.search(parent) and (
                _VAGGA_RE.search(entry.title) or entry.kind == "h1"
            ):
                parent_score += 8
            score = max(score, parent_score)
    if child_name:
        child_norm = normalize_title(child_name)
        child_score = _score_match(en, child_norm)
        if (
            entry.section_no is not None
            and child_no is not None
            and entry.section_no == child_no
        ):
            child_score += 12
        if child_score:
            score = max(score, child_score + 5)
    if entry.page is not None:
        page = seg.get("page")
        if page == entry.page:
            score += 25
        elif isinstance(page, int) and abs(page - entry.page) <= 1:
            score += 10
    return score


def _page_matches(entry: MatikaEntry, seg_page: object) -> bool:
    """
    Page-first anchor gate: a printed Mātikā page (e.g. ``... 10``) refers to
    the body page bearing that same folio/printed number (ฉ.10). When an
    entry carries a page, only segments on that exact page (or, failing
    that, the immediately adjacent page — a heading can start right at a
    page turn) are eligible; this keeps text-fuzzy scoring from pairing an
    entry with a same-vocabulary segment on a distant, unrelated page (the
    failure mode seen on non-Vinaya Mātikā, e.g. Kathāvatthu / Paṭṭhāna).
    """
    if entry.page is None:
        return True
    return isinstance(seg_page, int) and abs(seg_page - entry.page) <= 1


def match_entries_to_segments(
    entries: list[MatikaEntry], segments: list[dict]
) -> tuple[dict[int, int], list[int], list[int]]:
    """
    Map each Mātikā entry index → best segment index (entries may share a segment).

    Returns (entry_to_seg, unmatched_entry_idxs, unmatched_heading_idxs).
    """
    heading_idxs = [
        i
        for i, s in enumerate(segments)
        if (s.get("segment_type") in HEADING_TYPES)
        and (s.get("segment_type") not in {"namakkāraṃ", "niṭṭhitaṃ"})
        and not _CLOSER_RE.search(_roman_text(s))
        and not is_ordinal_section_closer(_roman_text(s))
    ]
    seg_norms = {
        i: normalize_title(_roman_text(segments[i])) for i in heading_idxs
    }

    kind_rank = {
        "boo": 0,
        "cha": 1,
        "h1": 2,
        "h2": 3,
        "h3": 4,
        "h4": 5,
        "h5": 6,
        "h6": 7,
        "nik": 8,
    }
    ordered_idxs = sorted(
        range(len(entries)),
        key=lambda i: (
            kind_rank.get(entries[i].kind, 9),
            0 if entries[i].page is not None else 1,
            entries[i].source_page,
            entries[i].title,
        ),
    )

    entry_to_seg: dict[int, int] = {}
    # Track which (segment, kind-band) already took a exclusive coarse match.
    # Multiple entries may share one compound segment.
    used_exclusive: set[int] = set()
    # Structural / book titles already matched: skip later identical chrome.
    matched_title_norms: set[str] = set()

    # Page-first anchoring: entries with a printed page number should only
    # ever anchor within that folio (± the adjacent page for a heading
    # sitting right at a page turn). This makes the Mātikā page number the
    # primary reference (as printed, ``...  10`` -> ฉ.10), and text scoring a
    # tie-breaker among same-page candidates rather than a document-wide
    # search — the latter is what let short/generic Abhidhamma titles
    # (Kathāvatthu, Paṭṭhāna, ...) latch onto unrelated segments elsewhere.
    on_page: dict[int, list[int]] = {}
    for i in heading_idxs:
        p = segments[i].get("page")
        if isinstance(p, int):
            on_page.setdefault(p, []).append(i)

    def _candidates_for(entry: MatikaEntry) -> list[int]:
        if entry.page is None:
            return heading_idxs
        exact = on_page.get(entry.page, [])
        if exact:
            return exact
        # No heading segment lands exactly on that folio: allow the
        # adjacent page only (still page-anchored, never document-wide).
        return on_page.get(entry.page - 1, []) + on_page.get(entry.page + 1, [])

    def _seg_order(seg_i: int) -> int:
        order = segments[seg_i].get("order")
        return int(order) if order is not None else 10**9

    for ei in ordered_idxs:
        entry = entries[ei]
        entry_norm = normalize_title(entry.title)
        # Duplicate unpaged titles: keep the first match (running headers /
        # recapitulated section labels latching onto the first body hit).
        if entry.page is None and entry_norm in matched_title_norms:
            continue

        best_i, best_score = None, 0.0
        candidates = heading_idxs if entry.kind == "boo" else _candidates_for(entry)
        for i in candidates:
            st = segments[i].get("segment_type")
            if entry.kind == "boo":
                if st not in {"gambhīra", "title", "chapter"}:
                    continue
                if i in used_exclusive:
                    continue
                score = _score_match(entry_norm, seg_norms[i])
                if st == "gambhīra":
                    score += 15
            else:
                score = _score_entry_against_segment(
                    entry, segments[i], seg_norms[i]
                )
                parent, _, _child_name = compound_parts(segments[i])
                # Non-compound exclusive: one entry per segment unless compound.
                if not parent and i in used_exclusive:
                    score -= 40
            # Book titles: prefer the earliest qualifying segment so a late
            # gambhīra / title rematch cannot invert the outline planner.
            if entry.kind == "boo":
                if score > best_score or (
                    score == best_score
                    and best_i is not None
                    and _seg_order(i) < _seg_order(best_i)
                ):
                    best_i, best_score = i, score
                elif best_i is None and score > 0:
                    best_i, best_score = i, score
            elif score > best_score:
                best_i, best_score = i, score
            elif (
                score == best_score
                and best_i is not None
                and _seg_order(i) < _seg_order(best_i)
            ):
                best_i, best_score = i, score

        threshold = 50.0 if entry.kind == "boo" else 40.0
        # Among all boo candidates at/above threshold, force the earliest.
        if entry.kind == "boo" and best_i is not None and best_score >= threshold:
            earliest_i, earliest_order = best_i, _seg_order(best_i)
            for i in candidates:
                st = segments[i].get("segment_type")
                if st not in {"gambhīra", "title", "chapter"}:
                    continue
                if i in used_exclusive:
                    continue
                score = _score_match(entry_norm, seg_norms[i])
                if st == "gambhīra":
                    score += 15
                if score >= threshold and _seg_order(i) < earliest_order:
                    earliest_i, earliest_order = i, _seg_order(i)
            best_i = earliest_i

        if best_i is not None and best_score >= threshold:
            entry_to_seg[ei] = best_i
            matched_title_norms.add(entry_norm)
            parent, _, _ = compound_parts(segments[best_i])
            if not parent or entry.kind in {"boo", "nik", "cha"}:
                used_exclusive.add(best_i)

    unmatched_entries = [i for i in range(len(entries)) if i not in entry_to_seg]
    matched_segs = set(entry_to_seg.values())
    unmatched_heads = [i for i in heading_idxs if i not in matched_segs]
    return entry_to_seg, unmatched_entries, unmatched_heads


def build_matika_document(
    entries: list[MatikaEntry],
    entry_to_seg: dict[int, int],
    segments: list[dict],
) -> dict:
    """Serialize Mātikā outline with optional body ``matched_order`` anchors."""
    out: list[dict] = []
    for i, entry in enumerate(entries):
        seg_i = entry_to_seg.get(i)
        order = None
        if seg_i is not None:
            order = segments[seg_i].get("order")
            if order is not None:
                order = int(order)
        row: dict = {
            "title": entry.title,
            "page": entry.page,
            "kind": entry.kind,
            "matched_order": order,
        }
        if entry.section_no is not None:
            row["section_no"] = entry.section_no
        out.append(row)
    return {"schema_version": 1, "entries": out}


def assign_levels(
    data: dict,
    entries: list[MatikaEntry],
) -> tuple[dict, dict, dict]:
    """Return (updated document, report stats, matika document)."""
    data = dict(data)
    segments = [dict(s) for s in (data.get("segments") or [])]
    entry_to_seg, unmatched_entry_idxs, unmatched_heads = match_entries_to_segments(
        entries, segments
    )

    seg_to_entries: dict[int, list[MatikaEntry]] = {}
    for ei, si in entry_to_seg.items():
        seg_to_entries.setdefault(si, []).append(entries[ei])

    kind_counts: dict[str, int] = {}
    toc_count = 0
    review_added = 0

    for i, seg in enumerate(segments):
        st = seg.get("segment_type") or ""
        if st not in HEADING_TYPES:
            seg.pop("heading_kind", None)
            seg.pop("in_toc", None)
            continue

        text = _roman_text(seg)
        # Section closers (นิฏฺฐิตํ / ordinal …vaggo paṭhamo.) are not headings.
        # Plain centered labels (Idaṃ sabbamūlakaṃ) likewise stay body centers.
        if (
            st == "niṭṭhitaṃ"
            or _CLOSER_RE.search(text)
            or is_ordinal_section_closer(text)
            or is_plain_centered_label(seg, text)
        ):
            seg.pop("heading_kind", None)
            seg.pop("in_toc", None)
            continue

        if i in seg_to_entries:
            matched_entries = seg_to_entries[i]
            # Deepest outline level wins for body typography (child of compound).
            best = max(
                matched_entries,
                key=lambda e: _KIND_DEPTH.get(e.kind, 0),
            )
            seg["heading_kind"] = best.kind
            seg["in_toc"] = True
            reasons = [
                r
                for r in (seg.get("review_reasons") or [])
                if r != "weak_heading_heuristic"
            ]
            if reasons != (seg.get("review_reasons") or []):
                seg["review_reasons"] = reasons
                seg["needs_review"] = bool(reasons)
        else:
            kind, in_toc = fallback_kind(seg, text)
            if kind:
                seg["heading_kind"] = kind
            else:
                seg.pop("heading_kind", None)
            seg["in_toc"] = bool(in_toc)
            if (
                st in {"chapter", "title"}
                and i in unmatched_heads
                and "heading_level_unmatched_matika"
                not in (seg.get("review_reasons") or [])
            ):
                if "weak_heading_heuristic" in (seg.get("review_reasons") or []):
                    reasons = list(seg.get("review_reasons") or [])
                    reasons.append("heading_level_unmatched_matika")
                    seg["review_reasons"] = reasons
                    seg["needs_review"] = True
                    review_added += 1

        kind = seg.get("heading_kind")
        if kind:
            kind_counts[kind] = kind_counts.get(kind, 0) + 1
        if seg.get("in_toc"):
            toc_count += 1

    matika_doc = build_matika_document(entries, entry_to_seg, segments)
    report = {
        "matika_entries": len(entries),
        "matika_matched_to_segments": len(entry_to_seg),
        "matika_unmatched": len(unmatched_entry_idxs),
        "heading_segments_without_matika": len(unmatched_heads),
        "heading_kind_counts": dict(sorted(kind_counts.items())),
        "in_toc_count": toc_count,
        "review_flags_added": review_added,
        "unmatched_matika_sample": [
            asdict(entries[i]) for i in unmatched_entry_idxs[:40]
        ],
        "unmatched_heading_sample": [
            {
                "page": segments[i].get("page"),
                "segment_type": segments[i].get("segment_type"),
                "heading_kind": segments[i].get("heading_kind"),
                "text": _roman_text(segments[i])[:80],
            }
            for i in unmatched_heads[:40]
        ],
    }

    # Heading stats live in *.heading-report.json only (schema v1).
    ordered: dict = {}
    for key, value in data.items():
        if key in {"segments", "heading_model", "heading_assignment"}:
            continue
        ordered[key] = value
    ordered["segments"] = segments
    return ordered, report, matika_doc


def matika_path_for_segments(json_path: Path) -> Path:
    """``foo.segments.json`` → ``foo.matika.json``; else ``<stem>.matika.json``."""
    name = json_path.name
    if name.endswith(".segments.json"):
        return json_path.with_name(name.replace(".segments.json", ".matika.json"))
    return json_path.with_suffix(".matika.json")


def save_matika(path: Path, matika_doc: dict) -> None:
    path.write_text(
        json.dumps(matika_doc, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def process_file(
    json_path: Path,
    pdf_path: Path,
    *,
    report_path: Path | None = None,
    matika_out: Path | None = None,
) -> dict:
    doc = fitz.open(pdf_path)
    try:
        content_start = detect_content_start(doc)
        if content_start is None:
            raise SystemExit(f"Could not detect content start in {pdf_path}")
        pages = extract_matika_pages(doc, content_start=content_start)
        if not pages:
            raise SystemExit(f"No Mātikā pages found before content in {pdf_path}")
        lines = extract_matika_lines(doc, content_start=content_start)
        entries = parse_matika(lines if lines else pages)
    finally:
        doc.close()

    data = json.loads(json_path.read_text(encoding="utf-8"))
    data, report, matika_doc = assign_levels(data, entries)
    report["pdf"] = str(pdf_path).replace("\\", "/")
    report["json"] = str(json_path).replace("\\", "/")
    report["content_start_pdf_page"] = content_start
    report["matika_pdf_pages"] = [p for p, _ in pages]

    save_segments(json_path, data, normalize=True)
    out_matika = matika_out or matika_path_for_segments(json_path)
    save_matika(out_matika, matika_doc)
    report["matika_json"] = str(out_matika).replace("\\", "/")

    if report_path is None:
        # foo.segments.json → foo.segments.heading-report.json
        report_path = json_path.with_suffix(".heading-report.json")
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "json",
        type=Path,
        nargs="?",
        default=OUTPUT_DIR / "01Vin01.segments.json",
        help="segments JSON to update",
    )
    parser.add_argument(
        "--pdf",
        type=Path,
        default=None,
        help="Source CS Roman PDF (default: books/cs-roman/source/<stem>.pdf)",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        help="Write match report JSON (default: <json>.heading-report.json)",
    )
    parser.add_argument(
        "--matika-out",
        type=Path,
        default=None,
        help="Write matika outline JSON (default: <stem>.matika.json)",
    )
    args = parser.parse_args(argv)

    json_path = args.json
    if not json_path.is_file():
        raise SystemExit(f"Missing JSON: {json_path}")

    pdf_path = args.pdf
    if pdf_path is None:
        stem = json_path.name.replace(".segments.json", "")
        pdf_path = SOURCE_DIR / f"{stem}.pdf"
    if not pdf_path.is_file():
        raise SystemExit(f"Missing PDF: {pdf_path}")

    report = process_file(
        json_path,
        pdf_path,
        report_path=args.report,
        matika_out=args.matika_out,
    )
    out_report = args.report or json_path.with_suffix(".heading-report.json")
    out_matika = report.get("matika_json", "")
    print(
        f"Mātikā {report['matika_entries']} entries "
        f"(PDF pages {report['matika_pdf_pages']}) -> "
        f"matched {report['matika_matched_to_segments']}, "
        f"kinds {report['heading_kind_counts']}, "
        f"in_toc={report['in_toc_count']}"
    )
    print(f"Updated {json_path}")
    print(f"Matika  {out_matika}")
    print(f"Report  {out_report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
