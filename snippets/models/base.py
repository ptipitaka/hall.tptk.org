"""Shared bases for hall.tptk.org catalog snippets."""

from django.core.exceptions import ValidationError
from django.db import models
from wagtail.admin.panels import FieldPanel
from wagtail.models import Locale, TranslatableMixin


class HallTranslatableMixin(TranslatableMixin):
    """Wagtail locale + translation_key for en / th snippet rows."""

    class Meta(TranslatableMixin.Meta):
        abstract = True

    @classmethod
    def get_default_locale(cls) -> Locale:
        return Locale.get_default()


def validate_same_locale_fk(instance, field_name: str, related) -> None:
    """Ensure a FK target uses the same Wagtail locale as *instance*."""
    if related is None:
        return
    if related.locale_id != instance.locale_id:
        label = instance._meta.get_field(field_name).verbose_name
        raise ValidationError(
            {field_name: f"{label} must use the same locale as this record."}
        )


def validate_same_locale_m2m(instance, field_name: str, related_manager) -> None:
    """Ensure every M2M target uses the same Wagtail locale as *instance*."""
    if not instance.pk:
        return
    label = instance._meta.get_field(field_name).verbose_name
    for related in related_manager.all():
        if related.locale_id != instance.locale_id:
            raise ValidationError(
                {field_name: f"{label} must use the same locale as this record."}
            )


class VocabularyPanelsMixin:
    """Admin panels shared by lookup snippets."""

    panels = [
        FieldPanel("code"),
        FieldPanel("slug"),
        FieldPanel("name"),
        FieldPanel("description"),
        FieldPanel("sort_order"),
    ]

    def __str__(self) -> str:
        return self.name or self.code
