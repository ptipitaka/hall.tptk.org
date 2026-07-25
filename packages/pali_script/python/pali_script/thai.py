"""Thai-script beautify / unbeautify for Pāli orthography."""

from __future__ import annotations

import re

from .data_loader import load_glyphs


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
    return re.sub(r"([ก-ฮ])([เโไใ])", r"\2\1", text)


def _unswap_front_vowels(text: str) -> str:
    return re.sub(r"([เโไใ])([ก-ฮ])", r"\2\1", text)
