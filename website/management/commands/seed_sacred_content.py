from django.core.management.base import BaseCommand

from website.sacred_content import seed_sacred_content


class Command(BaseCommand):
    help = "Seed SACRED homepage body and goal detail pages (English)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Overwrite existing homepage body and goal page content.",
        )

    def handle(self, *args, **options):
        stats = seed_sacred_content(force=options["force"])
        self.stdout.write(
            self.style.SUCCESS(
                "SACRED content seeded: "
                f"{stats['goals_created']} goal page(s) created, "
                f"{stats['goals_updated']} updated, "
                f"home seeded={bool(stats['home_seeded'])}."
            )
        )
