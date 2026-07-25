"""Multi-script text helpers for cs-roman segment JSON."""

from __future__ import annotations

import re
from typing import Any

from paths import ensure_import_paths

ensure_import_paths()

from pali_script import Script, convert  # noqa: E402

from cs_roman_bold import clip_ranges, ranges_to_runs  # noqa: E402

# Inline markers embedded in segment body (must not be transliterated).
# ``{{sp1}}`` = 1em gap in TeX after a visible sentence stop.
SP1_MARKER = "{{sp1}}"
# Legacy pot-ma-gyi marker (3em era); migrated to ``{{sp1}}`` on normalize.
SP3_MARKER = "{{sp3}}"
# Brief experiment marker; demigrated to periods before pot-ma-gyi normalize.
SP_MARKER = "{{sp}}"
_INLINE_MARKER_RE = re.compile(
    r"(\{\{n\d+\}\}|\{\{\*\}\}|\{\{\+\}\}|\{\{sp1\}\}|\{\{sp3\}\})"
)
# CS Roman peyyāla mark → Thai Tipiṭaka ฯเปฯ (do not letter-transliterate to -ป-).
_SPECIAL_CHUNK_RE = re.compile(
    r"(\{\{n\d+\}\}|\{\{\*\}\}|\{\{\+\}\}|\{\{sp1\}\}|\{\{sp3\}\}|-pa-)",
    re.IGNORECASE,
)
# Burmese pot-ma-gyi in CS Roman: ``. .`` → ``.{{sp1}}{{sp1}}`` (2em gap).
_POT_MA_GYI_RE = re.compile(r"\. \. ?")
# Legacy single-``{{sp1}}`` pot-ma-gyi (no space before next unit) → double.
_LEGACY_POT_MA_GYI_SP1_RE = re.compile(
    r"\.\{\{sp1\}\}(?!\{\{sp1\}\})(?=\S)"
)
# Older bug: stop eaten so ``word{{sp1}}Word`` → ``word.{{sp1}}{{sp1}}Word``.
# Preceding char must be a letter (not ``}`` from another ``{{…}}`` marker).
_GLUED_SP1_RE = re.compile(
    r"([^\W\d_])\{\{sp1\}\}(?!\{\{sp1\}\})(?=\S)"
)
# Ordinary sentence stop: ``. next`` → ``.{{sp1}} next`` (letter after spaces;
# skip ``1. 46`` style digit refs).
_SENTENCE_STOP_GAP_RE = re.compile(r"\.(?!\{\{sp1\}\})(\s+)(?=[^\W\d_])")
# Detect text that still needs spacing normalize (enrich / ensure).
_NEEDS_SPACING_RE = re.compile(
    r"\. \."
    r"|\{\{sp(?:3)?\}\}"
    r"|\.(?!\{\{sp1\}\})\s+[^\W\d_]"
    r"|\.\{\{sp1\}\}(?!\{\{sp1\}\})(?=\S)"
    r"|[^\W\d_]\{\{sp1\}\}(?!\{\{sp1\}\})(?=\S)"
    r"|\.\{\{sp1\}\}\.\{\{sp1\}\}\{\{sp1\}\}"
)
# PDF text extraction turns the short end-of-section rule into underscores.
_SECTION_RULE_RE = re.compile(r"\s*_{3,}\s*$")
SECTION_RULE_FLAG = "section_rule"


def demigrate_sp_markers(text: str) -> str:
    """Undo experimental ``{{sp}}`` markers; map legacy ``{{sp3}}`` → ``{{sp1}}``."""
    if not text:
        return text
    if SP_MARKER in text:
        text = text.replace(SP_MARKER + SP_MARKER, ". . ")
        text = text.replace(SP_MARKER, ". ")
    if SP3_MARKER in text:
        text = text.replace(SP3_MARKER, SP1_MARKER)
    return text


def needs_spacing_normalize(text: str) -> bool:
    """True when Roman/Thai still has raw pot-ma-gyi or missing sentence ``{{sp1}}``."""
    return bool(text and _NEEDS_SPACING_RE.search(text))


