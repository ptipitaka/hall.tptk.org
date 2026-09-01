"""Multi-script text helpers for cs-roman segment JSON."""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any

from paths import ensure_import_paths

ensure_import_paths()

from pali_script import Script, convert  # noqa: E402

from cs_roman_bold import (  # noqa: E402
    bold_ranges_one_per_span,
    clip_ranges,
    ranges_to_runs,
)

# Legacy sentence-spacer markers (retired). Normalize strips them to ordinary
# ``. `` / word space — TeX no longer emits ``\\csromanspacer`` from these.
SP1_MARKER = "{{sp1}}"
SP3_MARKER = "{{sp3}}"
# Brief experiment marker; demigrated to periods before pot-ma-gyi normalize.
SP_MARKER = "{{sp}}"
# Centered-block manual line break (typesetter's break inside a centered block,
# e.g. pātimokkha-uddesa ``…dhammā`` / ``uddesaṃ āgacchanti.``). Preserved through
# roman→thai transliteration; TeX renders it as ``\\`` inside ``\csromancenter``.
BR_MARKER = "{{br}}"
# Body units run sentence-stop normalize (collapse pot-ma-gyi / strip legacy
# spacers). Titles, chapters, footnotes skip inject paths historically gated
# by this set — still used as ``normalize_spacing`` for body vs heading.
_SENTENCE_SPACER_TYPES = frozenset(
    {
        "prose",
        "prose_continuation",
        "verse",
        "verse_continuation",
        "gatha",
        "gatha_continuation",
    }
)
_INLINE_MARKER_RE = re.compile(
    r"(\{\{n\d+\}\}|\{\{\*\}\}|\{\{\+\}\}|\{\{sp1\}\}|\{\{sp3\}\}|\{\{br\}\})"
)
_SP_MARKER_RE = re.compile(r"\{\{sp[13]\}\}")
# CS Roman peyyāla mark → Thai Tipiṭaka ฯเปฯ (do not letter-transliterate to -ป-).
_SPECIAL_CHUNK_RE = re.compile(
    r"(\{\{n\d+\}\}|\{\{\*\}\}|\{\{\+\}\}|\{\{sp1\}\}|\{\{sp3\}\}|\{\{br\}\}|-pa-)",
    re.IGNORECASE,
)
# CS→Thai letter convert maps ASCII digits to Thai digits; publication uses Arabic.
_THAI_DIGITS_TO_ARABIC = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")

# CS Roman pot-ma-gyi ``. .`` → ordinary full stop + word space (Thai edition).
_POT_MA_GYI_RE = re.compile(r"\. \. ?")
# Legacy double-spacer pot-ma-gyi → ordinary stop + word space.
_LEGACY_DOUBLE_SP1_RE = re.compile(r"\.\{\{sp1\}\}\{\{sp1\}\} ?")
# Legacy glued stop ``.{{sp1}}Word`` (no space) → ``. Word``.
_LEGACY_GLUED_STOP_SP1_RE = re.compile(
    r"\.\{\{sp1\}\}(?!\{\{sp1\}\})(?=\S)"
)
# Older bug: stop eaten so ``word{{sp1}}Word`` → ``word. Word``.
# Preceding char must be a letter (not ``}`` from another ``{{…}}`` marker).
_GLUED_SP1_RE = re.compile(
    r"([^\W\d_])\{\{sp1\}\}(?!\{\{sp1\}\})(?=\S)"
)
# Detect text that still needs spacing normalize (enrich / ensure): raw
# pot-ma-gyi or leftover spacer markers — not ordinary ``. next``.
_NEEDS_SPACING_RE = re.compile(
    r"\. \."
    r"|\{\{sp(?:1|3)?\}\}"
)
# Canonical body sentence stop after pot-ma-gyi / legacy-marker collapse.
_ORDINARY_SENTENCE_STOP = ". "
# PDF text extraction turns the short end-of-section rule into underscores.
_SECTION_RULE_RE = re.compile(r"\s*_{3,}\s*$")
SECTION_RULE_FLAG = "section_rule"

# Ordinal section closers: same name as the open category head, declined, plus
# an ordinal matching section_no (e.g. heading ``1. ปริมณฺฑลวคฺค`` → closer
# ``ปริมณฺฑลวคฺโค ปฐโม.``). Markers are nominative forms of category nouns;
# extend the tuples when a new category family is confirmed (นิปาโต, …).
ORDINAL_SECTION_CLOSER_MARKERS_THAI = (
    "วคฺโค",
)
ORDINAL_SECTION_CLOSER_MARKERS_ROMAN = (
    "vaggo",
)
_THAI_MASC_SECTION_ORDINAL = (
    r"ปฐโม|ทุติโย|ตติโย|จตุตฺโถ|ปญฺจโม|ฉฏฺโฐ|สตฺตโม|อฏฺฐโม|นวโม|ทสโม|"
    r"เอกาทสโม|ทฺวาทสโม|เตรสโม|จุทฺทสโม|ปนฺนรสโม|โสฬสโม"
)
_ROMAN_MASC_SECTION_ORDINAL = (
    r"pa[tṭ]hamo|dutiyo|tatiyo|catuttho|pa[nñ]camo|cha[tṭ]tho|sattamo|"
    r"a[tṭ]thamo|navamo|dasamo|ek[aā]dasamo|dv[aā]dasamo"
)
_INLINE_MARKER_STRIP_RE = re.compile(
    r"\{\{(?:n\d+|\*|\+|\[\]|\(\)|sp1|sp3|sp|sb|br)\}\}"
)


def _ordinal_section_closer_pattern(
    markers: tuple[str, ...], ordinals: str, *, flags: int = 0
) -> re.Pattern[str]:
    marker_alt = "|".join(re.escape(m) for m in markers)
    # Short line only: avoid body prose that merely ends near an ordinal.
    return re.compile(
        rf"^(?=.{{1,90}}$)\s*.*(?:{marker_alt})\s+(?:{ordinals})\s*\.?\s*$",
        flags,
    )


_ORDINAL_SECTION_CLOSER_THAI_RE = _ordinal_section_closer_pattern(
    ORDINAL_SECTION_CLOSER_MARKERS_THAI, _THAI_MASC_SECTION_ORDINAL
)
_ORDINAL_SECTION_CLOSER_ROMAN_RE = _ordinal_section_closer_pattern(
    ORDINAL_SECTION_CLOSER_MARKERS_ROMAN,
    _ROMAN_MASC_SECTION_ORDINAL,
    flags=re.IGNORECASE,
)


