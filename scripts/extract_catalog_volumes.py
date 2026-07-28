#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extract volume title lists from tipitaka-catalog TeX → Python-ready dicts."""
from __future__ import annotations

import pprint
import re
import sys
from pathlib import Path

BASE = Path(r"c:/Dev/tipitaka-catalog/catalog/content")
# Scratch output only — copy curated lists into website/catalog_volume_sets.py
OUT_DIR = Path(__file__).resolve().parent / "output"
OUT = OUT_DIR / "extracted_volumes.py"
SUMMARY = OUT_DIR / "extracted_volumes_SUMMARY.txt"

_PALI_SCRIPT_PYTHON = Path(__file__).resolve().parents[1] / "packages" / "pali_script" / "python"
if _PALI_SCRIPT_PYTHON.is_dir() and str(_PALI_SCRIPT_PYTHON) not in sys.path:
    sys.path.insert(0, str(_PALI_SCRIPT_PYTHON))

from pali_script import Script, convert as pali_convert  # noqa: E402


def thai_pali_to_roman(s: str) -> str:
    """Thai-script Pāli → Roman (IAST), title-cased for catalog titles."""
    s = s.replace("·", " · ").replace("—", " — ").replace("--", " – ")
    roman = pali_convert(s, Script.THAI, Script.ROMAN)
    roman = re.sub(r"\s+", " ", roman).strip()
    parts = []
    for tok in roman.split(" "):
        if not tok:
            continue
        if tok[0].isalpha():
            parts.append(tok[0].upper() + tok[1:])
        else:
            parts.append(tok)
    return " ".join(parts)


def read_braced(s: str, i: int) -> tuple[str, int]:
    """Read a {...} group starting at s[i]=='{', allowing nested braces."""
    if i >= len(s) or s[i] != "{":
        raise ValueError(f"expected '{{' at {i}: {s[i:i+40]!r}")
    depth = 0
    start = i + 1
    while i < len(s):
        if s[i] == "{":
            depth += 1
        elif s[i] == "}":
            depth -= 1
            if depth == 0:
                return s[start:i], i + 1
        i += 1
    raise ValueError("unbalanced braces")


def macro_args(line: str, name: str, nargs: int) -> list[str] | None:
    token = "\\" + name
    pos = line.find(token)
    if pos < 0:
        return None
    # avoid matching longer names that share prefix (item vs itembreak)
    end = pos + len(token)
    if end < len(line) and (line[end].isalpha() or line[end] == "*"):
        return None
    i = end
    args = []
    for _ in range(nargs):
        while i < len(line) and line[i].isspace():
            i += 1
        if i >= len(line) or line[i] != "{":
            return None
        arg, i = read_braced(line, i)
        args.append(arg)
    return args


def clean_tex(s: str) -> str:
    s = s.replace("~", " ")
    s = s.replace("\\&", "&")
    s = re.sub(r"\\mbox\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\textbf\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\textit\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\pali\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\jp\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\ycs\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\slk\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\khm\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\deva\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\catalogpart\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\catalogpartmuted\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\catalogparts\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\catalogattha\{([^}]*)\}", r" [\1]", s)
    s = re.sub(r"\\textnormal\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\[a-zA-Z]+\*?", "", s)
    s = s.replace("{", "").replace("}", "")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def section_from_heading(text: str) -> str | None:
    t = text.lower()
    # check nikaya / specific before generic pitaka
    checks = [
        (r"วินย|วินัย|vinaya|律", "vin"),
        (r"ทีฆ|dīgha|ทีฆ|长部|長部|trường", "dn"),
        (r"มชฺฌิม|มัชฌิม|majjhima|中部|trung", "mn"),
        (r"สํยุตฺต|สังยุตต|saṃyutta|samyutta|相应|相応|tương", "sn"),
        (r"องฺคุตฺตร|องฺคุตตร|อังคุตตร|องคุตตร|aṅguttara|anguttara|增支|増支|tăng", "an"),
        (r"ขุทฺทก|ขุททก|khuddaka|小部|tiểu", "kn"),
        (r"อภิธมฺม|อภิธรรม|abhidhamma|法集|分別|发趣|論事|双論", "abh"),
        (r"สุตฺตนฺต|สุตตันต|sutta", None),  # parent only
    ]
    for pat, code in checks:
        if re.search(pat, text, re.I) and code:
            return code
    return None


def track_section(line: str, current: str) -> str:
    # Prefer Thai/Pāli argument (2nd) for bilingual section macros.
    bilingual = (
        "laocatalogsubsection",
        "nldcatalogsubsection",
        "slkcatalogsubsection",
        "vnmcatalogsubsection",
        "laocatalogsection",
        "nldcatalogsection",
        "slkcatalogsection",
        "vnmcatalogsection",
        "vricatalogsection",
    )
    for name in bilingual:
        args = macro_args(line, name, 2) or macro_args(line, name, 3)
        if args:
            # args[0]=native, args[1]=thai/pali label
            label = args[1] if len(args) > 1 else args[0]
            code = section_from_heading(label) or section_from_heading(args[0])
            if code:
                return code
            blob = label + args[0]
            if re.search(r"สุตฺตนฺต|สุตตันต|sutta|සූත්", blob, re.I):
                return current
            if re.search(r"อภิธมฺม|อภิธรรม|abhidhamma|අභිධර්ම", blob, re.I):
                return "abh"
            if re.search(r"วินย|วินัย|vinaya|විනය", blob, re.I):
                return "vin"
    for name in (
        "catalogsubsectionpali",
        "catalogsubsection",
        "catalogsectionpali",
        "catalogsection",
    ):
        args = macro_args(line, name, 1) or macro_args(line, name, 2)
        if args:
            code = section_from_heading(args[0])
            if code:
                return code
            if re.search(r"สุตฺตนฺต|สุตตันต|sutta", args[0], re.I):
                return current
    # extra-canonical → kn best-fit (milinda, visuddhimagga, etc.)
    if re.search(r"นอกพระไตรปิฎก|藏外|蔵外|ดรรชนี", line):
        return "kn"
    return current


def entry(index: int, section: str, en: str, th: str) -> dict:
    return {"index": index, "section": section, "title": {"en": en, "th": th}}


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------

def parse_item_pali(path: Path) -> list[dict]:
    """\\item \\pali{...} with section tracking (mch-pali, rpo)."""
    text = path.read_text(encoding="utf-8")
    section = "vin"
    vols = []
    idx = 0
    for line in text.splitlines():
        section = track_section(line, section)
        m = re.search(r"\\setcounter\{enumi\}\{(\d+)\}", line)
        if m:
            idx = int(m.group(1))
            continue
        m = re.search(r"\\item\s+\\pali\{([^}]*)\}", line)
        if m:
            idx += 1
            th = m.group(1).strip()
            en = thai_pali_to_roman(th)
            vols.append(entry(idx, section, en, th))
    return vols


def parse_simple_items(path: Path, *, strip_prefix: bool = False) -> list[dict]:
    """Plain \\item TITLE for Thai translation catalogs."""
    text = path.read_text(encoding="utf-8")
    section = "vin"
    vols = []
    idx = 0
    for line in text.splitlines():
        section = track_section(line, section)
        m = re.search(r"\\setcounter\{enumi\}\{(\d+)\}", line)
        if m:
            idx = int(m.group(1))
            continue
        if re.match(r"\s*\\item\s+", line) and "\\item[" not in line:
            if any(x in line for x in ("\\newcommand", "\\begin", "\\end", "\\catalog")):
                continue
            title = re.sub(r"^\s*\\item\s+", "", line).strip()
            title = clean_tex(title)
            if not title or title.startswith("%"):
                continue
            idx += 1
            en = thai_modern_to_en(title)
            vols.append(entry(idx, section, en, title))
    return vols


