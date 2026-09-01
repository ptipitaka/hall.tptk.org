"""Admin listing helpers for translatable catalog snippets."""

from django.utils.translation import gettext_lazy as _
from wagtail.admin.ui.tables import Column, LocaleColumn, UpdatedAtColumn
from wagtail.models import Locale
from wagtail.snippets.views.snippets import IndexView


def localized_label(instance) -> str:
    for attr in ("title", "name"):
        value = getattr(instance, attr, None)
        if value:
            return value
    return str(instance)


def translation_siblings(instance):
    cached = getattr(instance, "_prefetched_siblings", None)
    if cached is not None:
        return cached
    return list(
        instance.get_translations(inclusive=False)
        .select_related("locale")
        .order_by("locale__language_code")
    )


def format_translation_siblings(instance) -> str:
    siblings = translation_siblings(instance)
    if not siblings:
        return "—"
    return " · ".join(
        f"{sibling.locale.get_display_name()}: {localized_label(sibling)}"
        for sibling in siblings
    )


def attach_translation_siblings(instances) -> list:
    rows = list(instances)
    if not rows:
        return rows
    model = rows[0].__class__
    keys = {row.translation_key for row in rows}
    by_key: dict = {}
    for sibling in (
        model.objects.filter(translation_key__in=keys)
        .select_related("locale")
        .order_by("locale__language_code")
    ):
        by_key.setdefault(sibling.translation_key, []).append(sibling)
    for row in rows:
        row._prefetched_siblings = [
            sibling
            for sibling in by_key.get(row.translation_key, [])
            if sibling.pk != row.pk
        ]
    return rows


class TranslationsColumn(Column):
    """Show the other locale version of the same snippet."""

    def __init__(self):
        super().__init__("translations", label=_("Translations"))

    def get_value(self, instance):
        return format_translation_siblings(instance)


def reference_list_display(*extra_fields):
    return [
        "__str__",
        *extra_fields,
        TranslationsColumn(),
        LocaleColumn(),
        UpdatedAtColumn(),
    ]


class ReferenceSnippetIndexView(IndexView):
    def get_base_queryset(self):
        return super().get_base_queryset().select_related("locale")

    def get_filterset_kwargs(self):
        kwargs = super().get_filterset_kwargs()
        data = kwargs.get("data")
        # No locale param → default locale (English). Explicit blank keeps "All".
        if data is not None and "locale" not in data:
            data = data.copy()
            data["locale"] = Locale.get_default().language_code
            kwargs["data"] = data
        return kwargs

    def get_table(self, object_list):
        return super().get_table(attach_translation_siblings(object_list))
