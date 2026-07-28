"""
Seed Thai translations of catalog pages (CatalogIndex → Collection → Edition).

Requires English catalog pages and ``seed_catalog_reference`` snippets.
Run via ``python manage.py seed_catalog_translations`` (or ``--force``).
"""

from __future__ import annotations

import html
from decimal import Decimal

from django.utils.html import strip_tags

TRANSLATION_LOCALES = ("th",)

CATALOG_SLUG = "buddhist-scriptures"

CATALOG_INDEX_EN = {
    "title": "Buddhist Scriptures",
    "search_description": (
        "Principal Tipiṭaka editions and related scriptures, "
        "organised for reference and cross-edition study."
    ),
    "intro": (
        "Principal Tipiṭaka editions and related scriptures, "
        "organised for reference and cross-edition study."
    ),
}

CATALOG_INDEX_TH = {
    "title": "คัมภีร์ทางพุทธศาสนา",
    "search_description": (
        "พระไตรปิฎกฉบับหลักและคัมภีร์ที่เกี่ยวข้อง "
        "จัดไว้เพื่อค้นคว้าและเทียบข้ามฉบับ"
    ),
    "intro": (
        "พระไตรปิฎกฉบับหลักและคัมภีร์ที่เกี่ยวข้อง "
        "จัดไว้เพื่อค้นคว้าและเทียบข้ามฉบับ"
    ),
}

def _collection_th_from_catalog() -> dict[str, dict[str, str]]:
    from website.tipitaka_catalog_data import COLLECTIONS

    return {
        coll["code"]: {
            "title": coll["title"]["th"],
            "body": coll["body"]["th"],
            "search_description": coll["body"]["th"],
        }
        for coll in COLLECTIONS
    }


def _edition_th_from_catalog() -> dict[tuple[str, str], dict[str, str]]:
    from website.tipitaka_catalog_data import COLLECTIONS

    # Keyed by (collection_code, edition_code): edition codes may repeat
    # across collections (unique among siblings only).
    return {
        (coll["code"], edition["code"]): {
            "title": edition["title"]["th"],
            "search_description": edition["description"]["th"],
        }
        for coll in COLLECTIONS
        for edition in coll["editions"]
    }


COLLECTION_TH: dict[str, dict[str, str]] = _collection_th_from_catalog()
EDITION_TH: dict[str, dict[str, str]] = _edition_th_from_catalog()


def _row_body(text: str) -> list[dict]:
    """Match English catalog StreamField shape: row → content → text."""
    return [
        {
            "type": "row",
            "value": {
                "fluid": False,
                "content": [
                    {
                        "type": "content",
                        "value": {
                            "content": [
                                {
                                    "type": "text",
                                    "value": f"<p>{html.escape(text)}</p>",
                                }
                            ],
                            "settings": {
                                "custom_id": "",
                                "custom_template": "",
                                "custom_css_class": "",
                                "column_breakpoint": "md",
                            },
                            "column_size": "",
                        },
                    }
                ],
                "settings": {
                    "custom_id": "",
                    "custom_template": "",
                    "custom_css_class": "",
                },
            },
        }
    ]


def _body_plain_text(body) -> str:
    return " ".join(strip_tags(str(body)).split())


def _get_or_copy_page(page, locale, *, copy_parents: bool = True):
    translated = page.get_translations(inclusive=False).filter(locale=locale).first()
    if translated is not None:
        if translated.alias_of_id:
            translated.delete()
        else:
            return translated.specific

    copied = page.copy_for_translation(
        locale,
        copy_parents=copy_parents,
        alias=False,
    )
    return copied.specific


def _remap_snippet(obj, model, locale):
    if obj is None:
        return None
    return model.objects.get(translation_key=obj.translation_key, locale=locale)


