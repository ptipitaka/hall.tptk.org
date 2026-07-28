"""Template tags for hall.tptk.org i18n UI."""

from django.conf import settings
from django import template
from django.utils import translation
from wagtail.models import Locale, Page, Site

from website.navbars import resolve_locale_navbar

register = template.Library()

LANGUAGE_SHORT_LABELS = {
    "en": "EN",
    "th": "ไทย",
}


def _page_for_locale(page: Page, language_code: str) -> Page | None:
    if page.locale.language_code == language_code:
        return page

    locale = Locale.objects.filter(language_code=language_code).first()
    if locale is None:
        return None

    translated = page.get_translations(inclusive=False).filter(locale=locale).first()
    if translated:
        return translated

    site = Site.objects.filter(is_default_site=True).select_related("root_page").first()
    if site is None:
        return None

    root = site.root_page
    if page.translation_key != root.translation_key:
        return None

    return root.get_translations(inclusive=False).filter(locale=locale).first()


def _active_language_code(context) -> str:
    request = context.get("request")
    if request is not None:
        code = translation.get_language_from_request(request, check_path=True)
        if code:
            return code.split("-")[0]

    page = context.get("page")
    if page is not None and hasattr(page, "locale"):
        return page.locale.language_code

    return settings.LANGUAGE_CODE.split("-")[0]


@register.simple_tag(takes_context=True)
def get_locale_navbar(context):
    """Return the CRX Navbar snippet for the active locale (main-en, main-th, …)."""
    return resolve_locale_navbar(_active_language_code(context))


@register.inclusion_tag("website/snippets/language_switcher.html", takes_context=True)
def language_switcher(context):
    page = context.get("page")
    if page is None:
        request = context.get("request")
        if request is not None:
            page = getattr(request, "page", None)

    if page is None or not hasattr(page, "locale"):
        return {"alternates": [], "current_code": ""}

    current_code = page.locale.language_code
    alternates = []

    for code, _label in settings.LANGUAGES:
        target = _page_for_locale(page, code)
        alternates.append(
            {
                "code": code,
                "label": LANGUAGE_SHORT_LABELS.get(code, code.upper()),
                "url": target.url if target else None,
                "active": code == current_code,
            }
        )

    return {
        "alternates": alternates,
        "current_code": current_code,
    }
