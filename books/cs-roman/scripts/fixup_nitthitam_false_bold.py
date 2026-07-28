#!/usr/bin/env python3
"""Sync niṭṭhitaṃ bold runs from the source PDF.

Major closers in CS Roman are full-line stroke-bold (often also larger).
Extract can paint short bold lemmas from nearby rule text onto a plain
closer. With ``\\nitthitam`` preserving ``\\textbf``, those fragments print
wrongly — and stripping every mixed run would also drop closers whose
stored runs were only partially bold while the PDF line is fully bold.

For each ``niṭṭhitaṃ`` segment this script:

- sets full-line bold runs when the PDF closer is special (full-line stroke
  bold and/or ≥2bp larger than body);
- otherwise removes bold runs.

Thai bold runs mirror the stored Thai value (full-line bold flag).

  python books/cs-roman/scripts/fixup_nitthitam_false_bold.py
  python books/cs-roman/scripts/fixup_nitthitam_false_bold.py --volume 01Vin01
  python books/cs-roman/scripts/fixup_nitthitam_false_bold.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import fitz
except ImportError:  # pragma: no cover
    print("PyMuPDF (pymupdf) is required", file=sys.stderr)
    raise

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
VOLUMES = ROOT / "volumes"
REPO = ROOT.parents[1]
sys.path.insert(0, str(SCRIPTS))

from cs_roman_bold import bold_span_texts  # noqa: E402
from cs_roman_vztime import vztime_to_unicode  # noqa: E402

NIT_RE = re.compile(r"ni[ṭt]{1,2}hitaṃ", re.I)


def page_lines(page) -> list[dict]:
    lines: list[dict] = []
    for block in page.get_text("dict").get("blocks") or []:
        for line in block.get("lines") or []:
            parts = []
            sizes = []
            for sp in line.get("spans") or []:
                text = vztime_to_unicode(sp.get("text") or "")
                if not text.strip():
                    continue
                parts.append(text)
                sizes.append(float(sp.get("size") or 0))
            if parts:
                lines.append(
                    {
                        "text": "".join(parts),
                        "size_max": max(sizes),
                        "size_avg": sum(sizes) / len(sizes),
                    }
                )
    return lines


def body_size(lines: list[dict]) -> float:
    counts: dict[float, int] = {}
    for line in lines:
        sz = round(line["size_avg"], 2)
        if sz < 11:
            continue
        counts[sz] = counts.get(sz, 0) + len(line["text"])
    if not counts:
        sizes = sorted(l["size_avg"] for l in lines if l["size_avg"] > 0)
        return sizes[len(sizes) // 2] if sizes else 0.0
    return max(counts.items(), key=lambda kv: kv[1])[0]


def line_is_full_bold(line_text: str, bold_spans: list[str]) -> bool:
    plain = re.sub(r"\s+", " ", line_text).strip().rstrip(".")
    if not plain:
        return False
    for span in bold_spans:
        sp = re.sub(r"\s+", " ", span).strip().rstrip(".")
        if not sp:
            continue
        if sp == plain or plain.startswith(sp) or sp.startswith(plain):
            if len(sp) >= max(12, int(0.6 * len(plain))):
                return True
    return False


def pdf_closer_is_special(
    page,
    *,
    value: str,
) -> bool | None:
    """True/False when a matching PDF line is found; None if unmatched."""
    lines = page_lines(page)
    body = body_size(lines)
    bold_spans = bold_span_texts(page)
    plain_val = re.sub(r"\{\{[^}]+\}\}", "", value).strip()
    matches = [l for l in lines if NIT_RE.search(l["text"])]
    best = None
    for line in matches:
        if plain_val and plain_val[:24].rstrip(".") in line["text"]:
            best = line
            break
    if best is None:
        return None
    larger = body > 0 and best["size_max"] >= body + 2.0
    full_bold = line_is_full_bold(best["text"], bold_spans)
    return larger or full_bold


def _is_full_bold_runs(runs: list) -> bool:
    values = [r for r in runs if isinstance(r, dict) and (r.get("value") or "")]
    return bool(values) and all(bool(r.get("bold")) for r in values)


def _set_full_bold(text: list) -> bool:
    roman = next((t for t in text if t.get("script") == "roman"), None)
    thai = next((t for t in text if t.get("script") == "thai"), None)
    if not isinstance(roman, dict):
        return False
    value = str(roman.get("value") or "")
    if not value:
        return False
    old = roman.get("runs")
    if _is_full_bold_runs(old or []):
        # Still refresh Thai if missing/partial.
        if isinstance(thai, dict) and _is_full_bold_runs(thai.get("runs") or []):
            return False
    roman["runs"] = [{"value": value, "bold": True}]
    if isinstance(thai, dict) and thai.get("value"):
        thai["runs"] = [{"value": str(thai["value"]), "bold": True}]
    return True


def _clear_bold(text: list) -> bool:
    changed = False
    for entry in text:
        if isinstance(entry, dict) and entry.pop("runs", None) is not None:
            changed = True
    return changed


def fix_volume(vol_id: str, *, dry_run: bool) -> tuple[int, int]:
    seg_path = VOLUMES / vol_id / "data" / "segments.json"
    layout_path = VOLUMES / vol_id / "data" / "layout.json"
    if not seg_path.is_file() or not layout_path.is_file():
        return 0, 0
    layout = json.loads(layout_path.read_text(encoding="utf-8"))
    source = REPO / layout["source"]
    if not source.is_file():
        print(f"MISSING PDF {vol_id}: {layout.get('source')}", file=sys.stderr)
        return 0, 0

    data = json.loads(seg_path.read_text(encoding="utf-8"))
    start = int(layout.get("content_start_pdf_page") or 1)
    doc = fitz.open(source)
    set_n = 0
    clear_n = 0
    changed = False

    for seg in data.get("segments") or []:
        if seg.get("segment_type") != "niṭṭhitaṃ":
            continue
        text = seg.get("text")
        if not isinstance(text, list):
            continue
        roman = next((t for t in text if t.get("script") == "roman"), None)
        if not isinstance(roman, dict):
            continue
        value = str(roman.get("value") or "")
        printed = int(seg.get("page") or 0)
        idx = start + printed - 2
        if idx < 0 or idx >= len(doc):
            continue
        special = pdf_closer_is_special(doc[idx], value=value)
        if special is None:
            continue
        if special:
            if _set_full_bold(text):
                set_n += 1
                changed = True
                print(f"SET  {vol_id} p{printed} o{seg.get('order')}: {value}")
        else:
            if _clear_bold(text):
                clear_n += 1
                changed = True
                print(f"CLR  {vol_id} p{printed} o{seg.get('order')}: {value}")

    doc.close()
    if changed and not dry_run:
        seg_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return set_n, clear_n


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--volume", default="")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    vols = (
        [args.volume]
        if args.volume
        else sorted(
            p.name
            for p in VOLUMES.iterdir()
            if (p / "data" / "segments.json").is_file()
        )
    )
    total_set = total_clear = 0
    for vol in vols:
        s, c = fix_volume(vol, dry_run=args.dry_run)
        total_set += s
        total_clear += c
    action = "would sync" if args.dry_run else "synced"
    print(f"{action}: set_bold={total_set} clear_bold={total_clear}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
