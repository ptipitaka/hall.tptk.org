"""Scan cs-roman volumes for กล้ำ clusters with front vowels (e/o/ai).

Candidates affected by research.md rule B4 (สระหน้าหน้าทั้งกลุ่มกล้ำ).
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

from pali_script.convert import _match_longest, _tables
from pali_script.roman import normalize_roman_input

ROOT = Path(__file__).resolve().parents[1] / "volumes"
OUT_TSV = (
    Path(__file__).resolve().parents[1]
    / "research"
    / "research_front_vowel_clusters.tsv"
)
GLIDE = {"y", "r", "l", "v", "h"}
FRONT = {"e", "o", "ai"}
TOKEN_RE = re.compile(
    r"[A-Za-zĀāĪīŪūĒēŌōṂṃṀṁṄṅÑñṬṭḌḍṆṇḶḷŚśṢṣḤḥ]+"
)


def extract_roman_strings(obj: object, out: list[str]) -> None:
    if isinstance(obj, dict):
        if obj.get("script") == "roman" and isinstance(obj.get("value"), str):
            out.append(obj["value"])
        for v in obj.values():
            extract_roman_strings(v, out)
    elif isinstance(obj, list):
        for item in obj:
            extract_roman_strings(item, out)


def find_hits(text: str, tables: dict) -> list[tuple[str, str, str, tuple[str, ...]]]:
    """Return (cluster+vowel, vowel, token, cons_tuple)."""
    t = tables
    hits: list[tuple[str, str, str, tuple[str, ...]]] = []
    for token in TOKEN_RE.findall(text):
        norm = normalize_roman_input(token)
        i = 0
        n = len(norm)
        cons_buf: list[str] = []
        while i < n:
            nig = t["niggahita"]["roman"]
            if norm.startswith(nig, i):
                cons_buf = []
                i += len(nig)
                continue
            cons_key = _match_longest(norm, i, t["roman_cons_keys"])
            if cons_key is not None:
                cons_buf.append(cons_key)
                i += len(cons_key)
                continue
            vow_key = _match_longest(norm, i, t["roman_vow_keys"])
            if vow_key is not None:
                if len(cons_buf) >= 2 and cons_buf[-1] in GLIDE and vow_key in FRONT:
                    hits.append(
                        (
                            "".join(cons_buf) + vow_key,
                            vow_key,
                            token,
                            tuple(cons_buf),
                        )
                    )
                cons_buf = []
                i += len(vow_key)
                continue
            cons_buf = []
            i += 1
    return hits


def main() -> int:
    tables = _tables()
    by_form: dict[str, dict] = {}
    paths = sorted(ROOT.glob("*/data/segments.json"))
    print(f"volumes\t{len(paths)}", flush=True)

    for idx, seg_path in enumerate(paths, 1):
        vol = seg_path.parent.parent.name
        data = json.loads(seg_path.read_text(encoding="utf-8"))
        romans: list[str] = []
        extract_roman_strings(data, romans)
        for roman in romans:
            for cluster_vowel, vowel, token, cons in find_hits(roman, tables):
                key = normalize_roman_input(token)
                if key not in by_form:
                    geminate = len(cons) == 2 and cons[0] == cons[1]
                    by_form[key] = {
                        "volumes": set(),
                        "count": 0,
                        "cluster_vowel": cluster_vowel,
                        "vowel": vowel,
                        "cons": "".join(cons),
                        "glide": cons[-1],
                        "geminate": geminate,
                    }
                by_form[key]["volumes"].add(vol)
                by_form[key]["count"] += 1
        print(f"[{idx}/{len(paths)}] {vol} unique_so_far={len(by_form)}", flush=True)

    rows = sorted(
        by_form.items(),
        key=lambda kv: (-len(kv[1]["volumes"]), -kv[1]["count"], kv[0]),
    )

    with OUT_TSV.open("w", encoding="utf-8") as f:
        f.write(
            "token\tcluster\tglide\tvowel\tgeminate_y_l\thits\tn_volumes\tvolumes\n"
        )
        for tok, info in rows:
            vols = ",".join(sorted(info["volumes"]))
            f.write(
                f"{tok}\t{info['cons']}\t{info['glide']}\t{info['vowel']}\t"
                f"{int(info['geminate'])}\t{info['count']}\t"
                f"{len(info['volumes'])}\t{vols}\n"
            )

    print(f"unique_tokens\t{len(rows)}")
    print(f"total_hits\t{sum(v['count'] for v in by_form.values())}")
    print(f"wrote\t{OUT_TSV}")
    print("---by_vowel---")
    for k, n in Counter(v["vowel"] for v in by_form.values()).most_common():
        print(f"{k}\t{n}")
    print("---by_glide---")
    for k, n in Counter(v["glide"] for v in by_form.values()).most_common():
        print(f"{k}\t{n}")
    print(f"geminate_yy_ll\t{sum(1 for v in by_form.values() if v['geminate'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
