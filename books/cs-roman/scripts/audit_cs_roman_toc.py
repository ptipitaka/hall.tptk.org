#!/usr/bin/env python3
"""Audit generated CS Roman Thai PDF contents against each source Mātikā.

The audit reads the source PDF again, rather than trusting the existing
``matika.json`` alone.  It then verifies both generated modes:

* PDF outline/bookmarks: completeness, order, title and hierarchy
* printed Mātikā pages: completeness, order, indentation and page references
* sync page references: equality with the printed page in the source Mātikā

Outputs are a detailed JSON file and a concise Thai Markdown report.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
import unicodedata
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Any

import fitz

from paths import BOOKS

from assign_cs_roman_heading_levels import (
    extract_matika_pages,
    parse_matika,
)
from cs_roman_text import roman_to_thai
from extract_cs_roman_pdf import detect_content_start


KIND_TO_LEVEL = {
    "nik": 1,
    "boo": 1,
    "cha": 2,
    "h1": 3,
    "h2": 4,
    "h3": 5,
    "h4": 6,
    "h5": 6,
    "h6": 6,
}

LEADER_PAGE_RE = re.compile(r"(?:\.\s*){2,}(\d+)\s*$")
PLAIN_PAGE_RE = re.compile(r"^(.*?)\s+(\d+)\s*$")
CHROME_PAGE_RANGE_RE = re.compile(r"^\.{2,}\s*[\d\s-]+$")
BARE_PAGE_RANGE_RE = re.compile(r"^\d+(?:-\d+){1,}$")
PATTHANA_RUNNING_RE = re.compile(
    r"^Paṭṭhānapāḷi\s+(?:paṭhama|dutiya|tatiya|catuttha)bhāga$",
    re.IGNORECASE,
)
INLINE_LEADER_MULTI_PAGE_RE = re.compile(
    r"^\s*(?:\.\s*){2,}(\d+(?:-\d+)+)\s*$"
)
BARE_MULTI_PAGE_RE = re.compile(r"^\s*(\d+(?:-\d+){2,})\s*$")
READING_FOLIO_RE = re.compile(r"ฉ\s*\.\s*(\d+)")


def normalized_title(value: object) -> str:
    """Unicode-stable comparison key insensitive to spacing/punctuation."""
    text = unicodedata.normalize("NFC", str(value or ""))
    # Source parsing preserves TeX-generation spacing/note markers, while PDF
    # outlines intentionally strip them.  They are formatting, not title text.
    text = re.sub(r"\{\{(?:n\d+|\*|\+|sp1|sp3)\}\}", "", text)
    return "".join(
        ch
        for ch in text
        if unicodedata.category(ch)[0] in {"L", "M", "N"}
    ).casefold()


def expected_thai_title(entry: dict[str, Any]) -> str:
    title = roman_to_thai(re.sub(r"\s+", " ", str(entry.get("title") or "").strip()))
    section_no = entry.get("section_no")
    if section_no is not None and section_no != "":
        title = f"{section_no}. {title}"
    return title


def is_source_chrome(entry: dict[str, Any]) -> bool:
    """True for running headers / orphan leader ranges, not TOC entries."""
    title = re.sub(r"\s+", " ", str(entry.get("title") or "").strip())
    folded = unicodedata.normalize("NFC", title).casefold()
    if CHROME_PAGE_RANGE_RE.fullmatch(title):
        return True
    if BARE_PAGE_RANGE_RE.fullmatch(title):
        return True
    if folded in {"matikā", "mātikā"}:
        return True
    return False


def filter_source_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove source chrome while retaining one real Paṭṭhāna book title."""
    has_generic_patthana = any(
        re.fullmatch(
            r"Paṭṭhānapāḷi",
            re.sub(r"\s+", " ", str(row.get("title") or "").strip()),
            re.IGNORECASE,
        )
        for row in rows
    )
    kept: list[dict[str, Any]] = []
    seen_full_patthana = False
    seen_book_running: set[str] = set()
    book_running_re = re.compile(r".+pāḷi$", re.IGNORECASE)
    for row in rows:
        if is_source_chrome(row):
            continue
        title = re.sub(r"\s+", " ", str(row.get("title") or "").strip())
        if PATTHANA_RUNNING_RE.fullmatch(title):
            # If the generic Paṭṭhānapāḷi title already exists (later parts),
            # every "... <ordinal>bhāga" occurrence is a running header.
            # Early parts have no generic title, so retain the first as the
            # book row and ignore later page headers.
            if has_generic_patthana or seen_full_patthana:
                continue
            seen_full_patthana = True
        # Repeated bare / compound ``…pāḷi`` chrome (Paṭṭhāna part 5).
        if book_running_re.fullmatch(title) and not re.match(r"^\d+\.", title):
            folded = normalized_title(title)
            if folded in seen_book_running:
                continue
            seen_book_running.add(folded)
        kept.append(row)
    return kept


