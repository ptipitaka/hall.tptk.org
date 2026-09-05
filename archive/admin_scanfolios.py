"""Scan folio listing in Wagtail admin (Digital archive).

Staff pick Collection → Edition → Book, optionally jump to a page number,
and open a folio to view the scan (or a clear 'no scan' message).
Last filter values are stored in the session for the next visit.
"""

from __future__ import annotations

from urllib.parse import urlencode

from django import forms
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import path, reverse
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from django_filters import CharFilter, ChoiceFilter
from wagtail.admin.auth import require_admin_access
from wagtail.admin.filters import WagtailFilterSet
from wagtail.admin.ui.tables import Column, TitleColumn
from wagtail.models import Locale
from wagtail.snippets.views.snippets import IndexView, InspectView, SnippetViewSet

from archive.models import ScanFolio
from website.models import CollectionPage, EditionPage, VolumePage

FILTER_SESSION_KEY = "archive_scanfolio_filters"
FILTER_QUERY_KEYS = ("collection", "edition", "volume", "folio_page", "page_order")

PAGE_ORDER_ASC = "asc"
PAGE_ORDER_DESC = "desc"
PAGE_ORDER_CHOICES = (
    (PAGE_ORDER_ASC, _("Low to high")),
    (PAGE_ORDER_DESC, _("High to low")),
)


def _default_locale():
    return Locale.get_default()


def _int_or_none(value) -> int | None:
    if value in (None, "", "null"):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _live_default(qs):
    return qs.live().filter(locale=_default_locale())


def collection_choices() -> list[tuple[int, str]]:
    pages = _live_default(CollectionPage.objects).order_by(
        "catalog_sort_order", "title"
    )
    return [(page.pk, page.title) for page in pages]


def edition_choices(collection_id=None) -> list[tuple[int, str]]:
    pk = _int_or_none(collection_id)
    if pk is None:
        return []
    try:
        collection = CollectionPage.objects.get(pk=pk)
    except CollectionPage.DoesNotExist:
        return []
    pages = (
        _live_default(EditionPage.objects)
        .child_of(collection)
        .order_by("catalog_sort_order", "title")
    )
    return [(page.pk, page.title) for page in pages]


def book_choices(edition_id=None) -> list[tuple[int, str]]:
    pk = _int_or_none(edition_id)
    if pk is None:
        return []
    try:
        edition = EditionPage.objects.get(pk=pk)
    except EditionPage.DoesNotExist:
        return []
    pages = (
        _live_default(VolumePage.objects)
        .child_of(edition)
        .order_by("volume_index", "title")
    )
    return [(page.pk, page.title) for page in pages]


def _select_widget(*, step: str, enabled: bool) -> forms.Select:
    attrs = {"data-cascade-step": step}
    if not enabled:
        attrs["disabled"] = True
    return forms.Select(attrs=attrs)


def _parent_ids_from_volume(volume_id) -> tuple[int | None, int | None]:
    """Return (collection_id, edition_id) for a book, if the volume exists."""
    pk = _int_or_none(volume_id)
    if pk is None:
        return None, None
    try:
        volume = VolumePage.objects.get(pk=pk)
    except VolumePage.DoesNotExist:
        return None, None
    edition = volume.get_parent()
    collection = edition.get_parent() if edition is not None else None
    return (
        collection.pk if collection is not None else None,
        edition.pk if edition is not None else None,
    )


def _parent_id_from_edition(edition_id) -> int | None:
    pk = _int_or_none(edition_id)
    if pk is None:
        return None
    try:
        edition = EditionPage.objects.get(pk=pk)
    except EditionPage.DoesNotExist:
        return None
    parent = edition.get_parent()
    return parent.pk if parent is not None else None


def _enrich_filter_data(data):
    """Fill parent dropdowns so a book-only query stays a valid choice."""
    if data is None or not hasattr(data, "copy"):
        return data
    collection_id = data.get("collection")
    edition_id = data.get("edition")
    inferred_collection, inferred_edition = _parent_ids_from_volume(data.get("volume"))
    if inferred_edition and not edition_id:
        edition_id = inferred_edition
    if not collection_id:
        collection_id = inferred_collection or _parent_id_from_edition(edition_id)
    out = data.copy()
    if collection_id and not data.get("collection"):
        out["collection"] = str(collection_id)
    if edition_id and not data.get("edition"):
        out["edition"] = str(edition_id)
    return out


