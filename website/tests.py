from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase
from wagtail.images import get_image_model
from wagtail.images.tests.utils import get_test_image_file
from wagtail.models import Locale, Site
from wagtail.test.utils import WagtailPageTestCase

from website.models import WebPage, WebPageScrollBackground


class SiteBootstrapTests(TestCase):
    def test_locales_exist_after_bootstrap(self):
        call_command("bootstrap_site")
        codes = set(Locale.objects.values_list("language_code", flat=True))
        self.assertEqual(codes, {"en", "th", "zh"})

    def test_homepage_exists(self):
        site = Site.objects.get(is_default_site=True)
        self.assertIsInstance(site.root_page.specific, WebPage)


class ScrollBackgroundTests(WagtailPageTestCase):
    def test_scroll_background_renders_when_configured(self):
        home = Site.objects.get(is_default_site=True).root_page.specific
        image = get_image_model().objects.create(
            title="scroll-bg",
            file=get_test_image_file(),
        )
        WebPageScrollBackground.objects.create(
            page=home,
            image=image,
            sort_order=0,
        )
        home.scroll_bg_opacity = Decimal("0.40")
        home.save()

        response = self.client.get(home.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="scroll-bg"')
        self.assertContains(response, 'data-max-opacity="0.40"')
        self.assertContains(response, "scroll-bg__layer")

    def test_scroll_background_hidden_without_images(self):
        home = Site.objects.get(is_default_site=True).root_page.specific
        home.scroll_backgrounds.all().delete()

        response = self.client.get(home.url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'id="scroll-bg"')


class SacredContentSeedTests(TestCase):
    def test_seed_creates_goal_pages_and_home_body(self):
        call_command("seed_sacred_content")
        home = Site.objects.get(is_default_site=True).root_page.specific
        self.assertIsInstance(home, WebPage)
        self.assertEqual(len(home.body), 5)
        self.assertEqual(home.body[0].block_type, "html")
        self.assertEqual(home.body[1].block_type, "html")
        self.assertEqual(home.body[-1].block_type, "cardgrid")

        slugs = {"goal-repository", "goal-cross-edition", "goal-mahapadesa"}
        child_slugs = set(home.get_children().values_list("slug", flat=True))
        self.assertTrue(slugs.issubset(child_slugs))

        cross_edition = home.get_children().get(slug="goal-cross-edition").specific
        self.assertEqual(
            cross_edition.search_description,
            "A master table of contents and unified reference system.",
        )
        self.assertTrue(home.search_description)


class SacredHomeRenderTests(WagtailPageTestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_sacred_content", force=True)

    def test_home_renders_sacred_sections(self):
        home = Site.objects.get(is_default_site=True).root_page
        response = self.client.get(home.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SACRED")
        self.assertContains(response, "home-hero")
        self.assertContains(response, "home-goals")
        self.assertContains(response, "home-cases-fold")
        self.assertContains(response, "home-goal-card")

    def test_goal_page_renders(self):
        home = Site.objects.get(is_default_site=True).root_page
        goal = home.get_children().get(slug="goal-repository")
        response = self.client.get(goal.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "goal-detail")
        self.assertContains(response, "Tipiṭaka Repository")