def plain_closer_probe_text(text: str) -> str:
    """Strip inline markers / light wrappers for closer-formula probes."""
    plain = _INLINE_MARKER_STRIP_RE.sub("", text or "")
    plain, _had_rule = split_trailing_section_rule(plain)
    return plain.strip()


def is_ordinal_section_closer(text: str) -> bool:
    """True for declined category + ordinal closers (``…วคฺโค ปฐโม.``).

    Not for sutta-end ``…ปฐมํ.``, apadāna titles, or bare ordinals. Add
    markers to ``ORDINAL_SECTION_CLOSER_MARKERS_*`` when new families appear.
    """
    plain = plain_closer_probe_text(text)
    if not plain or len(plain) > 90:
        return False
    return bool(
        _ORDINAL_SECTION_CLOSER_THAI_RE.match(plain)
        or _ORDINAL_SECTION_CLOSER_ROMAN_RE.match(plain)
    )


def ensure_ordinal_closer_section_rule(text: str, section_rule: bool) -> bool:
    """Ordinal category closers always carry ``section_rule`` in our edition.

    CS sometimes drops the underscore rule when the closer sits on a page
    foot that already has a footnote separator (pagination, not structure).
    Our layout differs, so restore the conventional end rule.
    """
    if section_rule:
        return True
    return is_ordinal_section_closer(text)


# Neuter/feminine -ṃ ordinals after the end-verb (…นิฏฺฐิตํ นวมํ.) or
# between stem and verb (…สิกฺขาปทํ ปฐมํ นิฏฺฐิตํ.).
_CLOSER_NEUTER_ORDINALS = (
    r"ปฐมํ|ทุติยํ|ตติยํ|จตุตฺถํ|ปญฺจมํ|ฉฏฺฐํ|สตฺตมํ|อฏฺฐมํ|นวมํ|ทสมํ|"
    r"เอกาทสมํ|ทฺวาทสมํ|เตรสมํ|จุทฺทสมํ|ปนฺนรสมํ|โสฬสมํ|"
    r"pa[tṭ]hama[ṃṁm]|dutiya[ṃṁm]|tatiya[ṃṁm]|catuttha[ṃṁm]|"
    r"pa[nñ]cama[ṃṁm]|cha[tṭ]tha[ṃṁm]|sattama[ṃṁm]|a[tṭ]thama[ṃṁm]|"
    r"navama[ṃṁm]|dasama[ṃṁm]|ek[aā]dasama[ṃṁm]|dv[aā]dasama[ṃṁm]|"
    r"terasama[ṃṁm]|cuddasama[ṃṁm]|pannarasama[ṃṁm]|so[ḷl]asama[ṃṁm]"
)
_CLOSER_TRAILING_ORDINAL = rf"(?:\s+(?:{_CLOSER_NEUTER_ORDINALS}))?"
# End formulas: นิฏฺฐิตํ/า/โต/านิ and สมตฺตํ/า/โต/านิ (Thai leading-vowel โต).
# Roman mirrors niṭṭhitaṃ / samattaṃ and gendered -o / -ā / -āni.
# Optional trailing sutta/rule ordinal: …niṭṭhitaṃ navamaṃ.
_SECTION_CLOSER_FORMULA_THAI_RE = re.compile(
    r"(?:นิฏฺฐิ(?:ตํ|ตา|ตานิ|โต)|สมตฺต(?:ํ|า|านิ)|สมตฺโต)"
    rf"{_CLOSER_TRAILING_ORDINAL}\s*\.?$"
)
_SECTION_CLOSER_FORMULA_ROMAN_RE = re.compile(
    r"(?:ni[ṭt]{1,2}hit(?:a[ṃṁm]|ā|o|āni)|samatt(?:a[ṃṁm]|ā|o|āni))"
    rf"{_CLOSER_TRAILING_ORDINAL}\s*\.?$",
    re.IGNORECASE,
)
# Split ``…cāti.{{sp1}} Mūlapaṇṇāsako samatto.`` after the verse-ending stop.
_TRAILING_CLOSER_SPLIT_RE = re.compile(
    r"^(?P<body>.*[.!?…][\"'\u201c\u201d]?)"
    r"(?:\{\{sp1\}\}+|\s+)"
    r"\s*"
    r"(?P<closer>\S.+)$",
    re.DOTALL,
)


def is_section_closer_formula(text: str) -> bool:
    """True for short niṭṭhitaṃ / samattaṃ (any gender) or ordinal closers.

    Used to recognize standalone end formulas and to peel them off the end of
    a verse/prose unit after a sentence stop. Rejects long body prose.
    Trailing sutta/rule ordinals after the verb (``…นิฏฺฐิตํ นวมํ.`` /
    ``…niṭṭhitaṃ navamaṃ.``) count; a short parenthetical prefix such as
    ``(Aññābhāgiya)`` is allowed because the probe searches the ending.
    """
    plain = plain_closer_probe_text(text)
    if not plain or len(plain) > 90:
        return False
    if is_ordinal_section_closer(plain):
        return True
    return bool(
        _SECTION_CLOSER_FORMULA_THAI_RE.search(plain)
        or _SECTION_CLOSER_FORMULA_ROMAN_RE.search(plain)
    )


def peel_trailing_section_closer(text: str) -> tuple[str, str] | None:
    """Split a trailing section closer after a sentence stop / ``{{sp1}}``.

    Example: ``…จาติ.{{sp1}} มูลปณฺณาสโก สมตฺโต.`` →
    (``…จาติ.``, ``มูลปณฺณาสโก สมตฺโต.``).

    The trailer must itself be a section-closer formula (not the next verse
    line). Nested ``{{sp1}}`` inside the trailer is rejected so multi-sentence
    bodies are not mis-split.
    """
    raw = (text or "").rstrip()
    if not raw:
        return None
    m = _TRAILING_CLOSER_SPLIT_RE.match(raw)
    if m is None:
        return None
    body = m.group("body").rstrip()
    closer = m.group("closer").strip()
    if not body or not closer:
        return None
    if SP1_MARKER in closer:
        return None
    if not is_section_closer_formula(closer):
        return None
    # Keep a real verse/prose remnant (not punctuation alone).
    remnant = plain_closer_probe_text(strip_sentence_spacers(body))
    if len(remnant) < 2:
        return None
    return body, closer


