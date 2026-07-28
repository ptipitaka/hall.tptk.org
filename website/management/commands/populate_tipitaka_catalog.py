"""
Populate Tipiṭaka CollectionPage + EditionPage tree (EN + TH) from
website.tipitaka_catalog_data, with covers from website/data/covers/.
"""

from __future__ import annotations

from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand
from django.db import transaction
from wagtail.images import get_image_model
from wagtail.models import Locale

from snippets.models import (
    Classification,
    ContentLanguage,
    ContentScript,
    Country,
    Tradition,
)
from website.catalog_content import _get_or_copy_page, _remap_snippet, _row_body
from website.models import CatalogIndexPage, CollectionPage, EditionPage
from website.tipitaka_catalog_data import COLLECTIONS, edition_publication_fields

CATALOG_SLUG = "buddhist-scriptures"
COVERS_DIR = Path(__file__).resolve().parents[2] / "data" / "covers"
Image = get_image_model()


class Command(BaseCommand):
    help = "Create/update Tipiṭaka catalog collections and editions (EN + TH)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Overwrite titles/bodies/metadata even when pages already exist.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        force = options["force"]
        en = Locale.objects.get(language_code="en")
        th = Locale.objects.get(language_code="th")

        try:
            catalog_en = CatalogIndexPage.objects.get(locale=en, slug=CATALOG_SLUG)
        except CatalogIndexPage.DoesNotExist as exc:
            raise SystemExit(
                f"Missing English CatalogIndexPage slug={CATALOG_SLUG!r}. "
                "Create the catalog index first."
            ) from exc

        catalog_th = _get_or_copy_page(catalog_en, th, copy_parents=True)

        tipitaka_en = Classification.objects.get(locale=en, slug="tipitaka")
        tipitaka_th = Classification.objects.get(locale=th, slug="tipitaka")

        stats = {
            "covers": 0,
            "collections_en": 0,
            "collections_th": 0,
            "editions_en": 0,
            "editions_th": 0,
            "updated": 0,
            "moved": 0,
            "pruned": 0,
        }

        cover_cache: dict[str, object] = {}

        for coll_spec in COLLECTIONS:
            cover = self._cover(coll_spec.get("cover"), cover_cache, stats)
            tradition_en = Tradition.objects.get(
                locale=en, code=coll_spec["tradition"]
            )
            country_en = Country.objects.get(locale=en, code=coll_spec["country"])

            coll_en, created = self._upsert_collection(
                parent=catalog_en,
                locale=en,
                spec=coll_spec,
                classification=tipitaka_en,
                tradition=tradition_en,
                country=country_en,
                cover=cover,
                lang="en",
                force=force,
            )
            if created:
                stats["collections_en"] += 1
            else:
                stats["updated"] += 1

            coll_th = _get_or_copy_page(coll_en, th)
            tradition_th = _remap_snippet(tradition_en, Tradition, th)
            country_th = _remap_snippet(country_en, Country, th)
            self._apply_collection_locale(
                coll_th,
                spec=coll_spec,
                classification=tipitaka_th,
                tradition=tradition_th,
                country=country_th,
                cover=cover,
                lang="th",
                force=force or created,
            )
            if created or force:
                stats["collections_th"] += 1

            edition_en_by_code: dict[str, EditionPage] = {}
            for ed_spec in coll_spec["editions"]:
                ed_cover = self._cover(ed_spec.get("cover"), cover_cache, stats)
                ed_en, ed_created, ed_moved = self._upsert_edition(
                    parent=coll_en,
                    locale=en,
                    spec=ed_spec,
                    cover=ed_cover,
                    lang="en",
                    force=force,
                    source_edition=None,
                    country=coll_spec["country"],
                )
                edition_en_by_code[ed_spec["code"]] = ed_en
                if ed_created:
                    stats["editions_en"] += 1
                else:
                    stats["updated"] += 1
                if ed_moved:
                    stats["moved"] += 1

            # Resolve source_edition on EN
            for ed_spec in coll_spec["editions"]:
                src_code = ed_spec.get("source_edition")
                if not src_code:
                    continue
                ed_en = edition_en_by_code[ed_spec["code"]]
                source = edition_en_by_code.get(src_code)
                if source and ed_en.source_edition_id != source.id:
                    ed_en.source_edition = source
                    ed_en.save_revision().publish()

            edition_th_by_code: dict[str, EditionPage] = {}
            for ed_spec in coll_spec["editions"]:
                ed_en = edition_en_by_code[ed_spec["code"]]
                ed_cover = self._cover(ed_spec.get("cover"), cover_cache, stats)
                ed_th = _get_or_copy_page(ed_en, th)
                if ed_th.get_parent().id != coll_th.id:
                    ed_th.move(coll_th, pos="last-child")
                    ed_th = EditionPage.objects.get(pk=ed_th.pk).specific
                    stats["moved"] += 1
                    self.stdout.write(
                        f"    moved edition {ed_spec['code']} (th) → {coll_th.code}"
                    )
                self._apply_edition_locale(
                    ed_th,
                    spec=ed_spec,
                    cover=ed_cover,
                    lang="th",
                    force=force,
                    country=coll_spec["country"],
                )
                edition_th_by_code[ed_spec["code"]] = ed_th
                stats["editions_th"] += 1

            for ed_spec in coll_spec["editions"]:
                src_code = ed_spec.get("source_edition")
                if not src_code:
                    continue
                ed_th = edition_th_by_code[ed_spec["code"]]
                source = edition_th_by_code.get(src_code)
                if source and ed_th.source_edition_id != source.id:
                    ed_th.source_edition = source
                    ed_th.save_revision().publish()

            self.stdout.write(
                f"  {coll_spec['code']}: "
                f"{coll_en.title} ({len(coll_spec['editions'])} editions)"
            )

        self._prune_removed_collections(catalog_en, catalog_th, stats)

        # Ensure Thai catalog parent stays published
        if not catalog_th.live:
            catalog_th.save_revision().publish()

        self.stdout.write(self.style.SUCCESS(f"Done: {stats}"))

    def _cover(self, key, cache, stats):
        if not key:
            return None
        if key in cache:
            return cache[key]
        path = COVERS_DIR / f"{key}.jpg"
        title = f"cover:{key}"
        existing = Image.objects.filter(title=title).first()
        if existing:
            cache[key] = existing
            return existing
        if not path.is_file():
            self.stdout.write(self.style.WARNING(f"Missing cover file: {path}"))
            cache[key] = None
            return None
        image = Image(title=title)
        with path.open("rb") as fh:
            image.file.save(f"catalog-covers/{key}.jpg", File(fh), save=True)
        stats["covers"] += 1
        cache[key] = image
        return image

    def _set_cover(self, page, cover, *, force=False):
        """Apply seed cover; keep a manually uploaded cover when seed has none."""
        if cover is not None:
            page.cover_image = cover
        elif force:
            page.cover_image = None

    def _upsert_collection(
        self,
        *,
        parent,
        locale,
        spec,
        classification,
        tradition,
        country,
        cover,
        lang,
        force,
    ):
        existing = (
            CollectionPage.objects.child_of(parent)
            .filter(locale=locale, code=spec["code"])
            .specific()
            .first()
        )
        if existing is None:
            for old_code in spec.get("former_codes") or ():
                existing = (
                    CollectionPage.objects.child_of(parent)
                    .filter(locale=locale, code=old_code)
                    .specific()
                    .first()
                )
                if existing is not None:
                    for page in existing.get_translations(inclusive=True).specific():
                        page.code = spec["code"]
                        page.slug = spec["code"]
                        page.save()
                    existing = CollectionPage.objects.get(pk=existing.pk).specific
                    self.stdout.write(
                        f"    renamed collection {old_code} → {spec['code']} "
                        f"({locale.language_code})"
                    )
                    break

        title = spec["title"][lang]
        body = _row_body(spec["body"][lang])
        search = spec["body"][lang]

        if existing is None:
            page = CollectionPage(
                title=title,
                code=spec["code"],
                slug=spec["code"],
                classification=classification,
                tradition=tradition,
                country=country,
                catalog_sort_order=spec["sort"],
                cover_image=cover,
                search_description=search[:500],
                locale=locale,
            )
            page.body = body
            parent.add_child(instance=page)
            page.save_revision().publish()
            return page, True

        needs = (
            force
            or existing.title != title
            or existing.code != spec["code"]
            or existing.slug != spec["code"]
            or existing.catalog_sort_order != spec["sort"]
            or existing.country_id != country.id
            or (cover is not None and existing.cover_image_id != getattr(cover, "pk", None))
        )
        if needs:
            existing.title = title
            existing.code = spec["code"]
            existing.slug = spec["code"]
            existing.classification = classification
            existing.tradition = tradition
            existing.country = country
            existing.catalog_sort_order = spec["sort"]
            self._set_cover(existing, cover, force=force)
            existing.body = body
            existing.search_description = search[:500]
            existing.save_revision().publish()
        return existing, False

    def _apply_collection_locale(
        self, page, *, spec, classification, tradition, country, cover, lang, force
    ):
        title = spec["title"][lang]
        body = _row_body(spec["body"][lang])
        search = spec["body"][lang]
        needs = (
            force
            or page.title != title
            or page.code != spec["code"]
            or page.slug != spec["code"]
            or page.classification_id != classification.id
            or page.country_id != country.id
            or page.catalog_sort_order != spec["sort"]
            or (cover is not None and page.cover_image_id != getattr(cover, "pk", None))
        )
        if needs:
            page.title = title
            page.code = spec["code"]
            page.slug = spec["code"]
            page.classification = classification
            page.tradition = tradition
            page.country = country
            page.catalog_sort_order = spec["sort"]
            self._set_cover(page, cover, force=force)
            page.body = body
            page.search_description = search[:500]
            page.save_revision().publish()

    def _upsert_edition(
        self, *, parent, locale, spec, cover, lang, force, source_edition, country=""
    ):
        # Edition codes are unique among siblings only (may repeat across
        # collections). Prefer child of target parent; otherwise rename via
        # former_codes (and move if that page lives under another collection).
        existing = (
            EditionPage.objects.child_of(parent)
            .filter(locale=locale, code=spec["code"])
            .specific()
            .first()
        )
        moved = False
        if existing is None:
            catalog = parent.get_parent().specific
            for old_code in spec.get("former_codes") or ():
                existing = (
                    EditionPage.objects.descendant_of(catalog)
                    .filter(locale=locale, code=old_code)
                    .specific()
                    .first()
                )
                if existing is not None:
                    for page in existing.get_translations(inclusive=True).specific():
                        page.code = spec["code"]
                        page.slug = spec["code"]
                        page.save()
                    existing = EditionPage.objects.get(pk=existing.pk).specific
                    self.stdout.write(
                        f"    renamed edition {old_code} → {spec['code']} "
                        f"({locale.language_code})"
                    )
                    break
            if existing is not None and existing.get_parent().id != parent.id:
                existing.move(parent, pos="last-child")
                existing = EditionPage.objects.get(pk=existing.pk).specific
                moved = True
                self.stdout.write(
                    f"    moved edition {spec['code']} → {parent.code}"
                )

        title = spec["title"][lang]
        description = f"<p>{spec['description'][lang]}</p>"
        pub = edition_publication_fields(spec, lang, country=country)

        if existing is None:
            page = EditionPage(
                title=title,
                code=spec["code"],
                slug=spec["code"],
                edition_role=spec["role"],
                source_edition=source_edition,
                publisher=pub["publisher"],
                place_of_publication=pub["place_of_publication"],
                published_year=pub["published_year"],
                print_number=pub["print_number"],
                volume_set_count=spec.get("volume_set_count"),
                physical_volume_count=spec.get("physical_volume_count"),
                catalog_sort_order=spec["sort"],
                cover_image=cover,
                description=description,
                search_description=spec["description"][lang][:500],
                locale=locale,
            )
            parent.add_child(instance=page)
            self._set_lang_script(page, spec, locale)
            page.save_revision().publish()
            return page, True, False

        needs = (
            force
            or existing.title != title
            or existing.code != spec["code"]
            or existing.slug != spec["code"]
            or existing.publisher != pub["publisher"]
            or existing.published_year != pub["published_year"]
            or existing.print_number != pub["print_number"]
            or existing.place_of_publication != pub["place_of_publication"]
            or existing.volume_set_count != spec.get("volume_set_count")
            or existing.physical_volume_count != spec.get("physical_volume_count")
            or (cover is not None and existing.cover_image_id != getattr(cover, "pk", None))
        )
        if needs:
            existing.title = title
            existing.code = spec["code"]
            existing.slug = spec["code"]
            existing.edition_role = spec["role"]
            existing.publisher = pub["publisher"]
            existing.place_of_publication = pub["place_of_publication"]
            existing.published_year = pub["published_year"]
            existing.print_number = pub["print_number"]
            existing.volume_set_count = spec.get("volume_set_count")
            existing.physical_volume_count = spec.get("physical_volume_count")
            existing.catalog_sort_order = spec["sort"]
            self._set_cover(existing, cover, force=force)
            existing.description = description
            existing.search_description = spec["description"][lang][:500]
            self._set_lang_script(existing, spec, locale)
            existing.save_revision().publish()
        return existing, False, moved

    def _prune_removed_collections(self, catalog_en, catalog_th, stats):
        keep_codes = {coll["code"] for coll in COLLECTIONS}
        for catalog in (catalog_en, catalog_th):
            for coll in (
                CollectionPage.objects.child_of(catalog).specific().iterator()
            ):
                if coll.code in keep_codes:
                    continue
                self.stdout.write(
                    self.style.WARNING(
                        f"  pruning collection {coll.code} ({coll.locale.language_code})"
                    )
                )
                coll.delete()
                stats["pruned"] += 1

    def _apply_edition_locale(self, page, *, spec, cover, lang, force, country=""):
        title = spec["title"][lang]
        description = f"<p>{spec['description'][lang]}</p>"
        pub = edition_publication_fields(spec, lang, country=country)
        needs = (
            force
            or page.title != title
            or page.code != spec["code"]
            or page.slug != spec["code"]
            or page.publisher != pub["publisher"]
            or page.published_year != pub["published_year"]
            or page.print_number != pub["print_number"]
            or page.place_of_publication != pub["place_of_publication"]
            or page.volume_set_count != spec.get("volume_set_count")
            or page.physical_volume_count != spec.get("physical_volume_count")
            or (cover is not None and page.cover_image_id != getattr(cover, "pk", None))
        )
        if needs:
            page.title = title
            page.code = spec["code"]
            page.slug = spec["code"]
            page.edition_role = spec["role"]
            page.publisher = pub["publisher"]
            page.place_of_publication = pub["place_of_publication"]
            page.published_year = pub["published_year"]
            page.print_number = pub["print_number"]
            page.volume_set_count = spec.get("volume_set_count")
            page.physical_volume_count = spec.get("physical_volume_count")
            page.catalog_sort_order = spec["sort"]
            self._set_cover(page, cover, force=force)
            page.description = description
            page.search_description = spec["description"][lang][:500]
            self._set_lang_script(page, spec, page.locale)
            page.save_revision().publish()

    def _set_lang_script(self, page, spec, locale):
        langs = [
            ContentLanguage.objects.get(locale=locale, code=code)
            for code in spec["languages"]
        ]
        scripts = [
            ContentScript.objects.get(locale=locale, code=code)
            for code in spec["scripts"]
        ]
        page.content_languages.set(langs)
        page.content_scripts.set(scripts)
