# -*- coding: utf-8 -*-
"""Compare page-fill metrics: CS Roman source vs Thai rebuild (print-page sync).

Roman printed page N lives at PDF index (N + roman_offset - 1), default offset 23
(01Vin01: print 1 = PDF page 24).

Thai PDF may begin with front matter (e.g. มหาติกา/มาติกา). Printed page N is at
PDF index (N + thai_offset - 1); default thai_offset=1 for the generated TOC sheet.
"""
from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyMuPDF (fitz) is required: pip install pymupdf") from exc

from paths import BOOKS, SOURCE_DIR

DEFAULT_ROMAN = SOURCE_DIR / "01Vin01.pdf"
DEFAULT_THAI = BOOKS / "volumes" / "01Vin01" / "out" / "01Vin01.pdf"
DEFAULT_OUT = (
    BOOKS / "volumes" / "01Vin01" / "out" / "_ref_pages" / "layout_metrics.json"
)


def detect_thai_body_offset(doc: fitz.Document, max_scan: int = 30) -> int:
    """Return number of leading front-matter pages before arabic body page 1."""
    for index in range(min(max_scan, doc.page_count)):
        text = doc[index].get_text("text")
        head = "".join(text.splitlines()[:6])
        # Generated TOC title, or roman numerals only.
        if "มาติกา" in head and index == 0:
            continue
        if "วินยปิฏก" in head or "นโม" in head or "ปาราชิก" in head:
            return index
    return 0


def header_page_number(page: fitz.Page, header_cut: float = 75.0) -> int | None:
    """Best-effort printed page number from the running head band."""
    import re

    candidates: list[int] = []
    for block in page.get_text("dict")["blocks"]:
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            spans = line.get("spans", [])
            if not spans:
                continue
            x0, y0, x1, y1 = line["bbox"]
            if y0 >= header_cut:
                continue
            text = "".join(span["text"] for span in spans).strip()
            if re.fullmatch(r"\d{1,3}", text):
                candidates.append(int(text))
    if not candidates:
        return None
    # Prefer a single clear marker; if several, take the smallest (page nums).
    return min(candidates)


def build_thai_page_index_map(doc: fitz.Document) -> dict[int, int]:
    """Map printed page number → PDF index with the most body lines for that number.

    Overflow can create several physical sheets that share one printed page
    number; prefer the fullest sheet for density comparisons.
    """
    best: dict[int, tuple[int, int]] = {}
    for index in range(doc.page_count):
        num = header_page_number(doc[index])
        if num is None:
            continue
        metrics = page_metrics(doc[index])
        lines = metrics["lines"] if metrics else 0
        prev = best.get(num)
        if prev is None or lines > prev[0]:
            best[num] = (lines, index)
    return {num: index for num, (_lines, index) in best.items()}


def page_metrics(page: fitz.Page, header_cut: float = 75.0, foot_cut: float = 640.0) -> dict | None:
    height = page.rect.height
    rows: list[dict] = []
    for block in page.get_text("dict")["blocks"]:
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            spans = line.get("spans", [])
            if not spans:
                continue
            text = "".join(span["text"] for span in spans).strip()
            if not text:
                continue
            x0, y0, x1, y1 = line["bbox"]
            rows.append(
                {
                    "y0": y0,
                    "y1": y1,
                    "x0": x0,
                    "x1": x1,
                    "size": spans[0]["size"],
                    "text": text,
                }
            )
    if not rows:
        return None

    body = [row for row in rows if header_cut <= row["y0"] < foot_cut]
    if not body:
        body = [row for row in rows if row["y0"] >= header_cut]
    if not body:
        return None

    ys = sorted({round(row["y0"], 1) for row in body})
    deltas = [round(ys[i + 1] - ys[i], 1) for i in range(len(ys) - 1)]
    lead_counts = Counter(delta for delta in deltas if 12.0 < delta < 24.0)
    modal_lead = lead_counts.most_common(1)[0][0] if lead_counts else None
    first_y = min(row["y0"] for row in body)
    last_y = max(row["y1"] for row in body)
    bottom_gap = height - last_y
    # Fill relative to a full Roman prose page ending near y≈620.
    fill_to_620 = min(1.0, (last_y - 90.0) / (620.0 - 90.0)) if last_y > 90 else 0.0
    widths = [row["x1"] - row["x0"] for row in body]
    return {
        "lines": len(ys),
        "first_y": round(first_y, 1),
        "last_y": round(last_y, 1),
        "bottom_gap": round(bottom_gap, 1),
        "modal_lead": modal_lead,
        "fill_to_620": round(fill_to_620, 3),
        "sizes": sorted({round(row["size"], 1) for row in body})[:8],
        "avg_line_width": round(statistics.mean(widths), 1) if widths else 0.0,
        "page_h": round(height, 3),
        "page_w": round(page.rect.width, 3),
    }


