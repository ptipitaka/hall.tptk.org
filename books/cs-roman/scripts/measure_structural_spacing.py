# -*- coding: utf-8 -*-
"""Measure heading / paragraph / closer vertical gaps from CS Roman PDF."""
from __future__ import annotations

import argparse
import json
import re
import statistics
from pathlib import Path

try:
    import fitz
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyMuPDF (fitz) is required: pip install pymupdf") from exc

from paths import BOOKS, SOURCE_DIR

DEFAULT_ROMAN = SOURCE_DIR / "01Vin01.pdf"
DEFAULT_OUT = (
    BOOKS / "volumes" / "01Vin01" / "out" / "_ref_pages" / "structural_spacing.json"
)


def lines_of(page: fitz.Page) -> list[dict]:
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
                    "y0": round(y0, 1),
                    "y1": round(y1, 1),
                    "x0": round(x0, 1),
                    "size": round(spans[0]["size"], 1),
                    "text": text,
                }
            )
    rows.sort(key=lambda row: (row["y0"], row["x0"]))
    return rows


def body_line_gaps(rows: list[dict], header_cut: float = 75.0, foot_cut: float = 640.0) -> list[float]:
    body = [row for row in rows if header_cut <= row["y0"] < foot_cut]
    ys = sorted({row["y0"] for row in body})
    return [round(ys[i + 1] - ys[i], 1) for i in range(len(ys) - 1)]


def classify_gaps(gaps: list[float]) -> dict:
    """Split gaps into body leading (~16-19) vs paragraph-ish (~20-30)."""
    body = [g for g in gaps if 15.0 <= g <= 19.5]
    para = [g for g in gaps if 20.0 <= g <= 30.0]
    large = [g for g in gaps if g > 30.0]
    return {
        "body_lead_median": statistics.median(body) if body else None,
        "body_lead_mode_sample": body[:20],
        "para_gap_median": statistics.median(para) if para else None,
        "para_gap_values": para[:40],
        "large_gap_values": large[:20],
        "n_body": len(body),
        "n_para": len(para),
        "n_large": len(large),
    }


NITTHITA_RE = re.compile(r"ni.{0,3}thita", re.I)
CHAPTER_HINT_RE = re.compile(r"(kaṇḍa|vagga|kanda|sutta)", re.I)


def measure_title_page(rows: list[dict]) -> dict:
    """Print page 1 / PDF page 24 style title stack."""
    body = [row for row in rows if 75 <= row["y0"] < 640]
    sizes = sorted({row["size"] for row in body}, reverse=True)
    named = []
    for row in body:
        if row["size"] >= 14 or "Namo" in row["text"] or "____" in row["text"] or row["size"] >= 16:
            named.append(row)
    deltas = []
    for i in range(len(named) - 1):
        deltas.append(
            {
                "from": named[i]["text"][:40],
                "to": named[i + 1]["text"][:40],
                "dy": round(named[i + 1]["y0"] - named[i]["y1"], 1),
                "sizes": [named[i]["size"], named[i + 1]["size"]],
            }
        )
    return {"sizes": sizes, "named_rows": named[:20], "deltas": deltas}


def find_nitthita_contexts(doc: fitz.Document, roman_offset: int, limit: int = 12) -> list[dict]:
    found: list[dict] = []
    for print_page in range(1, min(doc.page_count - roman_offset, 405) + 1):
        page = doc[print_page + roman_offset - 1]
        rows = lines_of(page)
        for idx, row in enumerate(rows):
            if not NITTHITA_RE.search(row["text"]):
                continue
            prev_row = rows[idx - 1] if idx else None
            next_row = rows[idx + 1] if idx + 1 < len(rows) else None
            next2 = rows[idx + 2] if idx + 2 < len(rows) else None
            # rule line often next after closer
            after = []
            if next_row:
                after.append(
                    {
                        "text": next_row["text"][:50],
                        "dy": round(next_row["y0"] - row["y1"], 1),
                        "size": next_row["size"],
                    }
                )
            if next2:
                after.append(
                    {
                        "text": next2["text"][:50],
                        "dy": round(next2["y0"] - row["y1"], 1),
                        "size": next2["size"],
                    }
                )
            found.append(
                {
                    "print_page": print_page,
                    "text": row["text"][:80],
                    "size": row["size"],
                    "y0": row["y0"],
                    "before_dy": round(row["y0"] - prev_row["y1"], 1) if prev_row else None,
                    "after": after,
                }
            )
            if len(found) >= limit:
                return found
    return found


