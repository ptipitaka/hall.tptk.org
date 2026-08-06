"""Scan cs-roman volumes for mid-word hyphens (e.g. nānā-ovarakā).

Emits Roman + Thai forms from all ``volumes/*/data/segments.json``.
Excludes peyyāla marker ``-pa-``. Soft line-wrap ``word- next`` counts as the
same solid form ``word-next`` (``spaced_hits`` column).
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from paths import BOOKS, VOLUMES_DIR, ensure_import_paths

ensure_import_paths()

from pali_script import Script, convert  # noqa: E402

ROOT = BOOKS
RESEARCH = BOOKS / "research"
VOLUMES = VOLUMES_DIR

MARKER_RE = re.compile(r"\{\{(?:n\d+|\*|sp1|sp3|\+)\}\}")
PA_RE = re.compile(r"(?i)-pa-")
# Pāli Roman letters (incl. diacritics).
_LETTERS = (
    r"A-Za-z"
    r"ĀāĪīŪūĒēŌō"
    r"ṂṃṀṁṄṅÑñṬṭḌḍṆṇḶḷŚśṢṣḤḥ"
)
# Solid: letters-hyphen-letters (one or more internal hyphens).
SOLID_RE = re.compile(
    rf"(?<![{_LETTERS}])([{_LETTERS}]+(?:-[{_LETTERS}]+)+)(?![{_LETTERS}])"
)
# Line-wrapped: letters-hyphen + whitespace + letters → treat as solid join.
SPACED_RE = re.compile(rf"([{_LETTERS}]+)-\s+([{_LETTERS}]+)")
VOWELS = set("aāiīuūeoAĀIĪUŪEO")


def extract_roman_strings(obj: object, out: list[str]) -> None:
    if isinstance(obj, dict):
        if obj.get("script") == "roman" and isinstance(obj.get("value"), str):
            out.append(obj["value"])
        for v in obj.values():
            extract_roman_strings(v, out)
    elif isinstance(obj, list):
        for item in obj:
            extract_roman_strings(item, out)


def roman_to_thai(word: str) -> str:
    """Transliterate Roman token to Thai; keep literal ``-``."""
    pieces: list[str] = []
    buf: list[str] = []
    for ch in word:
        if ch == "-":
            if buf:
                pieces.append(convert("".join(buf), Script.ROMAN, Script.THAI))
                buf = []
            pieces.append("-")
        else:
            buf.append(ch)
    if buf:
        pieces.append(convert("".join(buf), Script.ROMAN, Script.THAI))
    return "".join(pieces)


def junction_kind(token: str) -> str:
    """Classify first hyphen junction: V-V, C-V, V-C, C-C."""
    left, right = token.split("-", 1)
    if not left or not right:
        return "?"
    lv = left[-1] in VOWELS
    rv = right[0] in VOWELS
    if lv and rv:
        return "V-V"
    if not lv and rv:
        return "C-V"
    if lv and not rv:
        return "V-C"
    return "C-C"


def scan() -> dict[str, dict]:
    """Return key(lower) → info dict with surface casing, counts, volumes."""
    by_key: dict[str, dict] = {}
    paths = sorted(VOLUMES.glob("*/data/segments.json"))
    print(f"volumes\t{len(paths)}", flush=True)

    for idx, seg_path in enumerate(paths, 1):
        vol = seg_path.parent.parent.name
        data = json.loads(seg_path.read_text(encoding="utf-8"))
        romans: list[str] = []
        extract_roman_strings(data, romans)
        for roman in romans:
            cleaned = PA_RE.sub(" ", MARKER_RE.sub(" ", roman))
            for m in SOLID_RE.finditer(cleaned):
                tok = m.group(1)
                key = tok.casefold()
                info = by_key.get(key)
                if info is None:
                    info = {
                        "token": tok,
                        "surfaces": Counter({tok: 0}),
                        "solid_hits": 0,
                        "spaced_hits": 0,
                        "volumes": set(),
                    }
                    by_key[key] = info
                info["solid_hits"] += 1
                info["surfaces"][tok] += 1
                info["volumes"].add(vol)
                # Prefer the most frequent surface form.
                if info["surfaces"][tok] > info["surfaces"][info["token"]]:
                    info["token"] = tok
            for m in SPACED_RE.finditer(cleaned):
                tok = f"{m.group(1)}-{m.group(2)}"
                key = tok.casefold()
                info = by_key.get(key)
                if info is None:
                    info = {
                        "token": tok,
                        "surfaces": Counter({tok: 0}),
                        "solid_hits": 0,
                        "spaced_hits": 0,
                        "volumes": set(),
                    }
                    by_key[key] = info
                info["spaced_hits"] += 1
                info["surfaces"][tok] += 1
                info["volumes"].add(vol)
                if info["surfaces"][tok] > info["surfaces"][info["token"]]:
                    info["token"] = tok
        print(f"[{idx}/{len(paths)}] {vol} unique_so_far={len(by_key)}", flush=True)
    return by_key


def write_tsv(by_key: dict[str, dict], out_tsv: Path) -> list[tuple]:
    """Keep forms that appear solid at least once (drop soft-wrap-only)."""
    rows = []
    for _key, info in by_key.items():
        if info["solid_hits"] < 1:
            continue
        tok = info["token"]
        thai = roman_to_thai(tok)
        vols = sorted(info["volumes"])
        hits = info["solid_hits"] + info["spaced_hits"]
        rows.append(
            (
                tok,
                thai,
                junction_kind(tok),
                tok.count("-"),
                hits,
                info["solid_hits"],
                info["spaced_hits"],
                len(vols),
                ",".join(vols),
            )
        )
    rows.sort(key=lambda r: (-r[7], -r[4], r[0].casefold()))
    lines = [
        "token\tthai\tjunction\tn_hyphens\thits\tsolid_hits\t"
        "spaced_hits\tn_volumes\tvolumes"
    ]
    lines.extend(
        f"{tok}\t{thai}\t{junc}\t{nh}\t{hits}\t{solid}\t{spaced}\t{nv}\t{vols}"
        for tok, thai, junc, nh, hits, solid, spaced, nv, vols in rows
    )
    out_tsv.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return rows


def write_md(rows: list[tuple], out_md: Path, n_volumes_scanned: int) -> None:
    total_hits = sum(r[4] for r in rows)
    solid_hits = sum(r[5] for r in rows)
    spaced_hits = sum(r[6] for r in rows)
    by_junc: Counter[str] = Counter()
    hits_junc: Counter[str] = Counter()
    for _tok, _thai, junc, _nh, hits, _so, _sp, _nv, _vols in rows:
        by_junc[junc] += 1
        hits_junc[junc] += hits
    vols_covered: set[str] = set()
    for r in rows:
        if r[8]:
            vols_covered.update(r[8].split(","))

    top_freq = sorted(rows, key=lambda r: (-r[4], r[0].casefold()))[:40]
    top_vols = [r for r in rows if r[7] >= 10][:40]

    lines = [
        "# คำที่มีเครื่องหมายยัติภังค์กลางคำ (40 เล่ม)",
        "",
        "สแกนจาก `volumes/*/data/segments.json` ด้วยเกณฑ์:",
        "",
        "- โทเคนโรมันที่มี `-` คั่นระหว่างตัวอักษรติดกัน เช่น `nānā-ovarakā`",
        "- รูปขึ้นบรรทัดใหม่ `nānā- ovarakā` นับรวมในรูปเดียวกัน (`spaced_hits`)",
        "- **ตัดออก** รูปที่พบเฉพาะแบบขึ้นบรรทัดใหม่ (soft wrap ของ PDF)",
        "- **ไม่รวม** เครื่องหมาย peyyāla `-pa-`",
        "",
        f"รายการเต็ม: [`research_midword_hyphens.tsv`](research_midword_hyphens.tsv)",
        "",
        "## สรุปจำนวน",
        "",
        "| กลุ่ม | รูปคำไม่ซ้ำ | ครั้งที่พบ |",
        "|-------|------------|-----------|",
        f"| ทั้งหมด (มี solid อย่างน้อย 1) | {len(rows)} | {total_hits} |",
        f"| solid (`word-word`) | — | {solid_hits} |",
        f"| spaced (`word- word`) | "
        f"{sum(1 for r in rows if r[6])} | {spaced_hits} |",
        f"| ครอบคลุมเล่ม | {len(vols_covered)} / {n_volumes_scanned} | |",
        "",
        "### ชนิดรอยต่อที่ hyphen แรก",
        "",
        "| รอยต่อ | รูปคำไม่ซ้ำ | ครั้ง |",
        "|--------|------------|------|",
    ]
    for junc in ("V-V", "C-V", "V-C", "C-C", "?"):
        if by_junc[junc]:
            lines.append(
                f"| `{junc}` | {by_junc[junc]} | {hits_junc[junc]} |"
            )
    lines += [
        "",
        "## พบบ่อยสุด (ตามครั้ง)",
        "",
        "| ครั้ง | เล่ม | รอยต่อ | โรมัน | ไทย |",
        "|------:|-----:|--------|-------|------|",
    ]
    for tok, thai, junc, _nh, hits, _so, _sp, nv, _vols in top_freq:
        lines.append(f"| {hits} | {nv} | {junc} | `{tok}` | {thai} |")
    lines += [
        "",
        "## ครอบคลุมหลายเล่ม (≥ 10 เล่ม)",
        "",
        "| เล่ม | ครั้ง | รอยต่อ | โรมัน | ไทย |",
        "|-----:|------:|--------|-------|------|",
    ]
    if not top_vols:
        lines.append("| — | — | — | *(ไม่มี)* | — |")
    else:
        for tok, thai, junc, _nh, hits, _so, _sp, nv, _vols in top_vols:
            lines.append(f"| {nv} | {hits} | {junc} | `{tok}` | {thai} |")
    lines.append("")
    out_md.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tsv",
        type=Path,
        default=RESEARCH / "research_midword_hyphens.tsv",
        help="output TSV path",
    )
    parser.add_argument(
        "--md",
        type=Path,
        default=RESEARCH / "research_midword_hyphens.md",
        help="output markdown summary path",
    )
    parser.add_argument(
        "--no-md",
        action="store_true",
        help="skip writing the markdown summary",
    )
    args = parser.parse_args()

    by_key = scan()
    n_vol = len(list(VOLUMES.glob("*/data/segments.json")))
    rows = write_tsv(by_key, args.tsv)
    spaced_only = sum(1 for info in by_key.values() if info["solid_hits"] < 1)
    print(
        f"unique_solid={len(rows)} hits={sum(r[4] for r in rows)} "
        f"spaced_only_dropped={spaced_only}"
    )
    print(f"wrote {args.tsv}")
    if not args.no_md:
        write_md(rows, args.md, n_vol)
        print(f"wrote {args.md}")
    if rows:
        print("--- top 10 by hits ---")
        for tok, thai, junc, _nh, hits, _so, _sp, nv, _vols in sorted(
            rows, key=lambda r: (-r[4], r[0].casefold())
        )[:10]:
            print(f"{hits:5d}  vols={nv:2d}  {junc}  {tok}  →  {thai}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
