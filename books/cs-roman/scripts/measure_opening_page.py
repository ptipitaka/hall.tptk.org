# -*- coding: utf-8 -*-
"""Measure opening-page title stack: CS Roman vs Thai rebuild."""
from __future__ import annotations

import json
import re
from pathlib import Path

import fitz

from paths import BOOKS, SOURCE_DIR

ROMAN = SOURCE_DIR / "01Vin01.pdf"
THAI = BOOKS / "volumes" / "01Vin01" / "out" / "01Vin01.pdf"
OUT = BOOKS / "volumes" / "01Vin01" / "out" / "_ref_pages" / "opening_page_spacing.json"


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
                    "x1": round(x1, 1),
                    "size": round(spans[0]["size"], 1),
                    "text": text,
                }
            )
    rows.sort(key=lambda row: (row["y0"], row["x0"]))
    return rows


def first_match(rows: list[dict], pattern: str) -> dict | None:
    cre = re.compile(pattern, re.I)
    for row in rows:
        if cre.search(row["text"]):
            return row
    return None


def analyze(rows: list[dict], labels: list[tuple[str, str]]) -> dict:
    found: list[dict] = []
    for name, pattern in labels:
        row = first_match(rows, pattern)
        if row:
            found.append({"band": name, **row})
    gaps = []
    for i in range(1, len(found)):
        prev, cur = found[i - 1], found[i]
        gaps.append(
            {
                "from": prev["band"],
                "to": cur["band"],
                "y0_to_y0": round(cur["y0"] - prev["y0"], 1),
                "y1_to_y0": round(cur["y0"] - prev["y1"], 1),
            }
        )
    return {
        "bands": found,
        "gaps": gaps,
        "first_y": found[0]["y0"] if found else None,
        "body_y": next((b["y0"] for b in found if b["band"] == "body"), None),
    }


def find_thai_body_page(doc: fitz.Document) -> int:
    for i in range(min(12, doc.page_count)):
        text = doc[i].get_text("text")
        if "นโม" in text and ("ปาราชิก" in text or "วินย" in text or "วินัย" in text):
            return i
    return 0


def main() -> None:
    roman = fitz.open(ROMAN)
    thai = fitz.open(THAI)
    roman_rows = lines_of(roman[23])  # print page 1
    thai_idx = find_thai_body_page(thai)
    thai_rows = lines_of(thai[thai_idx])

    roman_labels = [
        ("pitaka", r"Vinaya"),
        ("gambhira", r"P[āa]r[āa]jika"),
        ("rule", r"^[_—\-]{3,}$"),
        ("namo", r"Namo\s+tassa"),
        ("chapter", r"Vera"),
        ("body", r"^1\."),
    ]
    thai_labels = [
        ("pitaka", r"วินย|วินัย"),
        ("gambhira", r"ปาราชิก"),
        ("namo", r"นโม"),
        ("chapter", r"เวรญ"),
        ("body", r"^1\."),
    ]

    report = {
        "roman_pdf_page": 24,
        "thai_pdf_index": thai_idx,
        "roman": analyze(roman_rows, roman_labels),
        "thai": analyze(thai_rows, thai_labels),
        "roman_sample": roman_rows[:16],
        "thai_sample": thai_rows[:16],
    }
    # Compare shared bands
    compare = {}
    for band in ("pitaka", "gambhira", "namo", "chapter", "body"):
        rb = next((b for b in report["roman"]["bands"] if b["band"] == band), None)
        tb = next((b for b in report["thai"]["bands"] if b["band"] == band), None)
        if rb and tb:
            compare[band] = {
                "roman_y0": rb["y0"],
                "thai_y0": tb["y0"],
                "delta_y0": round(tb["y0"] - rb["y0"], 1),
                "roman_size": rb["size"],
                "thai_size": tb["size"],
            }
    report["compare"] = compare
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("thai_body_index", thai_idx)
    print("compare", json.dumps(compare, indent=2))
    print("roman gaps", json.dumps(report["roman"]["gaps"], indent=2))
    print("thai gaps", json.dumps(report["thai"]["gaps"], indent=2))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
