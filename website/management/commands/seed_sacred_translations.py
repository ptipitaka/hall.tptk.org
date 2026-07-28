from django.core.management.base import BaseCommand

from website.sacred_content import seed_sacred_translations


class Command(BaseCommand):
    help = "Seed Thai translations of SACRED Home and goal pages."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Overwrite existing translated page content.",
        )
        parser.add_argument(
            "--locale",
            action="append",
            choices=("th",),
            dest="locales",
            help="Locale to seed (default: th). Repeat for multiple.",
        )

    def handle(self, *args, **options):
        locales = tuple(options["locales"]) if options["locales"] else ("th",)
        stats = seed_sacred_translations(force=options["force"], locales=locales)
        self.stdout.write(
            self.style.SUCCESS(
                "SACRED translations seeded: "
                f"{stats['translations_created']} page(s) created, "
                f"{stats['homes_updated']} home(s) updated, "
                f"{stats['goals_updated']} goal page(s) updated."
            )
        )
