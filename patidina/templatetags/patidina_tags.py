from datetime import date, timedelta

from django import template
from django.utils import translation
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _

from patidina.services.calendar import (
    dhammayut_uposatha,
    era,
    lunar_date_for,
    mahanikaya_uposatha,
)
from patidina.services.i18n_display import (
    dhammayut_legend_markers as dhammayut_legend_markers_fn,
    format_dhammayut_marker,
    maybe_thai_digits,
    phase_label as phase_label_fn,
)
from patidina.services.important_days import important_days_for, important_days_in_range
from patidina.services.moon import moon_phase_svg

register = template.Library()


def _lang(lang=None) -> str:
    if lang:
        return lang.split("-")[0]
    return (translation.get_language() or "en").split("-")[0]


@register.inclusion_tag("patidina/templatetags/lunar-date-tag.html")
def lunar_date_tag(ini_solar_date=None):
    if ini_solar_date is None:
        ini_solar_date = date.today()
    lunar = lunar_date_for(ini_solar_date)
    lang = _lang()
    if lang == "th":
        phase = lunar.phase
        date_unit = "ค่ำ"
        month = f"เดือน {lunar.month_display}"
        year = era(ini_solar_date, output_type=8)
    else:
        phase = phase_label_fn(lunar.phase)
        date_unit = ""
        month = _("lunar month %(month)s") % {"month": lunar.month_display}
        year = era(ini_solar_date, output_type=9)
    return {
        "lunar_phase": phase,
        "lunar_date": str(lunar.day),
        "lunar_date_unit": date_unit,
        "lunar_month": month,
        "BE": year,
    }


@register.inclusion_tag("patidina/templatetags/solar-date-tag.html")
def solar_date_tag(ini_solar_date=None):
    if ini_solar_date is None:
        ini_solar_date = date.today()
    lang = _lang()
    if lang == "th":
        weekday_name = "x จันทร์ อังคาร พุธ พฤหัสบดี ศุกร์ เสาร์ อาทิตย์".split()[
            ini_solar_date.isoweekday()
        ]
        month_name = (
            "x มกราคม กุมภาพันธ์ มีนาคม เมษายน พฤษภาคม มิถุนายน "
            "กรกฎาคม สิงหาคม กันยายน ตุลาคม พฤศจิกายน ธันวาคม"
        ).split()[ini_solar_date.month]
    else:
        weekday_name = (
            "x Monday Tuesday Wednesday Thursday Friday Saturday Sunday"
        ).split()[ini_solar_date.isoweekday()]
        month_name = (
            "x January February March April May June "
            "July August September October November December"
        ).split()[ini_solar_date.month]
    return {
        "solar_dow": weekday_name,
        "solar_date": str(ini_solar_date.day),
        "solar_month": month_name,
        "CE": era(ini_solar_date, output_type=9),
    }


@register.inclusion_tag("patidina/templatetags/current-moon-phase-tag.html")
def current_moon_phase(ini_solar_date=None):
    if ini_solar_date is None:
        ini_solar_date = date.today()
    return {"moon_svg": moon_phase_svg(ini_solar_date)}


@register.inclusion_tag("patidina/templatetags/important-day-tag.html")
def important_day_tag(ini_solar_date=None):
    if ini_solar_date is None:
        ini_solar_date = date.today()
    lunar_qs, solar_qs = important_days_for(ini_solar_date)
    return {
        "lunar_important_days": lunar_qs,
        "solar_important_days": solar_qs,
    }


@register.inclusion_tag("patidina/templatetags/important-day-of-the-mth-tag.html")
def important_day_of_the_mth_tag(first_day=None, last_day=None):
    if first_day is None:
        first_day = date.today()
    if last_day is None:
        last_day = first_day + timedelta(days=6)
    return important_days_in_range(first_day, last_day)


@register.inclusion_tag("patidina/templatetags/upcoming-uposatha-dates-tag.html")
def upcoming_uposatha_dates_tag(ini_solar_date=None, months_to_calculate=12):
    from patidina.services.calendar import uposatha_year

    if ini_solar_date is None:
        ini_solar_date = date(date.today().year, 1, 1)
    return uposatha_year(ini_solar_date.year)


@register.filter(name="fraction_format")
def fraction_format(text_with_space_for_split):
    parts = str(text_with_space_for_split).split(" ")
    if len(parts) < 2:
        return text_with_space_for_split
    top = maybe_thai_digits(parts[0])
    bottom = maybe_thai_digits(parts[1])
    html_content = f"<span><sup>{top}</sup>/<sub>{bottom}</sub></span>"
    return mark_safe(html_content)


@register.filter(name="text_weekday")
def text_weekday(value, lang=None):
    lang = _lang(lang)
    weekdays_th = ["จ.", "อ.", "พ.", "พฤ.", "ศ.", "ส.", "อา."]
    weekdays_en = ["M", "T", "W", "Th", "F", "Sa", "Su"]
    if lang == "th":
        return weekdays_th[value.weekday()]
    return weekdays_en[value.weekday()]


@register.filter(name="text_month")
def text_month(value=None, lang=None):
    if value is None:
        value = date.today()
    lang = _lang(lang)
    months_th = [
        "มกราคม",
        "กุมภาพันธ์",
        "มีนาคม",
        "เมษายน",
        "พฤษภาคม",
        "มิถุนายน",
        "กรกฎาคม",
        "สิงหาคม",
        "กันยายน",
        "ตุลาคม",
        "พฤศจิกายน",
        "ธันวาคม",
    ]
    months_en = [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ]
    if lang == "th":
        return months_th[value.month - 1]
    return months_en[value.month - 1]


@register.filter(name="text_year")
def text_year(date_value=None, lang=None):
    if date_value is None:
        date_value = date.today()
    lang = _lang(lang)
    if lang == "th":
        return str(date_value.year + 543)
    return str(date_value.year)


@register.filter(name="arabic_to_thai")
def arabic_to_thai_filter(value):
    return maybe_thai_digits(value)


@register.filter(name="phase_label")
def phase_label_filter(value):
    return phase_label_fn(str(value))


@register.filter(name="mahanikaya_uposatha")
def mahanikaya_uposatha_filter(today_solar_date):
    return mahanikaya_uposatha(today_solar_date)


@register.filter(name="dhammayut_uposatha")
def dhammayut_uposatha_filter(solar_date):
    return format_dhammayut_marker(dhammayut_uposatha(solar_date))


@register.filter(name="dhammayut_marker")
def dhammayut_marker_filter(code):
    """Wrap a stored P/Pt/Pk code with a locale-aware label and tooltip."""
    return format_dhammayut_marker(code or "")


@register.simple_tag(name="dhammayut_legend_markers")
def dhammayut_legend_markers_tag():
    """P Pt Pk (en) or ป ปถ ปข (th) for the uposatha legend."""
    return dhammayut_legend_markers_fn()


@register.filter(name="get_weekday")
def get_weekday(value):
    return value.weekday()