def compare_pages(
    roman_path: Path,
    thai_path: Path,
    roman_offset: int = 23,
    thai_offset: int | None = None,
    min_roman_lines: int = 15,
    pages: list[int] | None = None,
    match_by_header: bool = True,
) -> dict:
    roman = fitz.open(roman_path)
    thai = fitz.open(thai_path)
    if thai_offset is None:
        thai_offset = detect_thai_body_offset(thai)
    thai_by_num = build_thai_page_index_map(thai) if match_by_header else {}
    if pages is None:
        if match_by_header and thai_by_num:
            max_print = min(max(thai_by_num), roman.page_count - roman_offset)
        else:
            max_print = min(thai.page_count - thai_offset, roman.page_count - roman_offset)
        pages = list(range(1, max_print + 1))

    rows: list[dict] = []
    for print_page in pages:
        roman_index = print_page + roman_offset - 1
        if match_by_header and thai_by_num:
            thai_index = thai_by_num.get(print_page)
            if thai_index is None:
                continue
        else:
            thai_index = print_page + thai_offset - 1
        if roman_index >= roman.page_count or thai_index >= thai.page_count:
            continue
        roman_m = page_metrics(roman[roman_index])
        thai_m = page_metrics(thai[thai_index])
        if not roman_m or not thai_m:
            continue
        if roman_m["lines"] < min_roman_lines:
            continue
        ratio = thai_m["lines"] / roman_m["lines"] if roman_m["lines"] else 0.0
        rows.append(
            {
                "print_page": print_page,
                "thai_pdf_index": thai_index,
                "roman": roman_m,
                "thai": thai_m,
                "line_ratio": round(ratio, 3),
                "bottom_gap_delta": round(thai_m["bottom_gap"] - roman_m["bottom_gap"], 1),
                "last_y_delta": round(thai_m["last_y"] - roman_m["last_y"], 1),
            }
        )

    if not rows:
        return {
            "roman_pdf": str(roman_path),
            "thai_pdf": str(thai_path),
            "roman_offset": roman_offset,
            "thai_offset": thai_offset,
            "match_by_header": match_by_header,
            "n": 0,
            "summary": {},
            "pages": [],
        }

    ratios = [row["line_ratio"] for row in rows]
    gaps_r = [row["roman"]["bottom_gap"] for row in rows]
    gaps_t = [row["thai"]["bottom_gap"] for row in rows]
    lines_r = [row["roman"]["lines"] for row in rows]
    lines_t = [row["thai"]["lines"] for row in rows]
    leads_r = [row["roman"]["modal_lead"] for row in rows if row["roman"]["modal_lead"]]
    leads_t = [row["thai"]["modal_lead"] for row in rows if row["thai"]["modal_lead"]]

    prose = [
        row
        for row in rows
        if 20 <= row["roman"]["lines"] <= 35 and row["thai"]["lines"] >= 10
    ]
    prose_ratios = [row["line_ratio"] for row in prose]
    prose_median = statistics.median(prose_ratios) if prose_ratios else None
    summary = {
        "n": len(rows),
        "median_line_ratio": round(statistics.median(ratios), 3),
        "mean_line_ratio": round(statistics.mean(ratios), 3),
        "median_lines_roman": statistics.median(lines_r),
        "median_lines_thai": statistics.median(lines_t),
        "median_bottom_gap_roman": round(statistics.median(gaps_r), 1),
        "median_bottom_gap_thai": round(statistics.median(gaps_t), 1),
        "pct_thai_under_0_90": round(100 * sum(1 for r in ratios if r < 0.90) / len(ratios), 1),
        "pct_thai_over_1_05": round(100 * sum(1 for r in ratios if r > 1.05) / len(ratios), 1),
        "modal_lead_roman_median": statistics.median(leads_r) if leads_r else None,
        "modal_lead_thai_median": statistics.median(leads_t) if leads_t else None,
        "prose_n": len(prose),
        "prose_median_line_ratio": round(prose_median, 3) if prose_median is not None else None,
        "prose_pct_in_0_95_1_05": (
            round(100 * sum(1 for r in prose_ratios if 0.95 <= r <= 1.05) / len(prose_ratios), 1)
            if prose_ratios
            else None
        ),
        "target_line_ratio_ok": (
            prose_median is not None and 0.95 <= prose_median <= 1.05
        ),
    }
    return {
        "roman_pdf": str(roman_path),
        "thai_pdf": str(thai_path),
        "roman_offset": roman_offset,
        "thai_offset": thai_offset,
        "match_by_header": match_by_header,
        "n": len(rows),
        "summary": summary,
        "pages": rows,
    }