# Thai modern title → English gloss map (phrase level)
TH_EN = [
    ("มหาวิภังค์ ภาค 1", "Mahāvibhaṅga, Part 1"),
    ("มหาวิภังค์ ภาค 2", "Mahāvibhaṅga, Part 2"),
    ("ภิกขุนีวิภังค์", "Bhikkhunīvibhaṅga"),
    ("มหาวรรค ภาค 1", "Mahāvagga, Part 1"),
    ("มหาวรรค ภาค 2", "Mahāvagga, Part 2"),
    ("จุลลวรรค ภาค 1", "Cullavagga, Part 1"),
    ("จุลลวรรค ภาค 2", "Cullavagga, Part 2"),
    ("จุลวรรค ภาค 1", "Cullavagga, Part 1"),
    ("จุลวรรค ภาค 2", "Cullavagga, Part 2"),
    ("ปริวาร", "Parivāra"),
    ("สีลขันธวรรค", "Sīlakkhandhavagga"),
    ("ปาฏิกวรรค", "Pāṭikavagga"),
    ("มหาวรรค", "Mahāvagga"),
    ("มูลปัณณาสก์", "Mūlapaṇṇāsaka"),
    ("มัชฌิมปัณณาสก์", "Majjhimapaṇṇāsaka"),
    ("อุปริปัณณาสก์", "Uparipaṇṇāsaka"),
    ("สคาถาวรรค", "Sagāthāvagga"),
    ("สคาถวรรค", "Sagāthavagga"),
    ("นิทานวรรค", "Nidānavagga"),
    ("ขันธวารวรรค", "Khandhavāravagga"),
    ("สฬายตนวรรค", "Saḷāyatanavagga"),
    ("มหาวารวรรค", "Mahāvāravagga"),
    ("องคุตตรนิกาย ภาค 1", "Aṅguttaranikāya, Part 1"),
    ("องคุตตรนิกาย ภาค 2", "Aṅguttaranikāya, Part 2"),
    ("องคุตตรนิกาย ภาค 3", "Aṅguttaranikāya, Part 3"),
    ("องคุตตรนิกาย ภาค 4", "Aṅguttaranikāya, Part 4"),
    ("องคุตตรนิกาย ภาค 5", "Aṅguttaranikāya, Part 5"),
    ("เอกก ทุก ติกนิบาต", "Ekaka–Duka–Tika Nipāta"),
    ("เอก-ทุก-ติกนิบาต", "Ekaka–Duka–Tika Nipāta"),
    ("จตุกกนิบาต", "Catukka Nipāta"),
    ("ปัญจก ฉักกนิบาต", "Pañcaka–Chakka Nipāta"),
    ("ปัญจก-ฉักกนิบาต", "Pañcaka–Chakka Nipāta"),
    ("สัตตก อัฏฐก นวกนิบาต", "Sattaka–Aṭṭhaka–Navaka Nipāta"),
    ("สัตตก-อัฏฐก-นวกนิบาต", "Sattaka–Aṭṭhaka–Navaka Nipāta"),
    ("ทสก เอกาทสกนิบาต", "Dasaka–Ekādasaka Nipāta"),
    ("ทสก-เอกาทสกนิบาต", "Dasaka–Ekādasaka Nipāta"),
    ("ขุททกปาฐะ-ธรรมบท-อุทาน-อิติวุตตกะ-สุตตนิบาต", "Khuddakapāṭha–Dhammapada–Udāna–Itivuttaka–Suttanipāta"),
    ("ขุททกปาฐ-ธรรมบท-อุทาน-อิติวุตตก-สุตตนิบาต", "Khuddakapāṭha–Dhammapada–Udāna–Itivuttaka–Suttanipāta"),
    ("ขุททกปาฐะ ธรรมบท อุทาน อิติวุตตกะ สุตตนิบาต", "Khuddakapāṭha–Dhammapada–Udāna–Itivuttaka–Suttanipāta"),
    ("วิมานวัตถุ-เปตวัตถุ-เถรคาถา-เถรีคาถา", "Vimānavatthu–Petavatthu–Theragāthā–Therīgāthā"),
    ("วิมาน เปตวัตถุ เถรคาถา เถรีคาถา", "Vimānavatthu–Petavatthu–Theragāthā–Therīgāthā"),
    ("ชาดก ภาค 1 — เอก-จัตตาฬีสนิบาตชาดก", "Jātaka, Part 1 — Eka–Cattālīsa Nipāta"),
    ("ชาดก ภาค 2 — ปัญญาส-มหานิบาตชาดก", "Jātaka, Part 2 — Paññāsa–Mahā Nipāta"),
    ("ชาดก ภาค 1", "Jātaka, Part 1"),
    ("ชาดก ภาค 2", "Jātaka, Part 2"),
    ("มหานิเทส", "Mahāniddesa"),
    ("มหานิทเทส", "Mahāniddesa"),
    ("จูฬนิเทส", "Cūḷaniddesa"),
    ("จูฬนิทเทส", "Cūḷaniddesa"),
    ("ปฏิสัมภิทามรรค", "Paṭisambhidāmagga"),
    ("อปทาน ภาค 1", "Apadāna, Part 1"),
    ("อปทาน ภาค 2 — พุทธวังสะ-จริยาปิฎก", "Apadāna, Part 2 — Buddhavaṃsa–Cariyāpiṭaka"),
    ("อปทาน ภาค 2-พุทธวงส์-จริยาปิฎก", "Apadāna, Part 2 — Buddhavaṃsa–Cariyāpiṭaka"),
    ("อปทาน ภาค 2 พุทธวงศ์ จริยาปิฎก", "Apadāna, Part 2 — Buddhavaṃsa–Cariyāpiṭaka"),
    ("ธัมมสังคณี", "Dhammasaṅgaṇī"),
    ("ธัมมสังคนี", "Dhammasaṅgaṇī"),
    ("วิภังค์", "Vibhaṅga"),
    ("ธาตุกถา และ ปุคคลบัญญัติ", "Dhātukathā and Puggalapaññatti"),
    ("ธาตุกถา-ปุคคลบัญญัติ", "Dhātukathā–Puggalapaññatti"),
    ("ธาตุกถา ปุคคลบัญญัติ", "Dhātukathā–Puggalapaññatti"),
    ("กถาวัตถุ", "Kathāvatthu"),
    ("ยมก ภาค 1", "Yamaka, Part 1"),
    ("ยมก ภาค 2", "Yamaka, Part 2"),
    ("ปัฏฐาน ภาค 1", "Paṭṭhāna, Part 1"),
    ("ปัฏฐาน ภาค 2", "Paṭṭhāna, Part 2"),
    ("ปัฏฐาน ภาค 3", "Paṭṭhāna, Part 3"),
    ("ปัฏฐาน ภาค 4", "Paṭṭhāna, Part 4"),
    ("ปัฏฐาน ภาค 5", "Paṭṭhāna, Part 5"),
    ("ปัฏฐาน ภาค 6", "Paṭṭhāna, Part 6"),
]


def thai_modern_to_en(title: str) -> str:
    # strip common prefixes
    t = title
    for pref in (
        "วินัยปิฎก ",
        "สุตตันตปิฎก ทีฆนิกาย ",
        "สุตตันตปิฎก มัชฌิมนิกาย ",
        "สุตตันตปิฎก สังยุตตนิกาย ",
        "สุตตันตปิฎก อังคุตตรนิกาย ",
        "สุตตันตปิฎก ขุททกนิกาย ",
        "อภิธรรมปิฎก ",
        "พระวินัยปิฎก ",
        "พระสุตตันตปิฎก ",
        "พระอภิธรรมปิฎก ",
    ):
        if t.startswith(pref):
            t = t[len(pref) :]
    for th, en in sorted(TH_EN, key=lambda x: -len(x[0])):
        if th in title or t == th or t.startswith(th):
            # if title had prefix, keep english short form
            if title != t and th in t:
                return en
            if title == th or t == th:
                return en
            if th in title:
                # replace matched core
                return title.replace(th, en) if False else en
    # fallback: romanize leftover Thai Pali-ish
    return thai_pali_to_roman(t)


