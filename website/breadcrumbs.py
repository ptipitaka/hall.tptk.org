"""Catalog breadcrumb trail for Wagtail page tree (FRBR catalog pages)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from wagtail.models import Page

CATALOG_PAGE_CLASSES = frozenset(
    {
        "CatalogIndexPage",
        "CollectionPage",
        "EditionPage",
        "VolumePage",
    }
)


def get_catalog_breadcrumb_items(page: Page | None) -> list[Page]:
    """Return ordered catalog ancestors plus the current page, or [] when hidden."""
    if page is None:
        return []

    specific = page.specific
    class_name = specific.__class__.__name__

    if class_name == "CatalogIndexPage" or class_name not in CATALOG_PAGE_CLASSES:
        return []

    items: list[Page] = []
    for ancestor in page.get_ancestors(inclusive=False).live().specific():
        if ancestor.locale_id != page.locale_id:
            continue
        if ancestor.__class__.__name__ in CATALOG_PAGE_CLASSES:
            items.append(ancestor)

    items.append(specific)
    return items


def get_catalog_breadcrumb_parent(page: Page | None) -> Page | None:
    """Immediate live catalog parent for the one-level mobile back link."""
    if page is None:
        return None

    parent = page.get_parent()
    if parent is None or not parent.live:
        return None

    parent_specific = parent.specific
    if parent_specific.__class__.__name__ not in CATALOG_PAGE_CLASSES:
        return None
    if parent.locale_id != page.locale_id:
        return None
    return parent_specific


def catalog_breadcrumb_json_ld(request, items: list[Page]) -> str | None:
    if not request or not items:
        return None

    elements = []
    for position, crumb in enumerate(items, start=1):
        elements.append(
            {
                "@type": "ListItem",
                "position": position,
                "name": crumb.title,
                "item": request.build_absolute_uri(crumb.url),
            }
        )

    payload = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": elements,
    }
    return json.dumps(payload, ensure_ascii=False)