# Structural level of what a section-closer formula closes (lexical stem).
# Visual TeX uses only three tiers via ``closer_tier``; keep this enum fine-
# grained so new families can map without retuning macros.
CLOSER_LEVELS = frozenset(
    {
        "pāḷi",
        "saṃyutta_pāḷi",
        "nipāta_pāḷi",
        "nikāya",
        "khandhaka",
        "kaṇḍa",
        "paṇṇāsaka",
        "nipāta",
        "saṃyutta",
        "ordinal_vagga",
        "vagga",
        "vibhaṅga",
        "sikkhāpada",
        "sutta",
        "kathā",
        "bhāṇavāra",
        "vāra",
        "vatthu",
        "vatta",
        "pabbajjā",
        "kamma",
        "pārājika_unit",
        "peyyāla",
        "analytic",
        "unknown",
    }
)
CLOSER_TIERS = frozenset({"major", "mid", "leaf"})
_CLOSER_LEVEL_TO_TIER: dict[str, str] = {
    "pāḷi": "major",
    "saṃyutta_pāḷi": "major",
    "nipāta_pāḷi": "major",
    "nikāya": "major",
    "khandhaka": "major",
    "kaṇḍa": "major",
    "paṇṇāsaka": "major",
    "nipāta": "major",
    "vibhaṅga": "major",
    "saṃyutta": "mid",
    "ordinal_vagga": "mid",
    "vagga": "mid",
    "sikkhāpada": "leaf",
    "sutta": "leaf",
    "kathā": "leaf",
    "bhāṇavāra": "leaf",
    "vāra": "leaf",
    "vatthu": "leaf",
    "vatta": "leaf",
    "pabbajjā": "leaf",
    "kamma": "leaf",
    "pārājika_unit": "leaf",
    "peyyāla": "leaf",
    "analytic": "leaf",
    "unknown": "leaf",
}
# Optional short ordinal between stem and end-verb (…สิกฺขาปทํ ปฐมํ นิฏฺฐิตํ.).
_CLOSER_INLINE_ORDINAL = _CLOSER_TRAILING_ORDINAL
# Verb cue after the closed noun. Thai ``สมตฺโต`` is สมตฺ + โ + ต
# (leading vowel before final consonant) — not the prefix ``สมตฺต``.
_CLOSER_VERB_CUE = (
    r"(?:นิฏฺฐิ|สมตฺตํ|สมตฺตา|สมตฺตานิ|สมตฺโต|"
    r"ni[ṭt]{1,2}hit|samatt)"
)
# Longest-rightmost lexical cues. Thai leading vowels sit *before* the final
# consonant (ภาณวาโร, ขนฺธโก, ปณฺณาสโก, นิกาโย) — match that orthography.
_CLOSER_LEVEL_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "saṃyutta_pāḷi",
        re.compile(
            rf"(?:สํยุตฺตปาฬิ|sa[ṃṁm]yutta(?:pāḷi|pāli))\s*{_CLOSER_VERB_CUE}",
            re.IGNORECASE,
        ),
    ),
    (
        "nipāta_pāḷi",
        re.compile(
            rf"(?:นิปาตปาฬิ|nip[aā]ta(?:pāḷi|pāli))\s*{_CLOSER_VERB_CUE}",
            re.IGNORECASE,
        ),
    ),
    (
        "pāḷi",
        re.compile(
            rf"(?:ปาฬิ|pāḷi|pāli)\s*{_CLOSER_VERB_CUE}",
            re.IGNORECASE,
        ),
    ),
    (
        "nikāya",
        re.compile(
            rf"(?:นิกาโย|nik[aā]yo)\s*{_CLOSER_VERB_CUE}",
            re.IGNORECASE,
        ),
    ),
    (
        "khandhaka",
        re.compile(
            rf"(?:ขนฺธโก|khandhako)\s*{_CLOSER_VERB_CUE}",
            re.IGNORECASE,
        ),
    ),
    (
        "kaṇḍa",
        re.compile(
            rf"(?:กณฺฑํ|ka[nṇ][dḍ]a[ṃṁm])\s*{_CLOSER_VERB_CUE}",
            re.IGNORECASE,
        ),
    ),
    (
        "paṇṇāsaka",
        re.compile(
            rf"(?:ปณฺณาสโก|pa[nṇ]{{1,2}}[aā]sako)\s*{_CLOSER_VERB_CUE}",
            re.IGNORECASE,
        ),
    ),
    (
        "nipāta",
        re.compile(
            rf"(?:นิปาตํ|nip[aā]ta[ṃṁm])\s*{_CLOSER_VERB_CUE}",
            re.IGNORECASE,
        ),
    ),
    (
        "vibhaṅga",
        re.compile(
            rf"(?:วิภงฺโค|vibha[nṅ]go)\s*{_CLOSER_VERB_CUE}",
            re.IGNORECASE,
        ),
    ),
    (
        "saṃyutta",
        re.compile(
            rf"(?:สํยุตฺตํ|sa[ṃṁm]yutta[ṃṁm])\s*{_CLOSER_VERB_CUE}",
            re.IGNORECASE,
        ),
    ),
    (
        "sikkhāpada",
        re.compile(
            rf"(?:สิกฺขาปท(?:ํ|านิ)|สิกฺกาปทํ|sikkh[aā]pad(?:a[ṃṁm]|āni))"
            rf"{_CLOSER_INLINE_ORDINAL}\s*{_CLOSER_VERB_CUE}",
            re.IGNORECASE,
        ),
    ),
    (
        "sutta",
        re.compile(
            rf"(?:สุตฺตํ|sutta[ṃṁm])\s*{_CLOSER_VERB_CUE}",
            re.IGNORECASE,
        ),
    ),
    (
        "kathā",
        re.compile(
            rf"(?:กถา|kath[aā])\s*{_CLOSER_VERB_CUE}",
            re.IGNORECASE,
        ),
    ),
    (
        "bhāṇavāra",
        re.compile(
            rf"(?:ภาณวาโร|bh[aā][nṇ]av[aā]ro)\s*{_CLOSER_VERB_CUE}",
            re.IGNORECASE,
        ),
    ),
    (
        "vāra",
        re.compile(
            rf"(?:วาโร|v[aā]ro)\s*{_CLOSER_VERB_CUE}",
            re.IGNORECASE,
        ),
    ),
    (
        "vatthu",
        re.compile(
            rf"(?:วตฺถุ|vatthu)\s*{_CLOSER_VERB_CUE}",
            re.IGNORECASE,
        ),
    ),
    (
        "vatta",
        re.compile(
            rf"(?:วตฺตํ|vatta[ṃṁm])\s*{_CLOSER_VERB_CUE}",
            re.IGNORECASE,
        ),
    ),
    (
        "pabbajjā",
        re.compile(
            rf"(?:ปพฺพชฺชา|pabbajj[aā])\s*{_CLOSER_VERB_CUE}",
            re.IGNORECASE,
        ),
    ),
    (
        "kamma",
        re.compile(
            rf"(?:กมฺมํ|kamma[ṃṁm])\s*{_CLOSER_VERB_CUE}",
            re.IGNORECASE,
        ),
    ),
    (
        "pārājika_unit",
        re.compile(
            r"(?:ปาราชิกํ|p[aā]r[aā]jika[ṃṁm])\s*"
            r"(?:สมตฺตํ|สมตฺตา|สมตฺตานิ|สมตฺโต|samatt)",
            re.IGNORECASE,
        ),
    ),
    (
        "peyyāla",
        re.compile(
            rf"(?:เปยฺยาล|เปยฺยาโล|peyy[aā]la)",
            re.IGNORECASE,
        ),
    ),
    (
        "vagga",
        re.compile(
            rf"(?:วคฺโค|vaggo)\s*{_CLOSER_VERB_CUE}",
            re.IGNORECASE,
        ),
    ),
    (
        "analytic",
        re.compile(
            rf"(?:มูลกํ|จกฺกํ|คมนํ|"
            rf"m[uū]laka[ṃṁm]|cakka[ṃṁm]|gamana[ṃṁm])\s*{_CLOSER_VERB_CUE}",
            re.IGNORECASE,
        ),
    ),
)


