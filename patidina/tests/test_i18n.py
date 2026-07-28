"""Patidina multilingual smoke tests."""

from django.core.management import call_command
from django.test import TestCase
from django.utils import translation
from wagtail.models import Locale

from patidina.important_day_names import english_name_for
from patidina.models import (
    LunarImportantDay,
    LunarImportantDayDetail,
    PatidinaPage,
)
from patidina.services.i18n_display import (
    dhammayut_display_code,
    dhammayut_legend_markers,
)


class DhammayutMarkerLocaleTests(TestCase):
    def test_display_codes_follow_active_language(self):
        with translation.override("en"):
            self.assertEqual(dhammayut_display_code("P"), "P")
            self.assertEqual(dhammayut_display_code("Pt"), "Pt")
            self.assertEqual(dhammayut_display_code("Pk"), "Pk")
            self.assertEqual(dhammayut_legend_markers(), "P Pt Pk")
        with translation.override("th"):
            self.assertEqual(dhammayut_display_code("P"), "ป")
            self.assertEqual(dhammayut_display_code("Pt"), "ปถ")
            self.assertEqual(dhammayut_display_code("Pk"), "ปข")
            self.assertEqual(dhammayut_legend_markers(), "ป ปถ ปข")


class ImportantDayNameTests(TestCase):
    def test_purimassa_uses_pali_english(self):
        en = english_name_for("วันเข้าพรรษาแรก (ปุริมพรรษา)")
        self.assertIn("purimikā", en)
        self.assertIn("Rains Retreat", en)

    def test_localized_name_switches_with_language(self):
        day = LunarImportantDay.objects.create(
            moon_phase="01",
            day="15",
            month="03",
            moon_phase_adhikamasa="01",
            day_adhikamasa="15",
            month_adhikamasa="04",
        )
        detail = LunarImportantDayDetail.objects.create(
            parent=day,
            name="วันมาฆบูชา",
            name_en=english_name_for("วันมาฆบูชา"),
        )
        with translation.override("th"):
            self.assertEqual(detail.localized_name, "วันมาฆบูชา")
        with translation.override("en"):
            self.assertIn("Māgha", detail.localized_name)


class PatidinaLocalePageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Locale.objects.get_or_create(language_code="en")
        Locale.objects.get_or_create(language_code="th")
        # Ensure Thai home exists so copy_for_translation has a parent.
        from wagtail.models import Site

        home_en = Site.objects.get(is_default_site=True).root_page
        th = Locale.objects.get(language_code="th")
        if not home_en.get_translations(inclusive=False).filter(locale=th).exists():
            home_en.copy_for_translation(th, copy_parents=False, alias=False)

        call_command("seed_patidina_page")
        cls.page_en = PatidinaPage.objects.filter(locale__language_code="en").first()
        cls.page_th = cls.page_en.get_translation(th)

    def test_english_page_shows_english_chrome(self):
        response = self.client.get(self.page_en.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mahanikaya")
        self.assertContains(response, "Dhammayut")
        self.assertContains(response, "Uposatha days for the year")
        self.assertContains(response, "hall-lang-switcher")

    def test_thai_page_shows_thai_chrome(self):
        response = self.client.get(self.page_th.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "มหานิกาย")
        self.assertContains(response, "ธรรมยุติ")
        self.assertContains(response, "วันพระทั้งปี")

    def test_language_switcher_has_thai_alternate(self):
        response = self.client.get(self.page_en.url)
        self.assertContains(response, f'href="{self.page_th.url}"')

    def test_english_uposatha_uses_english_weekdays_and_clear_legend(self):
        url = self.page_en.url + self.page_en.reverse_subpage(
            "uposatha_year", args=(2026,)
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mahānikāya")
        self.assertContains(response, "Dhammayuttika")
        self.assertContains(response, "P Pt Pk")
        self.assertContains(response, "meditating-buddha.png")
        self.assertNotContains(response, "ป ปถ ปข")
        self.assertNotContains(response, "จ.1")
        self.assertNotContains(response, "อ.2")
        # English weekday abbreviations appear; Thai weekday dots should not.
        self.assertContains(response, "Sa")
        self.assertNotContains(response, "ส.")

    def test_thai_uposatha_uses_thai_weekdays(self):
        url = self.page_th.url + self.page_th.reverse_subpage(
            "uposatha_year", args=(2026,)
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "มหานิกาย")
        self.assertContains(response, "ธรรมยุตติก")
        self.assertContains(response, "ป ปถ ปข")
        self.assertNotContains(response, "P Pt Pk")
        self.assertContains(response, "ส.")
        # All visible year/month/day numerals use Thai digits.
        self.assertContains(response, "๒๕๖๙")
        self.assertContains(response, "๒๕๖๘")  # prev BE year in nav
        self.assertContains(response, "๒๕๗๐")  # next BE year in nav
        self.assertContains(response, "<sup>๑</sup>")
        self.assertNotContains(response, "พ.ศ. 2569")

    def test_uposatha_print_hides_chrome(self):
        url = self.page_en.url + self.page_en.reverse_subpage(
            "uposatha_year", args=(2026,)
        )
        html = self.client.get(url).content.decode()
        self.assertIn("hall-lang-switcher d-print-none", html)
        self.assertIn("hall-navbar__utilities", html)
        self.assertIn('d-print-none', html)
        self.assertIn('class="mt-3 d-print-none"', html)
        self.assertIn("Back to Patidina", html)