def _inspect_url(folio) -> str:
    return reverse("wagtailsnippets_archive_scanfolio:inspect", args=[folio.pk])


def _has_filter_params(request) -> bool:
    return any(key in request.GET for key in FILTER_QUERY_KEYS)


def _saved_filters(request) -> dict[str, str]:
    saved = request.session.get(FILTER_SESSION_KEY) or {}
    return {
        key: str(saved[key])
        for key in FILTER_QUERY_KEYS
        if saved.get(key) not in (None, "")
    }


class ScanFolioFilterSet(WagtailFilterSet):
    collection = ChoiceFilter(
        method="filter_collection",
        choices=collection_choices,
        label=_("Collection"),
        empty_label=_("Select collection"),
        null_label=None,
    )
    edition = ChoiceFilter(
        method="filter_edition",
        choices=lambda: edition_choices(),
        label=_("Edition"),
        empty_label=_("Select edition"),
        null_label=None,
    )
    volume = ChoiceFilter(
        method="filter_book",
        choices=lambda: book_choices(),
        label=_("Book"),
        empty_label=_("Select book"),
        null_label=None,
    )
    folio_page = CharFilter(
        method="filter_folio_page",
        label=_("Page no."),
        widget=forms.TextInput(
            attrs={
                "placeholder": _("Jump to page…"),
                "inputmode": "numeric",
                "autocomplete": "off",
            }
        ),
    )
    page_order = ChoiceFilter(
        method="passthrough",
        choices=PAGE_ORDER_CHOICES,
        label=_("Sort by page no."),
        empty_label=None,
        null_label=None,
        widget=forms.Select(),
    )

    class Meta:
        model = ScanFolio
        fields = ["collection", "edition", "volume", "folio_page", "page_order"]

    def __init__(self, data=None, *args, **kwargs):
        data = _enrich_filter_data(data)
        super().__init__(data, *args, **kwargs)
        collection_id = data.get("collection") if data is not None else None
        edition_id = data.get("edition") if data is not None else None
        volume_id = data.get("volume") if data is not None else None
        has_collection = _int_or_none(collection_id) is not None
        has_edition = _int_or_none(edition_id) is not None
        has_book = _int_or_none(volume_id) is not None
        # Set choices and enabled state before the form/field cache is built.
        self.filters["collection"].extra.update(
            {
                "choices": collection_choices(),
                "empty_label": str(_("Select collection")),
                "null_label": None,
                "widget": _select_widget(step="collection", enabled=True),
            }
        )
        self.filters["edition"].extra.update(
            {
                "choices": edition_choices(collection_id),
                "empty_label": str(_("Select edition")),
                "null_label": None,
                "widget": _select_widget(step="edition", enabled=has_collection),
            }
        )
        self.filters["volume"].extra.update(
            {
                "choices": book_choices(edition_id),
                "empty_label": str(_("Select book")),
                "null_label": None,
                "widget": _select_widget(step="book", enabled=has_edition),
            }
        )
        folio_attrs = {
            "placeholder": str(_("Jump to page…")),
            "inputmode": "numeric",
            "autocomplete": "off",
        }
        if not has_book:
            folio_attrs["disabled"] = True
        self.filters["folio_page"].extra["widget"] = forms.TextInput(attrs=folio_attrs)
        self.filters["page_order"].extra.update(
            {
                "empty_label": None,
                "null_label": None,
                "widget": forms.Select(attrs={} if has_book else {"disabled": True}),
            }
        )

    def filter_collection(self, qs, name, value):
        pk = _int_or_none(value)
        if pk is None:
            return qs
        try:
            collection = CollectionPage.objects.get(pk=pk)
        except CollectionPage.DoesNotExist:
            return qs.none()
        volume_ids = VolumePage.objects.descendant_of(collection).values_list(
            "pk", flat=True
        )
        return qs.filter(volume_id__in=list(volume_ids))

    def filter_edition(self, qs, name, value):
        pk = _int_or_none(value)
        if pk is None:
            return qs
        try:
            edition = EditionPage.objects.get(pk=pk)
        except EditionPage.DoesNotExist:
            return qs.none()
        volume_ids = VolumePage.objects.child_of(edition).values_list("pk", flat=True)
        return qs.filter(volume_id__in=list(volume_ids))

    def filter_book(self, qs, name, value):
        pk = _int_or_none(value)
        if pk is None:
            return qs
        return qs.filter(volume_id=pk)

    def filter_folio_page(self, qs, name, value):
        raw = (value or "").strip()
        if not raw:
            return qs
        match = Q(page_no__iexact=raw)
        if raw.isdigit():
            match |= Q(sequence=int(raw))
        return qs.filter(match)

    def passthrough(self, qs, name, value):
        return qs