def closer_tier(level: str) -> str:
    """Map a ``closer_level`` to visual tier ``major`` / ``mid`` / ``leaf``."""
    return _CLOSER_LEVEL_TO_TIER.get(level, "leaf")


def classify_section_closer_tier(text: str) -> str:
    """Shortcut: ``closer_tier(classify_section_closer(text))``."""
    return closer_tier(classify_section_closer(text))


# Bare nominative category label printed as its own centered line before a
# count/unit niṭṭhitaṃ trailer (two-line vagga closer), e.g.
# ``โสตาปตฺติวคฺโค.`` + ``อฏฺฐารสเวยฺยากรณํ นิฏฺฐิตํ.``
# Not ``…วคฺโค ปฐโม.`` (that is ordinal_vagga) and not ``…วคฺโค นิฏฺฐิโต.``.
_BARE_CATEGORY_CLOSER_LABEL_THAI_RE = re.compile(
    r"^(?=.{1,60}$)\s*\S.*วคฺโค\s*\.?\s*$"
)
_BARE_CATEGORY_CLOSER_LABEL_ROMAN_RE = re.compile(
    r"^(?=.{1,60}$)\s*\S.*vaggo\s*\.?\s*$",
    re.IGNORECASE,
)


def is_bare_category_closer_label(text: str) -> bool:
    """True for a short ``…วคฺโค.`` / ``…vaggo.`` line without end-verb/ordinal.

    Incomplete alone — pairs with the following niṭṭhitaṃ formula as one
    mid-tier vagga closer (see ``join_two_line_category_closer``).
    """
    plain = plain_closer_probe_text(text)
    if not plain or len(plain) > 60:
        return False
    if is_ordinal_section_closer(plain):
        return False
    if is_section_closer_formula(plain):
        return False
    return bool(
        _BARE_CATEGORY_CLOSER_LABEL_THAI_RE.match(plain)
        or _BARE_CATEGORY_CLOSER_LABEL_ROMAN_RE.match(plain)
    )


def join_two_line_category_closer(label: str, trailer: str) -> str | None:
    """Join bare ``…วคฺโค.`` + following end-formula into one closer body.

    Returns TeX-joined ``label\\\\trailer``, or ``None`` when not a pair.
    """
    lab = (label or "").strip()
    trail = (trailer or "").strip()
    if not is_bare_category_closer_label(lab):
        return None
    probe = plain_closer_probe_text(trail)
    if not probe or len(probe) > 90:
        return None
    if not re.search(
        r"(?:นิฏฺฐิ(?:ตํ|ตา|ตานิ|โต)|ni[ṭt]{1,2}hit(?:a[ṃṁm]|ā|o|āni))",
        probe,
        re.IGNORECASE,
    ):
        return None
    return f"{lab}\\\\{trail}"


def classify_section_closer(text: str) -> str:
    """Return structural ``closer_level`` from a section-closer formula.

    Uses longest-rightmost lexical cues on the closer string itself (not the
    preceding heading stack). Unmatched or non-formula text yields
    ``unknown`` (visual tier leaf). Trailing sutta/rule ordinals after the
    end verb (``…นิฏฺฐิตํ ปฐมํ.``) are fine — rules search mid-string.

    Two-line vagga closers joined with ``\\\\`` (``…วคฺโค.\\\\…นิฏฺฐิตํ.``)
    classify as ``vagga``.
    """
    plain = plain_closer_probe_text(text)
    # TeX join uses \\ ; probes may keep a single backslash pair.
    plain = plain.replace("\\\\", " ").replace("\\", " ")
    plain = re.sub(r"\s+", " ", plain).strip()
    if not plain or len(plain) > 160:
        return "unknown"
    if is_ordinal_section_closer(plain):
        return "ordinal_vagga"
    # Compound two-line: category nominative + end-formula → vagga (mid).
    if (
        re.search(r"วคฺโค|vaggo", plain, re.IGNORECASE)
        and re.search(
            r"นิฏฺฐิ|ni[ṭt]{1,2}hit", plain, re.IGNORECASE
        )
        and not re.search(
            r"วคฺโค\s+(?:ปฐโม|ทุติโย|ตติโย)|vaggo\s+pa[tṭ]hamo",
            plain,
            re.IGNORECASE,
        )
    ):
        # Prefer specific *pāḷi / saṃyutta rules when the trailer is those.
        for level, pattern in _CLOSER_LEVEL_RULES:
            if level in {
                "saṃyutta_pāḷi",
                "nipāta_pāḷi",
                "pāḷi",
                "saṃyutta",
            } and pattern.search(plain):
                return level
        return "vagga"
    for level, pattern in _CLOSER_LEVEL_RULES:
        if pattern.search(plain):
            return level
    return "unknown"


# Recitation topic-summary label (not a heading, not an end-formula).
_TASSUDDANA_LABEL_RE = re.compile(
    r"^tassuddāna[ṃṁm]$",
    re.IGNORECASE,
)
_TASSUDDANA_LABEL_THAI_RE = re.compile(r"^ตสฺสุทฺทานํ$")

