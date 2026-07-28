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
from cs_roman_vztime import vztime_to_unicode  # noqa: E402
from extract_cs_roman_pdf import detect_content_start  # noqa: E402

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
_SKIP_LINE_RE = re.compile(
    r"^(?:"
    r"mātikā|piṭṭhaṅka|piṭṭhaṃka|"
    r"_{3,}|"
    r"[ivxlcdm]+\.?|"  # roman folio
    r"\.{2,}|"
    r"\d+(?:-\d+)?"  # page, or page range e.g. Kathāvatthu "1-4"
    r")$",
    re.IGNORECASE,
)
_PAGE_NUM_RE = re.compile(r"^(\d+)(?:-(\d+))?$")
_BOOK_RUNNING_RE = re.compile(r"^.+pāḷi$", re.IGNORECASE)
_MATIKA_END_RE = re.compile(r"mātikā\s+niṭṭhit", re.IGNORECASE)
_NUMBERED_RE = re.compile(r"^(\d+)\.\s*(.+)$")
_KANDA_RE = re.compile(r"kaṇḍa\b", re.IGNORECASE)
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
# Body compound: "Kosiyavagga 5. Nisīdanasanthatasikkhāpada"
_COMPOUND_CHILD_RE = re.compile(
    r"^(.+?)\s+(\d+)\.\s+(.+)$",
)

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


@dataclass
class MatikaEntry:
    title: str
    page: int | None
    kind: str
    source_page: int  # 1-based PDF page in the Mātikā block
    section_no: int | None = None


def split_outline_title(title: str) -> tuple[int | None, str]:
    """Split ``N. Title`` into ``(N, Title)``; unnumbered → ``(None, title)``."""
    text = re.sub(r"\s+", " ", (title or "").strip())
    m = _NUMBERED_RE.match(text)
    if not m:
        return None, text
    return int(m.group(1)), m.group(2).strip()


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
    )
    text = _NUMBERED_RE.sub(r"\2", text.strip())
    text = text.lower()
    # Fold common anusvāra / niggahīta variants.
    text = text.replace("ṁ", "ṃ")
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
) -> str:
    """Infer heading_kind from a Mātikā line (boo / cha / h1 / h2 / h3)."""
    bare = _NUMBERED_RE.sub(r"\2", title.strip())
    numbered = bool(_NUMBERED_RE.match(title.strip()))
    if _MAJOR_VIBHANGA_RE.match(bare):
        # Bhikkhuvibhaṅga / Bhikkhunīvibhaṅga — major part, not h3 analysis.
        return "boo"
    if _KANDA_RE.search(bare) or _KANDA_PEER_RE.search(bare):
        # e.g. Sekhiyakaṇḍa and peer 8. Adhikaraṇasamatha
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


def extract_matika_pages(
    doc: fitz.Document, *, content_start: int
) -> list[tuple[int, str]]:
    """Return [(pdf_page_1based, unicode_text), ...] for Mātikā pages."""
    # Heuristic: Mātikā sits in the last front-matter pages before content.
    start = max(1, content_start - 12)
    end = content_start  # exclusive as 1-based end = content_start
    pages: list[tuple[int, str]] = []
    for pdf_page in range(start, end):
        raw = doc[pdf_page - 1].get_text("text")
        text = vztime_to_unicode(raw)
        if re.search(r"\bmātikā\b", text, re.IGNORECASE) or (
            pages and re.search(r"\bpiṭṭhaṅka\b", text, re.IGNORECASE)
        ):
            pages.append((pdf_page, text))
        elif pages:
            # Continue contiguous block after first Mātikā hit.
            pages.append((pdf_page, text))
    # If heuristic missed, fall back to pages that contain dotted leaders + pāḷi.
    if not pages:
        for pdf_page in range(1, content_start):
            text = vztime_to_unicode(doc[pdf_page - 1].get_text("text"))
            if text.count("...") >= 8 and re.search(r"pāḷi", text, re.I):
                pages.append((pdf_page, text))
    return pages


