"""Locale-aware display helpers for Patidina calendar UI."""

from __future__ import annotations

from django.utils.html import format_html
from django.utils.safestring import SafeString
from django.utils.translation import get_language, gettext as _

PHASE_KEYS = ("ขึ้น", "แรม")

# Canonical internal codes are Latin (see patidina.services.calendar).
_DHAMMAYUT_TOOLTIPS = {
    "P": "Pakkha (8th day)",
    "Pt": "Full pakkha (15 days)",
    "Pk": "Deficient pakkha (14 days)",
}
_DHAMMAYUT_THAI = {
    "P": "ป",
    "Pt": "ปถ",
    "Pk": "ปข",
}
_DHAMMAYUT_FROM_THAI = {thai: latin for latin, thai in _DHAMMAYUT_THAI.items()}


def active_lang() -> str:
    return (get_language() or "en").split("-")[0]


def phase_label(phase_key: str) -> str:
    """Map internal phase keys (ขึ้น/แรม) to a display label."""
    if phase_key == "ขึ้น":
        return _("Waxing")
    if phase_key == "แรม":
        return _("Waning")
    return phase_key


def normalize_dhammayut_code(code: str) -> str:
    """Map a display or internal marker to the canonical Latin code."""
    if not code:
        return ""
    if code in _DHAMMAYUT_TOOLTIPS:
        return code
    return _DHAMMAYUT_FROM_THAI.get(code, code)


def dhammayut_display_code(code: str) -> str:
    """Locale-aware abbreviation: Thai ป/ปถ/ปข, English P/Pt/Pk."""
    latin = normalize_dhammayut_code(code)
    if not latin or latin not in _DHAMMAYUT_TOOLTIPS:
        return code
    if active_lang() == "th":
        return _DHAMMAYUT_THAI[latin]
    return latin


def dhammayut_legend_markers() -> str:
    """Legend string for Dhammayut pakkha abbreviations in the active locale."""
    if active_lang() == "th":
        return "ป ปถ ปข"
    return "P Pt Pk"


def dhammayut_tooltip(code: str) -> str:
    """Full name for a Dhammayut abbreviation (P/Pt/Pk or ป/ปถ/ปข)."""
    msgid = _DHAMMAYUT_TOOLTIPS.get(normalize_dhammayut_code(code))
    return _(msgid) if msgid else ""


def format_dhammayut_marker(code: str) -> SafeString | str:
    """Render locale-aware abbreviation with a localized tooltip."""
    if not code:
        return ""
    return format_html(
        '<span title="{}">{}</span>',
        dhammayut_tooltip(code),
        dhammayut_display_code(code),
    )


def lunar_date_label(phase: str, day: int | str, month_display: str) -> str:
    return _("%(phase)s %(day)s of lunar month %(month)s") % {
        "phase": phase_label(phase),
        "day": day,
        "month": month_display,
    }


def maybe_thai_digits(value) -> str:
    from patidina.services.calendar import arabic_to_thai

    text = str(value)
    if active_lang() == "th":
        return arabic_to_thai(text)
    return text