# Trailing expansion paren after a verse/prose stop (not ``(12-13)`` / ``(150)``).
# Optional short underscore section rule may follow the closing paren.
_TRAILING_PAREN_SPLIT_RE = re.compile(
    r"^(?P<body>.*[.!?…][\"'\u201c\u201d]?)"
    r"(?:\{\{sp1\}\}+|\s+)"
    r"\s*"
    r"(?P<paren>\([^()]+\))"
    r"(?P<rule>\s*_{3,})?"
    r"\s*$",
    re.DOTALL,
)
_EXPANSION_PAREN_MIN_INNER = 40
_DIGITISH_PAREN_INNER_RE = re.compile(r"^[\d\s\-–—,./]+$")
_LETTER_RE = re.compile(r"[^\W\d_]", re.UNICODE)


def is_tassuddana_label(text: str) -> bool:
    """True for the exact centered label ``Tassuddānaṃ`` / ``ตสฺสุทฺทานํ``.

    Recitation topic-summary cue (what heads were just covered) — not a TOC
    heading and not an exclamation (udāna).
    """
    plain = plain_closer_probe_text(text).strip()
    if not plain:
        return False
    return bool(
        _TASSUDDANA_LABEL_RE.match(plain)
        or _TASSUDDANA_LABEL_THAI_RE.match(plain)
    )


def is_expansion_parenthetical(text: str) -> bool:
    """True for a long centered expansion note ``(…vitthāretabbo.)`` etc.

    Rejects short editorial refs ``(12-13)``, ``(150)``, and bare digits.
    """
    plain = plain_closer_probe_text(text).strip()
    plain, _had_rule = split_trailing_section_rule(plain)
    plain = plain.strip()
    if len(plain) < 3 or plain[0] != "(" or plain[-1] != ")":
        return False
    inner = plain[1:-1].strip()
    if len(inner) < _EXPANSION_PAREN_MIN_INNER:
        return False
    if _DIGITISH_PAREN_INNER_RE.match(inner):
        return False
    return bool(_LETTER_RE.search(inner))


# Section end-label printed centered after a chapter/pabba/kaṇḍa block:
# ``Maddīpabbaṃ nāma.`` / ``มทฺทีปพฺพํ นาม.`` — furniture, not a วรรค.
# Requires a capitalised Roman proper (or Thai section-name + นาม.) and
# rejects narrative ``… nāma.`` inside verse (lowercase lead-in).
_SECTION_NAMA_COLOPHON_ROMAN_RE = re.compile(
    r"^(?=.{1,55}$)"
    r"[A-ZĀĪŪĒŌṂṆḌḶṬÑ]"
    r"[A-Za-zāīūēōṃṇḍḷṭñĀĪŪĒŌṂṆḌḶṬÑ']*"
    r"\s+nāma\.\s*$"
)
_SECTION_NAMA_COLOPHON_THAI_RE = re.compile(
    r"^(?=.{1,55}$)"
    r"\S+"
    r"\s+นาม\.\s*$"
)


def is_section_nama_colophon(text: str) -> bool:
    """True for a short centered section label ``Name nāma.`` / ``… นาม.``.

    CS prints these after a finished pabba/kaṇḍa (etc.) as their own centered
    line. They must not fold as a leftover gāthā วรรค. Narrative verse that
    merely ends in ``nāma.`` (lowercase lead-in, multi-word) is rejected.
    """
    plain = plain_closer_probe_text(text).strip()
    plain, _had_rule = split_trailing_section_rule(plain)
    plain = plain.strip()
    if not plain or SP1_MARKER in plain or "," in plain:
        return False
    if _SECTION_NAMA_COLOPHON_ROMAN_RE.match(plain):
        return True
    return bool(_SECTION_NAMA_COLOPHON_THAI_RE.match(plain))


def peel_trailing_expansion_parenthetical(
    text: str,
) -> tuple[str, str] | None:
    """Split a trailing expansion ``(…)`` after a sentence stop / ``{{sp1}}``.

    Example: ``…padanti. (Appamādavaggo … vitthāretabbo.)`` →
    (``…padanti.``, ``(Appamādavaggo … vitthāretabbo.)``).

    A trailing short underscore section rule after the paren moves onto the
    parenthetical remnant (verse body stays a clean bat/wak line).
    """
    raw = (text or "").rstrip()
    if not raw:
        return None
    m = _TRAILING_PAREN_SPLIT_RE.match(raw)
    if m is None:
        return None
    body = m.group("body").rstrip()
    paren = m.group("paren").strip()
    rule = (m.group("rule") or "").strip()
    if not body or not paren:
        return None
    if SP1_MARKER in paren:
        return None
    if not is_expansion_parenthetical(paren):
        return None
    remnant = plain_closer_probe_text(strip_sentence_spacers(body))
    if len(remnant) < 2:
        return None
    if rule:
        paren = f"{paren} {rule}".rstrip()
    return body, paren

# Solid editorial hyphens in CS Roman (na-upanissaye); not soft wraps, not -pa-.
_PALI_LETTER_CLASS = (
    r"A-Za-z"
    r"ĀāĪīŪūĒēŌō"
    r"ṂṃṀṁṄṅÑñṬṭḌḍṆṇḶḷŚśṢṣḤḥ"
    r"Œœ"
)
_PA_MARKER_RE = re.compile(r"(?i)-pa-")
_SOLID_MIDWORD_HYPHEN_RE = re.compile(
    rf"(?<=[{_PALI_LETTER_CLASS}])-(?=[{_PALI_LETTER_CLASS}])"
)

# PDF often emits U+23AF (HORIZONTAL LINE EXTENSION) for discourse dashes.
# Sarabun has no glyph; map to CS Roman en-dash (TeX ``\\csromandash``).
HORIZONTAL_LINE_EXTENSION = "\u23af"
EN_DASH = "\u2013"


def normalize_printable_dashes(text: str) -> str:
    """Map non-printable dash lookalikes to CS Roman en-dash (U+2013)."""
    if not text or HORIZONTAL_LINE_EXTENSION not in text:
        return text
    return text.replace(HORIZONTAL_LINE_EXTENSION, EN_DASH)


def uses_sentence_spacer(segment_type: str | None) -> bool:
    """True when body sentence-stop normalize applies (collapse / strip).

    Historical name: once gated ``{{sp1}}`` injection. Now means pot-ma-gyi
    collapse and legacy spacer strip for body kinds only.
    """
    return str(segment_type or "") in _SENTENCE_SPACER_TYPES


