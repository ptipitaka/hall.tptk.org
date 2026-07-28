"""Helpers for resolving catalog pages when edition codes repeat across collections."""

from __future__ import annotations

from website.models import EditionPage


def get_edition_page(*, locale, collection_code: str, edition_code: str) -> EditionPage:
    """Return the EditionPage for locale under CollectionPage ``collection_code``."""
    for edition in EditionPage.objects.filter(locale=locale, code=edition_code).specific():
        parent = edition.get_parent()
        if parent is None:
            continue
        if getattr(parent.specific, "code", None) == collection_code:
            return edition
    raise EditionPage.DoesNotExist(
        f"EditionPage locale={getattr(locale, 'language_code', locale)!r} "
        f"collection={collection_code!r} code={edition_code!r}"
    )
