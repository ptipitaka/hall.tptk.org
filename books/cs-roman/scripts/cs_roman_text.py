"""Multi-script text helpers for cs-roman segment JSON."""

from __future__ import annotations

import re
from typing import Any

from paths import ensure_import_paths

ensure_import_paths()

from pali_script import Script, convert  # noqa: E402

from cs_roman_bold import (  # noqa: E402
    bold_ranges_in_text,
    clip_ranges,
    ranges_to_runs,
)

# Inline markers embedded in segment body (must not be transliterated).
# ``{{sp1}}`` = 0.5em gap in TeX after a visible sentence stop.
SP1_MARKER = "{{sp1}}"
# Legacy pot-ma-gyi marker (3em era); migrated to ``{{sp1}}`` on normalize.
SP3_MARKER = "{{sp3}}"
# Brief experiment marker; demigrated to periods before pot-ma-gyi normalize.
SP_MARKER = "{{sp}}"
# Sentence spacers apply only to body units — not titles, chapters, footnotes.
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
    r"(\{\{n\d+\}\}|\{\{\*\}\}|\{\{\+\}\}|\{\{sp1\}\}|\{\{sp3\}\})"
)
_SP_MARKER_RE = re.compile(r"\{\{sp[13]\}\}")
# CS Roman peyyāla mark → Thai Tipiṭaka ฯเปฯ (do not letter-transliterate to -ป-).
_SPECIAL_CHUNK_RE = re.compile(
    r"(\{\{n\d+\}\}|\{\{\*\}\}|\{\{\+\}\}|\{\{sp1\}\}|\{\{sp3\}\}|-pa-)",
    re.IGNORECASE,
)
# CS→Thai letter convert maps ASCII digits to Thai digits; publication uses Arabic.
_THAI_DIGITS_TO_ARABIC = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")

# Burmese pot-ma-gyi in CS Roman: ``. .`` → ``.{{sp1}}{{sp1}}`` (1.0em gap).
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


def uses_sentence_spacer(segment_type: str | None) -> bool:
    """True when ``{{sp1}}`` / TeX ``\\csromanspacer`` apply (body only)."""
    return str(segment_type or "") in _SENTENCE_SPACER_TYPES


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


def strip_sentence_spacers(text: str) -> str:
    """Remove ``{{sp1}}`` / ``{{sp3}}``; keep ordinary word spacing.

    Used for headings, closers, and footnote bodies where sentence-stop
    spacers must not apply (outline numbers like ``2. Name`` are not stops).
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
    """True when Roman/Thai still has raw pot-ma-gyi or missing sentence ``{{sp1}}``."""
    return bool(text and _NEEDS_SPACING_RE.search(text))


def has_sentence_spacer_marker(text: str) -> bool:
    """True when text still carries ``{{sp}}`` / ``{{sp1}}`` / ``{{sp3}}``."""
    return bool(text) and (
        SP1_MARKER in text or SP3_MARKER in text or SP_MARKER in text
    )


def normalize_pot_ma_gyi(text: str) -> str:
    """Normalize sentence-stop spacing to ``{{sp1}}`` markers.

    * ``word. .`` / ``word. . Next`` → ``word.{{sp1}}{{sp1}}Next`` (pot-ma-gyi)
    * ``word. next`` → ``word.{{sp1}} next`` (ordinary stop; keep the space)
    * ``1. 46`` unchanged (digit after the stop)

    Body segments only — callers must skip this for titles / footnotes.
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


def prepare_roman_body(
    roman: str, *, normalize_spacing: bool = True
) -> tuple[str, bool]:
    """Strip section-rule tail; optionally normalize sentence-stop ``{{sp1}}``.

    When ``normalize_spacing`` is false (headings / notes), strip any existing
    spacer markers instead of injecting new ones.
    """
    cleaned, has_rule = split_trailing_section_rule(roman)
    if normalize_spacing:
        return normalize_pot_ma_gyi(cleaned), has_rule
    return strip_sentence_spacers(cleaned), has_rule


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


def roman_to_thai(roman: str, *, normalize_spacing: bool = True) -> str:
    """Transliterate Roman Pāli → Thai; keep markers; ``-pa-`` → ฯเปฯ.

    When ``normalize_spacing`` is false (headings / footnote bodies), do not
    inject sentence-stop ``{{sp1}}`` and strip any leftover spacer markers so
    abbreviation / outline dots like ``1. 46`` / ``2. Name`` stay word-spaced.

    Digits are always Arabic (``4.`` not ``๔.``), including outline numbers and
    catalog refs — ``convert`` would otherwise emit Thai numerals.
    """
    if not roman:
        return ""
    text = (
        normalize_pot_ma_gyi(roman)
        if normalize_spacing
        else strip_sentence_spacers(roman)
    )
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
    return bold_ranges_in_text(prepared, spans)


def script_text_entries(
    roman: str,
    *,
    bold_ranges: list[tuple[int, int]] | None = None,
    normalize_spacing: bool = True,
) -> tuple[list[dict[str, Any]], bool]:
    """Build ``text`` as ``[{script, value(, runs)}, …]``; strip section-rule underscores.

    When ``normalize_spacing`` is true (body), also normalize sentence-stop
    spacing to ``{{sp1}}``. Pass ``bold_ranges`` computed on the *prepared*
    body (see ``prepare_roman_body``) so spans stay aligned.
    """
    cleaned, has_rule = prepare_roman_body(
        roman, normalize_spacing=normalize_spacing
    )
    roman_entry: dict[str, Any] = {"script": "roman", "value": cleaned}
    thai_entry: dict[str, Any] = {
        "script": "thai",
        "value": roman_to_thai(cleaned, normalize_spacing=normalize_spacing),
    }

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

    needs = (
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
