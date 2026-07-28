"""Wagtail admin forms for catalog pages — locale-filtered snippet pickers."""

from __future__ import annotations

from typing import Iterable

from django import forms
from django.db import models
from django.forms.models import ModelChoiceIterator
from wagtail.admin.forms.pages import WagtailAdminPageForm
from wagtail.models import Locale

from snippets.models import (
    CanonicalSection,
    Classification,
    ContentLanguage,
    ContentScript,
    Country,
    Tradition,
)


def catalog_page_locale(form: WagtailAdminPageForm) -> Locale | None:
    """Locale used to filter related snippets on catalog page forms."""
    instance = form.instance
    if getattr(instance, "locale_id", None):
        return instance.locale
    parent = getattr(form, "parent_page", None)
    if parent is not None and getattr(parent, "locale_id", None):
        return parent.locale
    return Locale.get_default()


def locale_queryset(model: type[models.Model], locale: Locale):
    qs = model.objects.filter(locale=locale)
    ordering = model._meta.ordering
    if ordering:
        qs = qs.order_by(*ordering)
    return qs


class LocaleFilteredCatalogPageForm(WagtailAdminPageForm):
    """Limit translatable snippet FK/M2M choices to the page locale."""

    locale_filtered_snippet_fields: Iterable[tuple[str, type[models.Model]]] = ()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        locale = catalog_page_locale(self)
        if locale is None:
            return
        for field_name, model in self.locale_filtered_snippet_fields:
            if field_name in self.fields:
                self.fields[field_name].queryset = locale_queryset(model, locale)


class CollectionPageForm(LocaleFilteredCatalogPageForm):
    locale_filtered_snippet_fields = (
        ("classification", Classification),
        ("tradition", Tradition),
        ("country", Country),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "cover_image" in self.fields:
            self.fields["cover_image"].help_text = (
                "Optional cover shown as a thumbnail on the catalog index. "
                "Not displayed as a large hero on the collection page."
            )


class EditionPageForm(LocaleFilteredCatalogPageForm):
    locale_filtered_snippet_fields = (
        ("content_languages", ContentLanguage),
        ("content_scripts", ContentScript),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        locale = catalog_page_locale(self)
        if locale is None or "source_edition" not in self.fields:
            return
        from website.models import EditionPage

        self.fields["source_edition"].queryset = EditionPage.objects.filter(
            locale=locale
        ).order_by("title")


class CanonicalSectionChoiceIterator(ModelChoiceIterator):
    """Emit piṭaka leaves as options; piṭakas with children become optgroups."""

    def __iter__(self):
        if self.field.empty_label is not None:
            yield ("", self.field.empty_label)

        sections = list(self.queryset)
        children_by_parent: dict[int, list[CanonicalSection]] = {}
        roots: list[CanonicalSection] = []
        for section in sections:
            if section.parent_id:
                children_by_parent.setdefault(section.parent_id, []).append(section)
            else:
                roots.append(section)

        for root in roots:
            children = children_by_parent.get(root.pk, [])
            if children:
                yield (root.name, [self.choice(child) for child in children])
            else:
                yield self.choice(root)


class CanonicalSectionChoiceField(forms.ModelChoiceField):
    """Nested Piṭaka → Nikāya select via HTML ``<optgroup>``."""

    iterator = CanonicalSectionChoiceIterator

    def label_from_instance(self, obj: CanonicalSection) -> str:
        return obj.name


class VolumePageForm(LocaleFilteredCatalogPageForm):
    """
    Section uses a plain select (not the snippet chooser).

    CanonicalSection is TranslatableMixin, so Wagtail's chooser opens a Locale
    filter modal that looks like the wrong field when the vocabulary is empty
    or when editors expect a Piṭaka/nikāya list. A select filtered to the page
    locale shows the tree directly (optgroups for nikāyas under their piṭaka).
    """

    locale_filtered_snippet_fields = (("section", CanonicalSection),)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "section" not in self.fields:
            return
        locale = catalog_page_locale(self)
        queryset = (
            locale_queryset(CanonicalSection, locale)
            if locale is not None
            else CanonicalSection.objects.none()
        )
        # Rebuild the field: replacing only the widget after queryset is set
        # leaves Select.choices empty (Django copies choices onto the widget
        # when queryset is assigned).
        self.fields["section"] = CanonicalSectionChoiceField(
            queryset=queryset.select_related("parent"),
            required=False,
            empty_label="---------",
            widget=forms.Select,
            label=self.fields["section"].label,
            help_text=self.fields["section"].help_text,
        )
