"""Import lunar/solar important days from a JSON export (tptk.org dump)."""

from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from patidina.important_day_names import english_name_for
from patidina.models import (
    LunarImportantDay,
    LunarImportantDayDetail,
    SolarImportantDay,
    SolarImportantDayDetail,
)


DEFAULT_FIXTURE = (
    Path(__file__).resolve().parents[2] / "fixtures" / "important_days_from_tptk.json"
)


class Command(BaseCommand):
    help = "Import Patidina important days from JSON (exported from tptk.org)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            type=str,
            default=str(DEFAULT_FIXTURE),
            help="Path to important_days JSON fixture",
        )
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Delete existing important days before import",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        path = Path(options["path"])
        if not path.is_file():
            raise CommandError(f"Fixture not found: {path}")

        data = json.loads(path.read_text(encoding="utf-8"))
        if options["replace"]:
            LunarImportantDay.objects.all().delete()
            SolarImportantDay.objects.all().delete()
            self.stdout.write("Cleared existing important days.")

        lunar_count = 0
        for row in data.get("lunar", []):
            obj = LunarImportantDay.objects.create(
                moon_phase=row["moon_phase"],
                day=row["lc_day"],
                month=row["lc_month"],
                moon_phase_adhikamasa=row["moon_phase_adhikamasa"],
                day_adhikamasa=row["lc_day_adhikamasa"],
                month_adhikamasa=row["lc_month_adhikamasa"],
            )
            for detail in row.get("details", []):
                thai_name = detail["name"]
                LunarImportantDayDetail.objects.create(
                    parent=obj,
                    name=thai_name,
                    name_en=detail.get("name_en") or english_name_for(thai_name),
                    is_buddhist_commemorative=detail.get(
                        "buddhist_commemorative_day", True
                    ),
                    sort_order=detail.get("sort_order", 0),
                )
            lunar_count += 1

        solar_count = 0
        for row in data.get("solar", []):
            obj = SolarImportantDay.objects.create(
                day=row["day"],
                month=row["month"],
            )
            for detail in row.get("details", []):
                thai_name = detail["name"]
                SolarImportantDayDetail.objects.create(
                    parent=obj,
                    name=thai_name,
                    name_en=detail.get("name_en") or english_name_for(thai_name),
                    sort_order=detail.get("sort_order", 0),
                )
            solar_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Imported {lunar_count} lunar and {solar_count} solar important days "
                f"from {path}"
            )
        )