def demigrate_sp_markers(text: str) -> str:
    """Undo experimental ``{{sp}}``; map legacy ``{{sp3}}`` → ``{{sp1}}`` for strip."""
    if not text:
        return text
    if SP_MARKER in text:
        text = text.replace(SP_MARKER + SP_MARKER, ". . ")
        text = text.replace(SP_MARKER, ". ")
    if SP3_MARKER in text:
        text = text.replace(SP3_MARKER, SP1_MARKER)
    return text


def strip_sentence_spacers(text: str) -> str:
    """Remove ``{{sp1}}`` / ``{{sp3}}``; keep ordinary word spacing.

    Used for headings, closers, footnote bodies, and as the final step of
    body normalize after pot-ma-gyi collapse.
    """
    if not text:
        return text
    text = demigrate_sp_markers(text)
    if SP1_MARKER not in text and SP3_MARKER not in text:
        return text
    # Pot-ma-gyi / glued forms → ordinary ``. `` before the next unit.
    text = text.replace("." + SP1_MARKER + SP1_MARKER, ". ")
    text = text.replace("." + SP1_MARKER, ". ")
    text = _SP_MARKER_RE.sub("", text)
    return re.sub(r"[ \t]{2,}", " ", text)


def needs_spacing_normalize(text: str) -> bool:
    """True when Roman/Thai still has raw pot-ma-gyi or leftover spacer markers."""
    return bool(text and _NEEDS_SPACING_RE.search(text))


def strip_solid_midword_hyphens(text: str) -> str:
    """Remove solid letter-hyphen-letter joins; keep peyyāla ``-pa-``.

    CS Roman often marks vowel-vowel compounds with an editorial hyphen
    (``na-upanissaye``). Extract-normalized text drops those hyphens
    (``naupanissaye``). Soft line-wrap hyphens are joined earlier in extract;
    this step only clears remaining solid mid-word hyphens.
    """
    if not text or "-" not in text:
        return text
    parts: list[str] = []
    last = 0
    for m in _PA_MARKER_RE.finditer(text):
        parts.append(_SOLID_MIDWORD_HYPHEN_RE.sub("", text[last : m.start()]))
        parts.append(m.group(0))
        last = m.end()
    parts.append(_SOLID_MIDWORD_HYPHEN_RE.sub("", text[last:]))
    return "".join(parts)


def needs_solid_midword_hyphen_strip(text: str) -> bool:
    """True when Roman still has solid editorial mid-word hyphens."""
    return bool(text) and strip_solid_midword_hyphens(text) != text


def has_sentence_spacer_marker(text: str) -> bool:
    """True when text still carries ``{{sp}}`` / ``{{sp1}}`` / ``{{sp3}}``."""
    return bool(text) and (
        SP1_MARKER in text or SP3_MARKER in text or SP_MARKER in text
    )


def normalize_pot_ma_gyi(text: str) -> str:
    """Normalize sentence stops: collapse pot-ma-gyi; strip legacy spacers.

    Thai edition treats CS Roman pot-ma-gyi like an ordinary full stop:

    * ``word. .`` / ``word. . Next`` → ``word. Next``
    * ``word. next`` unchanged (no marker injected)
    * legacy ``word.{{sp1}}`` / ``{{sp3}}`` / double markers → ``word. ``
    * ``1. 46`` unchanged (digit after the stop)

    Body segments only — callers must skip this for titles / footnotes when
    they only want strip without pot-ma-gyi collapse (use
    ``strip_sentence_spacers``).
    """
    if not text:
        return text
    text = demigrate_sp_markers(text)
    if ". ." in text:
        text = _POT_MA_GYI_RE.sub(_ORDINARY_SENTENCE_STOP, text)
    # Collapse legacy double-spacer pot-ma-gyi.
    text = _LEGACY_DOUBLE_SP1_RE.sub(_ORDINARY_SENTENCE_STOP, text)
    # Insert missing word space after ``.{{sp1}}`` before the next unit.
    text = _LEGACY_GLUED_STOP_SP1_RE.sub(_ORDINARY_SENTENCE_STOP, text)
    # Repair glued ``word{{sp1}}Word`` (visible stop was dropped).
    text = _GLUED_SP1_RE.sub(r"\1" + _ORDINARY_SENTENCE_STOP, text)
    # Undo a prior over-repair: ``.{{sp1}}.{{sp1}}{{sp1}}`` → ``. ``.
    text = text.replace(
        "." + SP1_MARKER + "." + SP1_MARKER + SP1_MARKER,
        _ORDINARY_SENTENCE_STOP,
    )
    # Drop any remaining spacer markers (no reinject).
    return strip_sentence_spacers(text)


def split_trailing_section_rule(text: str) -> tuple[str, bool]:
    """Strip trailing ``_____`` (extracted section rule); return (text, had_rule)."""
    if not text:
        return "", False
    m = _SECTION_RULE_RE.search(text)
    if not m:
        return text, False
    return text[: m.start()].rstrip(), True


def normalize_roman_body(
    roman: str, *, normalize_spacing: bool = True
) -> tuple[str, bool]:
    """Strip section-rule tail; optionally collapse pot-ma-gyi / strip spacers.

    Keeps solid editorial mid-word hyphens so Thai can be derived part-wise
    (``na-upanissaye`` → ``น`` + ``อุปนิสฺสเย``). Callers that store Roman
    should pass the result through ``strip_solid_midword_hyphens``.
    """
    roman = normalize_printable_dashes(roman)
    cleaned, has_rule = split_trailing_section_rule(roman)
    if normalize_spacing:
        return normalize_pot_ma_gyi(cleaned), has_rule
    return strip_sentence_spacers(cleaned), has_rule


def prepare_roman_body(
    roman: str, *, normalize_spacing: bool = True
) -> tuple[str, bool]:
    """Full extract-normalize: spacing / section-rule, then drop solid hyphens.

    When ``normalize_spacing`` is false (headings / notes), strip any existing
    spacer markers without pot-ma-gyi collapse beyond demigrate/strip.
    """
    cleaned, has_rule = normalize_roman_body(
        roman, normalize_spacing=normalize_spacing
    )
    return strip_solid_midword_hyphens(cleaned), has_rule


def thai_digits_to_arabic(text: str) -> str:
    """Map Thai digits U+0E50–U+0E59 to ASCII ``0``–``9``."""
    if not text:
        return text
    return text.translate(_THAI_DIGITS_TO_ARABIC)


