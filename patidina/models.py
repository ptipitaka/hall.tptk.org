from datetime import date

from coderedcms.models import CoderedWebPage
from django.db import models
from django.shortcuts import render
from django.utils.translation import get_language
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from wagtail.admin.panels import FieldPanel, FieldRowPanel, InlinePanel, MultiFieldPanel
from wagtail.contrib.routable_page.models import RoutablePageMixin, path
from wagtail.models import Orderable, Page

from patidina.constants import DAY_CHOICES, MONTH_CHOICES, MOON_PHASE_CHOICES
from patidina.services.i18n_display import lunar_date_label
from website.models import (
    SCROLL_BACKGROUND_PANEL,
    ScrollBackgroundImageBase,
    ScrollBackgroundPageMixin,
)


def _detail_localized_name(detail) -> str:
    lang = (get_language() or "en").split("-")[0]
    if lang != "th" and getattr(detail, "name_en", ""):
        return detail.name_en
    return detail.name


class LunarImportantDay(ClusterableModel):
    """Important Buddhist / commemorative days keyed by lunar date fields."""

    moon_phase = models.CharField(
        "ข้างขึ้น-ข้างแรม", max_length=10, choices=MOON_PHASE_CHOICES, default="01"
    )
    day = models.CharField("ค่ำ", max_length=2, choices=DAY_CHOICES)
    month = models.CharField("เดือน", max_length=2, choices=MONTH_CHOICES)

    moon_phase_adhikamasa = models.CharField(
        "ข้างขึ้น-ข้างแรม (อธิกมาส)",
        max_length=10,
        choices=MOON_PHASE_CHOICES,
        default="01",
    )
    day_adhikamasa = models.CharField(
        "ค่ำ (อธิกมาส)", max_length=2, choices=DAY_CHOICES
    )
    month_adhikamasa = models.CharField(
        "เดือน (อธิกมาส)", max_length=2, choices=MONTH_CHOICES
    )

    panels = [
        MultiFieldPanel(
            [
                FieldRowPanel(
                    [
                        FieldPanel("moon_phase"),
                        FieldPanel("day"),
                        FieldPanel("month"),
                    ]
                ),
            ],
            heading="Lunar Date",
        ),
        MultiFieldPanel(
            [
                FieldRowPanel(
                    [
                        FieldPanel("moon_phase_adhikamasa"),
                        FieldPanel("day_adhikamasa"),
                        FieldPanel("month_adhikamasa"),
                    ]
                ),
            ],
            heading="Lunar Date in Adhikamasa",
        ),
        InlinePanel("details", label="รายละเอียด"),
    ]

    class Meta:
        verbose_name = "วันสำคัญในปฏิทินจันทรคติ"
        verbose_name_plural = "วันสำคัญในปฏิทินจันทรคติ"
        ordering = ["month", "moon_phase", "day"]

    @property
    def lunar_date_label(self) -> str:
        phase_key = "ขึ้น" if self.moon_phase == "01" else "แรม"
        return lunar_date_label(
            phase_key,
            self.get_day_display().strip(),
            self.get_month_display().strip(),
        )

    @property
    def lunar_date_adhikamasa_label(self) -> str:
        phase_key = "ขึ้น" if self.moon_phase_adhikamasa == "01" else "แรม"
        return lunar_date_label(
            phase_key,
            self.get_day_adhikamasa_display().strip(),
            self.get_month_adhikamasa_display().strip(),
        )

    def __str__(self):
        names = ", ".join(_detail_localized_name(d) for d in self.details.all())
        return f"{self.lunar_date_label} - {names}"


class LunarImportantDayDetail(Orderable):
    parent = ParentalKey(
        LunarImportantDay,
        related_name="details",
        verbose_name="รายละเอียด",
    )
    name = models.CharField("ชื่อ (ไทย)", max_length=255)
    name_en = models.CharField("Name (English)", max_length=255, blank=True, default="")
    is_buddhist_commemorative = models.BooleanField(
        default=True, verbose_name="วันสำคัญทางพุทธศาสนา"
    )
    article_page = models.ForeignKey(
        Page,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="บทความ",
    )

    panels = [
        FieldPanel("name"),
        FieldPanel("name_en"),
        FieldPanel("is_buddhist_commemorative"),
        FieldPanel("article_page"),
    ]

    @property
    def localized_name(self) -> str:
        return _detail_localized_name(self)

    def __str__(self):
        return self.localized_name


