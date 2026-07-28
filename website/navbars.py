"""
Locale-specific CRX Navigation bars (main-en, main-th).
"""

from __future__ import annotations

from coderedcms.models.snippet_models import Navbar
from wagtail.models import Locale, Site

LOCALE_NAVBAR_PREFIX = "main"
FALLBACK_NAVBAR_NAME = "main-en"
LEGACY_NAVBAR_NAME = "main"

LOCALE_HOME_LABELS = {
    "en": "Home",
    "th": "หน้าแรก",
}

LOCALE_PATIDINA_LABELS = {
    "en": "Patidina",
    "th": "ปฏิทิน",
}


def _home_page_for_locale(language_code: str):
    site = Site.objects.get(is_default_site=True)
    home_en = site.root_page
    if language_code == "en":
        return home_en
    locale = Locale.objects.get(language_code=language_code)
    return home_en.get_translation(locale)


def _patidina_page_for_locale(language_code: str):
    from patidina.models import PatidinaPage

    return (
        PatidinaPage.objects.filter(locale__language_code=language_code, live=True).first()
        or PatidinaPage.objects.filter(locale__language_code=language_code).first()
    )


def _page_link_item(display_text: str, page) -> tuple[str, dict]:
    return (
        "page_link",
        {
            "settings": {
                "custom_template": "",
                "custom_css_class": "",
                "custom_id": "",
            },
            "display_text": display_text,
            "image": None,
            "page": page,
            "sub_links": [],
            "show_child_links": False,
        },
    )


def _page_link_raw(display_text: str, page) -> dict:
    """StreamField raw-data form of a page_link block."""
    return {
        "type": "page_link",
        "value": {
            "settings": {
                "custom_template": "",
                "custom_css_class": "",
                "custom_id": "",
            },
            "display_text": display_text,
            "image": None,
            "page": page.pk,
            "sub_links": [],
            "show_child_links": False,
        },
    }


def _navbar_links_page(navbar: Navbar, page) -> bool:
    page_id = page.pk
    for block in navbar.menu_items:
        if block.block_type != "page_link":
            continue
        linked = block.value.get("page")
        if linked is not None and linked.pk == page_id:
            return True
    return False


def _default_menu_items(language_code: str) -> list:
    home_page = _home_page_for_locale(language_code)
    items = [_page_link_item(LOCALE_HOME_LABELS[language_code], home_page)]
    patidina = _patidina_page_for_locale(language_code)
    if patidina is not None:
        items.append(
            _page_link_item(LOCALE_PATIDINA_LABELS[language_code], patidina)
        )
    return items


def locale_navbar_name(language_code: str) -> str:
    return f"{LOCALE_NAVBAR_PREFIX}-{language_code}"


def resolve_locale_navbar(language_code: str) -> Navbar | None:
    names = [locale_navbar_name(language_code)]
    if FALLBACK_NAVBAR_NAME not in names:
        names.append(FALLBACK_NAVBAR_NAME)
    for name in names:
        navbar = Navbar.objects.filter(name=name).first()
        if navbar is not None:
            return navbar
    return None


def delete_legacy_navbar() -> bool:
    """Remove pre-i18n navbar named ``main`` (not ``main-en`` etc.)."""
    deleted, _ = Navbar.objects.filter(name=LEGACY_NAVBAR_NAME).delete()
    return deleted > 0


def seed_locale_navbars(*, force: bool = False) -> dict[str, int]:
    """
    Create or update main-en and main-th navbars.

    Default menu: Home + Patidina (when PatidinaPage exists).
    Without --force, appends a missing Patidina link and leaves other items alone.

    Returns counts: {"created", "updated", "legacy_deleted"}.
    """
    stats = {"created": 0, "updated": 0, "legacy_deleted": 0}

    for language_code in LOCALE_HOME_LABELS:
        name = locale_navbar_name(language_code)
        menu_items = _default_menu_items(language_code)
        patidina = _patidina_page_for_locale(language_code)

        navbar = Navbar.objects.filter(name=name).first()
        if navbar is None:
            Navbar.objects.create(name=name, menu_items=menu_items)
            stats["created"] += 1
            continue

        if force or not navbar.menu_items:
            navbar.menu_items = menu_items
            navbar.save()
            stats["updated"] += 1
            continue

        if patidina is not None and not _navbar_links_page(navbar, patidina):
            raw = list(navbar.menu_items.get_prep_value())
            raw.append(
                _page_link_raw(LOCALE_PATIDINA_LABELS[language_code], patidina)
            )
            navbar.menu_items = raw
            navbar.save()
            stats["updated"] += 1

    if delete_legacy_navbar():
        stats["legacy_deleted"] = 1

    return stats