def _thai_runs_digits_to_arabic(runs: list[Any]) -> list[Any]:
    out: list[Any] = []
    for r in runs:
        if isinstance(r, dict):
            out.append(
                {**r, "value": thai_digits_to_arabic(str(r.get("value") or ""))}
            )
        else:
            out.append(r)
    return out


def _convert_roman_chunk(chunk: str) -> str:
    """Convert one Roman span; solid mid-word hyphens split morphemes, then drop.

    Joining before convert misreads vowel junctions (``naupanissaye`` →
    ``นฺเอา…``). Split on the hyphen, convert each side, concatenate without
    ``-`` (``นอุปนิสฺสเย``).
    """
    if not chunk:
        return ""
    if "-" not in chunk or not _SOLID_MIDWORD_HYPHEN_RE.search(chunk):
        return convert(chunk, Script.ROMAN, Script.THAI)
    return "".join(
        convert(part, Script.ROMAN, Script.THAI)
        for part in _SOLID_MIDWORD_HYPHEN_RE.split(chunk)
        if part
    )


def roman_to_thai(roman: str, *, normalize_spacing: bool = True) -> str:
    """Transliterate Roman Pāli → Thai; keep non-spacer markers; ``-pa-`` → ฯเปฯ.

    Solid editorial mid-word hyphens mark morpheme breaks for convert, then
    are omitted in Thai (``na-upanissaye`` → ``นอุปนิสฺสเย``). Peyyāla
    ``-pa-`` stays special-cased to ฯเปฯ.

    Body path collapses pot-ma-gyi and strips legacy ``{{sp1}}`` / ``{{sp3}}``.
    Heading / footnote path (``normalize_spacing=False``) only strips spacers
    so abbreviation / outline dots like ``1. 46`` / ``2. Name`` stay word-spaced.

    Digits are always Arabic (``4.`` not ``๔.``), including outline numbers and
    catalog refs — ``convert`` would otherwise emit Thai numerals.
    """
    if not roman:
        return ""
    roman = normalize_printable_dashes(roman)
    text = (
        normalize_pot_ma_gyi(roman)
        if normalize_spacing
        else strip_sentence_spacers(roman)
    )
    parts: list[str] = []
    for chunk in _SPECIAL_CHUNK_RE.split(text):
        if not chunk:
            continue
        if chunk in {SP1_MARKER, SP3_MARKER}:
            # Should already be stripped; never re-emit spacer markers.
            continue
        if _INLINE_MARKER_RE.fullmatch(chunk):
            parts.append(chunk)
        elif chunk.lower() == "-pa-":
            parts.append("ฯเปฯ")
        else:
            parts.append(_convert_roman_chunk(chunk))
    return thai_digits_to_arabic("".join(parts))


