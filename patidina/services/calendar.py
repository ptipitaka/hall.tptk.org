"""Thai Buddhist calendar / uposatha calculations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from pythaidate import CsDate, PakDate

from patidina.constants import MONTH_DISPLAY_TO_CODE


@dataclass(frozen=True)
class LunarDate:
    phase: str  # ขึ้น | แรม
    day: int
    month_display: str  # "1".."12" or "88"
    month_code: str  # model choice code
    raw: str

    @property
    def phase_code(self) -> str:
        return "01" if self.phase == "ขึ้น" else "02"

    @property
    def day_code(self) -> str:
        return f"{self.day:02d}"

    @property
    def label(self) -> str:
        return f"{self.phase} {self.day} ค่ำ เดือน {self.month_display}"


def thai_to_arabic(thai_number: str) -> str:
    mapping = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")
    return thai_number.translate(mapping)


def arabic_to_thai(text: str) -> str:
    mapping = str.maketrans("0123456789", "๐๑๒๓๔๕๖๗๘๙")
    return str(text).translate(mapping)


def xl_mod(a, b):
    return a % b


def adhikamasa(year: int) -> bool:
    """Return True if Gregorian year is a Thai lunar adhikamasa year."""
    athi = xl_mod((year - 78) - 0.45222, 2.7118886)
    return athi < 1


def era(input_date: date, output_type: int = 1) -> str:
    if output_type == 1:
        return "พุทธศักราช " + str(input_date.year + 543)
    if output_type == 5:
        return "คริสตศักราช " + str(input_date.year)
    if output_type == 6:
        return "พ.ศ. " + str(input_date.year + 543)
    if output_type == 8:
        return str(input_date.year + 543)
    if output_type == 9:
        return str(input_date.year)
    return ""


def gregorian_to_jdn(input_date: date) -> int:
    """Julian Day Number at noon (matches math.ceil of Astropy Time at midnight UTC)."""
    a = (14 - input_date.month) // 12
    y = input_date.year + 4800 - a
    m = input_date.month + 12 * a - 3
    return (
        input_date.day
        + (153 * m + 2) // 5
        + 365 * y
        + y // 4
        - y // 100
        + y // 400
        - 32045
    )


def _cs_date(input_date: date) -> CsDate:
    return CsDate.fromjulianday(gregorian_to_jdn(input_date))


def lunar_date_for(input_date: date) -> LunarDate:
    """Parse CsDate into structured lunar fields (general Thai lunar calendar)."""
    cs = _cs_date(input_date)
    parts = cs.csformat().split(" ")
    # Format: วัน… เดือน <m> ขึ้น|แรม <d> ค่ำ …
    phase = parts[3]
    day = int(thai_to_arabic(parts[4]).strip())
    month_display = thai_to_arabic(parts[2]).strip()
    month_code = MONTH_DISPLAY_TO_CODE.get(month_display, month_display.zfill(2))
    raw = f"{phase} {day} {parts[5]} {parts[1]} {month_display}"
    return LunarDate(
        phase=phase,
        day=day,
        month_display=month_display,
        month_code=month_code,
        raw=raw,
    )


def lunar_phase_marker(input_date: date) -> str:
    """Return 'ขึ้น-N' / 'แรม-N' style marker used by the month grid."""
    lunar = lunar_date_for(input_date)
    return f"{lunar.phase}-{lunar.day}"


def mahanikaya_uposatha(solar_date: date) -> str:
    """Uposatha marker for Mahanikaya from general lunar day rules."""
    lunar = lunar_date_for(solar_date)
    next_lunar = lunar_date_for(solar_date + timedelta(days=1))

    if lunar.phase == "ขึ้น":
        if lunar.day == 8:
            return "🌓"
        if lunar.day == 15:
            return "🌕"
    elif lunar.phase == "แรม":
        if lunar.day == 8:
            return "🌗"
        if lunar.day == 14 and next_lunar.day == 1:
            return "🌑"
        if lunar.day == 15:
            return "🌑"
    return ""


# Canonical Latin codes; UI maps to ป / ปถ / ปข when language is Thai.
DHAMMAYUT_PAKKHA = "P"  # ปักข์ — mid-fortnight (8th day)
DHAMMAYUT_PAKKHA_FULL = "Pt"  # ปักข์ถ้วน — full 15-day fortnight
DHAMMAYUT_PAKKHA_DEFICIENT = "Pk"  # ปักข์ขาด — deficient 14-day fortnight
DHAMMAYUT_CODES = (
    DHAMMAYUT_PAKKHA,
    DHAMMAYUT_PAKKHA_FULL,
    DHAMMAYUT_PAKKHA_DEFICIENT,
)


def dhammayut_uposatha(solar_date: date) -> str:
    """Uposatha marker for Dhammayut via PakDate (more precise).

    Returns Latin abbreviations: P (pakkha), Pt (full), Pk (deficient).
    """
    p = PakDate(date=solar_date)
    if not p.iswanphra:
        return ""

    parts = str(p).split()
    if len(parts) >= 3 and parts[-3] == "๘":
        return DHAMMAYUT_PAKKHA
    if parts and parts[-1] == "(ปักข์ถ้วน)":
        return DHAMMAYUT_PAKKHA_FULL
    if parts and parts[-1] == "(ปักข์ขาด)":
        return DHAMMAYUT_PAKKHA_DEFICIENT
    return ""


def moon_phase_row(days: list[date]) -> list[str]:
    """Build lunar row cells matching the original calendar widget."""
    previous_phase = None
    cells: list[str] = []
    for day in days:
        marker = lunar_phase_marker(day)
        current_phase, night = marker.split("-", 1)
        night = night.strip()
        if current_phase != previous_phase:
            cells.append(current_phase)
            previous_phase = current_phase
        elif current_phase == "ขึ้น":
            cells.append(f">{night}")
        else:
            cells.append(f"<{night}")
    return cells


def month_days(year: int, month: int) -> list[date]:
    first = date(year, month, 1)
    next_month = (first.replace(day=28) + timedelta(days=4)).replace(day=1)
    last = next_month - timedelta(days=1)
    return [first + timedelta(days=i) for i in range((last - first).days + 1)]


def month_calendar(year: int, month: int) -> dict:
    from patidina.services.important_days import important_days_for

    days = month_days(year, month)
    first_day = days[0]
    last_day = days[-1]
    days_with_important = []
    for day in days:
        lunar_qs, solar_qs = important_days_for(day)
        days_with_important.append(
            {
                "day": day,
                "lunar_important_days": lunar_qs,
                "solar_important_days": solar_qs,
                "mahanikaya": mahanikaya_uposatha(day),
                "dhammayut": dhammayut_uposatha(day),
            }
        )
    return {
        "first_day_of_month": first_day,
        "last_day_of_month": last_day,
        "days": days,
        "days_with_moon_phase_changes": moon_phase_row(days),
        "days_with_important_days": days_with_important,
        "prev_year": (first_day.replace(day=1) - timedelta(days=1)).year,
        "prev_month": (first_day.replace(day=1) - timedelta(days=1)).month,
        "next_year": (last_day + timedelta(days=1)).year,
        "next_month": (last_day + timedelta(days=1)).month,
    }


def uposatha_year(year: int) -> dict:
    """
    Build monthly uposatha lists for a Gregorian year.

    Each month maps to a list of up to ~5 date dicts (or None placeholders)
    for the year overview table used by the original template.
    """
    monthly: dict[str, list] = {}
    next_uposatha = None
    today = date.today()

    for month in range(1, 13):
        entries = []
        for day in month_days(year, month):
            maha = mahanikaya_uposatha(day)
            dham = dhammayut_uposatha(day)
            if not maha and not dham:
                continue
            lunar = lunar_date_for(day)
            phase_key = f"{lunar.phase} {lunar.day}"
            entry = {
                "ld": day.toordinal(),
                "date": day,
                "day": day.day,
                "phase": phase_key,
                "mahanikaya": maha,
                "dhammayut": dham,
            }
            entries.append(entry)
            if next_uposatha is None and day >= today and (maha or dham):
                next_uposatha = entry

        # Pad to 5 columns like the original table layout
        while len(entries) < 5:
            entries.append(None)
        monthly[f"{month} {year + 543}"] = entries[:5]

    return {
        "monthly_uposatha": monthly,
        "next_uposatha_day": next_uposatha or {"ld": -1},
        "show_all_in_year": True,
    }