def find_chapter_contexts(doc: fitz.Document, roman_offset: int, limit: int = 15) -> list[dict]:
    found: list[dict] = []
    for print_page in range(1, min(doc.page_count - roman_offset, 200) + 1):
        page = doc[print_page + roman_offset - 1]
        rows = lines_of(page)
        body = [row for row in rows if 75 <= row["y0"] < 640]
        for idx, row in enumerate(body):
            # centered-ish larger or bold-ish chapter titles: size>=14 or short centered
            centered = 150 < row["x0"] < 280 and len(row["text"]) < 50
            if not (row["size"] >= 14 or (centered and CHAPTER_HINT_RE.search(row["text"]))):
                continue
            if row["size"] < 12:
                continue
            prev_row = body[idx - 1] if idx else None
            next_row = body[idx + 1] if idx + 1 < len(body) else None
            found.append(
                {
                    "print_page": print_page,
                    "text": row["text"][:60],
                    "size": row["size"],
                    "x0": row["x0"],
                    "before_dy": round(row["y0"] - prev_row["y1"], 1) if prev_row else None,
                    "after_dy": round(next_row["y0"] - row["y1"], 1) if next_row else None,
                }
            )
            if len(found) >= limit:
                return found
    return found


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--roman", type=Path, default=DEFAULT_ROMAN)
    parser.add_argument("--roman-offset", type=int, default=23)
    parser.add_argument("--sample-pages", type=str, default="2,3,4,5,10,25,50,100,150")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    doc = fitz.open(args.roman)
    sample_pages = [int(p.strip()) for p in args.sample_pages.split(",") if p.strip()]

    all_gaps: list[float] = []
    per_page = []
    for print_page in sample_pages:
        idx = print_page + args.roman_offset - 1
        if idx >= doc.page_count:
            continue
        rows = lines_of(doc[idx])
        gaps = body_line_gaps(rows)
        all_gaps.extend(gaps)
        per_page.append({"print_page": print_page, "gap_stats": classify_gaps(gaps)})

    title = measure_title_page(lines_of(doc[args.roman_offset]))  # print page 1
    report = {
        "roman_pdf": str(args.roman),
        "page_size_pt": [doc[0].rect.width, doc[0].rect.height],
        "aggregate_gaps": classify_gaps(all_gaps),
        "per_page": per_page,
        "title_page": title,
        "chapter_samples": find_chapter_contexts(doc, args.roman_offset),
        "nitthita_samples": find_nitthita_contexts(doc, args.roman_offset),
        "geometry_hints": {
            "left_flush_x": 62.6,
            "indent_x": 84.2,
            "indent_pt": 21.6,
            "header_y": 50.4,
            "body_start_y": 90.7,
            "full_page_last_y_approx": 620,
            "bottom_gap_full_page_approx_pt": 89,
            "page_w_pt": 499.0,
            "page_h_pt": 709.0,
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    agg = report["aggregate_gaps"]
    print("body_lead_median=", agg["body_lead_median"])
    print("para_gap_median=", agg["para_gap_median"])
    print("title deltas=", len(report["title_page"]["deltas"]))
    for delta in report["title_page"]["deltas"][:8]:
        print(
            "  dy={dy} sizes={sizes} from={frm!r} to={to!r}".format(
                dy=delta["dy"],
                sizes=delta["sizes"],
                frm=delta["from"].encode("unicode_escape").decode("ascii"),
                to=delta["to"].encode("unicode_escape").decode("ascii"),
            )
        )
    print("chapter samples=", len(report["chapter_samples"]))
    print("nitthita samples=", len(report["nitthita_samples"]))
    if report["nitthita_samples"]:
        sample = report["nitthita_samples"][0]
        print(
            "nitthita[0]= page={print_page} before_dy={before_dy} after={after}".format(
                **sample
            )
        )
    print("wrote", args.out)


if __name__ == "__main__":
    main()