def print_summary(report: dict) -> None:
    summary = report.get("summary") or {}
    if not summary:
        print("No comparable pages.")
        return
    print(
        "offsets roman={roman_offset} thai={thai_offset}".format(
            roman_offset=report.get("roman_offset"),
            thai_offset=report.get("thai_offset"),
        )
    )
    print(
        "n={n} median_line_ratio={median_line_ratio:.3f} mean={mean_line_ratio:.3f}".format(
            **summary
        )
    )
    print(
        "median lines roman={median_lines_roman} thai={median_lines_thai}".format(**summary)
    )
    print(
        "median bottom_gap roman={median_bottom_gap_roman} thai={median_bottom_gap_thai}".format(
            **summary
        )
    )
    print(
        "pct underfilled(<0.90)={pct_thai_under_0_90}% overfilled(>1.05)={pct_thai_over_1_05}%".format(
            **summary
        )
    )
    print(
        "modal_lead median roman={modal_lead_roman_median} thai={modal_lead_thai_median}".format(
            **summary
        )
    )
    print(
        "prose n={prose_n} median_line_ratio={prose_median_line_ratio} "
        "in_band_0.95-1.05={prose_pct_in_0_95_1_05}%".format(**summary)
    )
    print("target_line_ratio_ok={target_line_ratio_ok}".format(**summary))

    # Show a few worst underfilled pages for tuning.
    worst = sorted(report["pages"], key=lambda row: row["line_ratio"])[:8]
    print("worst underfilled (print_page, ratio, roman_lines, thai_lines, thai_bottom_gap):")
    for row in worst:
        print(
            "  {print_page:4d}  {line_ratio:.2f}  {rl:3d}  {tl:3d}  {gap:6.1f}".format(
                print_page=row["print_page"],
                line_ratio=row["line_ratio"],
                rl=row["roman"]["lines"],
                tl=row["thai"]["lines"],
                gap=row["thai"]["bottom_gap"],
            )
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--roman", type=Path, default=DEFAULT_ROMAN)
    parser.add_argument("--thai", type=Path, default=DEFAULT_THAI)
    parser.add_argument("--roman-offset", type=int, default=23)
    parser.add_argument(
        "--thai-offset",
        type=int,
        default=None,
        help="Leading Thai front-matter pages before print page 1 (default: auto-detect)",
    )
    parser.add_argument(
        "--no-header-match",
        action="store_true",
        help="Pair by PDF index + offsets instead of Thai running-head page numbers",
    )
    parser.add_argument("--min-roman-lines", type=int, default=15)
    parser.add_argument(
        "--pages",
        type=str,
        default="",
        help="Comma-separated print pages, or empty for all comparable pages",
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    pages = None
    if args.pages.strip():
        pages = [int(part.strip()) for part in args.pages.split(",") if part.strip()]

    report = compare_pages(
        roman_path=args.roman,
        thai_path=args.thai,
        roman_offset=args.roman_offset,
        thai_offset=args.thai_offset,
        min_roman_lines=args.min_roman_lines,
        pages=pages,
        match_by_header=not args.no_header_match,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if not args.quiet:
        print_summary(report)
        print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
