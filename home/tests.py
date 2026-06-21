from django.test import TestCase
from wagtail.models import Site
from wagtail.test.utils import WagtailPageTestCase

from home.models import HomePage


class BootstrapSiteTests(TestCase):
    def test_bootstrap_creates_default_site(self):
        from django.core.management import call_command

        call_command("bootstrap_site")
        self.assertTrue(Site.objects.filter(is_default_site=True).exists())


class HomePageTests(WagtailPageTestCase):
    def test_homepage_template(self):
        self.assertEqual(HomePage.template, "home/home_page.html")
