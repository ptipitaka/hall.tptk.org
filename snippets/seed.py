"""Helpers for seeding translatable catalog snippets."""

from __future__ import annotations

import uuid
from typing import Any

from wagtail.models import Locale

SEED_NAMESPACE = uuid.UUID("6f8f2a1c-4b3e-4d5a-9c1e-2a7b8c9d0e1f")


def seed_translation_key(kind: str, identifier: str) -> uuid.UUID:
    return uuid.uuid5(SEED_NAMESPACE, f"{kind}:{identifier}")


def create_translated_rows(
    model,
    *,
    translation_key: uuid.UUID | None,
    shared: dict[str, Any],
    localized: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """
    Create or update one row per locale.

    *shared* fields are written on every locale row (code, slug, siglum, …).
    *localized* maps locale code → translatable field values (title, name, …).
    """
    if translation_key is None:
        raise ValueError("translation_key is required for idempotent seeding")

    rows: dict[str, Any] = {}
    for language_code, field_values in localized.items():
        locale = Locale.objects.get(language_code=language_code)
        defaults = {**shared, **field_values, "translation_key": translation_key}
        row, _created = model.objects.update_or_create(
            translation_key=translation_key,
            locale=locale,
            defaults=defaults,
        )
        rows[language_code] = row
    return rows


def classification_for_locale(
    translation_key: uuid.UUID,
    language_code: str,
) -> Any:
    from snippets.models import Classification

    locale = Locale.objects.get(language_code=language_code)
    return Classification.objects.get(
        translation_key=translation_key,
        locale=locale,
    )
