"""Roman (IAST) normalization helpers."""

from __future__ import annotations

from .data_loader import load_glyphs


def normalize_roman_input(text: str) -> str:
    """Lowercase and map alternate niggahita forms to ṃ."""
    text = text.casefold()
    glyphs = load_glyphs()
    for spec in glyphs["specials"]:
        if spec["id"] != "niggahita":
            continue
        canon = spec["roman"]
        for alt in spec.get("roman_alt", []):
            text = text.replace(alt, canon)
        # NFC-ish common variants already listed; also m-dot-below sometimes typed wrong
        text = text.replace("ṁ", canon)
    return text
