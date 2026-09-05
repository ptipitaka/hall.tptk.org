"""Tests for the Digital archive Wagtail admin (ScanFolio round)."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from wagtail.models import Locale, Site

from archive.admin_scanfolios import (
    FILTER_SESSION_KEY,
    ScanFolioFilterSet,
    ScanFolioViewSet,
    book_choices,
    collection_choices,
    edition_choices,
)
from archive.models import ScanFolio, generate_scan_folio_rows
from archive.wagtail_hooks import DigitalArchiveGroup
from website.models import CatalogIndexPage, CollectionPage, EditionPage, VolumePage

User = get_user_model()


class DigitalArchiveAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.en = Locale.get_default()
        cls.th, _ = Locale.objects.get_or_create(language_code="th")
        root = Site.objects.get(is_default_site=True).root_page
        cls.catalog = CatalogIndexPage(title="Cat", slug="da-cat")
        root.add_child(instance=cls.catalog)

        cls.collection = CollectionPage(
            title="Chaṭṭha Saṅgīti Piṭaka (Myanmar DORA)",
            code="ch-da",
            slug="ch-da",
        )
        cls.catalog.add_child(instance=cls.collection)
        cls.edition = EditionPage(
            title="Chaṭṭha Saṅgīti Piṭaka (Roman)",
            code="pali2552ro-da",
            slug="pali2552ro-da",
            edition_role=EditionPage.Role.SOURCE,
        )
        cls.collection.add_child(instance=cls.edition)
        cls.edition.save_revision().publish()
        cls.volume = VolumePage(
            title="Pārājikapāḷi",
            code="vol-01",
            slug="vol-01-da",
            volume_index=1,
            scan_folio_count=5,
        )
        cls.edition.add_child(instance=cls.volume)
        cls.volume.save_revision().publish()
        generate_scan_folio_rows(cls.volume, 5)
        ScanFolio.objects.filter(volume=cls.volume, sequence=1).update(
            status=ScanFolio.Status.PRESENT, page_no="1"
        )
        ScanFolio.objects.filter(volume=cls.volume, sequence=2).update(
            status=ScanFolio.Status.MISSING, page_no="2"
        )
        ScanFolio.objects.filter(volume=cls.volume, sequence=5).update(page_no="5")

        cls.volume_b = VolumePage(
            title="Pācittiyapāḷi",
            code="vol-02",
            slug="vol-02-da",
            volume_index=2,
            scan_folio_count=3,
        )
        cls.edition.add_child(instance=cls.volume_b)
        cls.volume_b.save_revision().publish()
        generate_scan_folio_rows(cls.volume_b, 3)

        cls.other_collection = CollectionPage(
            title="Other collection",
            code="other-da",
            slug="other-da",
        )
        cls.catalog.add_child(instance=cls.other_collection)
        cls.other_edition = EditionPage(
            title="Other edition",
            code="other-ed-da",
            slug="other-ed-da",
            edition_role=EditionPage.Role.SOURCE,
        )
        cls.other_collection.add_child(instance=cls.other_edition)
        cls.other_edition.save_revision().publish()
        cls.other_volume = VolumePage(
            title="Other book",
            code="vol-01",
            slug="vol-01-other-da",
            volume_index=1,
            scan_folio_count=2,
        )
        cls.other_edition.add_child(instance=cls.other_volume)
        cls.other_volume.save_revision().publish()
        generate_scan_folio_rows(cls.other_volume, 2)

        cls.staff = User.objects.create_superuser(
            username="daadmin", email="da@example.org", password="pw"
        )
        cls.list_url = reverse("wagtailsnippets_archive_scanfolio:list")

    def test_group_registered_with_scanfolio_viewset(self):
        self.assertIn(ScanFolioViewSet, DigitalArchiveGroup.items)
        self.assertEqual(ScanFolioViewSet.model, ScanFolio)
        self.assertTrue(ScanFolioViewSet.inspect_view_enabled)

    def test_cascade_choices_follow_parent(self):
        collections = dict(collection_choices())
        self.assertEqual(
            collections[self.collection.pk],
            "Chaṭṭha Saṅgīti Piṭaka (Myanmar DORA)",
        )
        self.assertEqual(edition_choices(), [])
        editions = dict(edition_choices(self.collection.pk))
        self.assertEqual(
            editions[self.edition.pk], "Chaṭṭha Saṅgīti Piṭaka (Roman)"
        )
        self.assertNotIn(self.other_edition.pk, editions)
        self.assertEqual(book_choices(), [])
        books = dict(book_choices(self.edition.pk))
        self.assertEqual(books[self.volume.pk], "Pārājikapāḷi")
        self.assertEqual(books[self.volume_b.pk], "Pācittiyapāḷi")
        self.assertNotIn(self.other_volume.pk, books)

    def test_filterset_narrows_by_collection_edition_book(self):
        qs = ScanFolio.objects.all()
        by_collection = ScanFolioFilterSet(
            data={"collection": str(self.collection.pk)}, queryset=qs
        ).qs
        self.assertEqual(by_collection.count(), 8)
        by_book = ScanFolioFilterSet(
            data={"volume": str(self.volume.pk)}, queryset=qs
        ).qs
        self.assertEqual(by_book.count(), 5)
        self.assertEqual(
            set(by_book.values_list("volume_id", flat=True)), {self.volume.pk}
        )
        other = ScanFolioFilterSet(
            data={"volume": str(self.other_volume.pk)}, queryset=qs
        ).qs
        self.assertEqual(other.count(), 2)

    def test_filterset_jumps_to_page_no_or_sequence(self):
        qs = ScanFolio.objects.filter(volume=self.volume)
        by_label = ScanFolioFilterSet(data={"folio_page": "5"}, queryset=qs).qs
        self.assertEqual(list(by_label.values_list("sequence", flat=True)), [5])
        by_sequence = ScanFolioFilterSet(data={"folio_page": "3"}, queryset=qs).qs
        self.assertEqual(list(by_sequence.values_list("sequence", flat=True)), [3])
        missing = ScanFolioFilterSet(data={"folio_page": "999"}, queryset=qs).qs
        self.assertEqual(missing.count(), 0)

    def test_filterset_form_cascade_choices(self):
        qs = ScanFolio.objects.all()
        fs = ScanFolioFilterSet(
            data={"collection": str(self.collection.pk)}, queryset=qs
        )
        edition_ids = {
            str(value) for value, _label in fs.form.fields["edition"].choices if value
        }
        self.assertIn(str(self.edition.pk), edition_ids)
        self.assertNotIn(str(self.other_edition.pk), edition_ids)
        blank_labels = [
            label for value, label in fs.form.fields["edition"].choices if not value
        ]
        self.assertEqual(blank_labels, ["Select edition"])
        self.assertTrue(fs.form.fields["volume"].widget.attrs.get("disabled"))

        fs_ed = ScanFolioFilterSet(
            data={
                "collection": str(self.collection.pk),
                "edition": str(self.edition.pk),
            },
            queryset=qs,
        )
        book_ids = {
            str(value) for value, _label in fs_ed.form.fields["volume"].choices if value
        }
        self.assertIn(str(self.volume.pk), book_ids)
        self.assertIn(str(self.volume_b.pk), book_ids)
        self.assertNotIn(str(self.other_volume.pk), book_ids)
        self.assertFalse(fs_ed.form.fields["volume"].widget.attrs.get("disabled"))

    def test_admin_index_waits_for_book_before_listing(self):
        self.client.force_login(self.staff)
        inspect_url = reverse(
            "wagtailsnippets_archive_scanfolio:inspect",
            args=[ScanFolio.objects.get(volume=self.volume, sequence=1).pk],
        )
        empty = self.client.get(self.list_url)
        self.assertEqual(empty.status_code, 200)
        self.assertContains(empty, "Select a collection, then an edition, then a book.")
        self.assertContains(empty, "Select a collection first.")
        self.assertContains(empty, 'disabled')
        self.assertNotContains(empty, inspect_url)
        self.assertNotContains(empty, "matches")

        by_collection = self.client.get(
            self.list_url, {"collection": str(self.collection.pk)}
        )
        self.assertEqual(by_collection.status_code, 200)
        self.assertContains(by_collection, "Chaṭṭha Saṅgīti Piṭaka (Roman)")
        self.assertNotContains(by_collection, "Other edition")
        self.assertNotContains(by_collection, inspect_url)

        by_edition = self.client.get(
            self.list_url,
            {
                "collection": str(self.collection.pk),
                "edition": str(self.edition.pk),
            },
        )
        self.assertEqual(by_edition.status_code, 200)
        self.assertContains(by_edition, "Pārājikapāḷi")
        self.assertContains(by_edition, "Pācittiyapāḷi")
        self.assertNotContains(by_edition, "Other book")
        self.assertNotContains(by_edition, inspect_url)

    def test_filterset_meta_fields(self):
        self.assertEqual(
            ScanFolioFilterSet.Meta.fields,
            ["collection", "edition", "volume", "folio_page", "page_order"],
        )

    def test_admin_index_renders_filters_and_book_title(self):
        self.client.force_login(self.staff)
        resp = self.client.get(self.list_url, {"volume": str(self.volume.pk)})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Pārājikapāḷi")
        self.assertContains(resp, "Collection")
        self.assertContains(resp, "Edition")
        self.assertContains(resp, "Book")
        self.assertContains(resp, "Sort by page no.")
        self.assertContains(resp, "Show folios")
        self.assertContains(resp, 'id="scanfolio-filter-form"')
        inspect_url = reverse(
            "wagtailsnippets_archive_scanfolio:inspect",
            args=[ScanFolio.objects.get(volume=self.volume, sequence=1).pk],
        )
        self.assertContains(resp, inspect_url)

    def test_admin_index_sorts_by_page_order(self):
        self.client.force_login(self.staff)
        asc = self.client.get(
            self.list_url,
            {"volume": str(self.volume.pk), "page_order": "asc"},
        )
        desc = self.client.get(
            self.list_url,
            {"volume": str(self.volume.pk), "page_order": "desc"},
        )
        self.assertEqual(asc.status_code, 200)
        self.assertEqual(desc.status_code, 200)
        f1 = ScanFolio.objects.get(volume=self.volume, sequence=1)
        f5 = ScanFolio.objects.get(volume=self.volume, sequence=5)
        u1 = reverse(
            "wagtailsnippets_archive_scanfolio:inspect", args=[f1.pk]
        ).encode()
        u5 = reverse(
            "wagtailsnippets_archive_scanfolio:inspect", args=[f5.pk]
        ).encode()
        self.assertLess(asc.content.find(u1), asc.content.find(u5))
        self.assertLess(desc.content.find(u5), desc.content.find(u1))

    def test_admin_index_restores_filters_from_session(self):
        self.client.force_login(self.staff)
        session = self.client.session
        session[FILTER_SESSION_KEY] = {
            "collection": str(self.collection.pk),
            "edition": str(self.edition.pk),
            "volume": str(self.volume.pk),
            "page_order": "desc",
            "folio_page": "5",
        }
        session.save()
        resp = self.client.get(self.list_url)
        self.assertEqual(resp.status_code, 302)
        location = resp["Location"]
        self.assertIn(f"volume={self.volume.pk}", location)
        self.assertIn("page_order=desc", location)
        self.assertIn("folio_page=5", location)
        followed = self.client.get(location)
        self.assertEqual(followed.status_code, 200)
        self.assertContains(followed, "Pārājikapāḷi")
        folio_five = ScanFolio.objects.get(volume=self.volume, sequence=5)
        folio_one = ScanFolio.objects.get(volume=self.volume, sequence=1)
        self.assertContains(
            followed,
            reverse(
                "wagtailsnippets_archive_scanfolio:inspect", args=[folio_five.pk]
            ),
        )
        self.assertNotContains(
            followed,
            reverse(
                "wagtailsnippets_archive_scanfolio:inspect", args=[folio_one.pk]
            ),
        )

    def test_admin_index_reset_clears_session(self):
        self.client.force_login(self.staff)
        session = self.client.session
        session[FILTER_SESSION_KEY] = {"volume": str(self.volume.pk)}
        session.save()
        resp = self.client.get(self.list_url, {"reset": "1"})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], self.list_url)
        self.assertNotIn(FILTER_SESSION_KEY, self.client.session)

    def test_inspect_present_shows_scan_image(self):
        self.client.force_login(self.staff)
        folio = ScanFolio.objects.get(volume=self.volume, sequence=1)
        url = reverse(
            "wagtailsnippets_archive_scanfolio:inspect", args=[folio.pk]
        )
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, folio.image_url)
        self.assertContains(resp, "Open scan image in a new tab")
        self.assertNotContains(resp, "No scan image is available")

    def test_inspect_missing_explains_no_scan(self):
        self.client.force_login(self.staff)
        folio = ScanFolio.objects.get(volume=self.volume, sequence=2)
        url = reverse(
            "wagtailsnippets_archive_scanfolio:inspect", args=[folio.pk]
        )
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "No scan image is available for this folio.")
        self.assertNotContains(resp, folio.image_url)

    def test_admin_index_wires_cascade_option_urls(self):
        self.client.force_login(self.staff)
        resp = self.client.get(self.list_url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'id="scanfolio-filter-form"')
        self.assertContains(resp, 'data-editions-url="')
        self.assertContains(resp, 'data-books-url="')
        self.assertContains(
            resp, reverse("wagtailsnippets_archive_scanfolio:edition_options")
        )
        self.assertContains(
            resp, reverse("wagtailsnippets_archive_scanfolio:book_options")
        )
        self.assertContains(resp, "DOMContentLoaded")

    def test_option_endpoints_cascade(self):
        self.client.force_login(self.staff)
        editions = self.client.get(
            reverse("wagtailsnippets_archive_scanfolio:edition_options"),
            {"collection": str(self.collection.pk)},
        )
        self.assertEqual(editions.status_code, 200)
        edition_ids = {item["id"] for item in editions.json()["choices"]}
        self.assertIn(self.edition.pk, edition_ids)
        self.assertNotIn(self.other_edition.pk, edition_ids)

        books = self.client.get(
            reverse("wagtailsnippets_archive_scanfolio:book_options"),
            {"edition": str(self.edition.pk)},
        )
        self.assertEqual(books.status_code, 200)
        book_ids = {item["id"] for item in books.json()["choices"]}
        self.assertIn(self.volume.pk, book_ids)
        self.assertNotIn(self.other_volume.pk, book_ids)

    def test_option_endpoints_require_login(self):
        url = reverse("wagtailsnippets_archive_scanfolio:edition_options")
        resp = self.client.get(url, {"collection": str(self.collection.pk)})
        self.assertIn(resp.status_code, (302, 403))

    def test_admin_requires_login(self):
        resp = self.client.get(self.list_url)
        self.assertIn(resp.status_code, (302, 403))
