#!/usr/bin/env python3
"""Write a printable annotate-footnote report (Thai via project transliteration).

  python books/cs-roman/scripts/report_annotate.py --volume 01Vin01
  # writes tmp/cs-roman/annotate_01Vin01.html (gitignored)
"""

from __future__ import annotations

import argparse
import html
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from paths import TMP_DIR, ensure_import_paths

ensure_import_paths()

from cs_roman_text import roman_to_thai  # noqa: E402
from cs_roman_transforms import load_shared_transforms  # noqa: E402
from generate_cs_roman_tex import note_to_thai  # noqa: E402
from scan_transform_hits import hits_in_segment, load_segments, volume_segment_paths  # noqa: E402

KIND_ORDER = (
    "dve padāni",
    "niggahītasandhi",
    "āgamasandhi",
    "sandhi",
    "dve nipātā",
    "pāṭho",
    "samāso",
    "อื่น",
)


@dataclass(frozen=True)
class AnnotateRow:
    page: int
    order: int
    printed: str
    footnote: str
    kind: str
    n: int


def classify_kind(footnote: str, *, rule_id: str = "") -> str:
    """Bucket an annotate footnote; ``patho`` in the rule id counts as pāṭho."""
    folded = footnote.casefold()
    rid = rule_id.casefold()
    if "dve padāni" in folded:
        return "dve padāni"
    if "dve nipātā" in folded:
        return "dve nipātā"
    if "niggahītasandhi" in folded:
        return "niggahītasandhi"
    if "āgamasandhi" in folded:
        return "āgamasandhi"
    if "sandhi" in folded:
        return "sandhi"
    if "pāṭho" in folded or "patho" in rid:
        return "pāṭho"
    if "samāso" in folded:
        return "samāso"
    return "อื่น"


def collect_annotate_rows(volume: str) -> list[AnnotateRow]:
    rules = [r for r in load_shared_transforms() if r.enabled and r.action == "annotate"]
    paths = volume_segment_paths(volume=volume)
    if not paths:
        raise FileNotFoundError(f"no segments.json for volume {volume}")
    _, path = paths[0]
    segs = load_segments(path)
    merged: dict[tuple[int, int, str, str], AnnotateRow] = {}
    for rule in rules:
        kind = classify_kind(rule.footnote or "", rule_id=rule.id)
        for seg in segs:
            for hit in hits_in_segment(
                seg,
                volume_id=volume,
                needle=rule.match,
                substring=False,
                rules=[rule],
            ):
                if rule.id not in hit.applying:
                    continue
                key = (hit.page, hit.order, hit.matched, rule.footnote or "")
                prev = merged.get(key)
                if prev is None:
                    merged[key] = AnnotateRow(
                        page=hit.page,
                        order=hit.order,
                        printed=hit.matched,
                        footnote=rule.footnote or "",
                        kind=kind,
                        n=1,
                    )
                else:
                    merged[key] = AnnotateRow(
                        page=prev.page,
                        order=prev.order,
                        printed=prev.printed,
                        footnote=prev.footnote,
                        kind=prev.kind,
                        n=prev.n + 1,
                    )
    return sorted(merged.values(), key=lambda r: (r.page, r.order, r.printed))


def kind_thai(kind: str) -> str:
    if kind == "อื่น":
        return kind
    return roman_to_thai(kind)


def _bilingual(thai: str, roman: str) -> str:
    esc = html.escape
    if thai == roman:
        return esc(thai)
    return f'{esc(thai)}<div class="roman">{esc(roman)}</div>'