def seed_catalog_translations(
    *,
    force: bool = False,
    locales: tuple[str, ...] = TRANSLATION_LOCALES,
) -> dict[str, int]:
    """
    Create or update Thai translations of the Buddhist Scriptures catalog tree.

    Remaps classification / tradition / country / content language / script FKs
    to the target locale and applies Thai copy for known collection/edition codes.
    """
    from wagtail.models import Locale

    from snippets.models import (
        Classification,
        ContentLanguage,
        ContentScript,
        Country,
        Tradition,
    )
    from website.models import CatalogIndexPage, CollectionPage, EditionPage

    stats = {
        "catalogs_updated": 0,
        "collections_created": 0,
        "collections_updated": 0,
        "editions_created": 0,
        "editions_updated": 0,
    }

    en = Locale.objects.get(language_code="en")
    try:
        catalog_en = CatalogIndexPage.objects.get(locale=en, slug=CATALOG_SLUG)
    except CatalogIndexPage.DoesNotExist as exc:
        raise RuntimeError(
            f"English CatalogIndexPage slug={CATALOG_SLUG!r} is required."
        ) from exc

    for language_code in locales:
        if language_code != "th":
            raise ValueError(f"Unsupported catalog locale: {language_code!r}")

        locale = Locale.objects.get(language_code=language_code)
        existed = catalog_en.get_translations(inclusive=False).filter(locale=locale).exists()
        catalog = _get_or_copy_page(catalog_en, locale, copy_parents=True)

        needs_catalog = force or not existed
        if catalog.title != CATALOG_INDEX_TH["title"]:
            needs_catalog = True
        if _body_plain_text(catalog.body) != CATALOG_INDEX_TH["intro"]:
            needs_catalog = True
        if not (catalog.search_description or "").strip():
            needs_catalog = True
        if catalog.scroll_bg_opacity != catalog_en.scroll_bg_opacity:
            needs_catalog = True

        if needs_catalog:
            catalog.title = CATALOG_INDEX_TH["title"]
            catalog.search_description = CATALOG_INDEX_TH["search_description"]
            catalog.body = _row_body(CATALOG_INDEX_TH["intro"])
            catalog.scroll_bg_opacity = catalog_en.scroll_bg_opacity or Decimal("0.10")
            catalog.save_revision().publish()
            stats["catalogs_updated"] += 1

        for coll_en in (
            CollectionPage.objects.child_of(catalog_en)
            .live()
            .specific()
            .order_by("catalog_sort_order", "title")
        ):
            existed = coll_en.get_translations(inclusive=False).filter(locale=locale).exists()
            coll = _get_or_copy_page(coll_en, locale)
            if not existed:
                stats["collections_created"] += 1

            th_data = COLLECTION_TH.get(coll_en.code, {})
            needs_update = force or not existed
            if coll.classification_id != getattr(
                _remap_snippet(coll_en.classification, Classification, locale), "id", None
            ):
                needs_update = True
            if coll.country_id != getattr(
                _remap_snippet(coll_en.country, Country, locale), "id", None
            ):
                needs_update = True
            if th_data.get("title") and coll.title != th_data["title"]:
                needs_update = True
            if th_data.get("body") and _body_plain_text(coll.body) != th_data["body"]:
                needs_update = True

            if needs_update:
                coll.classification = _remap_snippet(
                    coll_en.classification, Classification, locale
                )
                coll.tradition = _remap_snippet(coll_en.tradition, Tradition, locale)
                coll.country = _remap_snippet(coll_en.country, Country, locale)
                if th_data.get("title"):
                    coll.title = th_data["title"]
                if th_data.get("body"):
                    coll.body = _row_body(th_data["body"])
                if th_data.get("search_description"):
                    coll.search_description = th_data["search_description"]
                coll.cover_image = coll_en.cover_image
                coll.catalog_sort_order = coll_en.catalog_sort_order
                coll.save_revision().publish()
                stats["collections_updated"] += 1

            edition_map: dict[int, EditionPage] = {}
            for ed_en in EditionPage.objects.child_of(coll_en).live().specific():
                existed = ed_en.get_translations(inclusive=False).filter(locale=locale).exists()
                ed = _get_or_copy_page(ed_en, locale)
                if not existed:
                    stats["editions_created"] += 1

                ed_th = EDITION_TH.get((coll_en.code, ed_en.code), {})
                needs_ed = force or not existed
                if ed_th.get("title") and ed.title != ed_th["title"]:
                    needs_ed = True

                if needs_ed:
                    if ed_th.get("title"):
                        ed.title = ed_th["title"]
                    if ed_th.get("search_description"):
                        ed.search_description = ed_th["search_description"]
                    ed.content_languages.set(
                        [
                            ContentLanguage.objects.get(
                                translation_key=lang.translation_key,
                                locale=locale,
                            )
                            for lang in ed_en.content_languages.all()
                        ]
                    )
                    ed.content_scripts.set(
                        [
                            ContentScript.objects.get(
                                translation_key=script.translation_key,
                                locale=locale,
                            )
                            for script in ed_en.content_scripts.all()
                        ]
                    )
                    ed.source_edition = None
                    ed.cover_image = ed_en.cover_image
                    ed.save_revision().publish()
                    stats["editions_updated"] += 1

                edition_map[ed_en.id] = ed

            for ed_en in EditionPage.objects.child_of(coll_en).live().specific():
                if not ed_en.source_edition_id:
                    continue
                source = edition_map.get(ed_en.source_edition_id)
                ed = edition_map.get(ed_en.id)
                if ed is None or source is None:
                    continue
                if ed.source_edition_id != source.id:
                    ed.source_edition = source
                    ed.save_revision().publish()

    return stats
