"""Summarize research_front_vowel_clusters.tsv for research.md."""

from __future__ import annotations

import csv
import re
from collections import Counter
from pathlib import Path

from pali_script import Script, convert

RESEARCH = Path(__file__).resolve().parents[1] / "research"
TSV = RESEARCH / "research_front_vowel_clusters.tsv"
MD = RESEARCH / "research_front_vowel_clusters.md"
OUT_TRANSLIT_MD = RESEARCH / "research_front_vowel_clusters_translit.md"

# After current beautify: ทฺเว → move เ before the virama run → เทฺว
_FRONT_BEFORE_CLUSTER = re.compile(r"((?:[ก-ฮ]ฺ)+)([เโไใ])([ก-ฮ])")


def translit_current(roman: str) -> str:
    return convert(roman, Script.ROMAN, Script.THAI)


def translit_new_rule(roman: str) -> str:
    """ปริวรรต 2: สระหน้าอยู่หน้าทั้งกลุ่มกล้ำ (ยังไม่แก้ใน package)."""
    thai = translit_current(roman)
    return _FRONT_BEFORE_CLUSTER.sub(r"\2\1\3", thai)


def main() -> None:
    rows = list(csv.DictReader(TSV.open(encoding="utf-8"), delimiter="\t"))
    ng = [r for r in rows if r["geminate_y_l"] == "0"]
    g = [r for r in rows if r["geminate_y_l"] == "1"]

    clusters: Counter[str] = Counter()
    for r in ng:
        clusters[r["cluster"] + r["vowel"]] += int(r["hits"])

    ng_sorted = sorted(
        ng, key=lambda r: (-int(r["n_volumes"]), -int(r["hits"]), r["token"])
    )
    g_sorted = sorted(
        g, key=lambda r: (-int(r["n_volumes"]), -int(r["hits"]), r["token"])
    )

    vols: set[str] = set()
    for r in ng:
        vols.update(x for x in r["volumes"].split(",") if x)

    # One representative per cluster group (highest hits), ordered by group
    best_by_group: dict[str, dict] = {}
    for r in ng:
        key = r["cluster"] + r["vowel"]
        prev = best_by_group.get(key)
        if prev is None or int(r["hits"]) > int(prev["hits"]) or (
            int(r["hits"]) == int(prev["hits"]) and r["token"] < prev["token"]
        ):
            best_by_group[key] = r
    reps = sorted(
        best_by_group.values(),
        key=lambda r: (r["cluster"] + r["vowel"], -int(r["hits"]), r["token"]),
    )

    translit_lines = [
        "# ตารางปริวรรตคำกล้ำ + สระหน้า (ไม่รวม geminate)",
        "",
        "- **ปริวรรต 1** = `pali_script` ปัจจุบัน",
        "- **ปริวรรต 2** = หลักใหม่ (สระหน้า เ/โ/ไ อยู่หน้าทั้งกลุ่มกล้ำ) — จำลองนอก package",
        "- เรียงตาม **กลุ่ม** · กลุ่มละ **1 รูปคำ** ที่มียอด `ครั้ง` สูงสุดเป็นตัวแทน",
        "",
        f"จำนวน {len(reps)} กลุ่ม (จาก {len(ng)} รูปคำ) ",
        "",
        "| โรมัน | กลุ่ม | ครั้ง | ปริวรรต 1 | ปริวรรต 2 |",
        "|-------|------|------|----------|----------|",
    ]
    for r in reps:
        t1 = translit_current(r["token"])
        t2 = translit_new_rule(r["token"])
        translit_lines.append(
            f"| `{r['token']}` | `{r['cluster']}{r['vowel']}` | {r['hits']} "
            f"| {t1} | {t2} |"
        )
    translit_lines.append("")
    OUT_TRANSLIT_MD.write_text("\n".join(translit_lines), encoding="utf-8")

    lines = [
        "# คำโรมันที่อาจกระทบกฎสระหน้า + กล้ำ (40 เล่ม)",
        "",
        "สแกนจาก `volumes/*/data/segments.json` ด้วยเกณฑ์:",
        "",
        "- พยัญชนะ ≥๒ ตัวติดกัน ตัวท้ายเป็น **y r l v h**",
        "- สระร่วมของกลุ่มเป็น **e / o / ai**",
        "- ไม่รวม geminate `yy` / `ll` (ไม่เข้าข่ายกล้ำ)",
        "",
        f"รายการสแกนดิบ: [`research_front_vowel_clusters.tsv`](research_front_vowel_clusters.tsv)",
        f"ตารางปริวรรตเต็ม: [`research_front_vowel_clusters_translit.md`](research_front_vowel_clusters_translit.md)",
        "",
        "## สรุปจำนวน",
        "",
        "| กลุ่ม | รูปคำไม่ซ้ำ | ครั้งที่พบ |",
        "|-------|------------|-----------|",
        f"| ทั้งหมดในไฟล์สแกน | {len(rows)} | {sum(int(r['hits']) for r in rows)} |",
        f"| ไม่รวม geminate (ใช้ในตารางปริวรรต) | {len(ng)} | {sum(int(r['hits']) for r in ng)} |",
        f"| geminate yy/ll (ตัดออก) | {len(g)} | {sum(int(r['hits']) for r in g)} |",
        f"| ครอบคลุมเล่ม | {len(vols)} / 40 | |",
        "",
        "## กลุ่มคลัสเตอร์ที่พบบ่อย (ไม่รวม geminate)",
        "",
        "| คลัสเตอร์+สระ | ครั้ง |",
        "|---------------|------|",
    ]
    for k, n in clusters.most_common(40):
        lines.append(f"| `{k}` | {n} |")

    lines += [
        "",
        f"ตารางตัวแทนรายกลุ่ม + ปริวรรต 1/2: [`research_front_vowel_clusters_translit.md`](research_front_vowel_clusters_translit.md) ({len(reps)} กลุ่ม)",
        "",
    ]
    MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote\t{MD}")
    print(f"wrote\t{OUT_TRANSLIT_MD}")
    print(f"groups\t{len(reps)}")
    for sample in ("dve", "klesa", "tumhe", "anveti", "pañho"):
        print(f"{sample}\t{translit_current(sample)}\t{translit_new_rule(sample)}")


if __name__ == "__main__":
    main()
