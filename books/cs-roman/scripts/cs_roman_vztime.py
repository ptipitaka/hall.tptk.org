"""
Convert Chaṭṭha Saṅgāyana Roman PDF text-layer (VZTime font) to Unicode.

The cs-roman PDFs embed the custom font ``VZTime``. Extracted code points are
mostly Latin-1 lookalikes that the font draws as Pāli diacritics. This module
maps those code points to proper Unicode letters (UTF-8).
"""

from __future__ import annotations

# Observed in books/cs-roman/source/*.pdf (font name: VZTime).
# Validated against cover title Chaṭṭhasaṅgītipiṭakaṃ / Pārājikapāḷi and body text.
VZTIME_TO_UNICODE: dict[str, str] = {
    "È": "ā",
    "Ê": "ī",
    "|": "ū",
    "É": "ḍ",
    "Ä": "ḷ",
    "Ñ": "ṃ",
    "Ò": "ñ",
    "Ó": "ṇ",
    "Ô": "ṭ",
    "~": "ṅ",
    "Œ": "Ā",
    "\x7f": "Ū",  # capital ū (TOC / some notes)
    "©": "Ñ",  # capital ñ
    "®": "Ṭ",
    "£": "Ḷ",
}

_TRANSLATE = str.maketrans(VZTIME_TO_UNICODE)

# After conversion these are expected Pāli letters / punctuation.
_EXPECTED_EXTRA = set("āīūṅñṇṭḍḷṃĀĪŪṄÑṆṬḌḶṂ“”‘’–—…")


def vztime_to_unicode(text: str) -> str:
    """Return ``text`` with VZTime code points replaced by Unicode Pāli letters."""
    return text.translate(_TRANSLATE)


def unmapped_chars(text: str) -> set[str]:
    """
    Characters still outside ASCII + expected Pāli punctuation after conversion.

    Useful for spotting rare front-matter glyphs that need a map extension.
    """
    converted = vztime_to_unicode(text)
    return {
        ch
        for ch in converted
        if ord(ch) > 127 and ch not in _EXPECTED_EXTRA
    }
