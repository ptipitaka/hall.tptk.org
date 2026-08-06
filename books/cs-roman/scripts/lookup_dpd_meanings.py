"""Look up representative cluster words in Digital Pāḷi Dictionary (GoldenDict online)."""

from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
from html import unescape
from pathlib import Path

RESEARCH = Path(__file__).resolve().parents[1] / "research"
MD = RESEARCH / "research_front_vowel_clusters_translit.md"
OUT = RESEARCH / "research_front_vowel_clusters_meanings.md"

ROW_RE = re.compile(
    r"^\| `([^`]+)` \| `([^`]+)` \| (\d+) \| ([^|]+) \| ([^|]+) \|$"
)
TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")
SENSE_RE = re.compile(
    r"([a-zāīūṅñṭḍṇḷṃṁśṣḥ\-]+(?:\s+\d+)?)\s+"
    r"(card|masc|fem|nt|adj|pron|pr|ptp|ind|ordin|aor|pp|abs|inf|opt|imp|"
    r"sandhi|grammar|variants|deconstructor|english|letter|name)\.?\s*"
    r"([^►]*?)(?:►|$)",
    re.I,
)
SKIP_POS = {"grammar", "variants", "deconstructor", "english", "letter"}


def strip_html(html: str) -> str:
    text = TAG_RE.sub(" ", html or "")
    text = unescape(text)
    return WS_RE.sub(" ", text).strip()


def classify(summary_html: str) -> tuple[str, str]:
    """Return (status, meaning) status: yes|sandhi|variant|no|weak."""
    plain = strip_html(summary_html)
    if not plain or "no result" in plain.lower():
        return "no", "—"

    glosses: list[str] = []
    for m in SENSE_RE.finditer(plain):
        pos = m.group(2).lower()
        gloss = m.group(3).strip(" ;,.|")
        if pos in SKIP_POS:
            continue
        if gloss and re.search(r"[A-Za-z]{3,}", gloss):
            glosses.append(f"{m.group(1)} {pos}. {gloss}")
        if len(glosses) >= 2:
            break

    if glosses:
        meaning = " · ".join(glosses)
        if len(meaning) > 160:
            meaning = meaning[:157] + "…"
        return "yes", meaning

    low = plain.lower()
    if "deconstructor" in low or re.search(r"\bsandhi\b", low):
        return "sandhi", "sandhi / deconstructor (ไม่ใช่หัวข้อพจนานุกรมตรง ๆ)"
    if "variants" in low:
        return "variant", "มีเป็นรูป variants เท่านั้น"
    return "weak", plain[:120]


def lookup(word: str) -> tuple[str, str, str]:
    url = "https://www.dpdict.net/search_json?" + urllib.parse.urlencode({"q": word})
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "hall.tptk.org-research/1.0", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    status, meaning = classify(data.get("summary_html") or "")
    link = f"https://www.dpdict.net/?q={urllib.parse.quote(word)}"
    return status, meaning, link


STATUS_TH = {
    "yes": "มีคำแปล",
    "sandhi": "sandhi/แยกคำ",
    "variant": "variants",
    "weak": "ไม่ชัด",
    "no": "ไม่พบ",
}


def main() -> None:
    rows: list[tuple[str, str, str]] = []
    for line in MD.read_text(encoding="utf-8").splitlines():
        m = ROW_RE.match(line.strip())
        if not m:
            continue
        rows.append((m.group(1), m.group(2), m.group(3)))

    counts = {k: 0 for k in STATUS_TH}
    out_lines = [
        "# คำแปลจาก Digital Pāḷi Dictionary (GoldenDict Online)",
        "",
        "แหล่ง: [dpdict.net](https://www.dpdict.net/) — API เดียวกับที่ตั้งใน GoldenDict เป็น `https://dpdict.net/gd?search=…`",
        "",
        f"คำตัวแทน {len(rows)} กลุ่ม",
        "",
        "| โรมัน | กลุ่ม | สถานะ | คำแปล (สรุป) | ลิงก์ |",
        "|-------|------|-------|--------------|------|",
    ]

    for i, (token, cluster, _hits) in enumerate(rows, 1):
        try:
            status, meaning, link = lookup(token)
        except Exception as e:
            status, meaning, link = "no", f"(error: {e})", ""
        counts[status] = counts.get(status, 0) + 1
        meaning = meaning.replace("|", "/")
        link_md = f"[เปิด]({link})" if link else "—"
        out_lines.append(
            f"| `{token}` | `{cluster}` | {STATUS_TH.get(status, status)} "
            f"| {meaning} | {link_md} |"
        )
        print(f"[{i}/{len(rows)}] {token}\t{status}\t{meaning[:90]}", flush=True)
        time.sleep(0.15)

    out_lines += [
        "",
        "## สรุป",
        "",
        f"| สถานะ | จำนวน |",
        f"|-------|------|",
        f"| มีคำแปลชัด | {counts.get('yes', 0)} |",
        f"| sandhi / แยกคำ | {counts.get('sandhi', 0)} |",
        f"| variants อย่างเดียว | {counts.get('variant', 0)} |",
        f"| ไม่ชัด | {counts.get('weak', 0)} |",
        f"| ไม่พบ | {counts.get('no', 0)} |",
        "",
        "หมายเหตุ: `should` น่าจะเป็น noise จากข้อความอังกฤษในข้อมูล ไม่ใช่คำบาลี",
        "",
    ]
    OUT.write_text("\n".join(out_lines), encoding="utf-8")
    print(f"wrote\t{OUT}")
    print(counts)


if __name__ == "__main__":
    main()
