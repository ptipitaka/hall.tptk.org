"""Core converter: Roman (IAST) ↔ Thai for Pāli."""

from __future__ import annotations

import re
from enum import Enum
from functools import lru_cache
from typing import Any

from .data_loader import load_glyphs, load_scripts
from .roman import normalize_roman_input
from .thai import beautify_thai, unbeautify_thai


class Script(str, Enum):
    ROMAN = "roman"
    THAI = "thai"
    AUTO = "auto"


@lru_cache(maxsize=1)
def _tables() -> dict[str, Any]:
    g = load_glyphs()
    cons_by_roman = {c["roman"]: c for c in g["consonants"]}
    cons_by_thai = {c["thai"]: c for c in g["consonants"]}
    vow_by_roman = {v["roman"]: v for v in g["vowels"]}
    roman_cons_keys = sorted(cons_by_roman.keys(), key=len, reverse=True)
    roman_vow_keys = sorted(vow_by_roman.keys(), key=len, reverse=True)

    niggahita = next(s for s in g["specials"] if s["id"] == "niggahita")
    virama = g["thai"]["virama"]
    digits_r2t = {d["roman"]: d["thai"] for d in g["digits"]}
    digits_t2r = {d["thai"]: d["roman"] for d in g["digits"]}

    dep_vowel_thai = {
        v["thai_dep"]: v
        for v in g["vowels"]
        if v.get("thai_dep") is not None and v["thai_dep"] != ""
    }

    indep_pairs: list[tuple[str, dict]] = []
    for v in g["vowels"]:
        indep = v.get("thai_indep")
        if indep:
            indep_pairs.append((indep, v))
        short = v.get("thai_indep_short")
        if short:
            indep_pairs.append((short, v))
    indep_pairs.sort(key=lambda p: len(p[0]), reverse=True)

    return {
        "glyphs": g,
        "cons_by_roman": cons_by_roman,
        "cons_by_thai": cons_by_thai,
        "vow_by_roman": vow_by_roman,
        "roman_cons_keys": roman_cons_keys,
        "roman_vow_keys": roman_vow_keys,
        "niggahita": niggahita,
        "virama": virama,
        "digits_r2t": digits_r2t,
        "digits_t2r": digits_t2r,
        "dep_vowel_thai": dep_vowel_thai,
        "indep_pairs": indep_pairs,
        "tone_marks": set(g["thai"]["tone_marks"]),
        "mai_han": g["thai"]["mai_han_akat"],
        "mai_taikhu": g["thai"]["mai_taikhu"],
        "sara_a": g["thai"]["sara_a"],
    }


def detect_script(text: str) -> Script:
    """Detect dominant script from Unicode ranges in scripts.json."""
    scripts = load_scripts()["scripts"]
    counts: dict[str, int] = {s["code"]: 0 for s in scripts}
    for ch in text:
        code = ord(ch)
        for s in scripts:
            for rng in s["ranges"]:
                lo, hi = rng[0], rng[1]
                if lo <= code <= hi:
                    if s["code"] == "roman" and code < 128 and not ch.isalpha():
                        continue
                    counts[s["code"]] += 1
                    break
    if counts.get("thai", 0) > 0:
        return Script.THAI
    if counts.get("roman", 0) > 0:
        return Script.ROMAN
    return Script.ROMAN


def convert(
    text: str,
    from_script: Script | str,
    to_script: Script | str,
    *,
    thai_pua: bool = False,
) -> str:
    """Convert Pāli text between scripts (v1: roman ↔ thai)."""
    src = Script(from_script) if not isinstance(from_script, Script) else from_script
    dst = Script(to_script) if not isinstance(to_script, Script) else to_script
    if src == Script.AUTO:
        src = detect_script(text)
    if src == dst:
        if src == Script.ROMAN:
            return normalize_roman_input(text)
        return text
    if src == Script.ROMAN and dst == Script.THAI:
        return _roman_to_thai(text, thai_pua=thai_pua)
    if src == Script.THAI and dst == Script.ROMAN:
        return _thai_to_roman(text)
    raise ValueError(f"Unsupported conversion: {src.value} → {dst.value}")


def _match_longest(text: str, i: int, keys: list[str]) -> str | None:
    for key in keys:
        if text.startswith(key, i):
            return key
    return None


