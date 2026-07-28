"""Thai-script beautify / unbeautify for Pāli orthography."""

from __future__ import annotations

import re

from .data_loader import load_glyphs

# Front vowels in Thai writing order (Pāli uses เ/โ; ไ/ใ kept for legacy symmetry).
_FRONT = "เโไใ"
# Final letters of กล้ำ pairs (y r l v h ḷ).
_GLIDE = "ยรลวฬห"

_SWAP1 = re.compile(rf"([ก-ฮ])([{_FRONT}])")
_SWAP2 = re.compile(rf"((?:[ก-ฮ]ฺ)*)([ก-ฮ]ฺ)([{_FRONT}])([{_GLIDE}])")
_UNSWAP_CLUSTER = re.compile(rf"([{_FRONT}])([ก-ฮ]ฺ[{_GLIDE}])")
# After cluster unswap (…CฺGเ → …CฺGเ), front vowel sits after ฺG — do not move it again.
# Still unswap normal …วโต / …หโต where the glide is not a กล้ำ pair.
_UNSWAP_SINGLE = re.compile(rf"(?<!ฺ[{_GLIDE}])([{_FRONT}])([ก-ฮ])")


def _thai_meta() -> dict:
    return load_glyphs()["thai"]


def beautify_thai(text: str, *, thai_pua: bool = False) -> str:
    """Display normalization after Roman→Thai encode."""
    meta = _thai_meta()
    # Dependent e/o/ai stored after consonant; move to front for Thai writing order
    text = _swap_front_vowels(text)
    # Keep i + niggahita as ิํ (not Thai sara ue ึ — that mark is not Pāli).
    if thai_pua:
        text = text.replace(meta["pua_yo"]["from"], meta["pua_yo"]["to"])
        text = text.replace(meta["pua_tho"]["from"], meta["pua_tho"]["to"])
    return text


def unbeautify_thai(text: str) -> str:
    """Undo display forms before Thai→Roman decode."""
    meta = _thai_meta()
    text = text.replace(meta["wrong_tt"]["from"], meta["wrong_tt"]["to"])
    text = text.replace(meta["pua_yo"]["to"], meta["pua_yo"]["from"])
    text = text.replace(meta["pua_tho"]["to"], meta["pua_tho"]["from"])
    # Legacy tipitaka-style ึ → ิํ so Thai→Roman still works on older text.
    legacy = meta["legacy_im_composite"]
    text = text.replace(legacy["from"], legacy["to"])
    text = _unswap_front_vowels(text)
    return text


def _swap_front_vowels(text: str) -> str:
    """Move front vowels before their host; then before กล้ำ pair base if needed.

    1) Single consonant: กเ → เก, ทฺวเ → ทฺเว
    2) กล้ำ pair (…CฺเG with G in y/r/l/v/ḷ/h): ทฺเว → เทฺว, นฺทฺเร → นฺเทฺร
       Preceding coda consonants (สะกด) stay before the front vowel.
       Skip geminate bases (ยฺย / ลฺล) so ยฺโย stays ยฺโย, not โยฺย.
    """
    text = _SWAP1.sub(r"\2\1", text)

    def _glide_pair(m: re.Match[str]) -> str:
        codas, base_vir, front, glide = m.group(1), m.group(2), m.group(3), m.group(4)
        if base_vir[0] == glide:
            return m.group(0)
        return f"{codas}{front}{base_vir}{glide}"

    return _SWAP2.sub(_glide_pair, text)


def _unswap_front_vowels(text: str) -> str:
    """Inverse of ``_swap_front_vowels`` before Thai→Roman decode."""
    text = _UNSWAP_CLUSTER.sub(r"\2\1", text)
    text = _UNSWAP_SINGLE.sub(r"\2\1", text)
    return text
