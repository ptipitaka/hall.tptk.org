"""Wagtail admin grouping for catalog snippets."""

from django.utils.translation import gettext_lazy as _
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet, SnippetViewSetGroup

from snippets.admin_listing import ReferenceSnippetIndexView, reference_list_display
from snippets.models.vocabulary import (
    CanonicalSection,
    Classification,
    ContentLanguage,
    ContentScript,
    Country,
    SegmentKind,
    Tradition,
)


class ReferenceSnippetViewSet(SnippetViewSet):
    """Catalog vocabulary: listing opens on the default locale; Translations shows the rest."""

    add_to_admin_menu = False
    index_view_class = ReferenceSnippetIndexView


class ClassificationViewSet(ReferenceSnippetViewSet):
    model = Classification
    menu_label = _("Classifications")
    icon = "tag"
    ordering = ["sort_order", "slug", "locale__language_code"]
    list_display = reference_list_display("siglum")


class TraditionViewSet(ReferenceSnippetViewSet):
    model = Tradition
    menu_label = _("Traditions")
    icon = "globe"
    ordering = ["sort_order", "code", "locale__language_code"]
    list_display = reference_list_display("code")


class CountryViewSet(ReferenceSnippetViewSet):
    model = Country
    menu_label = _("Countries")
    icon = "site"
    ordering = ["sort_order", "code", "locale__language_code"]
    list_display = reference_list_display("code")


class ContentLanguageViewSet(ReferenceSnippetViewSet):
    model = ContentLanguage
    menu_label = _("Content languages")
    icon = "site"
    ordering = ["sort_order", "code", "locale__language_code"]
    list_display = reference_list_display("code")


class ContentScriptViewSet(ReferenceSnippetViewSet):
    model = ContentScript
    menu_label = _("Content scripts")
    icon = "doc-full"
    ordering = ["sort_order", "code", "locale__language_code"]
    list_display = reference_list_display("code")


class SegmentKindViewSet(ReferenceSnippetViewSet):
    model = SegmentKind
    menu_label = _("Segment kinds")
    icon = "list-ul"
    ordering = ["sort_order", "code", "locale__language_code"]
    list_display = reference_list_display("code")


class CanonicalSectionViewSet(ReferenceSnippetViewSet):
    model = CanonicalSection
    menu_label = _("Canonical sections")
    icon = "folder-open-inverse"
    ordering = ["sort_order", "code", "locale__language_code"]
    list_display = reference_list_display("code")


class ReferenceDataGroup(SnippetViewSetGroup):
    menu_label = _("Reference data")
    menu_icon = "list-ul"
    menu_order = 200
    items = (
        ClassificationViewSet,
        CanonicalSectionViewSet,
        TraditionViewSet,
        CountryViewSet,
        ContentLanguageViewSet,
        ContentScriptViewSet,
        SegmentKindViewSet,
    )


register_snippet(ReferenceDataGroup)
