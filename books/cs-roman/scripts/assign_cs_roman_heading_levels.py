"""
Assign heading_kind / in_toc to cs-roman segment JSON from the volume Mātikā.

Uses the printed Mātikā in the CS Roman PDF (same edition as segments) as the
primary TOC source. Kinds: nik | boo | cha | h1 | h2 | h3 | h4 | h5 | h6.
(nik/boo/cha = special stack; h1…h6 = generic section headers under cha.)

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
    r"\d+"
    r")$",
    re.IGNORECASE,
)
_BOOK_RUNNING_RE = re.compile(r"^.+pāḷi$", re.IGNORECASE)
_MATIKA_END_RE = re.compile(r"mātikā\s+niṭṭhit", re.IGNORECASE)
_NUMBERED_RE = re.compile(r"^(\d+)\.\s*(.+)$")
_KANDA_RE = re.compile(r"kaṇḍa\b", re.IGNORECASE)
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


@dataclass
class MatikaEntry:
    title: str
    page: int | None
    kind: str
    source_page: int  # 1-based PDF page in the Mātikā block


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


def classify_matika_title(title: str, *, has_page: bool) -> str:
    """Infer heading_kind from a Mātikā line (cha / h1 / h2)."""
    bare = _NUMBERED_RE.sub(r"\2", title.strip())
    numbered = bool(_NUMBERED_RE.match(title.strip()))
    if _KANDA_RE.search(bare):
        return "cha"
    if numbered and _RULE_RE.search(bare):
        return "h1"
    if numbered and not _SUB_HINT_RE.search(bare) and len(bare) <= 60:
        # e.g. "1. Paṭhamapārājika"
        return "h1"
    if has_page or _SUB_HINT_RE.search(bare):
        return "h2"
    if _RULE_RE.search(bare):
        return "h1"
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

    def flush_structural(title: str, source_page: int) -> None:
        kind = classify_matika_title(title, has_page=False)
        entries.append(
            MatikaEntry(title=title, page=None, kind=kind, source_page=source_page)
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
                elif re.fullmatch(r"\d+", line) and pending_title and dot_run:
                    entries.append(
                        MatikaEntry(
                            title=pending_title,
                            page=int(line),
                            kind=classify_matika_title(
                                pending_title, has_page=True
                            ),
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
                        MatikaEntry(
                            title=line,
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
    """
    st = seg.get("segment_type") or ""
    if st in {"namakkāraṃ", "niṭṭhitaṃ"} or _CLOSER_RE.search(text):
        return None, False
    if st == "piṭaka":
        return "nik", True
    if st == "gambhīra":
        return "boo", True
    if st == "chapter":
        if _KANDA_RE.search(text) and not re.search(
            r"sikkhāpada\b", text, re.I
        ):
            return "cha", True
        if _RULE_RE.search(text) or re.search(r"sikkhāpada\b", text, re.I):
            return "h1", True
        return "cha", True
    if st == "title":
        if _CLOSER_RE.search(text):
            return None, False
        if _RULE_RE.search(text) and not _SUB_HINT_RE.search(text):
            return "h1", True
        # Numbered rule-like short titles: Dutiyapārājika
        if re.search(
            r"(?:paṭhama|dutiya|tatiya|catuttha).+pārājika\b", text, re.I
        ):
            if "samatta" not in text.lower():
                return "h1", True
        if re.search(r"sikkhāpada\b", text, re.I):
            return "h1", True
        return "h2", True
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


