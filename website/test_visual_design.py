"""Tests for shared Visual Design template behaviour across project page types."""

from django.test import RequestFactory
from wagtail.images import get_image_model
from wagtail.images.tests.utils import get_test_image_file
from wagtail.models import Site
from wagtail.test.utils import WagtailPageTestCase

from website.models import (
    CatalogIndexPage,
    CollectionPage,
    EditionPage,
    VolumePage,
    WebPage,
)
from website.visual_design import (
    CRX_TEMPLATE_BLANK,
    CRX_TEMPLATE_HOME,
    CRX_TEMPLATE_WEB_COVER,
    CRX_TEMPLATE_WEB_NOTITLE,
    VISUAL_DESIGN_TEMPLATE_CHOICES,
)


class VisualDesignTemplateMixin:
    """Shared assertions; concrete test classes must set page_factory and template_prefix."""

    BODY_HTML = "<p>Visual design body content.</p>"
    TITLE = "Visual Design Test Page"

    page_factory = None
    template_prefix = None
    parent_factory = None
    extra_page_kwargs = None

    @classmethod
    def setUpTestData(cls):
        cls.site_root = Site.objects.get(is_default_site=True).root_page

    def _make_page(self):
        parent = (
            self.parent_factory(self.site_root)
            if self.parent_factory
            else self.site_root
        )
        kwargs = {
            "title": self.TITLE,
            "slug": f"vd-{self.__class__.__name__.lower()}",
        }
        if self.extra_page_kwargs:
            kwargs.update(self.extra_page_kwargs)
        page = self.page_factory(**kwargs)
        page.body = [("html", self.BODY_HTML)]
        parent.add_child(instance=page)
        page.save_revision().publish()
        return page

    def test_visual_design_template_mapping(self):
        page = self._make_page()
        request = RequestFactory().get("/")
        for custom_template, shell in VISUAL_DESIGN_TEMPLATE_CHOICES.items():
            with self.subTest(custom_template=custom_template or "default"):
                page.custom_template = custom_template
                page.save(update_fields=["custom_template"])
                expected = f"{self.template_prefix}/{shell}.html"
                self.assertEqual(page.get_template(request), expected)

    def test_default_shows_title_not_hero(self):
        page = self._make_page()
        page.custom_template = ""
        page.save(update_fields=["custom_template"])
        response = self.client.get(page.url)
        self.assertContains(response, f"<h1>{self.TITLE}</h1>")
        self.assertNotContains(response, "hero-bg")
        self.assertContains(response, self.BODY_HTML)

    def test_cover_shows_hero_when_cover_image_set(self):
        page = self._make_page()
        image = get_image_model().objects.create(
            title="cover-hero",
            file=get_test_image_file(),
        )
        page.cover_image = image
        page.custom_template = CRX_TEMPLATE_WEB_COVER
        page.save()
        response = self.client.get(page.url)
        self.assertContains(response, "hero-bg")

    def test_notitle_hides_title(self):
        page = self._make_page()
        page.custom_template = CRX_TEMPLATE_WEB_NOTITLE
        page.save(update_fields=["custom_template"])
        response = self.client.get(page.url)
        self.assertNotContains(response, f"<h1>{self.TITLE}</h1>")
        self.assertContains(response, self.BODY_HTML)

    def test_home_notitle_matches_web_notitle(self):
        page = self._make_page()
        request = RequestFactory().get("/")
        page.custom_template = CRX_TEMPLATE_WEB_NOTITLE
        page.save(update_fields=["custom_template"])
        notitle = page.get_template(request)
        page.custom_template = CRX_TEMPLATE_HOME
        page.save(update_fields=["custom_template"])
        self.assertEqual(page.get_template(request), notitle)

    def test_blank_hides_nav_and_title(self):
        page = self._make_page()
        page.custom_template = CRX_TEMPLATE_BLANK
        page.save(update_fields=["custom_template"])
        response = self.client.get(page.url)
        self.assertNotContains(response, "hall-navbar")
        self.assertNotContains(response, f"<h1>{self.TITLE}</h1>")
        self.assertContains(response, self.BODY_HTML)


