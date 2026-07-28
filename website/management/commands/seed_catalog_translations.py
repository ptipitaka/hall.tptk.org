from django.core.management.base import BaseCommand

from website.catalog_content import seed_catalog_translations


class Command(BaseCommand):
    help = "Seed Thai translations of Buddhist Scriptures catalog pages."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Overwrite existing translated catalog content.",
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
        stats = seed_catalog_translations(force=options["force"], locales=locales)
        self.stdout.write(
            self.style.SUCCESS(
                "Catalog translations seeded: "
                f"{stats['catalogs_updated']} catalog(s) updated, "
                f"{stats['collections_created']} collection(s) created, "
                f"{stats['collections_updated']} collection(s) updated, "
                f"{stats['editions_created']} edition(s) created, "
                f"{stats['editions_updated']} edition(s) updated."
            )
        )