def _roman_to_thai(text: str, *, thai_pua: bool = False) -> str:
    text = normalize_roman_input(text)
    t = _tables()
    out: list[str] = []
    i = 0
    n = len(text)
    cons_buf: list[dict] = []

    def flush_cluster(vowel: dict | None) -> None:
        nonlocal cons_buf
        if not cons_buf:
            if vowel is not None:
                if vowel["roman"] == "a":
                    out.append(vowel.get("thai_indep_short", "อ"))
                else:
                    out.append(vowel.get("thai_indep") or "")
            return
        for c in cons_buf[:-1]:
            out.append(c["thai"] + t["virama"])
        last = cons_buf[-1]["thai"]
        if vowel is None:
            out.append(last + t["virama"])
        elif vowel.get("inherent"):
            out.append(last)
        else:
            dep = vowel.get("thai_dep")
            if dep is None:
                out.append(last + t["virama"])
                out.append(vowel.get("thai_indep") or "")
            else:
                out.append(last + dep)
        cons_buf = []

    while i < n:
        ch = text[i]
        if ch.isspace() or ch in "[]()·–—.,;:/\\\"'?!…°ʼ-":
            flush_cluster(None)
            out.append(ch)
            i += 1
            continue
        if ch in t["digits_r2t"]:
            flush_cluster(None)
            out.append(t["digits_r2t"][ch])
            i += 1
            continue

        nig = t["niggahita"]["roman"]
        if text.startswith(nig, i):
            if cons_buf:
                flush_cluster(t["vow_by_roman"]["a"])
            elif out and out[-1].endswith(t["virama"]):
                out[-1] = out[-1][: -len(t["virama"])]
            out.append(t["niggahita"]["thai"])
            i += len(nig)
            continue

        cons_key = _match_longest(text, i, t["roman_cons_keys"])
        if cons_key is not None:
            cons_buf.append(t["cons_by_roman"][cons_key])
            i += len(cons_key)
            continue

        vow_key = _match_longest(text, i, t["roman_vow_keys"])
        if vow_key is not None:
            flush_cluster(t["vow_by_roman"][vow_key])
            i += len(vow_key)
            continue

        flush_cluster(None)
        out.append(ch)
        i += 1

    flush_cluster(None)
    return beautify_thai("".join(out), thai_pua=thai_pua)


def _thai_to_roman(text: str) -> str:
    text = unbeautify_thai(text)
    t = _tables()
    cons = t["cons_by_thai"]
    out: list[str] = []
    i = 0
    n = len(text)
    virama = t["virama"]
    nig = t["niggahita"]["thai"]
    mai_han = t["mai_han"]
    mai_taikhu = t["mai_taikhu"]
    sara_a = t["sara_a"]
    tones = t["tone_marks"]

    while i < n:
        ch = text[i]
        if ch in tones or ch == mai_taikhu:
            i += 1
            continue
        if ch in t["digits_t2r"]:
            out.append(t["digits_t2r"][ch])
            i += 1
            continue
        if ch.isspace() or ch in "[]()·–—.,;:/\\\"'?!…°ʼ-":
            out.append(ch)
            i += 1
            continue
        if ch == nig:
            out.append(t["niggahita"]["roman"])
            i += 1
            continue

        matched_indep = False
        for indep, vow in t["indep_pairs"]:
            if not text.startswith(indep, i):
                continue
            if indep == "อ":
                nxt = text[i + 1] if i + 1 < n else ""
                if nxt in t["dep_vowel_thai"] or nxt in (mai_han, sara_a, nig):
                    if nxt in (mai_han, sara_a):
                        out.append("a")
                        i += 2
                    elif nxt == nig:
                        out.append("aṃ")
                        i += 2
                    else:
                        out.append(t["dep_vowel_thai"][nxt]["roman"])
                        i += 2
                    matched_indep = True
                    break
                out.append("a")
                i += 1
                matched_indep = True
                break
            out.append(vow["roman"])
            i += len(indep)
            matched_indep = True
            break
        if matched_indep:
            continue

        if ch in cons:
            cluster_roman = cons[ch]["roman"]
            j = i + 1
            while j + 1 < n and text[j] == virama and text[j + 1] in cons:
                cluster_roman += cons[text[j + 1]]["roman"]
                j += 2
            if j < n and text[j] == virama:
                out.append(cluster_roman)
                i = j + 1
                continue
            if j < n and text[j] in t["dep_vowel_thai"]:
                out.append(cluster_roman + t["dep_vowel_thai"][text[j]]["roman"])
                i = j + 1
                continue
            if j < n and text[j] in (mai_han, sara_a):
                out.append(cluster_roman + "a")
                i = j + 1
                continue
            if j < n and text[j] == nig:
                out.append(cluster_roman + "a")
                i = j
                continue
            out.append(cluster_roman + "a")
            i = j
            continue

        if ch in t["dep_vowel_thai"]:
            out.append(t["dep_vowel_thai"][ch]["roman"])
            i += 1
            continue
        if ch in (mai_han, sara_a):
            out.append("a")
            i += 1
            continue
        if ch == virama:
            i += 1
            continue

        out.append(ch)
        i += 1

    return re.sub(r" {2,}", " ", "".join(out))