def match_entries_to_segments(
    entries: list[MatikaEntry], segments: list[dict]
) -> tuple[dict[int, MatikaEntry], list[MatikaEntry], list[int]]:
    """
    Map segment index → best Mātikā entry.

    Returns (matched, unmatched_entries, unmatched_heading_indices).
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
    used_segs: set[int] = set()
    matched: dict[int, MatikaEntry] = {}
    unmatched_entries: list[MatikaEntry] = []

    # Prefer coarser kinds first so a combined heading like
    # "Paṭhamapārājika Sudinnabhāṇavāra" keeps h1, not h2.
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
    ordered = sorted(
        entries,
        key=lambda e: (
            kind_rank.get(e.kind, 9),
            0 if e.page is not None else 1,
            e.source_page,
            e.title,
        ),
    )

    for entry in ordered:
        if entry.kind == "boo":
            # Match gambhīra / book title segment once.
            best_i, best_score = None, 0.0
            for i in heading_idxs:
                if i in used_segs:
                    continue
                st = segments[i].get("segment_type")
                if st not in {"gambhīra", "title", "chapter"}:
                    continue
                score = _score_match(normalize_title(entry.title), seg_norms[i])
                if st == "gambhīra":
                    score += 15
                if score > best_score:
                    best_i, best_score = i, score
            if best_i is not None and best_score >= 50:
                matched[best_i] = entry
                used_segs.add(best_i)
            else:
                unmatched_entries.append(entry)
            continue

        en = normalize_title(entry.title)
        best_i, best_score = None, 0.0
        for i in heading_idxs:
            if i in used_segs:
                continue
            score = _score_match(en, seg_norms[i])
            if entry.page is not None:
                page = segments[i].get("page")
                if page == entry.page:
                    score += 25
                elif isinstance(page, int) and abs(page - entry.page) <= 1:
                    score += 10
                elif isinstance(page, int) and abs(page - entry.page) > 5:
                    score -= 20
            if score > best_score:
                best_i, best_score = i, score
        if best_i is not None and best_score >= 55:
            matched[best_i] = entry
            used_segs.add(best_i)
        else:
            unmatched_entries.append(entry)

    unmatched_heads = [i for i in heading_idxs if i not in used_segs]
    return matched, unmatched_entries, unmatched_heads


def assign_levels(
    data: dict,
    entries: list[MatikaEntry],
) -> tuple[dict, dict]:
    """Return (updated document, report stats)."""
    data = dict(data)
    segments = [dict(s) for s in (data.get("segments") or [])]
    matched, unmatched_entries, unmatched_heads = match_entries_to_segments(
        entries, segments
    )

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
        if i in matched:
            entry = matched[i]
            seg["heading_kind"] = entry.kind
            seg["in_toc"] = True
            # Drop prior weak-heading review when Mātikā confirms.
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
            seg["in_toc"] = in_toc
            if (
                st in {"chapter", "title"}
                and in_toc
                and i in unmatched_heads
                and "heading_level_unmatched_matika"
                not in (seg.get("review_reasons") or [])
            ):
                # Only flag when fallback had to guess and title looks soft.
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

    report = {
        "matika_entries": len(entries),
        "matika_matched_to_segments": len(matched),
        "matika_unmatched": len(unmatched_entries),
        "heading_segments_without_matika": len(unmatched_heads),
        "heading_kind_counts": dict(sorted(kind_counts.items())),
        "in_toc_count": toc_count,
        "review_flags_added": review_added,
        "unmatched_matika_sample": [asdict(e) for e in unmatched_entries[:40]],
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
    return ordered, report


def process_file(
    json_path: Path,
    pdf_path: Path,
    *,
    report_path: Path | None = None,
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
    data, report = assign_levels(data, entries)
    report["pdf"] = str(pdf_path).replace("\\", "/")
    report["json"] = str(json_path).replace("\\", "/")
    report["content_start_pdf_page"] = content_start
    report["matika_pdf_pages"] = [p for p, _ in pages]

    save_segments(json_path, data, normalize=True)
    if report_path is None:
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

    report = process_file(json_path, pdf_path, report_path=args.report)
    out_report = args.report or json_path.with_suffix(".heading-report.json")
    print(
        f"Mātikā {report['matika_entries']} entries "
        f"(PDF pages {report['matika_pdf_pages']}) -> "
        f"matched {report['matika_matched_to_segments']}, "
        f"kinds {report['heading_kind_counts']}, "
        f"in_toc={report['in_toc_count']}"
    )
    print(f"Updated {json_path}")
    print(f"Report  {out_report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
