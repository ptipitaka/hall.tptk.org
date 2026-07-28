"""Template tags for catalog breadcrumb navigation."""

from django import template
from django.utils.safestring import mark_safe

from website.breadcrumbs import (
    catalog_breadcrumb_json_ld,
    get_catalog_breadcrumb_items,
    get_catalog_breadcrumb_parent,
)

register = template.Library()


@register.inclusion_tag("website/snippets/catalog_breadcrumbs.html", takes_context=True)
def catalog_breadcrumbs(context):
    page = context.get("page")
    request = context.get("request")
    items = get_catalog_breadcrumb_items(page)

    if not items:
        return {"show": False}

    breadcrumb_ld = catalog_breadcrumb_json_ld(request, items)

    return {
        "show": True,
        "ancestors": items[:-1],
        "parent": get_catalog_breadcrumb_parent(page),
        "breadcrumb_ld_json": mark_safe(breadcrumb_ld) if breadcrumb_ld else None,
    }
