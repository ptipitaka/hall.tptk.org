from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import RequestFactory
from wagtail.models import Locale, Site
from wagtail.test.utils import WagtailPageTestCase

from archive.models import (
    ScanFolio,
    Segment,
    generate_scan_folio_rows,
    replace_scan_folio_rows,
    scan_folios_for,
    scan_owner_volume,
    set_declared_scan_folio_count,
)
from snippets.models import SegmentKind
from website.models import CatalogIndexPage, CollectionPage, EditionPage, VolumePage


class ScanFolioOwnerTests(WagtailPageTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.en = Locale.get_default()
        cls.th, _ = Locale.objects.get_or_create(language_code="th")
        root = Site.objects.get(is_default_site=True).root_page
        cls.catalog = CatalogIndexPage(title="Cat", slug="sf-cat")
        root.add_child(instance=cls.catalog)
        cls.collection = CollectionPage(title="CH", code="ch-sf", slug="ch-sf")
        cls.catalog.add_child(instance=cls.collection)
        cls.edition = EditionPage(
            title="RO",
            code="pali2552ro-sf",
            slug="pali2552ro-sf",
            edition_role=EditionPage.Role.SOURCE,
        )
        cls.collection.add_child(instance=cls.edition)
        cls.edition.save_revision().publish()
        cls.volume_en = VolumePage(
            title="Pārājikapāḷi",
            code="vol-01",
            slug="vol-01-sf",
            volume_index=1,
            scan_folio_count=3,
        )
        cls.edition.add_child(instance=cls.volume_en)
        cls.volume_en.save_revision().publish()

        catalog_th = cls.catalog.copy_for_translation(cls.th, copy_parents=True)
        catalog_th.save_revision().publish()
        collection_th = cls.collection.copy_for_translation(cls.th)
        collection_th.save_revision().publish()
        edition_th = cls.edition.copy_for_translation(cls.th)
        edition_th.save_revision().publish()
        cls.volume_th = cls.volume_en.copy_for_translation(cls.th)
        cls.volume_th.save_revision().publish()

    def test_owner_is_default_locale_volume(self):
        self.assertEqual(scan_owner_volume(self.volume_en).pk, self.volume_en.pk)
        self.assertEqual(scan_owner_volume(self.volume_th).pk, self.volume_en.pk)

    def test_generate_from_thai_volume_writes_english_rows_only(self):
        created, existing = generate_scan_folio_rows(self.volume_th, 3)
        self.assertEqual(created, 3)
        self.assertEqual(existing, 0)
        self.assertEqual(ScanFolio.objects.filter(volume=self.volume_en).count(), 3)
        self.assertEqual(ScanFolio.objects.filter(volume=self.volume_th).count(), 0)
        self.assertEqual(scan_folios_for(self.volume_th).count(), 3)

    def test_generate_command_uses_declared_count(self):
        call_command(
            "generate_scan_folios",
            "--collection",
            "ch-sf",
            "--edition",
            "pali2552ro-sf",
            "--volume",
            "1",
        )
        self.assertEqual(ScanFolio.objects.filter(volume=self.volume_en).count(), 3)
        self.assertEqual(ScanFolio.objects.filter(volume=self.volume_th).count(), 0)
        self.assertEqual(
            list(
                ScanFolio.objects.filter(volume=self.volume_en)
                .order_by("sequence")
                .values_list("status", flat=True)
            ),
            [ScanFolio.Status.PENDING] * 3,
        )

    def test_import_scan_folios_pages_writes_default_locale_only(self):
        thai_count = self.volume_th.scan_folio_count
        call_command(
            "import_scan_folios",
            "--collection",
            "ch-sf",
            "--edition",
            "pali2552ro-sf",
            "--volume",
            "1",
            "--pages",
            "2",
        )
        self.assertEqual(ScanFolio.objects.filter(volume=self.volume_en).count(), 2)
        self.assertEqual(ScanFolio.objects.filter(volume=self.volume_th).count(), 0)
        self.volume_en.refresh_from_db()
        self.volume_th.refresh_from_db()
        self.assertEqual(self.volume_en.scan_folio_count, 2)
        self.assertEqual(self.volume_th.scan_folio_count, thai_count)

    def test_import_count_only_sets_declared_count_without_rows(self):
        before = ScanFolio.objects.filter(volume=self.volume_en).count()
        thai_count = self.volume_th.scan_folio_count
        call_command(
            "import_scan_folios",
            "--collection",
            "ch-sf",
            "--edition",
            "pali2552ro-sf",
            "--volume",
            "1",
            "--pages",
            "9",
            "--count-only",
        )
        self.volume_en.refresh_from_db()
        self.volume_th.refresh_from_db()
        self.assertEqual(self.volume_en.scan_folio_count, 9)
        self.assertEqual(self.volume_th.scan_folio_count, thai_count)
        self.assertEqual(ScanFolio.objects.filter(volume=self.volume_en).count(), before)
        self.assertEqual(ScanFolio.objects.filter(volume=self.volume_th).count(), 0)

    def test_set_declared_scan_folio_count_skips_when_unchanged(self):
        self.volume_en.refresh_from_db()
        current = self.volume_en.scan_folio_count or 3
        thai_count = self.volume_th.scan_folio_count
        self.assertFalse(set_declared_scan_folio_count(self.volume_en, current))
        new_pages = current + 11
        self.assertTrue(set_declared_scan_folio_count(self.volume_th, new_pages))
        self.volume_en.refresh_from_db()
        self.volume_th.refresh_from_db()
        self.assertEqual(self.volume_en.scan_folio_count, new_pages)
        self.assertEqual(self.volume_th.scan_folio_count, thai_count)

    def test_thai_volume_page_counts_shared_folios(self):
        generate_scan_folio_rows(self.volume_en, 3)
        factory = RequestFactory()
        request = factory.get("/")
        context = self.volume_th.specific.get_context(request)
        self.assertEqual(context["folio_count"], 3)
        self.assertEqual(context["first_folio_sequence"], 1)

    def test_import_requires_collection_or_all(self):
        with self.assertRaises(CommandError):
            call_command("import_scan_folios")

    def test_import_all_rejects_collection(self):
        with self.assertRaises(CommandError):
            call_command(
                "import_scan_folios",
                "--all",
                "--collection",
                "ch-sf",
                "--edition",
                "pali2552ro-sf",
            )

    def test_import_all_count_only_uses_existing_rows(self):
        generate_scan_folio_rows(self.volume_en, 4)
        call_command("import_scan_folios", "--all", "--count-only")
        self.volume_en.refresh_from_db()
        self.assertEqual(self.volume_en.scan_folio_count, 4)

    def test_replace_drops_locale_copies_and_shares_owner_rows(self):
        generate_scan_folio_rows(self.volume_en, 3)
        ScanFolio.objects.create(
            volume=self.volume_th,
            sequence=1,
            status=ScanFolio.Status.PRESENT,
        )
        deleted, created = replace_scan_folio_rows(self.volume_th, 3)
        self.assertEqual(deleted, 4)
        self.assertEqual(created, 3)
        self.assertEqual(ScanFolio.objects.filter(volume=self.volume_en).count(), 3)
        self.assertEqual(ScanFolio.objects.filter(volume=self.volume_th).count(), 0)
        en_ids = list(
            scan_folios_for(self.volume_en)
            .order_by("sequence")
            .values_list("id", "sequence")
        )
        th_ids = list(
            scan_folios_for(self.volume_th)
            .order_by("sequence")
            .values_list("id", "sequence")
        )
        self.assertEqual(en_ids, th_ids)
        self.assertEqual(
            list(
                ScanFolio.objects.filter(volume=self.volume_en)
                .order_by("sequence")
                .values_list("status", flat=True)
            ),
            [ScanFolio.Status.PRESENT] * 3,
        )

    def test_replace_refuses_when_segment_attached(self):
        generate_scan_folio_rows(self.volume_en, 3)
        folio = scan_folios_for(self.volume_en).get(sequence=1)
        kind = SegmentKind.objects.create(
            locale=self.en,
            code="prose-sf",
            slug="prose-sf",
            name="Prose",
        )
        Segment.objects.create(
            volume=self.volume_en,
            order=1,
            kind=kind,
            folio=folio,
            content={"text": [{"script": "roman", "value": "x"}]},
            plain_roman="x",
        )
        with self.assertRaises(ValidationError):
            replace_scan_folio_rows(self.volume_en, 3)
        self.assertEqual(ScanFolio.objects.filter(volume=self.volume_en).count(), 3)

    def test_generate_replace_command_clears_thai_copies(self):
        generate_scan_folio_rows(self.volume_en, 3)
        ScanFolio.objects.create(
            volume=self.volume_th,
            sequence=99,
            status=ScanFolio.Status.PRESENT,
        )
        call_command(
            "generate_scan_folios",
            "--collection",
            "ch-sf",
            "--edition",
            "pali2552ro-sf",
            "--volume",
            "1",
            "--replace",
        )
        self.assertEqual(ScanFolio.objects.filter(volume=self.volume_th).count(), 0)
        self.assertEqual(scan_folios_for(self.volume_th).count(), 3)
        self.assertEqual(scan_folios_for(self.volume_en).count(), 3)
