from decimal import Decimal
import uuid

from django.core.management import call_command
from django.test import RequestFactory, TestCase
from wagtail.images import get_image_model
from wagtail.images.tests.utils import get_test_image_file
from wagtail.models import Locale, Site
from wagtail.test.utils import WagtailPageTestCase

from snippets.models import (
    CanonicalSection,
    Classification,
    ContentLanguage,
    ContentScript,
    Country,
    Tradition,
)
from website.visual_design import (
    CRX_TEMPLATE_BLANK,
    CRX_TEMPLATE_HOME,
    CRX_TEMPLATE_WEB_COVER,
    CRX_TEMPLATE_WEB_NOTITLE,
)
from website.models import CatalogIndexPage, CollectionPage, EditionPage, VolumePage, WebPage, WebPageScrollBackground
from website.breadcrumbs import (
    get_catalog_breadcrumb_items,
    get_catalog_breadcrumb_parent,
)


class SiteBootstrapTests(TestCase):
    def test_locales_exist_after_bootstrap(self):
        call_command("bootstrap_site")
        codes = set(Locale.objects.values_list("language_code", flat=True))
        self.assertEqual(codes, {"en", "th"})

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


class CatalogIndexPageTemplateTests(WagtailPageTestCase):
    INTRO_TEXT = "Browse Theravada Tipitaka collections for cross-edition study."

    def setUp(self):
        self.catalog = CatalogIndexPage(
            title="Sacred Catalogue",
            slug="sacred-catalog-test",
        )
        self.catalog.body = [("html", f"<p>{self.INTRO_TEXT}</p>")]
        Site.objects.get(is_default_site=True).root_page.add_child(
            instance=self.catalog
        )

    def test_visual_design_templates_render_body(self):
        request = RequestFactory().get("/")
        templates = {
            "": "website/pages/catalog_index/default.html",
            CRX_TEMPLATE_WEB_COVER: "website/pages/catalog_index/cover.html",
            CRX_TEMPLATE_WEB_NOTITLE: "website/pages/catalog_index/notitle.html",
            CRX_TEMPLATE_HOME: "website/pages/catalog_index/notitle.html",
            CRX_TEMPLATE_BLANK: "website/pages/catalog_index/blank.html",
        }
        for custom_template, expected in templates.items():
            with self.subTest(custom_template=custom_template or "default"):
                self.catalog.custom_template = custom_template
                self.catalog.save(update_fields=["custom_template"])
                self.assertEqual(self.catalog.get_template(request), expected)
                response = self.client.get(self.catalog.url)
                self.assertContains(response, self.INTRO_TEXT)
                if custom_template in ("", CRX_TEMPLATE_WEB_COVER):
                    self.assertContains(response, "<h1>Sacred Catalogue</h1>")
                else:
                    self.assertNotContains(response, "<h1>Sacred Catalogue</h1>")


