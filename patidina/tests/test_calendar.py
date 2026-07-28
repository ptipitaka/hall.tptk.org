"""Calendar / uposatha service tests and PatidinaPage smoke tests."""

from datetime import date, timedelta

from django.test import SimpleTestCase, TestCase
from wagtail.models import Page, Site

from patidina.models import PatidinaPage
from patidina.services.calendar import (
    adhikamasa,
    dhammayut_uposatha,
    lunar_date_for,
    mahanikaya_uposatha,
    month_calendar,
    uposatha_year,
)


class LunarDateTests(SimpleTestCase):
    def test_lunar_date_has_structured_fields(self):
        lunar = lunar_date_for(date(2024, 5, 22))
        self.assertIn(lunar.phase, ("ขึ้น", "แรม"))
        self.assertGreaterEqual(lunar.day, 1)
        self.assertLessEqual(lunar.day, 15)
        self.assertTrue(lunar.month_code)
        self.assertTrue(lunar.phase_code in ("01", "02"))


class AdhikamasaTests(SimpleTestCase):
    def test_known_adhikamasa_years(self):
        self.assertTrue(adhikamasa(2023))
        self.assertFalse(adhikamasa(2024))


class UposathaNikayaTests(SimpleTestCase):
    def test_find_date_where_nikayas_differ(self):
        differed = []
        for day_offset in range(0, 366):
            d = date(2024, 1, 1) + timedelta(days=day_offset)
            maha = bool(mahanikaya_uposatha(d))
            dham = bool(dhammayut_uposatha(d))
            if maha != dham:
                differed.append(d)
                if len(differed) >= 3:
                    break
        self.assertTrue(
            differed,
            "Expected at least one day in 2024 where Mahanikaya and Dhammayut differ",
        )

    def test_reference_dates_nikayas_differ(self):
        self.assertEqual(mahanikaya_uposatha(date(2024, 3, 9)), "🌑")
        self.assertEqual(dhammayut_uposatha(date(2024, 3, 9)), "")
        self.assertEqual(mahanikaya_uposatha(date(2024, 3, 10)), "")
        self.assertEqual(dhammayut_uposatha(date(2024, 3, 10)), "Pt")
        self.assertEqual(mahanikaya_uposatha(date(2024, 3, 17)), "🌓")
        self.assertEqual(dhammayut_uposatha(date(2024, 3, 18)), "P")

    def test_mahanikaya_markers_are_emoji_or_empty(self):
        marker = mahanikaya_uposatha(date(2024, 5, 22))
        self.assertIn(marker, ("", "🌓", "🌕", "🌗", "🌑"))

    def test_dhammayut_markers_are_pakdate_codes_or_empty(self):
        from patidina.services.calendar import DHAMMAYUT_CODES

        marker = dhammayut_uposatha(date(2024, 5, 22))
        self.assertIn(marker, ("", *DHAMMAYUT_CODES))


class MonthCalendarTests(TestCase):
    def test_month_calendar_structure(self):
        cal = month_calendar(2024, 5)
        self.assertEqual(cal["first_day_of_month"], date(2024, 5, 1))
        self.assertEqual(cal["last_day_of_month"], date(2024, 5, 31))
        self.assertEqual(len(cal["days"]), 31)
        self.assertEqual(len(cal["days_with_moon_phase_changes"]), 31)
        self.assertEqual(len(cal["days_with_important_days"]), 31)


class UposathaYearTests(TestCase):
    def test_uposatha_year_has_twelve_months(self):
        data = uposatha_year(2024)
        self.assertEqual(len(data["monthly_uposatha"]), 12)


class PatidinaPageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        root = Page.get_first_root_node()
        site = Site.objects.filter(is_default_site=True).first()
        if site is None:
            home = root.add_child(
                instance=Page(title="Home", slug="home", draft_title="Home")
            )
            Site.objects.create(
                hostname="localhost",
                root_page=home,
                is_default_site=True,
            )
            parent = home
        else:
            parent = site.root_page

        page = PatidinaPage(title="Patidina", slug="patidina", draft_title="Patidina")
        parent.add_child(instance=page)
        page.save_revision().publish()
        cls.page = PatidinaPage.objects.get(pk=page.pk)

    def test_page_ok(self):
        response = self.client.get(self.page.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mahanikaya")
        self.assertContains(response, "Dhammayut")

    def test_calendar_route_ok(self):
        url = self.page.url + self.page.reverse_subpage(
            "calendar", args=(2024, 5)
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # Month pages keep the solar / moon / lunar header like the home widget.
        self.assertContains(response, "span-solar-date")
        self.assertContains(response, "span-lunar-date")
        self.assertContains(response, "resize-container")

    def test_calendar_nav_urls_are_absolute(self):
        """Prev/next must be absolute so they do not nest under /calendar/y/m/."""
        nav = self.page._calendar_nav_urls(2026, 8)
        self.assertTrue(nav["prev_calendar_url"].startswith(self.page.url))
        self.assertTrue(nav["next_calendar_url"].startswith(self.page.url))
        self.assertEqual(
            nav["prev_calendar_url"],
            self.page.url + self.page.reverse_subpage("calendar", args=(2026, 7)),
        )
        self.assertEqual(
            nav["next_calendar_url"],
            self.page.url + self.page.reverse_subpage("calendar", args=(2026, 9)),
        )
        self.assertNotIn("/calendar/2026/8/calendar/", nav["next_calendar_url"])

    def test_calendar_next_prev_chain_ok(self):
        url = self.page.url + self.page.reverse_subpage(
            "calendar", args=(2026, 8)
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        next_url = response.context["next_calendar_url"]
        prev_url = response.context["prev_calendar_url"]
        self.assertEqual(self.client.get(next_url).status_code, 200)
        self.assertEqual(self.client.get(prev_url).status_code, 200)

    def test_uposatha_route_ok(self):
        url = self.page.url + self.page.reverse_subpage(
            "uposatha_year", args=(2024,)
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_scroll_background_renders_when_configured(self):
        from wagtail.images import get_image_model
        from wagtail.images.tests.utils import get_test_image_file

        from patidina.models import PatidinaPageScrollBackground

        image = get_image_model().objects.create(
            title="patidina-bg",
            file=get_test_image_file(),
        )
        PatidinaPageScrollBackground.objects.create(
            page=self.page,
            image=image,
            sort_order=0,
        )
        response = self.client.get(self.page.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="scroll-bg"')
        self.assertContains(response, "has-scroll-bg")