class ScanFolioIndexView(IndexView):
    template_name = "archive/admin/scanfolio_index.html"

    def get_base_queryset(self):
        qs = super().get_base_queryset().select_related("volume")
        # Listing waits until a book is chosen; collection/edition only
        # populate the cascade dropdowns.
        if not _int_or_none(self.request.GET.get("volume")):
            return qs.none()
        return qs

    def get(self, request, *args, **kwargs):
        if not self.results_only:
            if request.GET.get("reset") == "1":
                request.session.pop(FILTER_SESSION_KEY, None)
                return redirect(request.path)
            if not _has_filter_params(request):
                saved = _saved_filters(request)
                if saved:
                    return redirect(f"{request.path}?{urlencode(saved)}")
        response = super().get(request, *args, **kwargs)
        if _has_filter_params(request):
            request.session[FILTER_SESSION_KEY] = {
                key: request.GET.get(key, "") for key in FILTER_QUERY_KEYS
            }
        return response

    def get_ordering(self):
        requested = self.request.GET.get("ordering")
        if requested in self.get_valid_orderings():
            return requested
        if self.request.GET.get("page_order") == PAGE_ORDER_DESC:
            return "-sequence"
        return "sequence"

    def get_valid_orderings(self):
        return [
            "sequence",
            "-sequence",
            "page_no",
            "-page_no",
            "status",
            "-status",
            "volume__title",
            "-volume__title",
        ]

    @cached_property
    def active_filters(self):
        # The cascade bar is the filter UI; hide Wagtail's pill row.
        return []

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["scanfolio_filterset"] = getattr(self, "filters", None) or context.get(
            "filters"
        )
        context["filters"] = None
        if not _int_or_none(self.request.GET.get("volume")):
            context["is_filtering"] = False
            context["add_url"] = None
            context["no_results_message"] = str(
                _("Select a collection, then an edition, then a book.")
            )
        return context


class ScanFolioInspectView(InspectView):
    template_name = "archive/admin/scanfolio_inspect.html"

    def get_queryset(self):
        return super().get_queryset().select_related("volume")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        folio = self.object
        context["has_scan_image"] = folio.has_scan_image
        context["scan_url"] = folio.image_url if folio.has_scan_image else ""
        return context


@require_admin_access
def edition_options(request):
    """JSON choices for the Scan folios cascade (Collection → Edition)."""
    choices = [
        {"id": pk, "label": label}
        for pk, label in edition_choices(request.GET.get("collection"))
    ]
    return JsonResponse({"choices": choices})


@require_admin_access
def book_options(request):
    """JSON choices for the Scan folios cascade (Edition → Book)."""
    choices = [
        {"id": pk, "label": label}
        for pk, label in book_choices(request.GET.get("edition"))
    ]
    return JsonResponse({"choices": choices})


class ScanFolioViewSet(SnippetViewSet):
    model = ScanFolio
    menu_label = _("Scan folios")
    menu_icon = "image"
    menu_order = 100

    list_display = [
        TitleColumn(
            "folio",
            label=_("Folio"),
            accessor="folio_label",
            get_url=_inspect_url,
            sort_key="sequence",
        ),
        Column(
            "book",
            label=_("Book"),
            accessor="volume.title",
            sort_key="volume__title",
        ),
        Column("sequence", label=_("Sequence"), sort_key="sequence"),
        Column("page_no", label=_("Page no."), sort_key="page_no"),
        Column("status", label=_("Status"), sort_key="status"),
    ]
    filterset_class = ScanFolioFilterSet
    search_fields = []
    ordering = ["sequence"]
    inspect_view_enabled = True
    inspect_view_class = ScanFolioInspectView
    inspect_view_fields = ["volume", "sequence", "page_no", "status"]
    index_view_class = ScanFolioIndexView
    add_to_admin_menu = False

    def get_index_template(self):
        return "archive/admin/scanfolio_index.html"

    def get_inspect_template(self):
        return "archive/admin/scanfolio_inspect.html"

    def get_urlpatterns(self):
        return super().get_urlpatterns() + [
            path("options/editions/", edition_options, name="edition_options"),
            path("options/books/", book_options, name="book_options"),
        ]