class CatalogIndexPageGroupingTests(WagtailPageTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.locale = Locale.get_default()
        cls.tipitaka_key = uuid.uuid4()
        cls.atthakatha_key = uuid.uuid4()
        cls.tipitaka = Classification.objects.create(
            locale=cls.locale,
            translation_key=cls.tipitaka_key,
            slug="tipitaka-test",
            siglum="TP",
            title="Tipiṭaka",
            sort_order=0,
        )
        cls.atthakatha = Classification.objects.create(
            locale=cls.locale,
            translation_key=cls.atthakatha_key,
            slug="atthakatha-test",
            siglum="AK",
            title="Aṭṭhakathā",
            sort_order=1,
        )
        cls.theravada = Tradition.objects.create(
            locale=cls.locale,
            translation_key=uuid.uuid4(),
            code="theravada-test",
            slug="theravada-test",
            name="Theravāda",
            sort_order=0,
        )
        cls.mahayana = Tradition.objects.create(
            locale=cls.locale,
            translation_key=uuid.uuid4(),
            code="mahayana-test",
            slug="mahayana-test",
            name="Mahāyāna",
            sort_order=1,
        )
        cls.thailand = Country.objects.create(
            locale=cls.locale,
            translation_key=uuid.uuid4(),
            code="th",
            slug="thailand-test",
            name="Thailand",
            sort_order=0,
        )

    def setUp(self):
        self.catalog = CatalogIndexPage(
            title="Sacred Catalogue",
            slug="sacred-catalog-group-test",
        )
        self.catalog.body = [("html", "<p>Grouped collections.</p>")]
        Site.objects.get(is_default_site=True).root_page.add_child(instance=self.catalog)

    def _add_collection(
        self,
        *,
        title,
        slug,
        code,
        classification,
        catalog_sort_order,
        tradition=None,
        country=None,
    ):
        collection = CollectionPage(
            title=title,
            slug=slug,
            code=code,
            classification=classification,
            tradition=tradition,
            country=country,
            catalog_sort_order=catalog_sort_order,
        )
        self.catalog.add_child(instance=collection)
        return collection

    def test_get_catalog_groups_orders_by_classification_then_sort_order(self):
        self._add_collection(
            title="Commentary Set",
            slug="commentary-set",
            code="commentary-set",
            classification=self.atthakatha,
            tradition=self.theravada,
            catalog_sort_order=0,
        )
        self._add_collection(
            title="Pali Canon B",
            slug="pali-canon-b",
            code="pali-canon-b",
            classification=self.tipitaka,
            tradition=self.theravada,
            catalog_sort_order=2,
        )
        self._add_collection(
            title="Pali Canon A",
            slug="pali-canon-a",
            code="pali-canon-a",
            classification=self.tipitaka,
            tradition=self.theravada,
            catalog_sort_order=1,
        )
        self._add_collection(
            title="Misc Canon",
            slug="misc-canon",
            code="misc-canon",
            classification=None,
            catalog_sort_order=0,
        )

        groups = self.catalog.get_catalog_groups()
        self.assertEqual(len(groups), 3)
        self.assertEqual(groups[0]["classification"], self.tipitaka)
        self.assertEqual(groups[0]["tradition_groups"][0]["tradition"], self.theravada)
        self.assertEqual(
            [c.title for c in groups[0]["tradition_groups"][0]["collections"]],
            ["Pali Canon A", "Pali Canon B"],
        )
        self.assertEqual(groups[1]["classification"], self.atthakatha)
        self.assertEqual(
            groups[1]["tradition_groups"][0]["collections"][0].title,
            "Commentary Set",
        )
        self.assertIsNone(groups[2]["classification"])
        self.assertIsNone(groups[2]["tradition_groups"][0]["tradition"])
        self.assertEqual(
            groups[2]["tradition_groups"][0]["collections"][0].title,
            "Misc Canon",
        )

    def test_get_catalog_groups_nests_by_tradition(self):
        self._add_collection(
            title="Mahayana Canon",
            slug="mahayana-canon",
            code="mahayana-canon",
            classification=self.tipitaka,
            tradition=self.mahayana,
            catalog_sort_order=1,
        )
        self._add_collection(
            title="Theravada Canon",
            slug="theravada-canon",
            code="theravada-canon",
            classification=self.tipitaka,
            tradition=self.theravada,
            catalog_sort_order=0,
        )

        groups = self.catalog.get_catalog_groups()
        self.assertEqual(len(groups), 1)
        tradition_groups = groups[0]["tradition_groups"]
        self.assertEqual(len(tradition_groups), 2)
        self.assertEqual(tradition_groups[0]["tradition"], self.theravada)
        self.assertEqual(tradition_groups[0]["collections"][0].title, "Theravada Canon")
        self.assertEqual(tradition_groups[1]["tradition"], self.mahayana)
        self.assertEqual(tradition_groups[1]["collections"][0].title, "Mahayana Canon")

    def test_catalog_index_renders_grouped_collections(self):
        self._add_collection(
            title="Pali Canon",
            slug="pali-canon",
            code="pali-canon",
            classification=self.tipitaka,
            tradition=self.theravada,
            catalog_sort_order=0,
        )
        self._add_collection(
            title="Chinese Canon",
            slug="chinese-canon",
            code="chinese-canon",
            classification=self.tipitaka,
            tradition=self.mahayana,
            catalog_sort_order=1,
        )

        response = self.client.get(self.catalog.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="catalog-group__heading"')
        self.assertContains(response, 'class="catalog-group__tradition-heading"')
        self.assertContains(response, "Tipiṭaka")
        self.assertContains(response, "Theravāda")
        self.assertContains(response, "Mahāyāna")
        self.assertContains(response, "Pali Canon")
        self.assertContains(response, "Chinese Canon")
        self.assertContains(response, 'id="catalog-index"')

    def test_catalog_index_shows_collection_blurb_under_title(self):
        collection = self._add_collection(
            title="Pali Canon",
            slug="pali-canon-body",
            code="pali-canon-body",
            classification=self.tipitaka,
            catalog_sort_order=0,
        )
        blurb = "45-volume Pali-language Canon in Thai script."
        collection.search_description = blurb
        collection.save_revision().publish()

        response = self.client.get(self.catalog.url)
        self.assertContains(response, "Pali Canon")
        self.assertContains(response, blurb)
        self.assertContains(response, 'class="catalog-group__item-description"')
        self.assertNotContains(response, "crx-grid")

    def test_catalog_index_shows_country_flag_beside_title(self):
        self._add_collection(
            title="Syāmaraṭṭhassa tepiṭakaṃ",
            slug="syamarattha-flag",
            code="syamarattha-flag",
            classification=self.tipitaka,
            country=self.thailand,
            catalog_sort_order=0,
        )

        response = self.client.get(self.catalog.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="catalog-group__flag"')
        self.assertContains(response, "website/img/flags/th.svg")
        self.assertContains(response, 'alt="Thailand"')

    def test_collection_cover_follows_visual_design(self):
        image = get_image_model().objects.create(
            title="collection-cover",
            file=get_test_image_file(),
        )
        collection = self._add_collection(
            title="Pali Canon",
            slug="pali-canon-cover",
            code="pali-canon-cover",
            classification=self.tipitaka,
            catalog_sort_order=0,
        )
        collection.cover_image = image
        collection.save()

        default_response = self.client.get(collection.url)
        self.assertEqual(default_response.status_code, 200)
        self.assertNotContains(default_response, "hero-bg")

        collection.custom_template = CRX_TEMPLATE_WEB_COVER
        collection.save(update_fields=["custom_template"])
        cover_response = self.client.get(collection.url)
        self.assertContains(cover_response, "hero-bg")

        index = self.client.get(self.catalog.url)
        self.assertEqual(index.status_code, 200)
        self.assertContains(index, "catalog-group__thumb")
        self.assertContains(index, "format-webp")


class CollectionPageEditionGroupsTests(WagtailPageTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.catalog = CatalogIndexPage(title="Catalog", slug="edition-groups-cat")
        Site.objects.get(is_default_site=True).root_page.add_child(instance=cls.catalog)
        cls.collection = CollectionPage(title="Work", code="work", slug="work")
        cls.catalog.add_child(instance=cls.collection)

    def _add_edition(self, *, title, code, edition_role):
        edition = EditionPage(
            title=title,
            code=code,
            edition_role=edition_role,
        )
        self.collection.add_child(instance=edition)
        edition.save_revision().publish()
        return edition

    def test_get_edition_groups_orders_by_role_then_menu_order(self):
        self._add_edition(
            title="Thai Translation",
            code="TH2559",
            edition_role=EditionPage.Role.TRANSLATION,
        )
        self._add_edition(
            title="Pali 2560",
            code="PALI2560",
            edition_role=EditionPage.Role.SOURCE,
        )
        self._add_edition(
            title="Pali 2538",
            code="PALI2538",
            edition_role=EditionPage.Role.SOURCE,
        )

        groups = self.collection.get_edition_groups()
        self.assertEqual(len(groups), 2)
        self.assertEqual(groups[0]["role"], EditionPage.Role.SOURCE)
        # Within a role, preserve Wagtail sibling menu order (path), not code.
        self.assertEqual(
            [edition.code for edition in groups[0]["editions"]],
            ["PALI2560", "PALI2538"],
        )
        self.assertEqual(groups[1]["role"], EditionPage.Role.TRANSLATION)
        self.assertEqual(groups[1]["editions"][0].code, "TH2559")

    def test_get_edition_groups_shows_shared_cover_only_once_per_run(self):
        image_model = get_image_model()
        cover_a = image_model.objects.create(
            title="cover-a",
            file=get_test_image_file(),
        )
        cover_b = image_model.objects.create(
            title="cover-b",
            file=get_test_image_file(),
        )

        first = self._add_edition(
            title="Pali 2538",
            code="PALI2538",
            edition_role=EditionPage.Role.SOURCE,
        )
        first.cover_image = cover_a
        first.save_revision().publish()

        second = self._add_edition(
            title="Pali 2556",
            code="PALI2556",
            edition_role=EditionPage.Role.SOURCE,
        )
        second.cover_image = cover_a
        second.save_revision().publish()

        third = self._add_edition(
            title="Pali other",
            code="PALIOTHER",
            edition_role=EditionPage.Role.SOURCE,
        )
        third.cover_image = cover_b
        third.save_revision().publish()

        groups = self.collection.get_edition_groups()
        source = groups[0]["editions"]
        self.assertTrue(source[0].show_cover_thumb)
        self.assertFalse(source[1].show_cover_thumb)
        self.assertTrue(source[2].show_cover_thumb)

        response = self.client.get(self.collection.url)
        self.assertContains(response, 'class="collection-editions__thumb"')
        self.assertContains(
            response,
            'class="collection-editions__thumb-wrap collection-editions__thumb-wrap--placeholder"',
        )

    def test_collection_page_renders_grouped_editions(self):
        self._add_edition(
            title="Pali 2560",
            code="PALI2560",
            edition_role=EditionPage.Role.SOURCE,
        )

        response = self.client.get(self.collection.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="collection-editions__group-heading"')
        self.assertContains(response, "Source")
        self.assertContains(response, "PALI2560")
        # Title leads; code is secondary.
        content = response.content.decode()
        title_pos = content.index("Pali 2560")
        code_pos = content.index("PALI2560")
        self.assertLess(title_pos, code_pos)

    def test_collection_page_omits_edition_publication_metadata(self):
        locale = Locale.get_default()
        tradition = Tradition.objects.create(
            locale=locale,
            translation_key=uuid.uuid4(),
            code="theravada-ed-meta",
            slug="theravada-ed-meta",
            name="Theravāda",
        )
        language = ContentLanguage.objects.create(
            locale=locale,
            translation_key=uuid.uuid4(),
            code="pali-ed-meta",
            slug="pali-ed-meta",
            name="Pāli",
        )
        script = ContentScript.objects.create(
            locale=locale,
            translation_key=uuid.uuid4(),
            code="thai-ed-meta",
            slug="thai-ed-meta",
            name="Thai",
        )
        self.collection.tradition = tradition
        self.collection.save()

        edition = EditionPage(
            title="Catalogued Edition",
            code="CAT-ED",
            edition_role=EditionPage.Role.SOURCE,
            publisher="Mahamakut Buddhist University",
            place_of_publication="Bangkok, Thailand",
            published_year="2560BE/2017CE",
            print_number="8",
            isbn_number="978-974-651-234-5",
            volume_set_count=65,
            physical_volume_count=70,
            description="<p>Short summary that should not appear on the edition page.</p>",
        )
        self.collection.add_child(instance=edition)
        edition.content_languages.add(language)
        edition.content_scripts.add(script)
        edition.save_revision().publish()

        response = self.client.get(self.collection.url)
        self.assertContains(response, "CAT-ED")
        self.assertContains(response, "Catalogued Edition")
        self.assertNotContains(response, "Volumes")
        self.assertNotContains(response, "65 sets (70 books)")
        self.assertNotContains(response, 'class="edition-catalog-meta"')
        self.assertNotContains(response, "Mahamakut Buddhist University")
        self.assertNotContains(response, "Bangkok, Thailand")

        edition_response = self.client.get(edition.url)
        self.assertEqual(edition_response.status_code, 200)
        self.assertContains(edition_response, "Tradition")
        self.assertContains(edition_response, "Theravāda")
        self.assertContains(edition_response, "Language")
        self.assertContains(edition_response, "Pāli")
        self.assertContains(edition_response, "Script")
        self.assertContains(edition_response, "Thai")
        self.assertContains(edition_response, "Volumes")
        self.assertContains(edition_response, "65 sets (70 books)")
        self.assertNotContains(edition_response, "Volume sets")
        self.assertNotContains(edition_response, "Physical volumes")
        self.assertContains(edition_response, "Mahamakut Buddhist University")
        self.assertContains(edition_response, "Print number")
        self.assertContains(edition_response, "Published year")
        self.assertContains(edition_response, 'class="edition-catalog-meta"')
        self.assertNotContains(
            edition_response,
            "Short summary that should not appear on the edition page.",
        )
        self.assertNotContains(edition_response, 'class="edition-description"')


class EditionPageVolumeGroupsTests(WagtailPageTestCase):
    @classmethod
    def setUpTestData(cls):
        Locale.objects.get_or_create(language_code="en")
        en = Locale.objects.get(language_code="en")
        cls.vin = CanonicalSection.objects.create(
            locale=en,
            code="vin",
            slug="vin",
            kind=CanonicalSection.Kind.PITAKA,
            name="Vinayapiṭaka",
            sort_order=0,
        )
        cls.sut = CanonicalSection.objects.create(
            locale=en,
            code="sut",
            slug="sut",
            kind=CanonicalSection.Kind.PITAKA,
            name="Suttantapiṭaka",
            sort_order=1,
        )
        cls.dn = CanonicalSection.objects.create(
            locale=en,
            code="dn",
            slug="dn",
            kind=CanonicalSection.Kind.NIKAYA,
            name="Dīghanikāya",
            parent=cls.sut,
            sort_order=0,
        )
        cls.mn = CanonicalSection.objects.create(
            locale=en,
            code="mn",
            slug="mn",
            kind=CanonicalSection.Kind.NIKAYA,
            name="Majjhimanikāya",
            parent=cls.sut,
            sort_order=1,
        )

        cls.catalog = CatalogIndexPage(title="Catalog", slug="volume-groups-cat")
        Site.objects.get(is_default_site=True).root_page.add_child(instance=cls.catalog)
        cls.collection = CollectionPage(title="Work", code="vol-work", slug="vol-work")
        cls.catalog.add_child(instance=cls.collection)
        cls.edition = EditionPage(
            title="Pali Edition",
            code="pali-vol",
            slug="pali-vol",
            edition_role=EditionPage.Role.SOURCE,
        )
        cls.collection.add_child(instance=cls.edition)
        cls.edition.save_revision().publish()

    def _add_volume(self, *, title, code, volume_index, section=None, number=""):
        volume = VolumePage(
            title=title,
            code=code,
            slug=code,
            volume_index=volume_index,
            number=number or str(volume_index),
            section=section,
        )
        self.edition.add_child(instance=volume)
        volume.save_revision().publish()
        return volume

    def test_get_volume_groups_nests_nikayas_under_pitaka(self):
        self._add_volume(
            title="Vinaya 1",
            code="vol-01",
            volume_index=1,
            section=self.vin,
        )
        self._add_volume(
            title="Vinaya 2",
            code="vol-02",
            volume_index=2,
            section=self.vin,
        )
        self._add_volume(
            title="DN 1",
            code="vol-09",
            volume_index=9,
            section=self.dn,
        )
        self._add_volume(
            title="MN 1",
            code="vol-12",
            volume_index=12,
            section=self.mn,
        )
        self._add_volume(
            title="Unsorted",
            code="vol-99",
            volume_index=99,
            section=None,
        )

        groups = self.edition.get_volume_groups()
        self.assertEqual(len(groups), 3)

        vin_group = groups[0]
        self.assertEqual(vin_group["section"], self.vin)
        self.assertEqual(vin_group["count"], 2)
        self.assertEqual([v.code for v in vin_group["volumes"]], ["vol-01", "vol-02"])
        self.assertEqual(vin_group["subgroups"], [])

        sut_group = groups[1]
        self.assertEqual(sut_group["section"], self.sut)
        self.assertEqual(sut_group["count"], 2)
        self.assertEqual(sut_group["volumes"], [])
        self.assertEqual(len(sut_group["subgroups"]), 2)
        self.assertEqual(sut_group["subgroups"][0]["section"], self.dn)
        self.assertEqual(sut_group["subgroups"][0]["count"], 1)
        self.assertEqual(sut_group["subgroups"][0]["volumes"][0].code, "vol-09")
        self.assertEqual(sut_group["subgroups"][1]["section"], self.mn)

        other = groups[2]
        self.assertIsNone(other["section"])
        self.assertEqual(other["count"], 1)
        self.assertEqual(other["volumes"][0].code, "vol-99")

    def test_edition_page_renders_grouped_volumes(self):
        self._add_volume(
            title="Vinayapiṭake Mahāvibhaṅgassa",
            code="vol-01",
            volume_index=1,
            section=self.vin,
        )
        self._add_volume(
            title="Dīghanikāyassa Sīlakkhandhavaggo",
            code="vol-09",
            volume_index=9,
            section=self.dn,
        )

        response = self.client.get(self.edition.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="edition-volumes__group-heading"')
        self.assertContains(response, "Vinayapiṭaka")
        self.assertContains(response, "Suttantapiṭaka")
        self.assertContains(response, 'class="edition-volumes__subgroup-heading"')
        self.assertContains(response, "Dīghanikāya")
        self.assertContains(response, "Vinayapiṭake Mahāvibhaṅgassa")
        self.assertContains(response, "1 volume")
        self.assertContains(response, "Dīghanikāyassa Sīlakkhandhavaggo")


class CatalogBreadcrumbTests(WagtailPageTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.catalog = CatalogIndexPage(title="Buddhist Scriptures", slug="breadcrumbs-catalog")
        Site.objects.get(is_default_site=True).root_page.add_child(instance=cls.catalog)
        cls.collection = CollectionPage(
            title="Syāmaraṭṭhassa tepiṭakaṃ",
            code="syamarattha",
            slug="syamarattha",
        )
        cls.catalog.add_child(instance=cls.collection)
        cls.edition = EditionPage(
            title="Pali 2538",
            code="pali2538",
            slug="pali2538",
            edition_role=EditionPage.Role.SOURCE,
        )
        cls.collection.add_child(instance=cls.edition)
        cls.volume = VolumePage(
            title="Volume 1",
            code="vol-1",
            slug="vol-1",
            volume_index=1,
        )
        cls.edition.add_child(instance=cls.volume)

    def test_catalog_index_has_no_breadcrumb_items(self):
        self.assertEqual(get_catalog_breadcrumb_items(self.catalog), [])

    def test_collection_breadcrumb_trail(self):
        items = get_catalog_breadcrumb_items(self.collection)
        self.assertEqual([page.title for page in items], [
            "Buddhist Scriptures",
            "Syāmaraṭṭhassa tepiṭakaṃ",
        ])
        self.assertEqual(
            get_catalog_breadcrumb_parent(self.collection),
            self.catalog,
        )

    def test_edition_breadcrumb_trail(self):
        items = get_catalog_breadcrumb_items(self.edition)
        self.assertEqual(len(items), 3)
        self.assertEqual(items[-1], self.edition)
        self.assertEqual(get_catalog_breadcrumb_parent(self.edition), self.collection)

    def test_volume_breadcrumb_trail(self):
        items = get_catalog_breadcrumb_items(self.volume)
        self.assertEqual(len(items), 4)
        self.assertEqual(items[-1], self.volume)
        self.assertEqual(get_catalog_breadcrumb_parent(self.volume), self.edition)

    def test_catalog_index_page_renders_without_breadcrumbs(self):
        response = self.client.get(self.catalog.url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "catalog-breadcrumbs")

    def test_collection_page_renders_breadcrumbs(self):
        response = self.client.get(self.collection.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="catalog-breadcrumbs"')
        self.assertContains(response, 'href="%s"' % self.catalog.url)
        self.assertContains(response, "Buddhist Scriptures")
        self.assertNotContains(response, "catalog-breadcrumbs__item--current")
        self.assertContains(response, '"@type": "BreadcrumbList"')

    def test_edition_page_renders_ancestor_trail_only(self):
        response = self.client.get(self.edition.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'href="%s"' % self.catalog.url)
        self.assertContains(response, 'href="%s"' % self.collection.url)
        self.assertNotContains(response, "catalog-breadcrumbs__item--current")
        self.assertContains(response, "catalog-breadcrumbs__back-link")
        self.assertContains(response, "catalog-breadcrumbs__trail")
        self.assertContains(response, "<h1>Pali 2538</h1>")


class SacredContentSeedTests(TestCase):
    def test_seed_creates_goal_pages_and_home_body(self):
        call_command("seed_sacred_content")
        home = Site.objects.get(is_default_site=True).root_page.specific
        self.assertIsInstance(home, WebPage)
        self.assertEqual(len(home.body), 6)
        self.assertEqual(home.body[0].block_type, "html")
        self.assertEqual(home.body[1].block_type, "html")
        self.assertEqual(home.body[-1].block_type, "zigzag")

        slugs = {"goal-repository", "goal-cross-edition", "goal-mahapadesa"}
        child_slugs = set(home.get_children().values_list("slug", flat=True))
        self.assertTrue(slugs.issubset(child_slugs))

        cross_edition = home.get_children().get(slug="goal-cross-edition").specific
        self.assertEqual(
            cross_edition.search_description,
            "A master table of contents and unified reference system.",
        )
        self.assertTrue(home.search_description)

    def test_repository_goal_card_links_to_catalog(self):
        from website.models import CatalogIndexPage

        home = Site.objects.get(is_default_site=True).root_page.specific
        catalog = CatalogIndexPage(
            title="Buddhist Scriptures",
            slug="buddhist-scriptures",
        )
        home.add_child(instance=catalog)
        catalog.save_revision().publish()

        call_command("seed_sacred_content")
        home.refresh_from_db()

        from website.sacred_content import _first_goal_card_link_slug

        self.assertEqual(_first_goal_card_link_slug(home.body), "buddhist-scriptures")


class SacredTranslationSeedTests(TestCase):
    def test_seed_creates_thai_home(self):
        call_command("seed_sacred_content", force=True)
        call_command("seed_sacred_translations", force=True)
        home_en = Site.objects.get(is_default_site=True).root_page
        home_th = home_en.get_translation(Locale.objects.get(language_code="th"))
        self.assertEqual(home_th.url, "/th/")
        self.assertEqual(len(home_th.specific.body), 6)
        self.assertEqual(home_th.specific.body[-1].block_type, "zigzag")
        self.assertFalse(
            home_en.get_translations(inclusive=False)
            .filter(locale__language_code="zh")
            .exists()
        )


class SacredTranslationRenderTests(WagtailPageTestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_sacred_content", force=True)
        call_command("seed_sacred_translations", force=True)
        call_command("seed_locale_navbars", force=True)

    def test_thai_home_renders_localized_content(self):
        home_en = Site.objects.get(is_default_site=True).root_page
        home_th = home_en.get_translation(Locale.objects.get(language_code="th"))
        response = self.client.get(home_th.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "หอพระไตรปิฎกเพื่อประชาชน")
        self.assertContains(response, "พันธกิจ")
        self.assertContains(response, "ประเภทคัมภีร์")

    def test_language_switcher_renders(self):
        home = Site.objects.get(is_default_site=True).root_page
        response = self.client.get(home.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "hall-lang-switcher")
        self.assertContains(response, 'href="/th/"')
        self.assertNotContains(response, 'href="/zh/"')
        self.assertNotContains(response, "中文")

    def test_thai_goal_page_renders(self):
        home_en = Site.objects.get(is_default_site=True).root_page
        goal_en = home_en.get_children().get(slug="goal-repository")
        goal_th = goal_en.get_translation(Locale.objects.get(language_code="th"))
        response = self.client.get(goal_th.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "คลังพระไตรปิฎก")

    def test_locale_navbar_switches_home_label(self):
        home_en = Site.objects.get(is_default_site=True).root_page
        home_th = home_en.get_translation(Locale.objects.get(language_code="th"))
        en_response = self.client.get(home_en.url)
        th_response = self.client.get(home_th.url)
        en_menu = en_response.content.decode().split('id="navbar-menu"', 1)[1].split("</ul>", 1)[0]
        th_menu = th_response.content.decode().split('id="navbar-menu"', 1)[1].split("</ul>", 1)[0]
        self.assertIn("Home", en_menu)
        self.assertIn("หน้าแรก", th_menu)
        self.assertNotIn("หน้าแรก", en_menu)

    def test_locale_navbar_includes_patidina(self):
        call_command("seed_patidina_page")
        call_command("seed_locale_navbars", force=True)
        home_en = Site.objects.get(is_default_site=True).root_page
        home_th = home_en.get_translation(Locale.objects.get(language_code="th"))
        en_menu = (
            self.client.get(home_en.url)
            .content.decode()
            .split('id="navbar-menu"', 1)[1]
            .split("</ul>", 1)[0]
        )
        th_menu = (
            self.client.get(home_th.url)
            .content.decode()
            .split('id="navbar-menu"', 1)[1]
            .split("</ul>", 1)[0]
        )
        self.assertIn("Patidina", en_menu)
        self.assertIn('href="/patidina/"', en_menu)
        self.assertIn("ปฏิทิน", th_menu)
        self.assertIn('href="/th/patidina/"', th_menu)

    def test_navbar_menu_behind_hamburger(self):
        home = Site.objects.get(is_default_site=True).root_page
        response = self.client.get(home.url)
        html = response.content.decode()
        self.assertIn("hall-navbar--menu-toggle", html)
        self.assertIn('id="navbar-menu"', html)
        self.assertIn("hall-navbar__menu-toggler", html)
        self.assertIn("hall-lang-switcher", html)
        self.assertIn('class="collapse hall-navbar__menu w-100"', html)
        self.assertIn("hall-navbar__search--bar", html)
        self.assertIn("hall-navbar__search--menu", html)


class CatalogTranslationSeedTests(WagtailPageTestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("bootstrap_site")
        call_command("seed_catalog_reference")
        call_command("seed_sacred_translations", force=True)
        cls.en = Locale.get_default()
        cls.th = Locale.objects.get(language_code="th")
        home = Site.objects.get(is_default_site=True).root_page
        cls.catalog_en = CatalogIndexPage(
            title="Buddhist Scriptures",
            slug="buddhist-scriptures",
            search_description="English catalog",
        )
        cls.catalog_en.body = [
            (
                "html",
                "<p>The Tipiṭaka and Buddhist Scripture Catalog (SACRED).</p>",
            )
        ]
        home.add_child(instance=cls.catalog_en)
        cls.catalog_en.save_revision().publish()

        tipitaka = Classification.objects.get(locale=cls.en, slug="tipitaka")
        tradition = Tradition.objects.get(locale=cls.en, code="theravada")
        cls.collection_en = CollectionPage(
            title="Syāmaraṭṭhassa tepiṭakaṃ",
            slug="syamarattha-seed",
            code="sy",
            classification=tipitaka,
            tradition=tradition,
            search_description="English collection",
        )
        cls.collection_en.body = [
            ("html", "<p>English collection description.</p>")
        ]
        cls.catalog_en.add_child(instance=cls.collection_en)
        cls.collection_en.save_revision().publish()

    def test_seed_creates_thai_catalog_tree(self):
        call_command("seed_catalog_translations", force=True)
        catalog_th = self.catalog_en.get_translation(self.th).specific
        self.assertEqual(catalog_th.title, "คัมภีร์ทางพุทธศาสนา")
        self.assertEqual(catalog_th.url, "/th/buddhist-scriptures/")

        response = self.client.get(catalog_th.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "พระไตรปิฎก")
        self.assertNotContains(response, "TP ·")
        self.assertContains(response, "เถรวาท")
        self.assertContains(response, "สยามรัฐเตปิฎกํ")
        self.assertNotContains(response, "No collections yet.")

        collection_th = self.collection_en.get_translation(self.th).specific
        self.assertEqual(collection_th.title, "สยามรัฐเตปิฎกํ")
        self.assertEqual(collection_th.classification.locale_id, self.th.id)
        self.assertEqual(collection_th.tradition.locale_id, self.th.id)


class CatalogPageFormLocaleFilterTests(WagtailPageTestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_catalog_reference")
        cls.en = Locale.get_default()
        cls.th = Locale.objects.get(language_code="th")
        cls.catalog = CatalogIndexPage(title="Catalog", slug="catalog-locale-test")
        Site.objects.get(is_default_site=True).root_page.add_child(instance=cls.catalog)
        cls.collection = CollectionPage(
            title="Tipitaka",
            code="tipitaka-locale-test",
            locale=cls.th,
        )
        cls.catalog.add_child(instance=cls.collection)

    def test_edition_form_filters_content_languages_by_page_locale(self):
        edition = EditionPage(title="Edition", code="ed-locale-test", locale=self.th)
        form_class = EditionPage.get_edit_handler().get_form_class()
        form = form_class(instance=edition, parent_page=self.collection)
        locales = set(
            form.fields["content_languages"].queryset.values_list(
                "locale__language_code", flat=True
            )
        )
        self.assertEqual(locales, {"th"})
        self.assertGreater(form.fields["content_languages"].queryset.count(), 0)

    def test_edition_form_uses_parent_locale_when_instance_has_none(self):
        edition = EditionPage(title="Edition", code="ed-parent-locale")
        form_class = EditionPage.get_edit_handler().get_form_class()
        form = form_class(instance=edition, parent_page=self.collection)
        locales = set(
            form.fields["content_scripts"].queryset.values_list(
                "locale__language_code", flat=True
            )
        )
        self.assertEqual(locales, {"th"})

    def test_collection_form_filters_classification_by_page_locale(self):
        form_class = CollectionPage.get_edit_handler().get_form_class()
        form = form_class(instance=self.collection)
        locales = set(
            form.fields["classification"].queryset.values_list(
                "locale__language_code", flat=True
            )
        )
        self.assertEqual(locales, {"th"})


class LocaleNavbarTests(TestCase):
    def test_seed_creates_locale_navbars(self):
        call_command("seed_sacred_translations", force=True)
        call_command("seed_locale_navbars", force=True)
        from coderedcms.models.snippet_models import Navbar

        from website.navbars import resolve_locale_navbar

        self.assertEqual(Navbar.objects.filter(name="main-en").count(), 1)
        self.assertEqual(Navbar.objects.filter(name="main-th").count(), 1)
        self.assertEqual(Navbar.objects.filter(name="main-zh").count(), 0)
        self.assertEqual(resolve_locale_navbar("th").name, "main-th")
        self.assertFalse(Navbar.objects.filter(name="main").exists())

    def test_fallback_to_main_en_for_unknown_locale(self):
        call_command("seed_sacred_translations", force=True)
        call_command("seed_locale_navbars", force=True)
        from website.navbars import resolve_locale_navbar

        self.assertEqual(resolve_locale_navbar("xx").name, "main-en")

    def test_seed_appends_patidina_without_force(self):
        call_command("seed_sacred_translations", force=True)
        call_command("seed_locale_navbars", force=True)
        from coderedcms.models.snippet_models import Navbar
        from patidina.models import PatidinaPage

        from website.navbars import _navbar_links_page

        call_command("seed_patidina_page")
        # Simulate a customized navbar that is not the default Home set.
        en = Navbar.objects.get(name="main-en")
        en.menu_items = [
            (
                "page_link",
                {
                    "settings": {
                        "custom_template": "",
                        "custom_css_class": "",
                        "custom_id": "",
                    },
                    "display_text": "Buddhist scriptures",
                    "image": None,
                    "page": Site.objects.get(is_default_site=True).root_page,
                    "sub_links": [],
                    "show_child_links": False,
                },
            )
        ]
        en.save()

        call_command("seed_locale_navbars")
        en.refresh_from_db()
        labels = [
            block.value["display_text"]
            for block in en.menu_items
            if block.block_type == "page_link"
        ]
        self.assertIn("Buddhist scriptures", labels)
        self.assertIn("Patidina", labels)
        patidina = PatidinaPage.objects.filter(locale__language_code="en").first()
        self.assertTrue(_navbar_links_page(en, patidina))


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
        self.assertContains(response, "home-section--zigzag")
        self.assertContains(response, "home-zigzag-siglum")
        self.assertContains(response, "Classification")
        self.assertContains(response, "Tipiṭaka")

    def test_goal_page_renders(self):
        home = Site.objects.get(is_default_site=True).root_page
        goal = home.get_children().get(slug="goal-repository")
        response = self.client.get(goal.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "goal-detail")
        self.assertContains(response, "Tipiṭaka Repository")
