from django.core.management.base import BaseCommand

from website.navbars import seed_locale_navbars


class Command(BaseCommand):
    help = (
        "Create or update CRX navbars main-en and main-th "
        "(Home + Patidina when the page exists)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help=(
                "Replace menu items with the default Home + Patidina set. "
                "Without this flag, a missing Patidina link is appended."
            ),
        )

    def handle(self, *args, **options):
        stats = seed_locale_navbars(force=options["force"])
        self.stdout.write(
            self.style.SUCCESS(
                "Locale navbars seeded: "
                f"{stats['created']} created, {stats['updated']} updated, "
                f"{stats['legacy_deleted']} legacy removed."
            )
        )