class SolarImportantDay(ClusterableModel):
    """Important days keyed by Gregorian day/month."""

    DAY_CHOICES = [(i, i) for i in range(1, 32)]
    MONTH_CHOICES = [
        (1, "มกราคม"),
        (2, "กุมภาพันธ์"),
        (3, "มีนาคม"),
        (4, "เมษายน"),
        (5, "พฤษภาคม"),
        (6, "มิถุนายน"),
        (7, "กรกฎาคม"),
        (8, "สิงหาคม"),
        (9, "กันยายน"),
        (10, "ตุลาคม"),
        (11, "พฤศจิกายน"),
        (12, "ธันวาคม"),
    ]

    day = models.IntegerField("วัน", choices=DAY_CHOICES)
    month = models.IntegerField("เดือน", choices=MONTH_CHOICES)

    panels = [
        MultiFieldPanel(
            [
                FieldRowPanel(
                    [
                        FieldPanel("day"),
                        FieldPanel("month"),
                    ]
                ),
            ],
            heading="Solar Calendar Date",
        ),
        InlinePanel("details", label="รายละเอียด"),
    ]

    class Meta:
        verbose_name = "วันสำคัญในปฏิทินสุริยคติ"
        verbose_name_plural = "วันสำคัญในปฏิทินสุริยคติ"
        ordering = ["month", "day"]

    def __str__(self):
        names = ", ".join(_detail_localized_name(d) for d in self.details.all())
        return f"{self.day}/{self.month} - {names}"


class SolarImportantDayDetail(Orderable):
    parent = ParentalKey(
        SolarImportantDay,
        related_name="details",
        verbose_name="รายละเอียด",
    )
    name = models.CharField("ชื่อ (ไทย)", max_length=255)
    name_en = models.CharField("Name (English)", max_length=255, blank=True, default="")
    article_page = models.ForeignKey(
        Page,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="บทความ",
    )

    panels = [
        FieldPanel("name"),
        FieldPanel("name_en"),
        FieldPanel("article_page"),
    ]

    @property
    def localized_name(self) -> str:
        return _detail_localized_name(self)

    def __str__(self):
        return self.localized_name


class PatidinaPageScrollBackground(ScrollBackgroundImageBase):
    page = ParentalKey(
        "patidina.PatidinaPage",
        on_delete=models.CASCADE,
        related_name="scroll_backgrounds",
    )


class PatidinaPage(RoutablePageMixin, ScrollBackgroundPageMixin, CoderedWebPage):
    """Wagtail page hosting the Thai Buddhist calendar widget and sub-routes."""

    class Meta:
        verbose_name = "Patidina calendar"

    template = "patidina/pages/patidina_page.html"
    max_count = 1
    parent_page_types = ["website.WebPage", "wagtailcore.Page"]
    subpage_types = []

    content_panels = CoderedWebPage.content_panels + [SCROLL_BACKGROUND_PANEL]

    def _subpage_url(self, name: str, args=()) -> str:
        """Absolute URL for a RoutablePageMixin route (not relative to current path)."""
        return self.url + self.reverse_subpage(name, args=args)

    def _calendar_nav_urls(self, year: int, month: int) -> dict:
        from patidina.services.calendar import month_calendar

        cal = month_calendar(year, month)
        cal["prev_calendar_url"] = self._subpage_url(
            "calendar", args=(cal["prev_year"], cal["prev_month"])
        )
        cal["next_calendar_url"] = self._subpage_url(
            "calendar", args=(cal["next_year"], cal["next_month"])
        )
        cal["uposatha_url"] = self._subpage_url("uposatha_year", args=(year,))
        cal["patidina_home_url"] = self.url
        return cal

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        today = date.today()
        context["ini_solar_date"] = today
        context.update(self._calendar_nav_urls(today.year, today.month))
        return context

    @path("calendar/<int:y>/<int:m>/")
    def calendar(self, request, y, m):
        context = self.get_context(request)
        context["ini_solar_date"] = date(y, m, 1)
        context.update(self._calendar_nav_urls(y, m))
        return render(request, "patidina/pages/calendar_page.html", context)

    @path("uposatha/")
    def uposatha(self, request):
        return self.uposatha_year(request, date.today().year)

    @path("uposatha/<int:y>/")
    def uposatha_year(self, request, y):
        from patidina.services.calendar import uposatha_year as build_uposatha_year

        context = self.get_context(request)
        context["year"] = y
        context["prev_year"] = y - 1
        context["next_year"] = y + 1
        context["be_year"] = y + 543
        context["ini_solar_date"] = date(y, 1, 1)
        context.update(build_uposatha_year(y))
        context["patidina_home_url"] = self.url
        context["prev_uposatha_url"] = self._subpage_url(
            "uposatha_year", args=(y - 1,)
        )
        context["next_uposatha_url"] = self._subpage_url(
            "uposatha_year", args=(y + 1,)
        )
        return render(request, "patidina/pages/uposatha_page.html", context)
