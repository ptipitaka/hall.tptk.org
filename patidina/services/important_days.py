"""Structured lookup for important lunar/solar days."""

from __future__ import annotations

from datetime import date, timedelta

from django.db.models import QuerySet

from patidina.models import LunarImportantDay, SolarImportantDay
from patidina.services.calendar import adhikamasa, lunar_date_for


def important_days_for(solar_date: date) -> tuple[QuerySet, QuerySet]:
    lunar = lunar_date_for(solar_date)
    if adhikamasa(solar_date.year):
        lunar_qs = LunarImportantDay.objects.filter(
            moon_phase_adhikamasa=lunar.phase_code,
            day_adhikamasa=lunar.day_code,
            month_adhikamasa=lunar.month_code,
        ).prefetch_related("details")
    else:
        lunar_qs = LunarImportantDay.objects.filter(
            moon_phase=lunar.phase_code,
            day=lunar.day_code,
            month=lunar.month_code,
        ).prefetch_related("details")

    solar_qs = SolarImportantDay.objects.filter(
        day=solar_date.day,
        month=solar_date.month,
    ).prefetch_related("details")
    return lunar_qs, solar_qs


def important_days_in_range(first_day: date, last_day: date) -> dict:
    """Collect important-day display rows for a date range (month footer)."""
    lunar_rows: list[dict] = []
    solar_rows: list = []
    seen_lunar: set[int] = set()
    seen_solar: set[int] = set()

    current = first_day
    while current <= last_day:
        lunar_qs, solar_qs = important_days_for(current)
        for obj in lunar_qs:
            if obj.pk in seen_lunar:
                continue
            seen_lunar.add(obj.pk)
            details = ", ".join(d.localized_name for d in obj.details.all())
            label = (
                obj.lunar_date_adhikamasa_label
                if adhikamasa(current.year)
                else obj.lunar_date_label
            )
            lunar_rows.append({"lunar_date": label, "details": details})
        for obj in solar_qs:
            if obj.pk in seen_solar:
                continue
            seen_solar.add(obj.pk)
            solar_rows.append(
                {
                    "label": f"{obj.day}/{obj.month}",
                    "details": ", ".join(
                        d.localized_name for d in obj.details.all()
                    ),
                }
            )
        current += timedelta(days=1)

    return {
        "lunar_important_days": lunar_rows,
        "solar_important_days": solar_rows,
    }