def parse_matika(pages: list[tuple[int, str]]) -> list[MatikaEntry]:
    """Parse Mātikā text pages into ordered TOC entries."""
    entries: list[MatikaEntry] = []
    book_title: str | None = None
    pending_title: str | None = None
    pending_source = 0
    dot_run = 0
    under_vagga = False

    def _kind_for(title: str, *, has_page: bool) -> str:
        nonlocal under_vagga
        kind = classify_matika_title(
            title, has_page=has_page, under_vagga=under_vagga
        )
        bare = _NUMBERED_RE.sub(r"\2", title.strip())
        if (
            kind in {"boo", "cha", "nik"}
            or _KANDA_RE.search(bare)
            or _KANDA_PEER_RE.search(bare)
            or _MAJOR_VIBHANGA_RE.match(bare)
        ):
            under_vagga = False
        elif _VAGGA_RE.search(bare) and not _RULE_RE.search(bare):
            under_vagga = True
        return kind

    def flush_structural(title: str, source_page: int) -> None:
        entries.append(
            _matika_entry(
                title,
                page=None,
                kind=_kind_for(title, has_page=False),
                source_page=source_page,
            )
        )

    for pdf_page, text in pages:
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if _MATIKA_END_RE.search(line):
                pending_title = None
                dot_run = 0
                continue
            if _SKIP_LINE_RE.match(line):
                if line.startswith("..."):
                    if pending_title:
                        dot_run += 1
                elif (m := _PAGE_NUM_RE.match(line)) and pending_title and dot_run:
                    # A range ("1-4") anchors on its start page.
                    entries.append(
                        _matika_entry(
                            pending_title,
                            page=int(m.group(1)),
                            kind=_kind_for(pending_title, has_page=True),
                            source_page=pending_source,
                        )
                    )
                    pending_title = None
                    dot_run = 0
                continue

            if _BOOK_RUNNING_RE.match(line) and not _NUMBERED_RE.match(line):
                if book_title is None:
                    book_title = line
                    entries.append(
                        _matika_entry(
                            line,
                            page=None,
                            kind="boo",
                            source_page=pdf_page,
                        )
                    )
                # Skip later running headers.
                pending_title = None
                dot_run = 0
                continue

            # New candidate title line.
            if pending_title and not dot_run:
                flush_structural(pending_title, pending_source)
            pending_title = line
            pending_source = pdf_page
            dot_run = 0

    if pending_title and not dot_run:
        flush_structural(pending_title, pending_source)

    return entries


def fallback_kind(seg: dict, text: str) -> tuple[str | None, bool]:
    """
    Return (heading_kind, in_toc) when no Mātikā match applies.

    ``in_toc`` is True only for edition title stack (nik/boo) so front-matter
    titles still enter the memoir TOC when absent from the Mātikā block.
    """
    st = seg.get("segment_type") or ""
    if st in {"namakkāraṃ", "niṭṭhitaṃ"} or _CLOSER_RE.search(text):
        return None, False
    if st == "piṭaka":
        return "nik", True
    if st == "gambhīra":
        return "boo", True
    if st == "chapter":
        if _MAJOR_VIBHANGA_RE.match(text.strip()):
            return "boo", False
        if (
            _KANDA_RE.search(text) or _KANDA_PEER_RE.search(text)
        ) and not re.search(r"sikkhāpada\b", text, re.I):
            return "cha", False
        if _RULE_RE.search(text) or re.search(r"sikkhāpada\b", text, re.I):
            return "h1", False
        return "cha", False
    if st == "title":
        if _CLOSER_RE.search(text):
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

    for ei in ordered_idxs:
        entry = entries[ei]
        best_i, best_score = None, 0.0
        for i in heading_idxs if entry.kind == "boo" else _candidates_for(entry):
            st = segments[i].get("segment_type")
            if entry.kind == "boo":
                if st not in {"gambhīra", "title", "chapter"}:
                    continue
                if i in used_exclusive:
                    continue
                score = _score_match(
                    normalize_title(entry.title), seg_norms[i]
                )
                if st == "gambhīra":
                    score += 15
            else:
                score = _score_entry_against_segment(
                    entry, segments[i], seg_norms[i]
                )
                parent, _, child_name = compound_parts(segments[i])
                # Non-compound exclusive: one entry per segment unless compound.
                if not parent and i in used_exclusive:
                    score -= 40
            if score > best_score:
                best_i, best_score = i, score
        threshold = 50.0 if entry.kind == "boo" else 40.0
        if best_i is not None and best_score >= threshold:
            entry_to_seg[ei] = best_i
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
        entries = parse_matika(pages)
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
