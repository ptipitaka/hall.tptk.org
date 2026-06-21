from django.core.management.base import BaseCommand
from wagtail.models import Page, Site

from home.models import HomePage


class Command(BaseCommand):
    help = "Create Wagtail root page, homepage, and default site if missing."

    def handle(self, *args, **options):
        if Site.objects.filter(is_default_site=True).exists():
            self.stdout.write("Site already bootstrapped.")
            return

        root = Page.get_first_root_node()
        if root is None:
            root = Page.add_root(instance=Page(title="Root"))
            self.stdout.write(self.style.SUCCESS("Created root page."))

        home = HomePage(title="Home")
        root.add_child(instance=home)
        revision = home.save_revision()
        revision.publish()

        Site.objects.create(
            hostname="localhost",
            port=8000,
            root_page=home,
            is_default_site=True,
            site_name="hall.tptk.org",
        )
        self.stdout.write(self.style.SUCCESS("Bootstrapped Wagtail site."))