def repair_source_matika_pages(
    pages: list[tuple[int, str]],
) -> tuple[list[tuple[int, str]], int]:
    """Repair page-list lines that the project parser otherwise treats as titles.

    CS Roman Mātikā sometimes prints one entry against several disjoint pages,
    e.g. ``Sahetukaduka ... 21-30-38``.  PDF text extraction can put
    ``... 21-30-38`` on one logical line.  The production parser accepts only
    a single page or a two-number range, so it overwrites the pending title.
    For auditing completeness, anchor such an entry on its first page.
    """
    repaired_pages: list[tuple[int, str]] = []
    repair_count = 0
    for page_no, text in pages:
        lines: list[str] = []
        for line in text.splitlines():
            match = INLINE_LEADER_MULTI_PAGE_RE.fullmatch(line)
            if match is None:
                match = BARE_MULTI_PAGE_RE.fullmatch(line)
            if match is not None:
                lines.append(match.group(1).split("-", 1)[0])
                repair_count += 1
            else:
                lines.append(line)
        repaired_pages.append((page_no, "\n".join(lines)))
    return repaired_pages, repair_count


def source_entries(source_pdf: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    doc = fitz.open(source_pdf)
    try:
        content_start = detect_content_start(doc)
        pages = extract_matika_pages(doc, content_start=content_start)
        repaired_pages, page_list_repair_count = repair_source_matika_pages(pages)
        parsed = [asdict(row) for row in parse_matika(repaired_pages)]
        entries = filter_source_rows(parsed)
        meta = {
            "pdf_pages": len(doc),
            "content_start_pdf_page": content_start,
            "matika_pdf_pages": [page for page, _ in pages],
            "ignored_source_chrome_count": len(parsed) - len(entries),
            "repaired_page_list_count": page_list_repair_count,
        }
    finally:
        doc.close()
    return entries, meta


def source_key(entry: dict[str, Any]) -> tuple[object, ...]:
    return (
        normalized_title(entry.get("title")),
        entry.get("section_no"),
        entry.get("page"),
        entry.get("kind"),
    )


def align_titles(
    expected: list[dict[str, Any]], actual: list[dict[str, Any]]
) -> tuple[list[tuple[int, int]], list[int], list[int], bool]:
    expected_keys = [normalized_title(row["title"]) for row in expected]
    actual_keys = [normalized_title(row["title"]) for row in actual]

    # Exact longest-common-subsequence alignment.  Mātikā contains many
    # repeated generic titles (Paññatti, Uddānagāthā, ...); SequenceMatcher's
    # popularity heuristic can shift an entire repeated run after one missing
    # row and falsely report dozens of changed titles.
    n, m = len(expected_keys), len(actual_keys)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            if expected_keys[i] == actual_keys[j]:
                dp[i][j] = 1 + dp[i + 1][j + 1]
            else:
                dp[i][j] = max(dp[i + 1][j], dp[i][j + 1])

    matched: list[tuple[int, int]] = []
    missing: list[int] = []
    extra: list[int] = []
    i = j = 0
    while i < n and j < m:
        if expected_keys[i] == actual_keys[j]:
            matched.append((i, j))
            i += 1
            j += 1
        elif dp[i + 1][j] >= dp[i][j + 1]:
            missing.append(i)
            i += 1
        else:
            extra.append(j)
            j += 1
    missing.extend(range(i, n))
    extra.extend(range(j, m))
    reordered = (
        Counter(expected_keys) == Counter(actual_keys) and expected_keys != actual_keys
    )
    return matched, missing, extra, reordered


def parse_printed_toc(doc: fitz.Document, front_pages: int) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    layout_issues: list[str] = []
    for page_index in range(max(front_pages, 0)):
        page = doc[page_index]
        blocks = sorted(page.get_text("blocks"), key=lambda block: (block[1], block[0]))
        previous_bottom: float | None = None
        for block in blocks:
            x0, y0, x1, y1, raw = block[:5]
            text = " ".join(str(raw).split())
            if not text:
                continue
            if "\ufffd" in text:
                layout_issues.append(
                    f"หน้า PDF {page_index + 1}: พบอักขระทดแทน U+FFFD"
                )
            if x0 < -0.5 or y0 < -0.5 or x1 > page.rect.width + 0.5 or y1 > page.rect.height + 0.5:
                layout_issues.append(
                    f"หน้า PDF {page_index + 1}: บล็อกข้อความล้นกรอบหน้า"
                )
            leader = LEADER_PAGE_RE.search(text)
            if leader:
                title = text[: leader.start()].rstrip(" .")
                page_ref = int(leader.group(1))
            else:
                plain = PLAIN_PAGE_RE.match(text)
                if not plain or normalized_title(plain.group(1)) == normalized_title("มาติกา"):
                    continue
                title = plain.group(1).rstrip(" .")
                page_ref = int(plain.group(2))
            if not title:
                continue
            if previous_bottom is not None and y0 < previous_bottom - 0.75:
                layout_issues.append(
                    f"หน้า PDF {page_index + 1}: บรรทัดสารบัญซ้อนกันใกล้ '{title}'"
                )
            previous_bottom = max(previous_bottom or y1, y1)
            rows.append(
                {
                    "title": title,
                    "page_ref": page_ref,
                    "physical_page": page_index + 1,
                    "x0": round(float(x0), 2),
                    "bbox": [round(float(v), 2) for v in (x0, y0, x1, y1)],
                }
            )
    return rows, sorted(set(layout_issues))


def reading_folio_contexts(
    doc: fitz.Document, front_pages: int
) -> tuple[dict[int, list[int]], dict[str, Any]]:
    """Map physical PDF page -> source folios active/touched on that page.

    Reading mode may place more than one ``ฉ.N`` marker on a physical page,
    and a source folio may continue onto a later physical page without
    repeating its marker.  Carrying the last marker forward models both cases.
    """
    contexts: dict[int, list[int]] = {}
    marker_pages: dict[int, list[int]] = {}
    active: int | None = None
    all_markers: list[int] = []
    for page_index in range(front_pages, len(doc)):
        page = doc[page_index]
        markers: list[int] = []
        blocks = sorted(page.get_text("blocks"), key=lambda block: (block[1], block[0]))
        for block in blocks:
            markers.extend(int(value) for value in READING_FOLIO_RE.findall(block[4]))
        touched: set[int] = set()
        if active is not None:
            touched.add(active)
        touched.update(markers)
        if markers:
            active = markers[-1]
            all_markers.extend(markers)
            marker_pages[page_index + 1] = markers
        contexts[page_index + 1] = sorted(touched)

    regressions = [
        {"previous": previous, "current": current}
        for previous, current in zip(all_markers, all_markers[1:])
        if current < previous
    ]
    gaps = [
        {"previous": previous, "current": current}
        for previous, current in zip(all_markers, all_markers[1:])
        if current > previous + 1
    ]
    return contexts, {
        "marker_count": len(all_markers),
        "distinct_marker_count": len(set(all_markers)),
        "first_marker": all_markers[0] if all_markers else None,
        "last_marker": all_markers[-1] if all_markers else None,
        "regressions": regressions,
        "gaps": gaps,
        "marker_pages": marker_pages,
    }


def short_entry(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        key: entry.get(key)
        for key in ("title", "roman_title", "kind", "level", "page", "page_ref", "pdf_page")
        if entry.get(key) is not None
    }


def inspect_generated_pdf(
    pdf_path: Path,
    expected: list[dict[str, Any]],
    *,
    mode: str,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": str(pdf_path),
        "mode": mode,
        "exists": pdf_path.is_file(),
    }
    if not pdf_path.is_file():
        result["status"] = "FAIL"
        result["issues"] = ["ไม่พบไฟล์ PDF"]
        return result

    doc = fitz.open(pdf_path)
    try:
        outline_raw = doc.get_toc(simple=True)
        outline = [
            {"level": int(level), "title": title, "pdf_page": int(page)}
            for level, title, page in outline_raw
        ]
        # Generated front matter uses lower-case Roman page labels; body pages
        # restart at Arabic 1.  Bookmark destinations are not suitable for
        # finding the boundary because a bad anchor can point far into the body.
        front_pages = 0
        for page in doc:
            if str(page.get_label()).isdigit():
                break
            front_pages += 1
        printed, layout_issues = parse_printed_toc(doc, front_pages)
        if mode in ("reading", "printing"):
            folio_contexts, folio_stats = reading_folio_contexts(doc, front_pages)
        else:
            folio_contexts, folio_stats = {}, {}

        expected_for_compare = [
            {
                "title": expected_thai_title(row),
                "roman_title": row.get("title"),
                "kind": row.get("kind"),
                "level": KIND_TO_LEVEL.get(str(row.get("kind"))),
                "page": row.get("page"),
            }
            for row in expected
        ]

        eo_pairs, missing_idx, extra_idx, reordered = align_titles(
            expected_for_compare, outline
        )
        outline_title_mismatches: list[dict[str, Any]] = []
        source_page_mismatches: list[dict[str, Any]] = []
        reading_folio_mismatches: list[dict[str, Any]] = []
        for expected_i, actual_i in eo_pairs:
            exp = expected_for_compare[expected_i]
            act = outline[actual_i]
            if normalized_title(exp["title"]) != normalized_title(act["title"]):
                outline_title_mismatches.append(
                    {"expected": short_entry(exp), "actual": short_entry(act)}
                )
                continue
            if mode == "sync" and exp.get("page") is not None:
                destination = act["pdf_page"]
                label = (
                    doc[destination - 1].get_label()
                    if 1 <= destination <= len(doc)
                    else ""
                )
                if label != str(exp["page"]):
                    source_page_mismatches.append(
                        {
                            "title": exp["title"],
                            "source_page": exp["page"],
                            "destination_pdf_page": destination,
                            "destination_label": label,
                        }
                    )
            if mode in ("reading", "printing") and exp.get("page") is not None:
                destination = act["pdf_page"]
                contexts = folio_contexts.get(destination, [])
                if int(exp["page"]) not in contexts:
                    reading_folio_mismatches.append(
                        {
                            "title": exp["title"],
                            "source_page": exp["page"],
                            "destination_pdf_page": destination,
                            "destination_label": (
                                doc[destination - 1].get_label()
                                if 1 <= destination <= len(doc)
                                else ""
                            ),
                            "folio_contexts_on_destination": contexts,
                        }
                    )

        op_pairs, printed_missing_idx, printed_extra_idx, printed_reordered = align_titles(
            outline, printed
        )
        ep_pairs, source_printed_missing_idx, source_printed_extra_idx, source_printed_reordered = align_titles(
            expected_for_compare, printed
        )
        printed_title_mismatches: list[dict[str, Any]] = []
        printed_page_mismatches: list[dict[str, Any]] = []
        printed_source_page_mismatches: list[dict[str, Any]] = []
        indent_samples: dict[tuple[int, int], list[float]] = {}
        for outline_i, printed_i in op_pairs:
            out_row = outline[outline_i]
            print_row = printed[printed_i]
            if normalized_title(out_row["title"]) != normalized_title(print_row["title"]):
                printed_title_mismatches.append(
                    {
                        "outline": short_entry(out_row),
                        "printed": short_entry(print_row),
                    }
                )
                continue
            destination = out_row["pdf_page"]
            label = (
                doc[destination - 1].get_label()
                if 1 <= destination <= len(doc)
                else ""
            )
            page_ref_matches = (
                str(label).isdigit() and print_row["page_ref"] == int(label)
            )
            if not page_ref_matches:
                printed_page_mismatches.append(
                    {
                        "title": out_row["title"],
                        "printed_page_ref": print_row["page_ref"],
                        "destination_pdf_page": destination,
                        "destination_label": label,
                    }
                )
        # PDF bookmark levels collapse when a parent level is absent, so they
        # cannot be compared numerically to h1/h2/h3.  Printed indentation is
        # stable and directly represents the intended Mātikā hierarchy.
        for expected_i, printed_i in ep_pairs:
            exp = expected_for_compare[expected_i]
            print_row = printed[printed_i]
            if normalized_title(exp["title"]) != normalized_title(print_row["title"]):
                continue
            level = exp.get("level")
            if level is not None:
                parity = print_row["physical_page"] % 2
                indent_samples.setdefault((level, parity), []).append(print_row["x0"])
            if (
                mode == "sync"
                and exp.get("page") is not None
                and print_row["page_ref"] != int(exp["page"])
            ):
                printed_source_page_mismatches.append(
                    {
                        "title": exp["title"],
                        "source_page": exp["page"],
                        "printed_page_ref": print_row["page_ref"],
                        "printed_toc_pdf_page": print_row["physical_page"],
                    }
                )

        indent_medians_raw = {
            key: round(statistics.median(values), 2)
            for key, values in sorted(indent_samples.items())
            if values
        }
        indent_medians = {
            f"level-{level}-parity-{parity}": median
            for (level, parity), median in indent_medians_raw.items()
        }
        hierarchy_indent_issues: list[str] = []
        for parity in (0, 1):
            levels = sorted(
                level for level, row_parity in indent_medians_raw if row_parity == parity
            )
            for previous, current in zip(levels, levels[1:]):
                previous_median = indent_medians_raw[(previous, parity)]
                current_median = indent_medians_raw[(current, parity)]
                if current_median <= previous_median + 0.5:
                    hierarchy_indent_issues.append(
                        f"หน้าคู่คี่ {parity}: ระดับ {current} ไม่ได้เยื้องมากกว่า "
                        f"ระดับ {previous} ({current_median} <= {previous_median})"
                    )
        for expected_i, printed_i in ep_pairs:
            out_row = expected_for_compare[expected_i]
            print_row = printed[printed_i]
            parity = print_row["physical_page"] % 2
            median = indent_medians_raw.get((out_row["level"], parity))
            if median is not None and abs(print_row["x0"] - median) > 2.0:
                hierarchy_indent_issues.append(
                    f"หน้า PDF {print_row['physical_page']}: '{print_row['title']}' "
                    f"เยื้อง x={print_row['x0']} ต่างจากระดับ {out_row['level']} "
                    f"(ค่ากลาง {median})"
                )

        missing = [short_entry(expected_for_compare[i]) for i in missing_idx]
        extra = [short_entry(outline[i]) for i in extra_idx]
        printed_missing = [short_entry(outline[i]) for i in printed_missing_idx]
        printed_extra = [short_entry(printed[i]) for i in printed_extra_idx]
        source_printed_missing = [
            short_entry(expected_for_compare[i]) for i in source_printed_missing_idx
        ]
        source_printed_extra = [
            short_entry(printed[i]) for i in source_printed_extra_idx
        ]

        issues: list[str] = []
        if missing:
            issues.append(f"สารบัญขาด {len(missing)} รายการจากต้นฉบับ")
        if extra:
            issues.append(f"สารบัญเกิน {len(extra)} รายการ")
        if reordered:
            issues.append("ลำดับรายการ bookmark ไม่ตรงต้นฉบับ")
        if outline_title_mismatches:
            issues.append(f"ชื่อรายการ bookmark ไม่ตรง {len(outline_title_mismatches)} รายการ")
        if source_page_mismatches:
            issues.append(f"ปลายทาง bookmark แบบ sync ไม่ตรงหน้าต้นฉบับ {len(source_page_mismatches)} รายการ")
        if reading_folio_mismatches:
            issues.append(
                "ปลายทาง reading ไม่อยู่ในบริบท margin ฉ.N ของต้นฉบับ "
                f"{len(reading_folio_mismatches)} รายการ"
            )
        if source_printed_missing:
            issues.append(f"รายการที่พิมพ์บนหน้าสารบัญขาดจากต้นฉบับ {len(source_printed_missing)} รายการ")
        if source_printed_extra:
            issues.append(f"รายการที่พิมพ์บนหน้าสารบัญเกินต้นฉบับ {len(source_printed_extra)} รายการ")
        if source_printed_reordered:
            issues.append("ลำดับรายการที่พิมพ์ไม่ตรงต้นฉบับ")
        if printed_source_page_mismatches:
            issues.append(f"เลขหน้าที่พิมพ์ใน sync ไม่ตรงต้นฉบับ {len(printed_source_page_mismatches)} รายการ")
        if printed_missing:
            issues.append(f"รายการที่พิมพ์บนหน้าสารบัญขาดจาก bookmark {len(printed_missing)} รายการ")
        if printed_extra:
            issues.append(f"รายการที่พิมพ์บนหน้าสารบัญเกิน bookmark {len(printed_extra)} รายการ")
        if printed_reordered:
            issues.append("ลำดับรายการที่พิมพ์ไม่ตรง bookmark")
        if printed_title_mismatches:
            issues.append(f"ชื่อรายการที่พิมพ์ไม่ตรง bookmark {len(printed_title_mismatches)} รายการ")
        if printed_page_mismatches:
            issues.append(f"เลขหน้าที่พิมพ์ไม่ตรงปลายทาง {len(printed_page_mismatches)} รายการ")
        if hierarchy_indent_issues:
            issues.append(f"การเยื้องระดับโครงสร้างผิดปกติ {len(hierarchy_indent_issues)} จุด")
        issues.extend(layout_issues)

        result.update(
            {
                "status": "FAIL" if issues else "PASS",
                "pdf_pages": len(doc),
                "front_matter_pages": front_pages,
                "expected_count": len(expected_for_compare),
                "outline_count": len(outline),
                "printed_count": len(printed),
                "issues": issues,
                "missing_from_source": missing,
                "extra_vs_source": extra,
                "outline_reordered": reordered,
                "outline_title_mismatches": outline_title_mismatches,
                "sync_source_page_mismatches": source_page_mismatches,
                "reading_folio_mismatches": reading_folio_mismatches,
                "reading_folio_stats": folio_stats,
                "source_printed_missing": source_printed_missing,
                "source_printed_extra": source_printed_extra,
                "source_printed_reordered": source_printed_reordered,
                "sync_printed_source_page_mismatches": printed_source_page_mismatches,
                "printed_missing_vs_outline": printed_missing,
                "printed_extra_vs_outline": printed_extra,
                "printed_reordered": printed_reordered,
                "printed_title_mismatches": printed_title_mismatches,
                "printed_page_mismatches": printed_page_mismatches,
                "indent_medians": indent_medians,
                "hierarchy_indent_issues": sorted(set(hierarchy_indent_issues)),
                "layout_issues": layout_issues,
            }
        )
    finally:
        doc.close()
    return result


def markdown_report(audit: dict[str, Any]) -> str:
    volumes = audit["volumes"]
    failed = [row for row in volumes if row["status"] == "FAIL"]
    def has_list_problem(row: dict[str, Any]) -> bool:
        result = row["generated"]["printing"]
        return any(
            (
                result.get("missing_from_source"),
                result.get("extra_vs_source"),
                result.get("outline_reordered"),
                result.get("source_printed_missing"),
                result.get("source_printed_extra"),
                result.get("source_printed_reordered"),
                result.get("printed_missing_vs_outline"),
                result.get("hierarchy_indent_issues"),
            )
        )

    list_problem = [row for row in volumes if has_list_problem(row)]
    list_complete = [row for row in volumes if not has_list_problem(row)]
    reference_only = [
        row
        for row in list_complete
        if row["status"] == "FAIL"
    ]
    reading_folio_problem = [
        row
        for row in volumes
        if row["generated"]["printing"].get("reading_folio_mismatches")
    ]
    reading_folio_mismatch_count = sum(
        len(row["generated"]["printing"].get("reading_folio_mismatches", []))
        for row in volumes
    )
    lines = [
        "# รายงานตรวจสอบสารบัญ PDF ชุด CS Roman",
        "",
        f"- ตรวจเมื่อ: {audit['audited_at']}",
        f"- ขอบเขต: ต้นฉบับ {len(volumes)} เล่ม; PDF ผลลัพธ์ {len(volumes) * 2} ไฟล์ (sync + printing)",
        "- เกณฑ์: ความครบถ้วน, ลำดับ, ชื่อรายการ, ระดับโครงสร้าง, รายการที่พิมพ์จริง, เลขหน้าอ้างอิง และการเยื้อง",
        f"- ผลรวม: ผ่าน {len(volumes) - len(failed)} เล่ม; พบความผิดปกติ {len(failed)} เล่ม",
        f"- รายการ/ลำดับ/โครงสร้างครบทั้งสองโหมด: {len(list_complete)} เล่ม "
        f"(ในจำนวนนี้ {len(reference_only)} เล่มผิดเฉพาะการอ้างอิงหน้า)",
        f"- รายการขาด/เกินหรือพิมพ์ไม่ครบ: {len(list_problem)} เล่ม",
        f"- ปลายทาง printing ไม่ตรงบริบทเลขริมกระดาษ `ฉ.N`: "
        f"{len(reading_folio_problem)} เล่ม รวม {reading_folio_mismatch_count} รายการ",
        "- ไม่พบการสลับลำดับหรือการเยื้องระดับโครงสร้างผิดในรายการที่ปรากฏ",
        "",
        "## สรุปรายเล่ม",
        "",
        "| เล่ม | ต้นฉบับ | sync | printing | ผลรวม |",
        "|---|---:|---:|---:|---|",
    ]
    for row in volumes:
        sync = row["generated"]["sync"]
        printing = row["generated"]["printing"]
        lines.append(
            f"| {row['volume']} | {row['source_entry_count']} รายการ | "
            f"{sync.get('outline_count', 0)}/{sync.get('printed_count', 0)} "
            f"({'ผ่าน' if sync['status'] == 'PASS' else 'ผิดปกติ'}) | "
            f"{printing.get('outline_count', 0)}/{printing.get('printed_count', 0)} "
            f"({'ผ่าน' if printing['status'] == 'PASS' else 'ผิดปกติ'}) | "
            f"{'ผ่าน' if row['status'] == 'PASS' else 'ตรวจพบปัญหา'} |"
        )

    if failed:
        lines.extend(["", "## เล่มที่พบความผิดปกติ", ""])
        for row in failed:
            lines.extend([f"### {row['volume']}", ""])
            if row["source_vs_matika_issues"]:
                lines.append(
                    "- ข้อมูล `matika.json` ไม่ตรงกับการสกัดต้นฉบับใหม่: "
                    + "; ".join(row["source_vs_matika_issues"])
                )
            for mode in ("sync", "printing"):
                result = row["generated"][mode]
                if result["status"] == "PASS":
                    continue
                lines.append(f"- `{mode}`: " + "; ".join(result["issues"]))
                if result.get("missing_from_source"):
                    for item in result["missing_from_source"]:
                        roman = item.get("roman_title") or item.get("title")
                        detail = f"  - ขาด: `{roman}`"
                        if item.get("kind"):
                            detail += f" ({item['kind']})"
                        if item.get("page") is not None:
                            detail += f", หน้า {item['page']}"
                        lines.append(detail)
                for mismatch in result.get("sync_source_page_mismatches", [])[:20]:
                    lines.append(
                        f"  - ปลายทาง bookmark sync ผิด: `{mismatch['title']}` "
                        f"ต้นฉบับ {mismatch['source_page']} "
                        f"แต่ปลายทางมี label `{mismatch['destination_label']}`"
                    )
                for mismatch in result.get("sync_printed_source_page_mismatches", [])[:20]:
                    lines.append(
                        f"  - เลขหน้า sync ที่พิมพ์ผิด: `{mismatch['title']}` "
                        f"ต้นฉบับ {mismatch['source_page']} "
                        f"แต่พิมพ์ {mismatch['printed_page_ref']}"
                    )
                for mismatch in result.get("reading_folio_mismatches", [])[:20]:
                    contexts = ", ".join(
                        f"ฉ.{value}"
                        for value in mismatch["folio_contexts_on_destination"]
                    ) or "ไม่พบ marker"
                    lines.append(
                        f"  - margin printing ผิด: `{mismatch['title']}` "
                        f"ต้นฉบับ ฉ.{mismatch['source_page']} แต่หน้าปลายทางอยู่ใน "
                        f"`{contexts}`"
                    )
                for mismatch in result.get("printed_page_mismatches", [])[:20]:
                    lines.append(
                        f"  - เลขหน้าที่พิมพ์ผิด: `{mismatch['title']}` "
                        f"พิมพ์ {mismatch['printed_page_ref']} "
                        f"แต่ปลายทาง label `{mismatch['destination_label']}`"
                    )
            lines.append("")

    lines.extend(
        [
            "## หมายเหตุวิธีตรวจ",
            "",
            "- รายการต้นฉบับถูกสกัดใหม่จากหน้า Mātikā ใน PDF ต้นฉบับทุกเล่มด้วยตัวถอด VZTime เดียวกับโครงการ",
            "- จำนวนในคอลัมน์ sync/printing แสดง `bookmark/รายการที่พิมพ์จริง`",
            "- PDF แบบ sync ต้องอ้างเลขหน้าเดียวกับต้นฉบับ ส่วน printing อนุญาตให้เลขหน้าเปลี่ยน แต่เลขที่พิมพ์ต้องชี้ไปยัง page label จริง",
            "- สำหรับ printing ปลายทางของรายการหน้า N ต้องอยู่บน physical page ที่มีหรือสืบเนื่องจาก margin marker `ฉ.N`",
            "- รายละเอียดดิบทุก mismatch อยู่ในไฟล์ JSON คู่กับรายงานนี้",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-json",
        type=Path,
        default=BOOKS / "research" / "toc_audit_2026-07-28.json",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=BOOKS / "research" / "toc_audit_2026-07-28.md",
    )
    args = parser.parse_args()

    volume_dirs = sorted(
        path
        for path in (BOOKS / "volumes").iterdir()
        if path.is_dir() and re.fullmatch(r"\d{2}[A-Za-z]+\d{2}", path.name)
    )
    audit: dict[str, Any] = {
        "schema_version": 1,
        "audited_at": "2026-07-28",
        "root": str(BOOKS),
        "volumes": [],
    }

    for volume_dir in volume_dirs:
        volume = volume_dir.name
        source_pdf = volume_dir / "source" / f"{volume}.pdf"
        stored_matika = volume_dir / "data" / "matika.json"
        if not source_pdf.is_file():
            source_rows: list[dict[str, Any]] = []
            source_meta: dict[str, Any] = {}
            source_issues = ["ไม่พบ PDF ต้นฉบับ"]
        else:
            source_rows, source_meta = source_entries(source_pdf)
            source_issues = []

        if not stored_matika.is_file():
            source_issues.append("ไม่พบ matika.json")
            stored_rows: list[dict[str, Any]] = []
        else:
            stored_rows_raw = json.loads(
                stored_matika.read_text(encoding="utf-8")
            ).get("entries", [])
            stored_rows = filter_source_rows(stored_rows_raw)
            source_keys = [source_key(row) for row in source_rows]
            stored_keys = [source_key(row) for row in stored_rows]
            if source_keys != stored_keys:
                source_issues.append(
                    f"ลำดับ/เนื้อหา matika.json ต่างจากต้นฉบับที่สกัดใหม่ "
                    f"(source={len(source_keys)}, data={len(stored_keys)})"
                )

        generated = {
            "sync": inspect_generated_pdf(
                volume_dir / "out" / f"{volume}.pdf",
                source_rows,
                mode="sync",
            ),
            "printing": inspect_generated_pdf(
                volume_dir / "out" / f"{volume}.printing.pdf",
                source_rows,
                mode="printing",
            ),
        }
        status = (
            "PASS"
            if not source_issues
            and all(row["status"] == "PASS" for row in generated.values())
            else "FAIL"
        )
        audit["volumes"].append(
            {
                "volume": volume,
                "status": status,
                "source_pdf": str(source_pdf),
                "source_entry_count": len(source_rows),
                "source_meta": source_meta,
                "stored_matika_count": len(stored_rows),
                "source_vs_matika_issues": source_issues,
                "generated": generated,
            }
        )
        print(
            f"{volume}: source={len(source_rows)} "
            f"sync={generated['sync'].get('outline_count', 0)}/"
            f"{generated['sync'].get('printed_count', 0)} "
            f"printing={generated['printing'].get('outline_count', 0)}/"
            f"{generated['printing'].get('printed_count', 0)} {status}"
        )

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(markdown_report(audit), encoding="utf-8")
    print(f"JSON -> {args.output_json}")
    print(f"Markdown -> {args.output_md}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
