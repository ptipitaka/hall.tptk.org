from datetime import date

from django.views.generic import TemplateView

from patidina.services.calendar import month_calendar, uposatha_year


class PatidinaWidgetView(TemplateView):
    template_name = "patidina/patidina_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = date.today()
        context["ini_solar_date"] = today
        context.update(month_calendar(today.year, today.month))
        return context


class LunarDateWidgetView(TemplateView):
    template_name = "patidina/lunar-date-widget.html"


class SolarDateWidgetView(TemplateView):
    template_name = "patidina/solar-date-widget.html"


class MoonPhaseWidgetView(TemplateView):
    template_name = "patidina/moon-phase-widget.html"


class BuddhistCalendarWidgetView(TemplateView):
    template_name = "patidina/calendar_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        y = kwargs["y"]
        m = kwargs["m"]
        context["ini_solar_date"] = date(y, m, 1)
        context.update(month_calendar(y, m))
        return context


class UposathaDatesWidgetView(TemplateView):
    template_name = "patidina/uposatha_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year = kwargs.get("y") or date.today().year
        context["year"] = year
        context["prev_year"] = year - 1
        context["next_year"] = year + 1
        context["be_year"] = year + 543
        context["ini_solar_date"] = date(year, 1, 1)
        context.update(uposatha_year(year))
        return context