def normalize_pot_ma_gyi(text: str) -> str:
    """Normalize sentence-stop spacing to ``{{sp1}}`` markers.

    * ``word. .`` / ``word. . Next`` → ``word.{{sp1}}{{sp1}}Next`` (pot-ma-gyi)
    * ``word. next`` → ``word.{{sp1}} next`` (ordinary stop; keep the space)
    * ``1. 46`` unchanged (digit after the stop)
    """
    if not text:
        return text
    text = demigrate_sp_markers(text)
    if ". ." in text:
        text = _POT_MA_GYI_RE.sub("." + SP1_MARKER + SP1_MARKER, text)
    # Upgrade legacy pot-ma-gyi ``.{{sp1}}Word`` → ``.{{sp1}}{{sp1}}Word``.
    text = _LEGACY_POT_MA_GYI_SP1_RE.sub("." + SP1_MARKER + SP1_MARKER, text)
    # Repair glued ``word{{sp1}}Word`` (visible stop was dropped).
    text = _GLUED_SP1_RE.sub(r"\1." + SP1_MARKER + SP1_MARKER, text)
    # Undo a prior over-repair: ``.{{sp1}}.{{sp1}}{{sp1}}`` → ``.{{sp1}}{{sp1}}``.
    text = text.replace(
        "." + SP1_MARKER + "." + SP1_MARKER + SP1_MARKER,
        "." + SP1_MARKER + SP1_MARKER,
    )
    text = _SENTENCE_STOP_GAP_RE.sub("." + SP1_MARKER + r"\1", text)
    return text


def split_trailing_section_rule(text: str) -> tuple[str, bool]:
    """Strip trailing ``_____`` (extracted section rule); return (text, had_rule)."""
    if not text:
        return "", False
    m = _SECTION_RULE_RE.search(text)
    if not m:
        return text, False
    return text[: m.start()].rstrip(), True


def prepare_roman_body(roman: str) -> tuple[str, bool]:
    """Strip section-rule tail, then normalize sentence-stop ``{{sp1}}`` markers."""
    cleaned, has_rule = split_trailing_section_rule(roman)
    return normalize_pot_ma_gyi(cleaned), has_rule


def roman_to_thai(roman: str) -> str:
    """Transliterate Roman Pāli → Thai; keep markers; ``-pa-`` → ฯเปฯ."""
    if not roman:
        return ""
    text = normalize_pot_ma_gyi(roman)
    parts: list[str] = []
    for chunk in _SPECIAL_CHUNK_RE.split(text):
        if not chunk:
            continue
        if chunk == SP3_MARKER:
            parts.append(SP1_MARKER)
        elif _INLINE_MARKER_RE.fullmatch(chunk):
            parts.append(chunk)
        elif chunk.lower() == "-pa-":
            parts.append("ฯเปฯ")
        else:
            parts.append(convert(chunk, Script.ROMAN, Script.THAI))
    return "".join(parts)


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


def script_text_entries(
    roman: str,
    *,
    bold_ranges: list[tuple[int, int]] | None = None,
) -> tuple[list[dict[str, Any]], bool]:
    """Build ``text`` as ``[{script, value(, runs)}, …]``; strip section-rule underscores.

    Also normalizes sentence-stop spacing to ``{{sp1}}``. Pass ``bold_ranges``
    computed on the *prepared* body (see ``prepare_roman_body``) so spans stay
    aligned.
    """
    cleaned, has_rule = prepare_roman_body(roman)
    roman_entry: dict[str, Any] = {"script": "roman", "value": cleaned}
    thai_entry: dict[str, Any] = {"script": "thai", "value": roman_to_thai(cleaned)}

    if bold_ranges:
        clipped = clip_ranges(bold_ranges, length=len(cleaned))
        runs = ranges_to_runs(cleaned, clipped)
        if runs:
            roman_entry["runs"] = runs
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


def ensure_script_text(text: Any, *, force: bool = False) -> tuple[list[dict[str, Any]], bool]:
    """Normalize any legacy/new ``text`` field to multi-script list.

    With ``force=True``, rebuild Thai from the Roman value (e.g. after
    pali_script orthography fixes such as iṃ → ิํ not ึ).

    Always rebuild when Roman still needs sentence-stop ``{{sp1}}`` normalize
    (raw ``. .``, missing gaps, legacy ``{{sp}}`` / ``{{sp3}}``).

    Returns ``(entries, had_section_rule)``.
    """
    roman = roman_value_from_text_field(text)
    if force or needs_spacing_normalize(roman):
        return script_text_entries(roman)

    if (
        isinstance(text, list)
        and len(text) >= 2
        and all(isinstance(e, dict) and e.get("script") and "value" in e for e in text)
        and any(e.get("script") == "thai" for e in text)
    ):
        # Still strip underscore tails left from older enrich runs.
        entries: list[dict[str, Any]] = []
        had_rule = False
        for e in text:
            value = str(e.get("value") or "")
            cleaned, rule = split_trailing_section_rule(value)
            had_rule = had_rule or rule
            entry: dict[str, Any] = {"script": str(e["script"]), "value": cleaned}
            runs = e.get("runs")
            if isinstance(runs, list) and runs and not rule:
                entry["runs"] = runs
            elif isinstance(runs, list) and runs and rule:
                # Trailing rule removed: drop runs rather than risk misaligned spans.
                pass
            entries.append(entry)
        return entries, had_rule
    return script_text_entries(roman)