class WebPageVisualDesignTests(VisualDesignTemplateMixin, WagtailPageTestCase):
    page_factory = staticmethod(lambda **kwargs: WebPage(**kwargs))
    template_prefix = "website/pages/web"


class CatalogIndexVisualDesignTests(VisualDesignTemplateMixin, WagtailPageTestCase):
    page_factory = staticmethod(lambda **kwargs: CatalogIndexPage(**kwargs))
    template_prefix = "website/pages/catalog_index"

    def test_catalog_index_lists_collections_after_body(self):
        catalog = self._make_page()
        collection = CollectionPage(
            title="Listed Canon", code="listed-canon", slug="listed-canon"
        )
        catalog.add_child(instance=collection)
        collection.save_revision().publish()
        response = self.client.get(catalog.url)
        body_index = response.content.decode().index(self.BODY_HTML)
        list_index = response.content.decode().index("Listed Canon")
        self.assertLess(body_index, list_index)
        self.assertContains(response, 'id="catalog-index"')


class CollectionPageVisualDesignTests(VisualDesignTemplateMixin, WagtailPageTestCase):
    page_factory = staticmethod(lambda **kwargs: CollectionPage(**kwargs))
    template_prefix = "website/pages/collection"
    extra_page_kwargs = {"code": "vd-collection"}

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.catalog = CatalogIndexPage(title="Parent Catalog", slug="vd-parent-catalog")
        cls.site_root.add_child(instance=cls.catalog)

    def parent_factory(self, site_root):
        return self.catalog

    def test_editions_list_after_body(self):
        collection = self._make_page()
        edition = EditionPage(title="Listed Edition", code="listed-ed")
        collection.add_child(instance=edition)
        edition.save_revision().publish()
        response = self.client.get(collection.url)
        body_index = response.content.decode().index(self.BODY_HTML)
        list_index = response.content.decode().index("Listed Edition")
        self.assertLess(body_index, list_index)
        self.assertContains(response, 'id="editions"')


class EditionPageVisualDesignTests(VisualDesignTemplateMixin, WagtailPageTestCase):
    page_factory = staticmethod(lambda **kwargs: EditionPage(**kwargs))
    template_prefix = "website/pages/edition"
    extra_page_kwargs = {"code": "vd-edition"}

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.catalog = CatalogIndexPage(title="Cat", slug="vd-ed-cat")
        cls.site_root.add_child(instance=cls.catalog)
        cls.collection = CollectionPage(title="Col", code="vd-ed-col", slug="vd-ed-col")
        cls.catalog.add_child(instance=cls.collection)

    def parent_factory(self, site_root):
        return self.collection


class VolumePageVisualDesignTests(VisualDesignTemplateMixin, WagtailPageTestCase):
    page_factory = staticmethod(lambda **kwargs: VolumePage(**kwargs))
    template_prefix = "website/pages/volume"
    extra_page_kwargs = {"code": "vd-vol"}

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.catalog = CatalogIndexPage(title="Cat", slug="vd-vol-cat")
        cls.site_root.add_child(instance=cls.catalog)
        cls.collection = CollectionPage(title="Col", code="vd-vol-col", slug="vd-vol-col")
        cls.catalog.add_child(instance=cls.collection)
        cls.edition = EditionPage(title="Ed", code="vd-vol-ed", slug="vd-vol-ed")
        cls.collection.add_child(instance=cls.edition)

    def parent_factory(self, site_root):
        return self.edition

    def test_volume_viewer_after_body(self):
        volume = self._make_page()
        response = self.client.get(volume.url)
        body_index = response.content.decode().index(self.BODY_HTML)
        viewer_index = response.content.decode().index('id="edition-app"')
        self.assertLess(body_index, viewer_index)
