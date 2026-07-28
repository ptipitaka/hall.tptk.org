"""Wagtail snippet admin for Patidina important days."""

from django.utils.translation import gettext_lazy as _
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet, SnippetViewSetGroup

from .models import LunarImportantDay, SolarImportantDay


class LunarImportantDayViewSet(SnippetViewSet):
    model = LunarImportantDay
    menu_label = _("Important days in the lunar calendar")
    icon = "date"
    list_display = ("__str__",)
    search_fields = ("day", "month")
    add_to_admin_menu = False


class SolarImportantDayViewSet(SnippetViewSet):
    model = SolarImportantDay
    menu_label = _("Important days in the solar calendar")
    icon = "date"
    list_display = ("__str__",)
    search_fields = ("day", "month")
    add_to_admin_menu = False


class PatidinaGroup(SnippetViewSetGroup):
    menu_label = _("Patidina")
    menu_icon = "date"
    menu_order = 250
    items = (
        LunarImportantDayViewSet,
        SolarImportantDayViewSet,
    )


register_snippet(PatidinaGroup)
