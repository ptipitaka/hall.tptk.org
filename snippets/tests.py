from django.core.exceptions import ValidationError
from django.test import TestCase
from wagtail.models import Locale

from snippets.models import (
    CanonicalSection,
    Classification,
    ContentLanguage,
    ContentScript,
    Country,
    SegmentKind,
    Tradition,
)
from snippets.seed import create_translated_rows, seed_translation_key


class ReferenceSnippetModelTests(TestCase):
    def setUp(self):
        for code in ("en", "th"):
            Locale.objects.get_or_create(language_code=code)

    def _classification_en(self, siglum: str, slug: str, title: str) -> Classification:
        rows = create_translated_rows(
            Classification,
            translation_key=seed_translation_key("classification", slug),
            shared={"siglum": siglum, "slug": slug, "sort_order": 0},
            localized={
                "en": {"title": title, "description": ""},
                "th": {"title": title, "description": ""},
            },
        )
        return rows["en"]

    def test_classification_translations_share_translation_key(self):
        tp = self._classification_en("TP", "tipitaka", "Tipiṭaka")
        locales = Classification.objects.filter(translation_key=tp.translation_key)
        self.assertEqual(locales.count(), 2)

    def test_canonical_section_slug_defaults_from_code(self):
        en_locale = Locale.objects.get(language_code="en")
        section = CanonicalSection(
            locale=en_locale,
            code="sut",
            name="Sutta Piṭaka",
            kind=CanonicalSection.Kind.PITAKA,
        )
        section.save()
        self.assertEqual(section.slug, "sut")

    def test_canonical_section_rejects_self_parent(self):
        en_locale = Locale.objects.get(language_code="en")
        section = CanonicalSection.objects.create(
            locale=en_locale,
            code="sut",
            slug="sut",
            name="Sutta Piṭaka",
        )
        section.parent = section
        with self.assertRaises(ValidationError):
            section.full_clean()

    def test_canonical_section_parent_must_share_locale(self):
        en_locale = Locale.objects.get(language_code="en")
        th_locale = Locale.objects.get(language_code="th")
        parent = CanonicalSection.objects.create(
            locale=en_locale,
            code="sut",
            slug="sut",
            name="Sutta Piṭaka",
        )
        child = CanonicalSection(
            locale=th_locale,
            code="dn",
            slug="dn",
            name="ทีฆนิกาย",
            parent=parent,
        )
        with self.assertRaises(ValidationError):
            child.full_clean()

    def test_seed_reference_command(self):
        from django.core.management import call_command

        call_command("seed_catalog_reference")
        self.assertEqual(
            SegmentKind.objects.filter(locale__language_code="en").count(),
            14,
        )
        self.assertEqual(Classification.objects.filter(siglum="TP").count(), 2)
        self.assertEqual(
            Tradition.objects.filter(locale__language_code="en").count(),
            3,
        )
        theravada = Tradition.objects.get(
            locale__language_code="th",
            code="theravada",
        )
        self.assertEqual(theravada.name, "เถรวาท")
        self.assertEqual(
            Country.objects.filter(locale__language_code="en").count(),
            12,
        )
        thailand = Country.objects.get(locale__language_code="th", code="th")
        self.assertEqual(thailand.name, "ประเทศไทย")
        self.assertEqual(thailand.flag_static_path, "website/img/flags/th.svg")
        self.assertEqual(
            ContentLanguage.objects.filter(locale__language_code="en").count(),
            12,
        )
        self.assertEqual(
            ContentScript.objects.filter(locale__language_code="en").count(),
            13,
        )
        pali = ContentLanguage.objects.get(locale__language_code="en", code="pali")
        self.assertEqual(pali.sort_order, 0)
        self.assertEqual(
            CanonicalSection.objects.filter(locale__language_code="en").count(),
            8,
        )
        dn = CanonicalSection.objects.get(locale__language_code="th", code="dn")
        self.assertEqual(dn.kind, CanonicalSection.Kind.NIKAYA)
        self.assertEqual(dn.parent.code, "sut")
        self.assertEqual(dn.name, "ทีฆนิกาย")