def transliterate_runs(roman_runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Map roman ``[{value, bold}, …]`` to Thai runs with the same bold flags."""
    out: list[dict[str, Any]] = []
    for run in roman_runs:
        out.append(
            {
                "value": roman_to_thai(str(run.get("value") or "")),
                "bold": bool(run.get("bold")),
            }
        )
    return out


def runs_have_bold(runs: Any) -> bool:
    if not isinstance(runs, list):
        return False
    return any(isinstance(r, dict) and r.get("bold") and r.get("value") for r in runs)


def text_field_has_bold_runs(text: Any) -> bool:
    """True when any script entry (or nested list item) carries bold runs."""
    if isinstance(text, list):
        for entry in text:
            if isinstance(entry, dict) and runs_have_bold(entry.get("runs")):
                return True
    return False


def roman_runs_from_text_field(text: Any) -> list[dict[str, Any]] | None:
    """Roman ``runs`` list when present."""
    if not isinstance(text, list):
        return None
    for entry in text:
        if isinstance(entry, dict) and entry.get("script") == "roman":
            runs = entry.get("runs")
            if isinstance(runs, list) and runs:
                return runs
            return None
    return None


def bold_ranges_from_runs(runs: list[dict[str, Any]]) -> list[tuple[int, int]]:
    """Byte-index bold ranges implied by ``runs`` over ``join(runs[].value)``."""
    ranges: list[tuple[int, int]] = []
    pos = 0
    for run in runs:
        if not isinstance(run, dict):
            continue
        value = str(run.get("value") or "")
        end = pos + len(value)
        if run.get("bold") and value:
            ranges.append((pos, end))
        pos = end
    return ranges


def remap_bold_ranges(
    old_roman: str,
    prepared: str,
    old_runs: list[dict[str, Any]] | None,
) -> list[tuple[int, int]]:
    """Map prior Roman bold runs onto ``prepared`` (post ``prepare_roman_body``).

    Prefer index copy when the string is unchanged (or only lost a trailing
    section-rule). Otherwise re-locate bold span strings in the new text.
    """
    if not old_runs or not runs_have_bold(old_runs):
        return []
    if old_roman == prepared:
        return bold_ranges_from_runs(old_runs)
    stripped, _ = split_trailing_section_rule(old_roman)
    if stripped == prepared:
        return clip_ranges(bold_ranges_from_runs(old_runs), length=len(prepared))
    spans = [
        str(r.get("value") or "")
        for r in old_runs
        if isinstance(r, dict) and r.get("bold") and r.get("value")
    ]
    if not spans:
        return []
    # One stored bold run → one occurrence (do not re-bleed repeated lemmas).
    return bold_ranges_one_per_span(prepared, spans)


def _bold_flags_from_runs(text: str, runs: list[dict[str, Any]]) -> list[bool]:
    flags = [False] * len(text)
    pos = 0
    for run in runs:
        if not isinstance(run, dict):
            continue
        value = str(run.get("value") or "")
        bold = bool(run.get("bold"))
        for i, _ch in enumerate(value):
            idx = pos + i
            if idx < len(flags):
                flags[idx] = bold
        pos += len(value)
    return flags


def _map_bold_flags(old: str, new: str, old_flags: list[bool]) -> list[bool]:
    """Align per-character bold flags from ``old`` onto ``new``."""
    new_flags = [False] * len(new)
    sm = SequenceMatcher(a=old, b=new, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            new_flags[j1:j2] = old_flags[i1:i2]
        elif tag == "insert":
            inherit = old_flags[i1 - 1] if i1 > 0 else False
            for j in range(j1, j2):
                new_flags[j] = inherit
        elif tag == "replace":
            old_len = i2 - i1
            new_len = j2 - j1
            for n in range(new_len):
                src = i1 + min(n, old_len - 1) if old_len else i1
                if 0 <= src < len(old_flags):
                    new_flags[j1 + n] = old_flags[src]
    return new_flags


def _flags_to_ranges(flags: list[bool]) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    start: int | None = None
    for i, bold in enumerate(flags):
        if bold and start is None:
            start = i
        elif not bold and start is not None:
            ranges.append((start, i))
            start = None
    if start is not None:
        ranges.append((start, len(flags)))
    return ranges


def remap_runs_through_edit(
    old_text: str,
    new_text: str,
    old_runs: list[dict[str, Any]] | None,
) -> list[dict[str, Any]] | None:
    """Map bold ``runs`` from ``old_text`` onto ``new_text`` after a string edit.

    Inserted characters inherit bold from the preceding kept character.
    ``ranges_to_runs`` then strips bold from inline markers (``{{nN}}``, …).
    Returns ``None`` when there is no bold, the runs do not join to ``old_text``,
    or the aligned flags yield no bold span.
    """
    if not old_runs or not runs_have_bold(old_runs):
        return None
    if old_text == new_text:
        return old_runs
    joined = "".join(
        str(r.get("value") or "") for r in old_runs if isinstance(r, dict)
    )
    if joined != old_text:
        return None
    new_flags = _map_bold_flags(
        old_text, new_text, _bold_flags_from_runs(old_text, old_runs)
    )
    return ranges_to_runs(new_text, _flags_to_ranges(new_flags))


def script_text_entries(
    roman: str,
    *,
    bold_ranges: list[tuple[int, int]] | None = None,
    normalize_spacing: bool = True,
) -> tuple[list[dict[str, Any]], bool]:
    """Build ``text`` as ``[{script, value(, runs)}, …]``; strip section-rule underscores.

    When ``normalize_spacing`` is true (body), also normalize sentence-stop
    spacing to ``{{sp1}}``. Thai is derived from the hyphenated Roman (morpheme
    breaks), then solid mid-word hyphens are dropped from stored Roman.
    Pass ``bold_ranges`` on the *final* Roman (post hyphen-strip) so spans
    stay aligned — prefer ranges from ``prepare_roman_body``.
    """
    spaced, has_rule = normalize_roman_body(
        roman, normalize_spacing=normalize_spacing
    )
    # Thai before stripping hyphens so ``na-u…`` ≠ joined ``nau…``.
    # Same spacing flag as Roman (idempotent); do not strip ``{{sp1}}`` here.
    thai_value = roman_to_thai(spaced, normalize_spacing=normalize_spacing)
    cleaned = strip_solid_midword_hyphens(spaced)
    roman_entry: dict[str, Any] = {"script": "roman", "value": cleaned}
    thai_entry: dict[str, Any] = {"script": "thai", "value": thai_value}

    if bold_ranges:
        clipped = clip_ranges(bold_ranges, length=len(cleaned))
        runs = ranges_to_runs(cleaned, clipped)
        if runs:
            roman_entry["runs"] = runs
            # Re-derive Thai runs from stripped Roman chunks (hyphens already gone).
            thai_entry["runs"] = transliterate_runs(runs)

    return [roman_entry, thai_entry], has_rule


def roman_value_from_text_field(text: Any) -> str:
    """Read roman string from legacy ``str`` or multi-script ``list``."""
    if isinstance(text, str):
        return text
    if isinstance(text, list):
        for entry in text:
            if isinstance(entry, dict) and entry.get("script") == "roman":
                return str(entry.get("value") or "")
        if text and isinstance(text[0], dict) and "value" in text[0]:
            return str(text[0]["value"] or "")
    return ""


def ensure_script_text(
    text: Any,
    *,
    force: bool = False,
    normalize_spacing: bool = True,
) -> tuple[list[dict[str, Any]], bool, bool]:
    """Normalize any legacy/new ``text`` field to multi-script list.

    With ``force=True``, rebuild Thai from the Roman value (e.g. after
    pali_script orthography fixes such as iṃ → ิํ not ึ).

    When ``normalize_spacing`` is true (body), rebuild if Roman still needs
    sentence-stop ``{{sp1}}`` normalize. When false (headings / notes), rebuild
    only to strip leftover spacer markers — never inject new ones.

    Preserves bold ``runs`` across force/spacing rebuilds when spans can be
    remapped onto the prepared Roman string.

    Returns ``(entries, had_section_rule, bold_lost)``.
    """
    roman = roman_value_from_text_field(text)
    had_bold = text_field_has_bold_runs(text)
    old_runs = roman_runs_from_text_field(text)

    needs = needs_solid_midword_hyphen_strip(roman) or (
        needs_spacing_normalize(roman)
        if normalize_spacing
        else has_sentence_spacer_marker(roman)
    )
    if force or needs:
        prepared, _ = prepare_roman_body(
            roman, normalize_spacing=normalize_spacing
        )
        ranges = remap_bold_ranges(roman, prepared, old_runs)
        entries, had_rule = script_text_entries(
            roman,
            bold_ranges=ranges or None,
            normalize_spacing=normalize_spacing,
        )
        bold_lost = had_bold and not text_field_has_bold_runs(entries)
        return entries, had_rule, bold_lost

    if (
        isinstance(text, list)
        and len(text) >= 2
        and all(isinstance(e, dict) and e.get("script") and "value" in e for e in text)
        and any(e.get("script") == "thai" for e in text)
    ):
        # Still strip underscore tails left from older enrich runs.
        entries: list[dict[str, Any]] = []
        had_rule = False
        bold_lost = False
        for e in text:
            value = str(e.get("value") or "")
            cleaned, rule = split_trailing_section_rule(value)
            had_rule = had_rule or rule
            script = str(e["script"])
            if script == "thai":
                cleaned = thai_digits_to_arabic(cleaned)
            entry: dict[str, Any] = {"script": script, "value": cleaned}
            runs = e.get("runs")
            if isinstance(runs, list) and runs_have_bold(runs):
                if not rule:
                    entry["runs"] = (
                        _thai_runs_digits_to_arabic(runs)
                        if script == "thai"
                        else runs
                    )
                else:
                    clipped = clip_ranges(
                        bold_ranges_from_runs(runs), length=len(cleaned)
                    )
                    new_runs = ranges_to_runs(cleaned, clipped) if clipped else None
                    if new_runs:
                        entry["runs"] = (
                            _thai_runs_digits_to_arabic(new_runs)
                            if script == "thai"
                            else new_runs
                        )
                    else:
                        bold_lost = True
            entries.append(entry)
        return entries, had_rule, bold_lost

    entries, had_rule = script_text_entries(
        roman, normalize_spacing=normalize_spacing
    )
    return entries, had_rule, had_bold and not text_field_has_bold_runs(entries)