def parse_volumeentry(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    section = "vin"
    vols = []
    for line in text.splitlines():
        section = track_section(line, section)
        m = re.match(r"\\volumeentry\{(\d+)\}\{([^}]*)\}", line)
        if m:
            idx = int(m.group(1))
            th = m.group(2).strip()
            en = thai_modern_to_en(th)
            vols.append(entry(idx, section, en, th))
    return vols


def parse_bilingual_item(path: Path, cmd: str, *, th_arg: int = 2, en_arg: int | None = None) -> list[dict]:
    """Generic \\cmd{a}{b} items. th_arg/en_arg are 1-based arg positions."""
    text = path.read_text(encoding="utf-8")
    section = "vin"
    vols = []
    idx = 0
    # also capture split items if present
    split_cmds = {
        "slk": ("slksplititem", "slksplitcont"),
        "ndz": ("ndzsplititem", "ndzsplitcont"),
        "lao": (),
        "nld": (),
        "vnm": (),
        "vri": (),
        "ycs": (),
    }
    prefix = cmd.replace("item", "").replace("itembreak", "")
    for line in text.splitlines():
        section = track_section(line, section)
        m = re.search(r"\\setcounter\{enumi\}\{(\d+)\}", line)
        if m:
            idx = int(m.group(1))
            continue
        # split items: \slksplititem{vol}{part}{th}{native}
        m = re.search(
            rf"\\(?:{prefix}splititem|{prefix}splitcont)\{{(\d+)\}}{{(\d+)}}{{([^}}]*)}}{{([^}}]*)}}",
            line,
        )
        if m:
            idx = max(idx + 1, int(m.group(1)))  # sequential book index
            # For split: arg3 is thai pali, arg4 is native script title
            th = m.group(3).strip()
            native = clean_tex(m.group(4).strip())
            # Prefer sequential listing of physical books
            en = thai_pali_to_roman(th) if re.search(r"[\u0E00-\u0E7F]", th) else th
            # For JP/CJK, en = roman from pali paren; th = thai pali; also keep native in en note
            if re.search(r"[\u3040-\u30ff\u4e00-\u9fff]", native):
                en = f"{native} ({en})" if en else native
            vols.append(entry(len(vols) + 1, section, en, th if re.search(r"[\u0E00-\u0E7F]", th) else native))
            continue
        m = re.search(rf"\\{cmd}\{{([^}}]*)\}}(?:\{{([^}}]*)\}})?", line)
        if not m:
            # itembreak variant
            m = re.search(rf"\\{cmd}break\{{([^}}]*)\}}(?:\{{([^}}]*)\}})?", line)
        if m:
            a1, a2 = m.group(1).strip(), (m.group(2) or "").strip()
            idx += 1
            if th_arg == 2:
                th, other = a2, a1
            else:
                th, other = a1, a2
            th = clean_tex(th)
            other = clean_tex(other)
            if en_arg == 1:
                en = other
            elif re.search(r"[\u0E00-\u0E7F]", th):
                en = thai_pali_to_roman(th)
                if other and re.search(r"[\u3040-\u30ff\u4e00-\u9fff\u0E80-\u0EFF\u0900-\u097F]", other):
                    # keep native as secondary in en for CJK/Lao/Deva? User asked en=Roman of Thai column
                    pass
            else:
                en = other or th
            # For vnm: arg1 vietnamese, arg2 thai description
            if cmd == "vnmitem":
                en = a1  # Vietnamese as "en" surrogate / primary latin-script title
                th = a2
            vols.append(entry(len(vols) + 1, section, en, th))
    return vols


def parse_mmr91(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    section = "vin"
    # Build map index -> title by expanding ranges
    by_idx: dict[int, tuple[str, str]] = {}
    for line in text.splitlines():
        section = track_section(line, section)
        m = re.search(r"\\catalogitemrange\{(\d+)\}\{(\d+)\}\{(.+)\}", line)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            title = clean_tex(m.group(3))
            for i in range(a, b + 1):
                # annotate part within range if multi
                th = title if a == b else f"{title} (เล่มพิมพ์ {i})"
                en = thai_modern_to_en(re.sub(r"\s*\[.*?\]\s*", " ", title))
                if a != b:
                    en = f"{en} (printed vol. {i})"
                by_idx[i] = (section, th, en)
            continue
        m = re.search(r"\\catalogitem\{(.+)\}", line)
        if m:
            # need current enumi - track separately
            pass
    # Second pass with counter
    section = "vin"
    idx = 0
    by_idx = {}
    for line in text.splitlines():
        section = track_section(line, section)
        m = re.search(r"\\setcounter\{enumi\}\{(\d+)\}", line)
        if m:
            idx = int(m.group(1))
            continue
        m = re.search(r"\\catalogitemrange\{(\d+)\}\{(\d+)\}\{(.+)\}", line)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            title = clean_tex(m.group(3))
            for i in range(a, b + 1):
                th = title if a == b else f"{title} — พิมพ์เล่ม {i}"
                core = re.sub(r"\s*\[.*?\]\s*", " ", title).strip()
                en = thai_modern_to_en(core)
                if a != b:
                    en = f"{en} — printed vol. {i}"
                by_idx[i] = (section, th, en)
            idx = b
            continue
        m = re.search(r"\\catalogitem\{(.+)\}", line)
        if m:
            idx += 1
            title = clean_tex(m.group(1))
            core = re.sub(r"\s*\[.*?\]\s*", " ", title).strip()
            en = thai_modern_to_en(core)
            by_idx[idx] = (section, title, en)
    vols = []
    for i in sorted(by_idx):
        sec, th, en = by_idx[i]
        vols.append(entry(i, sec, en, th))
    return vols


# TeX short title → (Thai display, English) aligned to printed 100-vol list.
SDB_TH_DISPLAY: dict[str, tuple[str, str]] = {
    "อาทิกรรม": ("คัมภีร์อาทิกรรม", "Ādikamma"),
    "ปาจิตตีย์": ("คัมภีร์ปาจิตตีย์", "Pācittiya"),
    "มหาวรรค": ("คัมภีร์มหาวรรค", "Mahāvagga"),
    "จุลวรรค": ("คัมภีร์จุลวรรค", "Cullavagga"),
    "ปริวาร": ("คัมภีร์ปริวาร", "Parivāra"),
    "สีลขันธวรรค": ("ทีฆนิกาย สีลขันธวรรค", "Dīghanikāya Sīlakkhandhavagga"),
    "ปาฏิกวรรค": ("ทีฆนิกาย ปาฏิกวรรค", "Dīghanikāya Pāṭikavagga"),
    "มูลปัณณาสก์": ("มัชฌิมนิกาย มูลปัณณาสก์", "Majjhimanikāya Mūlapaṇṇāsaka"),
    "มัชฌิมปัณณาสก์": (
        "มัชฌิมนิกาย มัชฌิมปัณณาสก์",
        "Majjhimanikāya Majjhimapaṇṇāsaka",
    ),
    "อุปริปัณณาสก์": ("มัชฌิมนิกาย อุปริปัณณาสก์", "Majjhimanikāya Uparipaṇṇāsaka"),
    "สคาถวรรค": ("สังยุตตนิกาย สคาถวรรค", "Saṃyuttanikāya Sagāthavagga"),
    "นิทานขันธวรรค": (
        "สังยุตตนิกาย นิทาน ขันธวรรค",
        "Saṃyuttanikāya Nidāna Khandhavagga",
    ),
    "สฬายตนวรรค": ("สังยุตตนิกาย สฬายตนวรรค", "Saṃyuttanikāya Saḷāyatanavagga"),
    "มหาวารวรรค": ("สังยุตตนิกาย มหาวารวรรค", "Saṃyuttanikāya Mahāvāravagga"),
    "เอกนิบาต--ทุกนิบาต": ("เอกนิบาต กับทุกนิบาต", "Eka and Duka Nipāta"),
    "ติกนิบาต": ("อังคุตตรนิกาย ติกนิบาต", "Aṅguttaranikāya Tika Nipāta"),
    "จตุกกนิบาต": ("อังคุตตรนิกาย จตุกกนิบาต", "Aṅguttaranikāya Catukka Nipāta"),
    "ปัญจกนิบาต": ("อังคุตตรนิกาย ปัญจกนิบาต", "Aṅguttaranikāya Pañcaka Nipāta"),
    "ฉักกนิบาต": ("อังคุตตรนิกาย ฉักกนิบาต", "Aṅguttaranikāya Chakka Nipāta"),
    "สัตตก--อัฏฐ--นวกนิบาต": (
        "อังคุตตรนิกาย สัตตก-อัฏฐ-นวกนิบาต",
        "Aṅguttaranikāya Sattaka-Aṭṭha-Navaka Nipāta",
    ),
    "ทสกนิบาต": ("อังคุตตรนิกาย ทสกนิบาต", "Aṅguttaranikāya Dasaka Nipāta"),
    "เอกาทสกนิบาต": (
        "อังคุตตรนิกาย เอกาทสกนิบาต",
        "Aṅguttaranikāya Ekādasaka Nipāta",
    ),
    "ขุททกปาฐะ": ("ขุททกนิกาย ขุททกปาฐะ", "Khuddakanikāya Khuddakapāṭha"),
    "ธรรมบท": ("ขุททกนิกาย ธรรมบท", "Khuddakanikāya Dhammapada"),
    "พุทธอุทาน": ("ขุททกนิกาย พุทธอุทาน", "Khuddakanikāya Udāna"),
    "อิติวุตตก": ("ขุททกนิกาย อิติวุตตก", "Khuddakanikāya Itivuttaka"),
    "สุตตนิบาต": ("ขุททกนิกาย สุตตนิบาต", "Khuddakanikāya Suttanipāta"),
    "วิมานวัตถุ": ("ขุททกนิกาย วิมานวัตถุ", "Khuddakanikāya Vimānavatthu"),
    "เปตวัตถุ": ("ขุททกนิกาย เปตวัตถุ", "Khuddakanikāya Petavatthu"),
    "เถรคาถา": ("ขุททกนิกาย เถรคาถา", "Khuddakanikāya Theragāthā"),
    "เถรีคาถา": ("ขุททกนิกาย เถรีคาถา", "Khuddakanikāya Therīgāthā"),
    "ชาดก (๕๐๐ ชาติ)": (
        "ขุททกนิกาย ชาดก (๕๐๐ ชาติ)",
        "Khuddakanikāya Jātaka (500 births)",
    ),
    "มหานิทเทส": ("ขุททกนิกาย มหานิทเทส", "Khuddakanikāya Mahāniddesa"),
    "จูฬนิทเทส": ("ขุททกนิกาย จูฬนิทเทส", "Khuddakanikāya Cūḷaniddesa"),
    "ปฏิสัมภิทามรรค": (
        "ขุททกนิกาย ปฏิสัมภิทามรรค",
        "Khuddakanikāya Paṭisambhidāmagga",
    ),
    "อปทาน": ("ขุททกนิกาย อปทาน", "Khuddakanikāya Apadāna"),
    "พุทธวงศ์": ("ขุททกนิกาย พุทธวงศ์", "Khuddakanikāya Buddhavaṃsa"),
    "จริยาปิฎก": ("ขุททกนิกาย จริยาปิฎก", "Khuddakanikāya Cariyāpiṭaka"),
    "พระสังคณี": ("คัมภีร์พระสังคณี", "Dhammasaṅgaṇī"),
    "พระวิภังค์": ("คัมภีร์พระวิภังค์", "Vibhaṅga"),
    "พระธาตุกถา--พระปุคคลบัญญัติ": (
        "พระธาตุกถา-พระปุคคลบัญญัติ",
        "Dhātukathā–Puggalapaññatti",
    ),
    "พระกถาวัตถุ": ("คัมภีร์พระกถาวัตถุ", "Kathāvatthu"),
    "พระยมก": ("คัมภีร์พระยมก", "Yamaka"),
    "พระมหาปัฏฐาน": ("คัมภีร์พระมหาปัฏฐาน", "Mahāpaṭṭhāna"),
}

# DN Mahāvagga shares TeX short title with Vinaya Mahāvagga; disambiguate by section.
SDB_TH_DISPLAY_BY_SECTION: dict[tuple[str, str], tuple[str, str]] = {
    ("dn", "มหาวรรค"): ("ทีฆนิกาย มหาวรรค", "Dīghanikāya Mahāvagga"),
}


def parse_sdb(path: Path) -> list[dict]:
    """Expand \\catalogvolrangeline ranges; multi-volume titles get ภาค N."""
    text = path.read_text(encoding="utf-8")
    section = "vin"
    vols: list[dict] = []
    for line in text.splitlines():
        section = track_section(line, section)
        args = macro_args(line, "catalogvolrangeline", 4)
        if not args:
            continue
        a, b = int(args[0]), int(args[1])
        title = clean_tex(args[2])
        display = SDB_TH_DISPLAY_BY_SECTION.get((section, title)) or SDB_TH_DISPLAY.get(
            title
        )
        if display:
            th_base, en_base = display
        else:
            th_base, en_base = title, thai_modern_to_en(title)
        n = b - a + 1
        for i, idx in enumerate(range(a, b + 1), start=1):
            if n == 1:
                th, en = th_base, en_base
            else:
                th = f"{th_base} ภาค {thai_digits_str(i)}"
                en = f"{en_base}, Part {i}"
            vols.append(entry(idx, section, en, th))
    return vols


def thai_digits_str(n: int) -> str:
    return "".join("๐๑๒๓๔๕๖๗๘๙"[int(ch)] for ch in str(n))


# Curated Thai-script Pāli (+ Thai structural wording) for PTS Roman titles.
# Kept in sync with website.catalog_volume_sets.PTS_PALI_VOLUMES*_ title.th.
PTS_PALI_TITLE_TH: dict[str, str] = {
    "Vol. I: Pārājika": "เล่ม ๑: ปาราชิก",
    "Vol. II: Pācittiya": "เล่ม ๒: ปาจิตฺติย",
    "Vol. III: Bhikkhunīvibhaṅga": "เล่ม ๓: ภิกฺขุนีวิภงฺค",
    "Vol. IV: Mahāvagga": "เล่ม ๔: มหาวคฺค",
    "Vol. V: Cūḷavagga": "เล่ม ๕: จูฬวคฺค",
    "Vol. VI: Parivāra / Index": "เล่ม ๖: ปริวาร / ดัชนี",
    "Vol. I: Sīlakkhandhavagga": "เล่ม ๑: สีลกฺขนฺธวคฺค",
    "Vol. II: Mahāvagga": "เล่ม ๒: มหาวคฺค",
    "Vol. III: Pāṭikavagga": "เล่ม ๓: ปาฏิกวคฺค",
    "Index": "ดัชนี",
    "Vol. I: Mūlapaṇṇāsaka": "เล่ม ๑: มูลปณฺณาสก",
    "Vol. II: Majjhimapaṇṇāsaka": "เล่ม ๒: มชฺฌิมปณฺณาสก",
    "Vol. III: Uparipaṇṇāsaka": "เล่ม ๓: อุปริปณฺณาสก",
    "Vol. I: Sagāthāvagga": "เล่ม ๑: สคาถาวคฺค",
    "Vol. II: Nidānavagga": "เล่ม ๒: นิทานวคฺค",
    "Vol. III: Khandhavagga": "เล่ม ๓: ขนฺธวคฺค",
    "Vol. IV: Saḷāyatanavagga": "เล่ม ๔: สฬายตนวคฺค",
    "Vol. V: Mahāvagga": "เล่ม ๕: มหาวคฺค",
    "Vol. I: Ekaka–Tika Nipāta": "เล่ม ๑: เอกก–ติก นิปาต",
    "Vol. II: Catukka Nipāta": "เล่ม ๒: จตุกฺก นิปาต",
    "Vol. III: Pañcaka–Chakka Nipāta": "เล่ม ๓: ปญฺจก–ฉกฺก นิปาต",
    "Vol. IV: Sattaka–Aṭṭhaka–Navaka Nipāta": "เล่ม ๔: สตฺตก–อฏฺฐก–นวก นิปาต",
    "Vol. V: Dasaka–Ekādasaka Nipāta": "เล่ม ๕: ทสก–เอกาทสก นิปาต",
    "Khuddakapāṭha with Commentary": "ขุทฺทกปาฐ พร้อมอรรถกถา",
    "Dhammapada": "ธมฺมปท",
    "Dhammapada Commentary": "อรรถกถาธมฺมปท",
    "Udāna": "อุทาน",
    "Itivuttaka": "อิติวุตฺตก",
    "Suttanipāta": "สุตฺตนิปาต",
    "Vimānavatthu and Petavatthu": "วิมานวตฺถุ และ เปตวตฺถุ",
    "Theragāthā / Therīgāthā": "เถรคาถา / เถรีคาถา",
    "Jātaka with Commentary, Vol. I": "ชาตก พร้อมอรรถกถา เล่ม ๑",
    "Jātaka with Commentary, Vol. II": "ชาตก พร้อมอรรถกถา เล่ม ๒",
    "Jātaka with Commentary, Vol. III": "ชาตก พร้อมอรรถกถา เล่ม ๓",
    "Jātaka with Commentary, Vol. IV": "ชาตก พร้อมอรรถกถา เล่ม ๔",
    "Jātaka with Commentary, Vol. V": "ชาตก พร้อมอรรถกถา เล่ม ๕",
    "Jātaka with Commentary, Vol. VI": "ชาตก พร้อมอรรถกถา เล่ม ๖",
    "Jātaka with Commentary, Vol. VII — Indexes": "ชาตก พร้อมอรรถกถา เล่ม ๗ — ดัชนี",
    "Mahāniddesa": "มหานิทฺเทส",
    "Cūḷaniddesa": "จูฬนิทฺเทส",
    "Paṭisambhidāmagga, 2 Vols in one": "ปฏิสมฺภิทามคฺค ๒ เล่มรวมเล่มเดียว",
    "Apadāna, 2 Vols in one": "อปทาน ๒ เล่มรวมเล่มเดียว",
    "Buddhavaṃsa and Cariyāpiṭaka": "พุทฺธวํส และ จริยาปิฏก",
    "Dhammasaṅgaṇī": "ธมฺมสงฺคณี",
    "Vibhaṅga": "วิภงฺค",
    "Dhātukathā with Commentary": "ธาตุกถา พร้อมอรรถกถา",
    "Puggalapaññatti \\& Commentary, 2 Vols in one": (
        "ปุคฺคลปญฺญตฺติ และอรรถกถา ๒ เล่มรวมเล่มเดียว"
    ),
    "Puggalapaññatti & Commentary, 2 Vols in one": (
        "ปุคฺคลปญฺญตฺติ และอรรถกถา ๒ เล่มรวมเล่มเดียว"
    ),
    "Index to the Dīgha-nikāya": "ดัชนีทีฆนิกาย",
    "Index to the Majjhima-nikāya": "ดัชนีมัชฌิมนิกาย",
    "Index to the Saṃyutta-nikāya": "ดัชนีสังยุตตนิกาย",
    "Index to the Aṅguttara-nikāya": "ดัชนีอังคุตตรนิกาย",
    "Index to the Mahāniddesa": "ดัชนีมหานิทเทส",
    "Kathāvatthu, Vol. I": "กถาวตฺถุ เล่ม ๑",
    "Kathāvatthu, Vol. II / Index": "กถาวตฺถุ เล่ม ๒ / ดัชนี",
    "Yamaka, Vol. I": "ยมก เล่ม ๑",
    "Yamaka, Vol. II": "ยมก เล่ม ๒",
    "Paṭṭhāna, Dukapaṭṭhāna": "ปฏฺฐาน ทุกปฏฺฐาน",
    "Paṭṭhāna, Tikapaṭṭhāna with Commentary": "ปฏฺฐาน ติกปฏฺฐาน พร้อมอรรถกถา",
}


def parse_pts_pali(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    section = "vin"
    vols = []
    n = 0
    for line in text.splitlines():
        section = track_section(line, section)
        m = re.search(r"\\catalogitem\{([^}]*)\}", line)
        if m:
            n += 1
            title = clean_tex(m.group(1))
            th = PTS_PALI_TITLE_TH.get(title, title)
            vols.append(entry(n, section, title, th))
        elif re.match(r"\s*\\item\s+Index", line):
            n += 1
            vols.append(entry(n, section, "Index", PTS_PALI_TITLE_TH["Index"]))
    return vols


def parse_pts_english(path: Path) -> list[dict]:
    """Concordance rows from ``\\ptsrow`` / ``\\ptsnone`` (aligned to Pāli catalog slots).

    Display title: ``{pali} -- {english}`` or ``{pali} -- (Not Published)``.
    ``catalog_no`` keeps TeX slot labels including splits (``33.(1)``).
    """
    text = path.read_text(encoding="utf-8")
    section = "vin"
    vols: list[dict] = []
    not_pub_en = "(Not Published)"
    not_pub_th = "(ยังไม่ได้จัดพิมพ์)"

    def add(catalog_no: str, pali: str, eng: str | None, sec: str) -> None:
        pali = clean_tex(pali)
        th_pali = PTS_PALI_TITLE_TH.get(pali, pali)
        not_published = eng is None
        if eng:
            eng = clean_tex(eng)
            title_en = f"{pali} -- {eng}"
            title_th = f"{th_pali} -- {eng}"
        else:
            title_en = f"{pali} -- {not_pub_en}"
            title_th = f"{th_pali} -- {not_pub_th}"
        n = len(vols) + 1
        row = {
            "index": n,
            "section": sec,
            "catalog_no": catalog_no,
            "title": {"en": title_en, "th": title_th},
        }
        if not_published:
            row["not_published"] = True
        vols.append(row)

    for line in text.splitlines():
        section = track_section(line, section)
        args = macro_args(line, "ptsrow", 3)
        if args:
            add(args[0].strip(), args[1], args[2], section)
            continue
        args = macro_args(line, "ptsnone", 2) or macro_args(line, "ptsnoneplain", 2)
        if args:
            add(args[0].strip(), args[1], None, section)
            continue
    return vols


# Curated English for Khmer range titles (Thai-script Pāli cores)
KHM_EN = {
    "มหาวิภังค์": "Mahāvibhaṅga",
    "ภิกฺขุนีวิภงฺค": "Bhikkhunīvibhaṅga",
    "มหาวคฺค": "Mahāvagga",
    "จูฬวคฺค": "Cūḷavagga",
    "ปริวาร": "Parivāra",
    "สีลกฺขนฺธวคฺค": "Sīlakkhandhavagga",
    "ปาฏิกวคฺค": "Pāṭikavagga",
    "มูลปณฺณาสก": "Mūlapaṇṇāsaka",
    "มชฺฌิมปณฺณาสก": "Majjhimapaṇṇāsaka",
    "อุปริปณฺณาสก": "Uparipaṇṇāsaka",
    "สคาถวคฺค": "Sagāthavagga",
    "นิทานวคฺค": "Nidānavagga",
    "ขนฺธวารวคฺค": "Khandhavāravagga",
    "สฬายตนวคฺค": "Saḷāyatanavagga",
    "มหาวารวคฺค": "Mahāvāravagga",
    "เอกก-ทุก-ติกนิปาต": "Ekaka–Duka–Tika Nipāta",
    "จตุกฺกนิปาต": "Catukka Nipāta",
    "ปญฺจก-ฉกฺกนิปาต": "Pañcaka–Chakka Nipāta",
    "สตฺตก-อฏฺฐก-นวกนิปาต": "Sattaka–Aṭṭhaka–Navaka Nipāta",
    "ทสก-เอกาทสกนิปาต": "Dasaka–Ekādasaka Nipāta",
    "ขุทฺทกปาถ": "Khuddakapāṭha · Dhammapada · Udāna",
    "อิติวุตฺตก": "Itivuttaka",
    "สุตฺตนิปาต": "Suttanipāta",
    "วิมานวตฺถุ": "Vimānavatthu",
    "เปตวตฺถุ": "Petavatthu · Theragāthā",
    "เถรีคาถา": "Therīgāthā",
    "ชาตก": "Jātaka",
    "มหานิทฺเทส": "Mahāniddesa",
    "จุลฺลนิทฺเทส": "Cullaniddesa",
    "ปฏิสมฺภิทามคฺค": "Paṭisambhidāmagga",
    "อปทาน": "Apadāna",
    "พุทฺธวํส": "Buddhavaṃsa · Cariyāpiṭaka",
    "ธมฺมสงฺคณี": "Dhammasaṅgaṇī",
    "วิภงฺค": "Vibhaṅga",
    "ธาตุกถา": "Dhātukathā · Puggalapaññatti",
    "กถาวตฺถุ": "Kathāvatthu",
    "ยมก": "Yamaka",
    "ปฏฺฐาน": "Paṭṭhāna",
}


def parse_khm(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    section = "vin"
    vols = []
    for line in text.splitlines():
        section = track_section(line, section)
        args = macro_args(line, "khmvol", 2)
        if not args:
            continue
        rng, title_raw = args[0].strip(), clean_tex(args[1])
        th_title = title_raw
        en_title = None
        for th, en in sorted(KHM_EN.items(), key=lambda x: -len(x[0])):
            if th in title_raw:
                # special-case compound first volumes
                if th == "มหาวิภังค์" and "ปาราชิก" in title_raw:
                    en_title = "Mahāvibhaṅga — Pārājika and Saṅghādisesa"
                elif th == "มหาวิภังค์" and "ปาจิตฺติย" in title_raw:
                    en_title = "Mahāvibhaṅga — Pācittiya"
                else:
                    en_title = en
                break
        if en_title is None:
            core = re.split(r"\s*—\s*|\s*---\s*", title_raw)[0]
            en_title = thai_pali_to_roman(core)
        if re.search(r"\d", rng) and re.search(r"--|–|-", rng):
            parts = re.split(r"--|–|-", rng)
            a, b = int(parts[0]), int(parts[-1])
            for i in range(a, b + 1):
                vols.append(
                    entry(
                        i,
                        section,
                        f"{en_title} (vol. {i})" if a != b else en_title,
                        f"{th_title} (เล่ม {i})" if a != b else th_title,
                    )
                )
        else:
            i = int(rng)
            vols.append(entry(i, section, en_title, th_title))
    return vols


def polish_mch_pali(vols: list[dict]) -> list[dict]:
    """Override roman with curated IAST for Mahācuḷā (closer to standard)."""
    curated = {
        1: "Vinayapiṭake Mahāvibhaṅgapāli [paṭhamabhāga]",
        2: "Vinayapiṭake Mahāvibhaṅgapāli [dutiyabhāga]",
        3: "Vinayapiṭake Bhikkhunīvibhaṅgapāli",
        4: "Vinayapiṭake Mahāvaggapāli [paṭhamabhāga]",
        5: "Vinayapiṭake Mahāvaggapāli [dutiyabhāga]",
        6: "Vinayapiṭake Cūḷavaggapāli [paṭhamabhāga]",
        7: "Vinayapiṭake Cūḷavaggapāli [dutiyabhāga]",
        8: "Vinayapiṭake Parivārapāli",
        9: "Suttantapiṭake Dīghanikāye Sīlakkhandhavaggapāli",
        10: "Suttantapiṭake Dīghanikāye Mahāvaggapāli",
        11: "Suttantapiṭake Dīghanikāye Pāṭikavaggapāli",
        12: "Suttantapiṭake Majjhimanikāye Mūlapaṇṇāsakapāli",
        13: "Suttantapiṭake Majjhimanikāye Majjhimapaṇṇāsakapāli",
        14: "Suttantapiṭake Majjhimanikāye Uparipaṇṇāsakapāli",
        15: "Suttantapiṭake Saṃyuttanikāye Sagāthavaggapāli",
        16: "Suttantapiṭake Saṃyuttanikāye Nidānavaggapāli",
        17: "Suttantapiṭake Saṃyuttanikāye Khandhavāravaggapāli",
        18: "Suttantapiṭake Saṃyuttanikāye Saḷāyatanavaggapāli",
        19: "Suttantapiṭake Saṃyuttanikāye Mahāvāravaggapāli",
        20: "Suttantapiṭake Aṅguttaranikāye Ekaka-Duka-Tikanipātapāli",
        21: "Suttantapiṭake Aṅguttaranikāye Catukkanipātapāli",
        22: "Suttantapiṭake Aṅguttaranikāye Pañcaka-Chakkanipātapāli",
        23: "Suttantapiṭake Aṅguttaranikāye Sattaka-Aṭṭhaka-Navakanipātapāli",
        24: "Suttantapiṭake Aṅguttaranikāye Dasaka-Ekādasakanipātapāli",
        25: "Suttantapiṭake Khuddakanikāye Khuddakapāṭha-Dhammapada-Udāna-Itivuttaka-Suttanipātapāli",
        26: "Suttantapiṭake Khuddakanikāye Vimānavatthu-Petavatthu-Theragāthā-Therīgāthāpāli",
        27: "Suttantapiṭake Khuddakanikāye Jātakapāli [paṭhamabhāga]",
        28: "Suttantapiṭake Khuddakanikāye Jātakapāli [dutiyabhāga]",
        29: "Suttantapiṭake Khuddakanikāye Mahāniddesapāli",
        30: "Suttantapiṭake Khuddakanikāye Cūḷaniddesapāli",
        31: "Suttantapiṭake Khuddakanikāye Paṭisambhidāmaggapāli",
        32: "Suttantapiṭake Khuddakanikāye Apadānapāli [paṭhamabhāga]",
        33: "Suttantapiṭake Khuddakanikāye Apadānapāli [dutiyabhāga]-Buddhavamsa-Cariyāpiṭaka",
        34: "Abhidhammapiṭake Dhammasaṅgaṇipāli",
        35: "Abhidhammapiṭake Vibhaṅgapāli",
        36: "Abhidhammapiṭaka Dhātukathā Puggalapaññatti",
        37: "Abhidhammapiṭake Kathāvatthupāli",
        38: "Abhidhammapiṭake Yamakapāli [paṭhamabhāga]",
        39: "Abhidhammapiṭake Yamakapāli [dutiyabhāga]",
        40: "Abhidhammapiṭake Paṭṭhānapāli [paṭhamabhāga]",
        41: "Abhidhammapiṭake Paṭṭhānapāli [dutiyabhāga]",
        42: "Abhidhammapiṭake Paṭṭhānapāli [tatiyabhāga]",
        43: "Abhidhammapiṭake Paṭṭhānapāli [catutthabhāga]",
        44: "Abhidhammapiṭake Dukatikapaṭṭhānapāli [pañcamabhāga]",
        45: "Abhidhammapiṭake Paṭṭhānapāli [chaṭṭhabhāga]",
    }
    for v in vols:
        if v["index"] in curated:
            v["title"]["en"] = curated[v["index"]]
    return vols


def polish_lao(vols: list[dict]) -> list[dict]:
    curated_en = {
        1: "Pārājikapāli",
        2: "Pācittiyapāli",
        3: "Mahāvaggapāli",
        4: "Cūḷavaggapāli",
        5: "Parivārapāli",
        6: "Sīlakkhandhavaggapāli",
        7: "Mahāvaggapāli",
        8: "Pāthikavaggapāli",
        9: "Mūlapaṇṇāsakapāli",
        10: "Majjhimapaṇṇāsakapāli",
        11: "Uparipaṇṇāsakapāli",
        12: "Sagāthāvaggasaṃyuttapāli",
        13: "Nidānavaggasaṃyuttapāli",
        14: "Khandhavāravaggasaṃyuttapāli",
        15: "Saḷāyatanavaggasaṃyuttapāli",
        16: "Mahāvaggasaṃyuttapāli",
        17: "Ekaka-Duka-Tikanipātapāli",
        18: "Catukkanipātapāli",
        19: "Pañcakanipātapāli",
        20: "Chakka-Sattakanipātapāli",
        21: "Aṭṭhaka-Navakanipātapāli",
        22: "Dasaka-Ekādasakanipātapāli",
        23: "Khuddakapāṭha · Dhammapada · Udānapāli",
        24: "Itivuttaka · Suttanipātapāli",
        25: "Vimānavatthu · Petavatthupāli",
        26: "Theragāthā · Therīgāthāpāli",
        27: "Jātakapāli — paṭhamo bhāgo",
        28: "Jātakapāli — dutiyo bhāgo",
        29: "Mahāniddesapāli",
        30: "Cūḷaniddesapāli",
        31: "Paṭisambhidāmaggapāli",
        32: "Apadānapāli — paṭhamo bhāgo",
        33: "Apadānapāli — dutiyo bhāgo · Buddhavamsa · Cariyāpiṭakapāli",
        34: "Dhammasaṅgaṇīpāli",
        35: "Vibhaṅgapāli",
        36: "Dhātukathā · Puggalapaññattipāli",
        37: "Kathāvatthupāli",
        38: "Yamakapāli — paṭhamo bhāgo",
        39: "Yamakapāli — dutiyo bhāgo",
        40: "Yamakapāli — tatiyo bhāgo",
        41: "Paṭṭhānapāli — paṭhamo bhāgo",
        42: "Paṭṭhānapāli — dutiyo bhāgo",
        43: "Paṭṭhānapāli — tatiyo bhāgo",
        44: "Paṭṭhānapāli — catuttho bhāgo",
        45: "Paṭṭhānapāli — pañcamo bhāgo",
    }
    for v in vols:
        if v["index"] in curated_en:
            v["title"]["en"] = curated_en[v["index"]]
    return vols


def nld_from_script() -> list[dict]:
    # Import data inline from generate-nld script constants
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "nldgen",
        Path(r"c:/Dev/tipitaka-catalog/scripts/generate-nld-pali-devanagari-tex.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    sections = (
        ["vin"] * 5
        + ["dn"] * 3
        + ["mn"] * 3
        + ["sn"] * 4
        + ["an"] * 4
        + ["kn"] * 9
        + ["abh"] * 13
    )
    vols = []
    for i, ((iast, thai), sec) in enumerate(zip(mod.ALL, sections), 1):
        iast = iast.replace("ṭhṭṭhamo", "chaṭṭhamo").replace("cūlavagga", "cūḷavagga")
        en = " ".join(w[:1].upper() + w[1:] if w else w for w in iast.split(" "))
        vols.append(entry(i, sec, en, thai))
    return vols


def polish_rpo(vols: list[dict]) -> list[dict]:
    for v in vols:
        v["title"]["en"] = thai_pali_to_roman(v["title"]["th"])
    # light curated fixes for common tokens
    fixes = [
        ("Suttantapitake", "Suttantapiṭake"),
        ("Abhidhammapitake", "Abhidhammapiṭake"),
        ("Vinayapitake", "Vinayapiṭake"),
        ("Dighanikayassa", "Dīghanikāyassa"),
        ("Majjhimanikayassa", "Majjhimanikāyassa"),
        ("Samyuttanikayassa", "Saṃyuttanikāyassa"),
        ("Anguttaranikayassa", "Aṅguttaranikāyassa"),
        ("Khuddakanikayassa", "Khuddakanikāyassa"),
        ("Silakkhandhavaggo", "Sīlakkhandhavaggo"),
        ("Patikavaggo", "Pāṭikavaggo"),
        ("Mulapannasakam", "Mūlapaṇṇāsakaṃ"),
        ("Majjhimapannasakam", "Majjhimapaṇṇāsakaṃ"),
        ("Uparipannasakam", "Uparipaṇṇāsakaṃ"),
        ("Sagathavaggo", "Sagāthavaggo"),
        ("Nidanavaggo", "Nidānavaggo"),
        ("Khandhavaravaggo", "Khandhavāravaggo"),
        ("Salayatanavaggo", "Saḷāyatanavaggo"),
        ("Mahavaravaggo", "Mahāvāravaggo"),
        ("Pathamo", "Paṭhamo"),
        ("Dutiyo", "Dutiyo"),
        ("Tatiyo", "Tatiyo"),
        ("Catuttho", "Catuttho"),
        ("Pancamo", "Pañcamo"),
        ("Chattho", "Chaṭṭho"),
        ("Sattamo", "Sattamo"),
        ("Atthamo", "Aṭṭhamo"),
        ("Navamo", "Navamo"),
        ("Dasamo", "Dasamo"),
        ("Patisambhidamaggo", "Paṭisambhidāmaggo"),
        ("Culaniddeso", "Cūḷaniddeso"),
        ("Mahaniddeso", "Mahāniddeso"),
        ("Buddhavamsa", "Buddhavaṃsa"),
        ("Cariyapitaka", "Cariyāpiṭaka"),
        ("Dhammasanganai", "Dhammasaṅgaṇi"),
        ("Dhammasangani", "Dhammasaṅgaṇi"),
        ("Vibhango", "Vibhaṅgo"),
        ("Dhatukatha", "Dhātukathā"),
        ("Puggalapannatti", "Puggalapaññatti"),
        ("Kathavatthu", "Kathāvatthu"),
        ("Patthanam", "Paṭṭhānaṃ"),
        ("Parajikam", "Pārājikaṃ"),
        ("Pacitti", "Pācitti"),
        ("Cullavaggo", "Cullavaggo"),
        ("Mahavaggo", "Mahāvaggo"),
    ]
    for v in vols:
        en = v["title"]["en"]
        for a, b in fixes:
            en = en.replace(a, b)
        v["title"]["en"] = en
    return vols


def fix_mmr91_en(vols: list[dict]) -> list[dict]:
    """Better English for 91-vol Thai tipitaka+attha titles."""
    for v in vols:
        th = v["title"]["th"]
        # Extract attha in brackets
        attha = ""
        m = re.search(r"\[([^\]]+)\]", th)
        if m:
            attha = m.group(1)
        core = re.sub(r"\s*—\s*พิมพ์เล่ม \d+", "", th)
        core = re.sub(r"\s*\[[^\]]+\]\s*", " ", core).strip()
        # Build English from known pieces
        en = core
        reps = [
            ("พระวินัยปิฎก", "Vinayapiṭaka"),
            ("พระสุตตันตปิฎก", "Suttantapiṭaka"),
            ("พระอภิธรรมปิฎก", "Abhidhammapiṭaka"),
            ("ทีฆนิกาย", "Dīghanikāya"),
            ("มัชฌิมนิกาย", "Majjhimanikāya"),
            ("สังยุตตนิกาย", "Saṃyuttanikāya"),
            ("อังคุตรนิกาย", "Aṅguttaranikāya"),
            ("อังคุตตรนิกาย", "Aṅguttaranikāya"),
            ("ขุททกนิกาย", "Khuddakanikāya"),
            ("มหาวิภังค์", "Mahāvibhaṅga"),
            ("ภิกขุนีวิภังค์", "Bhikkhunīvibhaṅga"),
            ("มหาวรรค", "Mahāvagga"),
            ("จุลวรรค", "Cullavagga"),
            ("ปริวาร", "Parivāra"),
            ("สีลขันธวรรค", "Sīlakkhandhavagga"),
            ("ปาฏิกวรรค", "Pāṭikavagga"),
            ("มูลปัณณาสก์", "Mūlapaṇṇāsaka"),
            ("มัชฌิมปัณณาสก์", "Majjhimapaṇṇāsaka"),
            ("อุปริปัณณาสก์", "Uparipaṇṇāsaka"),
            ("สคาถวรรค", "Sagāthavagga"),
            ("นิทานวรรค", "Nidānavagga"),
            ("ขันธวารวรรค", "Khandhavāravagga"),
            ("สฬายตนวรรค", "Saḷāyatanavagga"),
            ("มหาวารวรรค", "Mahāvāravagga"),
            ("เอกนิบาต", "Eka Nipāta"),
            ("ทุกนิบาต", "Duka Nipāta"),
            ("ติกนิบาต", "Tika Nipāta"),
            ("จตุกนิบาต", "Catukka Nipāta"),
            ("ปัญจก-ฉักกนิบาต", "Pañcaka–Chakka Nipāta"),
            ("สัตตก-อัฏฐก-นวกนิบาต", "Sattaka–Aṭṭhaka–Navaka Nipāta"),
            ("ทสก--เอกาทสกนิบาต", "Dasaka–Ekādasaka Nipāta"),
            ("ขุททกปาฐะ", "Khuddakapāṭha"),
            ("คาถาธรรมบท", "Dhammapada"),
            ("อุทาน", "Udāna"),
            ("อิติวุตตก", "Itivuttaka"),
            ("สุตตนิบาต", "Suttanipāta"),
            ("วิมานวัตถุ", "Vimānavatthu"),
            ("เปตวัตถุ", "Petavatthu"),
            ("เถรคาถา", "Theragāthā"),
            ("เถรีคาถา", "Therīgāthā"),
            ("ชาดก", "Jātaka"),
            ("มหานิเทส", "Mahāniddesa"),
            ("จูฬนิเทส", "Cūḷaniddesa"),
            ("ปฏิสัมภิทามรรค", "Paṭisambhidāmagga"),
            ("อปทาน", "Apadāna"),
            ("พุทธวงศ์", "Buddhavaṃsa"),
            ("จริยาปิฎก", "Cariyāpiṭaka"),
            ("ธรรมสังคณี", "Dhammasaṅgaṇī"),
            ("วิภังค์", "Vibhaṅga"),
            ("ธาตุกถา--บุคคลบัญญัติ", "Dhātukathā–Puggalapaññatti"),
            ("กถาวัตถุ", "Kathāvatthu"),
            ("ยมก", "Yamaka"),
            ("ปัฏฐาน", "Paṭṭhāna"),
            ("เล่ม", "vol."),
            ("ภาค", "part"),
        ]
        for a, b in reps:
            en = en.replace(a, b)
        en = re.sub(r"\s+", " ", en).strip()
        if attha:
            en = f"{en} [{attha}]"
        mprint = re.search(r"พิมพ์เล่ม (\d+)", th)
        if mprint:
            en = f"{en} — printed vol. {mprint.group(1)}"
        v["title"]["en"] = en
    return vols


def polish_thai45_en(vols: list[dict], style: str) -> list[dict]:
    """Ensure English for mmr/mch/clpk 45-vol Thai translations."""
    # Rebuild en from th using TH_EN more carefully
    for v in vols:
        th = v["title"]["th"]
        v["title"]["en"] = thai_modern_to_en(th)
    return vols


def parse_slk(path: Path) -> list[dict]:
    """57 physical books from Buddha Jayanti (cover nos may split)."""
    text = path.read_text(encoding="utf-8")
    section = "vin"
    vols = []
    for line in text.splitlines():
        section = track_section(line, section)
        args = macro_args(line, "slksplititem", 4) or macro_args(line, "slksplitcont", 4)
        if args:
            th = args[2].strip()
            vols.append(entry(len(vols) + 1, section, thai_pali_to_roman(th), th))
            continue
        args = macro_args(line, "slkitem", 2)
        if args:
            th = args[1].strip()
            vols.append(entry(len(vols) + 1, section, thai_pali_to_roman(th), th))
    # curated roman for slk
    for v in vols:
        en = v["title"]["en"]
        for a, b in [
            ("Parajikapali", "Pārājikapāli"),
            ("Pacittiyapali", "Pācittiyapāli"),
            ("Mahavaggapali", "Mahāvaggapāli"),
            ("Cullavaggapali", "Cullavaggapāli"),
            ("Parivarapali", "Parivārapāli"),
            ("Dighanikaya", "Dīghanikāya"),
            ("Majjhimanikaya", "Majjhimanikāya"),
            ("Samyuttanikaya", "Saṃyuttanikāya"),
            ("Anguttaranikaya", "Aṅguttaranikāya"),
            ("Khuddakapatha", "Khuddakapāṭha"),
            ("Dhammapada", "Dhammapada"),
            ("Udana", "Udāna"),
            ("Itivuttakapali", "Itivuttakapāli"),
            ("Suttanipatapali", "Suttanipātapāli"),
            ("Vimanavatthu", "Vimānavatthu"),
            ("Petavatthupali", "Petavatthupāli"),
            ("Thera-Therigathapali", "Thera-Therīgāthāpāli"),
            ("Jatakapali", "Jātakapāli"),
            ("Mahaniddesapali", "Mahāniddesapāli"),
            ("Culaniddesapali", "Cūḷaniddesapāli"),
            ("Patisambhidamaggapali", "Paṭisambhidāmaggapāli"),
            ("Apadanapali", "Apadānapāli"),
            ("Buddhavamsa", "Buddhavaṃsa"),
            ("Cariyapitakapali", "Cariyāpiṭakapāli"),
            ("Nettippakaranapali", "Nettippakaraṇapāli"),
            ("Petakopadesapali", "Peṭakopadesapāli"),
            ("Dhammasangani", "Dhammasaṅgaṇī"),
            ("Vibhanga", "Vibhaṅga"),
            ("Kathavatthu", "Kathāvatthu"),
            ("Dhatukatha", "Dhātukathā"),
            ("Puggalapannatti", "Puggalapaññatti"),
            ("Patthana", "Paṭṭhāna"),
        ]:
            en = en.replace(a, b)
        v["title"]["en"] = en
    return vols


def polish_ndz(vols: list[dict]) -> list[dict]:
    """Fix known Thai→Roman quirks in NDZ English titles (Thai stays TeX-faithful)."""
    fixes = (
        ("Dīpavṃsa", "Dīpavaṃsa"),
        ("Mahāvṃsa", "Mahāvaṃsa"),
        ("Cullavṃsa", "Cullavaṃsa"),
        ("Visudadhimagga", "Visuddhimagga"),
    )
    for v in vols:
        en = v["title"]["en"]
        for a, b in fixes:
            en = en.replace(a, b)
        v["title"]["en"] = en
    return vols


def parse_ndz(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    section = "vin"
    vols = []
    for line in text.splitlines():
        section = track_section(line, section)
        args = macro_args(line, "ndzsplititem", 4) or macro_args(line, "ndzsplitcont", 4)
        if args:
            pali = args[2].strip()
            jp = clean_tex(args[3])
            vols.append(entry(len(vols) + 1, section, f"{jp} ({thai_pali_to_roman(pali)})", pali))
            continue
        args = macro_args(line, "ndzitembreak", 2) or macro_args(line, "ndzitem", 2)
        if args:
            jp = clean_tex(args[0])
            pali = args[1].strip()
            vols.append(entry(len(vols) + 1, section, f"{jp} ({thai_pali_to_roman(pali)})", pali))
            continue
        args = macro_args(line, "catalognote", 1)
        if args:
            note = clean_tex(args[0])
            vols.append(entry(len(vols) + 1, "kn", note, note))
    return vols


def parse_ycs(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    section = "vin"
    vols = []
    idx = 0
    for line in text.splitlines():
        section = track_section(line, section)
        m = re.search(r"\\setcounter\{enumi\}\{(\d+)\}", line)
        if m:
            idx = int(m.group(1))
            continue
        args = macro_args(line, "ycsitembreak", 2) or macro_args(line, "ycsitem", 2)
        if args:
            idx += 1
            zh = clean_tex(args[0])
            pali = args[1].strip()
            vols.append(entry(idx, section, f"{zh} ({thai_pali_to_roman(pali)})", pali))
            continue
        args = macro_args(line, "catalognote", 1)
        if args:
            idx += 1
            note = clean_tex(args[0])
            vols.append(entry(idx, "kn", note, note))
    return vols


def parse_tai(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    vols = []
    for line in text.splitlines():
        m = re.search(r"\\vriitem\{([^}]*)\}\{([^}]*)\}", line)
        if m:
            th = m.group(2).strip()
            vols.append(entry(len(vols) + 1, "vin", thai_pali_to_roman(th), th))
    curated = {
        1: "Pārājikapāḷi",
        2: "Pācittiyapāḷi",
        3: "Mahāvaggapāḷi",
        4: "Cūḷavaggapāḷi",
        5: "Parivārapāḷi",
    }
    for v in vols:
        v["title"]["en"] = curated.get(v["index"], v["title"]["en"])
    return vols


def parse_vnm(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    section = "dn"
    vols = []
    idx = 0
    for line in text.splitlines():
        section = track_section(line, section)
        m = re.search(r"\\setcounter\{enumi\}\{(\d+)\}", line)
        if m:
            idx = int(m.group(1))
            continue
        m = re.search(r"\\vnmitem\{([^}]*)\}\{([^}]*)\}", line)
        if m:
            idx += 1
            vi = m.group(1).strip()
            th = m.group(2).strip()
            vols.append(entry(idx, section, vi, th))
    return vols


def emit_module(name: str, code: str, source: str, vols: list[dict], notes: str = "") -> str:
    lines = [
        f"# === {name} ===",
        f"# hall edition code(s): {code}",
        f"# source: tipitaka-catalog/catalog/content/{source}",
        f"# count: {len(vols)}",
    ]
    if notes:
        for n in notes.split("\n"):
            lines.append(f"# {n}")
    lines.append(f"{name} = [")
    for v in vols:
        lines.append("    {")
        lines.append(f'        "index": {v["index"]},')
        lines.append(f'        "section": "{v["section"]}",')
        if "catalog_no" in v:
            cn = str(v["catalog_no"]).replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f'        "catalog_no": "{cn}",')
        if v.get("not_published"):
            lines.append('        "not_published": True,')
        lines.append('        "title": {')
        en = v["title"]["en"].replace("\\", "\\\\").replace('"', '\\"')
        th = v["title"]["th"].replace("\\", "\\\\").replace('"', '\\"')
        lines.append(f'            "en": "{en}",')
        lines.append(f'            "th": "{th}",')
        lines.append("        },")
        lines.append("    },")
    lines.append("]")
    lines.append("")
    return "\n".join(lines)


def main():
    editions = []

    mch_pali = polish_mch_pali(parse_item_pali(BASE / "mch-pali-thai.tex"))
    editions.append(
        (
            "MCH_PALI_VOLUMES",
            "pali2506",
            "mch-pali-thai.tex",
            mch_pali,
            "Compare to MMR Pāli (mmr_pali_volumes): MCU uses -pāli locative forms "
            "(Mahāvibhaṅgapāli vs MMR Mahāvibhaṅgassa); Cūḷa vs Cullavagga; "
            "AN named nipātas vs MMR numbered bhāga; KN/Abhidhamma wording differs slightly; "
            "same 8+3+3+5+5+9+12 = 45 structure.",
        )
    )

    mmr_thai = polish_thai45_en(parse_volumeentry(BASE / "mmr-thai.tex"), "mmr")
    editions.append(("MMR_THAI_VOLUMES", "th2559", "mmr-thai.tex", mmr_thai, ""))

    mch_thai = polish_thai45_en(parse_simple_items(BASE / "mch-thai.tex"), "mch")
    editions.append(("MCH_THAI_VOLUMES", "th2539", "mch-thai.tex", mch_thai, ""))

    clpk = polish_thai45_en(parse_simple_items(BASE / "clpk-thai.tex"), "clpk")
    editions.append(("CLPK_THAI_VOLUMES", "th2549", "clpk-thai.tex", clpk, ""))

    mmr91 = fix_mmr91_en(parse_mmr91(BASE / "_body-mmr-91.tex"))
    editions.append(
        (
            "MMR_91_VOLUMES",
            "th2525, th2552",
            "_body-mmr-91.tex",
            mmr91,
            "Tipiṭaka+Aṭṭhakathā; ranges expanded to printed volume numbers 1–91.",
        )
    )

    sdb = parse_sdb(BASE / "sdb-pali-thai.tex")
    editions.append(
        (
            "SDB_THAI_VOLUMES",
            "sdb/th2528",
            "sdb-pali-thai.tex",
            sdb,
            "Maha-Vitthara-Naya Tipiṭaka; \\catalogvolrangeline expanded to 1–100 "
            "with Thai ภาค for multi-volume titles.",
        )
    )

    lao = polish_lao(parse_bilingual_item(BASE / "lao-pali-lao.tex", "laoitem", th_arg=2))
    lao_sections = (
        ["vin"] * 5
        + ["dn"] * 3
        + ["mn"] * 3
        + ["sn"] * 5
        + ["an"] * 6
        + ["kn"] * 11
        + ["abh"] * 12
    )
    for i, v in enumerate(lao, 1):
        v["index"] = i
        v["section"] = lao_sections[i - 1]
    editions.append(
        (
            "LAO_PALI_VOLUMES",
            "lao/pali2556",
            "lao-pali-lao.tex",
            lao,
            "Vinaya is 5 vols (Chaṭṭha-like), not 8; AN=6, KN=11, Abhidhamma Yamaka 3 + Paṭṭhāna 5.",
        )
    )

    nld = nld_from_script()
    editions.append(("NLD_PALI_VOLUMES", "nld/pali2560", "nld-pali-devanagari.tex", nld, "41 vols; en from IAST in generator script."))

    slk = parse_slk(BASE / "slk-pali-sinhala.tex")
    editions.append(
        (
            "SLK_PALI_VOLUMES",
            "bj/pali2499",
            "slk-pali-sinhala.tex",
            slk,
            "57 physical volumes (cover numbers 1–52 with splits). th = Thai-script Pāli from TeX.",
        )
    )

    pts_pali_all = parse_pts_pali(BASE / "pts-pali-roman.tex")
    catalogitem_only = [dict(v) for v in pts_pali_all if v["title"]["en"] != "Index"]
    for i, v in enumerate(catalogitem_only, 1):
        v["index"] = i
    pts_with_index = [dict(v) for v in pts_pali_all]
    for i, v in enumerate(pts_with_index, 1):
        v["index"] = i
    editions.append(
        (
            "PTS_PALI_VOLUMES",
            "pts/pali2424",
            "pts-pali-roman.tex",
            catalogitem_only,
            f"\\catalogitem only → {len(catalogitem_only)}. Meta says 57 vols including Index; "
            f"see PTS_PALI_VOLUMES_WITH_INDEX ({len(pts_with_index)}) for Index lines too.",
        )
    )
    editions.append(
        (
            "PTS_PALI_VOLUMES_WITH_INDEX",
            "pts/pali2424",
            "pts-pali-roman.tex",
            pts_with_index,
            "Includes bare \\item Index entries (DN/MN/SN/AN/Niddesa indexes). "
            "title.th = Thai-script Pāli (ปริวรรต) via PTS_PALI_TITLE_TH.",
        )
    )

    pts_en = parse_pts_english(BASE / "pts-english.tex")
    editions.append(
        (
            "PTS_ENGLISH_VOLUMES",
            "pts/en2438",
            "pts-english.tex",
            pts_en,
            "Concordance rows from \\ptsrow / \\ptsnone (Pāli slot labels via catalog_no). "
            "title = '{pali} -- {english|Not Published}'. Splits 33.(1)/33.(2) and 34.(1)/34.(2) "
            "are separate rows. Sequential index 1..N; display number = catalog_no.",
        )
    )

    tai = parse_tai(BASE / "tai-pali-shan.tex")
    editions.append(("TAI_PALI_VOLUMES", "tai/pali2567", "tai-pali-shan.tex", tai, "Vinaya only (5)."))

    vnm = parse_vnm(BASE / "vnm-vietnamese.tex")
    editions.append(
        (
            "VNM_VIETNAMESE_VOLUMES",
            "vnm/vi2563",
            "vnm-vietnamese.tex",
            vnm,
            "Sutta only 13 vols; title.en = Vietnamese; title.th = Thai description from TeX.",
        )
    )

    ndz = polish_ndz(parse_ndz(BASE / "ndz-japanese.tex"))
    editions.append(
        (
            "NDZ_JAPANESE_VOLUMES",
            "ndz/ja2544",
            "ndz-japanese.tex",
            ndz,
            "65 set / ~70 physical with splits; includes 蔵外 + index note. "
            "title.en = Japanese (+ Roman of Pāli); title.th = Thai-script Pāli from TeX.",
        )
    )

    ycs = parse_ycs(BASE / "ycs-chinese.tex")
    editions.append(
        (
            "YCS_CHINESE_VOLUMES",
            "ych/zh2533",
            "ycs-chinese.tex",
            ycs,
            "Parallel to NDZ structure; title.en = Chinese (+ Roman Pāli); title.th = Thai-script Pāli.",
        )
    )

    rpo = polish_rpo(parse_item_pali(BASE / "rpo-pali-lanna.tex"))
    # fix sections: sutta first then abh then vin
    rpo_sec = ["dn"] * 5 + ["mn"] * 7 + ["sn"] * 6 + ["an"] * 8 + ["kn"] * 29 + ["abh"] * 12 + ["vin"] * 13
    for i, v in enumerate(rpo, 1):
        v["index"] = i
        v["section"] = rpo_sec[i - 1]
    editions.append(
        (
            "RPO_LANNA_VOLUMES",
            "lan/lanna2556",
            "rpo-pali-lanna.tex",
            rpo,
            "80 vols; order Suttanta→Abhidhamma→Vinaya (Wat Rampoeng).",
        )
    )

    khm = parse_khm(BASE / "khm-pali-khmer.tex")
    editions.append(
        (
            "KHM_PALI_VOLUMES",
            "kmr/pali2472",
            "khm-pali-khmer.tex",
            khm,
            "Range-based catalog expanded to 110 individual volume numbers.",
        )
    )

    header = '''# -*- coding: utf-8 -*-
"""Auto-extracted Tipiṭaka volume title lists from tipitaka-catalog TeX.

Each list entry:
    {"index": int, "section": "vin"|"dn"|"mn"|"sn"|"an"|"kn"|"abh",
     "title": {"en": str, "th": str}}

Hall edition codes noted per list. Generated by extract_catalog_volumes.py — review before seeding.
"""
from __future__ import annotations

'''
    parts = [header]
    summary = []
    for name, code, source, vols, notes in editions:
        parts.append(emit_module(name, code, source, vols, notes))
        summary.append(f"  {code:20} {name:28} n={len(vols):3}  ← {source}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(parts), encoding="utf-8")
    SUMMARY.write_text(
        "EXTRACTED VOLUME LISTS\n" + "\n".join(summary) + f"\n\nFull data: {OUT}\n",
        encoding="utf-8",
    )
    print("\n".join(summary))
    print("Wrote", OUT)
    print("Wrote", SUMMARY)


if __name__ == "__main__":
    main()