def render_html(*, volume: str, rows: list[AnnotateRow]) -> str:
    esc = html.escape
    kind_counts = Counter(r.kind for r in rows for _ in range(r.n))
    callouts = sum(r.n for r in rows)
    pages = sorted({r.page for r in rows})
    by_fn: dict[str, dict[str, object]] = {}
    for row in rows:
        rec = by_fn.setdefault(
            row.footnote,
            {"printed": row.printed, "kind": row.kind, "n": 0, "pages": []},
        )
        rec["n"] = int(rec["n"]) + row.n
        pages_list = rec["pages"]
        assert isinstance(pages_list, list)
        pages_list.append(row.page)

    kind_rows = []
    for kind in KIND_ORDER:
        count = kind_counts.get(kind, 0)
        if not count:
            continue
        kind_rows.append(
            "<tr>"
            f"<td>{_bilingual(kind_thai(kind), kind)}</td>"
            f'<td class="num">{count}</td>'
            "</tr>"
        )

    rule_rows = []
    for footnote, rec in sorted(
        by_fn.items(),
        key=lambda kv: (-int(kv[1]["n"]), kv[0]),  # type: ignore[arg-type]
    ):
        page_s = ", ".join(str(p) for p in sorted(set(rec["pages"])))  # type: ignore[arg-type]
        printed = str(rec["printed"])
        rule_rows.append(
            "<tr>"
            f'<td class="num">{rec["n"]}</td>'
            f"<td>{_bilingual(roman_to_thai(printed), printed)}</td>"
            f"<td>{_bilingual(note_to_thai(footnote), footnote)}</td>"
            f"<td>{esc(page_s)}</td>"
            "</tr>"
        )

    hit_rows = []
    for row in rows:
        nx = f"×{row.n}" if row.n > 1 else "1"
        hit_rows.append(
            "<tr>"
            f'<td class="num">{row.page}</td>'
            f'<td class="num">{row.order}</td>'
            f'<td class="num">{esc(nx)}</td>'
            f"<td>{_bilingual(roman_to_thai(row.printed), row.printed)}</td>"
            f"<td>{_bilingual(note_to_thai(row.footnote), row.footnote)}</td>"
            f"<td>{_bilingual(kind_thai(row.kind), row.kind)}</td>"
            "</tr>"
        )

    return f"""<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="utf-8">
<title>เชิงอรรถ annotate · {esc(volume)}</title>
<style>
  :root {{ color-scheme: light; }}
  body {{
    font-family: "Sarabun", "Noto Serif Thai", "Times New Roman", serif;
    margin: 1.4cm 1.6cm;
    color: #111;
    font-size: 11pt;
    line-height: 1.35;
  }}
  h1 {{ font-size: 18pt; margin: 0 0 .2em; font-weight: 700; }}
  h2 {{ font-size: 13pt; margin: 1.4em 0 .4em; }}
  .meta {{ color: #444; margin: 0 0 1em; }}
  .stats {{ display: flex; gap: 1.2em; flex-wrap: wrap; margin: 0 0 1em; }}
  .stat {{ border: 1px solid #ccc; padding: .4em .7em; min-width: 6.5em; }}
  .stat b {{ display: block; font-size: 16pt; }}
  .stat span {{ font-size: 9pt; color: #444; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 10pt; }}
  th, td {{ border: 1px solid #bbb; padding: .28em .4em; vertical-align: top; }}
  th {{ background: #eee; text-align: left; }}
  td.num {{ text-align: right; white-space: nowrap; }}
  .roman {{ font-size: 8.5pt; color: #555; margin-top: .15em; }}
  .note {{ font-size: 9.5pt; color: #333; margin: .4em 0 1em; }}
  .toolbar {{ margin: 0 0 1em; }}
  button {{ font: inherit; padding: .35em .8em; }}
  @media print {{
    @page {{ size: A4 portrait; margin: 1.4cm; }}
    .toolbar {{ display: none; }}
    thead {{ display: table-header-group; }}
    tr {{ break-inside: avoid; }}
    h2 {{ break-after: avoid; }}
    a {{ color: inherit; text-decoration: none; }}
  }}
</style>
</head>
<body>
  <div class="toolbar"><button type="button" onclick="window.print()">พิมพ์</button></div>
  <h1>เชิงอรรถ annotate · เล่ม {esc(volume)}</h1>
  <p class="meta">ปริวรรตด้วย <code>roman_to_thai</code> / <code>note_to_thai</code> ให้ตรงฉบับพิมพ์ไทย · เชิงอรรถลงท้าย – ม.พ.ป.</p>
  <div class="stats">
    <div class="stat"><b>{callouts}</b><span>จุดที่โดนกฎ</span></div>
    <div class="stat"><b>{len(by_fn)}</b><span>เนื้อเชิงอรรถ</span></div>
    <div class="stat"><b>{len(pages)}</b><span>หน้าต้นฉบับ</span></div>
  </div>
  <p class="note">คำโรมันในฉบับพิมพ์ไม่ถูกแก้ — มีแต่เชิงอรรถบรรณาธิการ บรรทัดเล็กใต้คำไทยคือรูปโรมันในแคตตาล็อก หน้า = เลข folio ในต้นฉบับ ไม่ใช่หน้า PDF พิมพ์ คอลัมน์ × คือจำนวนครั้งใน segment เดียวกัน</p>
  <h2>ชนิดเชิงอรรถ</h2>
  <table>
    <thead><tr><th>ชนิด</th><th>จุด</th></tr></thead>
    <tbody>
{"".join(kind_rows)}
    </tbody>
  </table>
  <h2>ตามกฎ</h2>
  <table>
    <thead><tr><th>จุด</th><th>คำพิมพ์</th><th>เชิงอรรถ</th><th>หน้าต้นฉบับ</th></tr></thead>
    <tbody>
{chr(10).join(rule_rows)}
    </tbody>
  </table>
  <h2>ตามหน้า</h2>
  <table>
    <thead><tr><th>หน้า</th><th>order</th><th>×</th><th>คำพิมพ์</th><th>เชิงอรรถ</th><th>ชนิด</th></tr></thead>
    <tbody>
{chr(10).join(hit_rows)}
    </tbody>
  </table>
</body>
</html>
"""


def default_output(volume: str) -> Path:
    return TMP_DIR / f"annotate_{volume}.html"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--volume", default="01Vin01", help="Folder id (e.g. 01Vin01)")
    ap.add_argument("--output", type=Path, help="HTML path (default: tmp/cs-roman/annotate_<volume>.html)")
    args = ap.parse_args(argv)
    rows = collect_annotate_rows(args.volume)
    out = args.output or default_output(args.volume)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_html(volume=args.volume, rows=rows), encoding="utf-8")
    print(f"wrote {out} rows={len(rows)} callouts={sum(r.n for r in rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
