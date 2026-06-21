from django.core.management.base import BaseCommand
from wagtail.models import Locale


class Command(BaseCommand):
    help = "Ensure Wagtail locales exist for hall.tptk.org (en, th, zh)."

    def handle(self, *args, **options):
        created = []
        for code in ("en", "th", "zh"):
            _locale, was_created = Locale.objects.get_or_create(language_code=code)
            if was_created:
                created.append(code)

        if created:
            self.stdout.write(
                self.style.SUCCESS(f"Created locales: {', '.join(created)}")
            )
        else:
            self.stdout.write("Locales en, th, zh already exist.")
