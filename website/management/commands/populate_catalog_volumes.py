"""
Create/update VolumePages for Theravāda catalog editions whose lists live in
``website.catalog_volume_sets`` (extracted from tipitaka-catalog TeX).
"""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction
from wagtail.models import Locale

from snippets.models import CanonicalSection
from website.catalog_content import _get_or_copy_page, _remap_snippet
from website.catalog_lookup import get_edition_page
from website.catalog_volume_sets import (
    CATALOG_VOLUME_SETS,
    thai_digits,
    volume_code,
)
from website.models import EditionPage, VolumePage


def _default_edition_keys() -> list[tuple[str, str]]:
    return sorted(CATALOG_VOLUME_SETS)


def _parse_edition_arg(raw: str) -> tuple[str, str] | None:
    """Accept ``collection/edition`` or a unique edition code."""
    if "/" in raw:
        collection_code, edition_code = raw.split("/", 1)
        key = (collection_code, edition_code)
        return key if key in CATALOG_VOLUME_SETS else None
    matches = [key for key in CATALOG_VOLUME_SETS if key[1] == raw]
    if len(matches) == 1:
        return matches[0]
    return None


class Command(BaseCommand):
    help = (
        "Populate VolumePages for Theravāda editions defined in "
        "catalog_volume_sets (MCU, Thai translations, Lao, PTS, etc.)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Overwrite titles/section/number when volumes already exist.",
        )
        labels = ", ".join(f"{c}/{e}" for c, e in _default_edition_keys())
        parser.add_argument(
            "--edition",
            action="append",
            dest="editions",
            help=(
                "Edition to populate as ``collection/edition`` or unique edition "
                f"code (repeatable). Default: all of {labels}."
            ),
        )

    @transaction.atomic
    def handle(self, *args, **options):
        force = options["force"]
        if options["editions"]:
            edition_keys: list[tuple[str, str]] = []
            for raw in options["editions"]:
                key = _parse_edition_arg(raw)
                if key is None:
                    self.stdout.write(
                        self.style.WARNING(
                            f"skip unknown edition {raw!r} "
                            "(use collection/edition; see CATALOG_VOLUME_SETS)"
                        )
                    )
                    continue
                edition_keys.append(key)
        else:
            edition_keys = _default_edition_keys()
        en = Locale.objects.get(language_code="en")
        th = Locale.objects.get(language_code="th")

        if CanonicalSection.objects.filter(locale=en).count() == 0:
            raise SystemExit(
                "No CanonicalSection rows. Run: "
                "python manage.py seed_catalog_reference"
            )

        sections_en = {
            s.code: s for s in CanonicalSection.objects.filter(locale=en)
        }
        stats = {
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "deleted": 0,
            "missing_editions": 0,
        }

        for collection_code, edition_code in edition_keys:
            volumes = CATALOG_VOLUME_SETS[(collection_code, edition_code)]

            try:
                edition_en = get_edition_page(
                    locale=en,
                    collection_code=collection_code,
                    edition_code=edition_code,
                )
            except EditionPage.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(
                        f"skip missing edition {collection_code}/{edition_code}"
                    )
                )
                stats["missing_editions"] += 1
                continue

            edition_th = _get_or_copy_page(edition_en, th)
            published_n = sum(1 for v in volumes if not v.get("not_published"))
            self.stdout.write(
                f"{collection_code}/{edition_code} "
                f"({published_n} vols"
                + (
                    f", {len(volumes) - published_n} list-only"
                    if published_n != len(volumes)
                    else ""
                )
                + "):"
            )

            for vol_spec in volumes:
                code = volume_code(vol_spec["index"])
                if vol_spec.get("not_published"):
                    for edition in (edition_en, edition_th):
                        existing = (
                            VolumePage.objects.child_of(edition)
                            .filter(code=code)
                            .specific()
                            .first()
                        )
                        if existing is not None:
                            existing.delete()
                            stats["deleted"] += 1
                            self.stdout.write(
                                f"  - {edition.locale.language_code} {code} "
                                "(not published)"
                            )
                    continue
                section_en = sections_en[vol_spec["section"]]
                created_or_updated = self._upsert_volume(
                    parent=edition_en,
                    locale=en,
                    lang="en",
                    code=code,
                    vol_spec=vol_spec,
                    section=section_en,
                    force=force,
                    stats=stats,
                )
                vol_en = (
                    VolumePage.objects.child_of(edition_en)
                    .filter(locale=en, code=code)
                    .specific()
                    .get()
                )
                vol_th = _get_or_copy_page(vol_en, th)
                section_th = _remap_snippet(section_en, CanonicalSection, th)
                self._apply_locale(
                    vol_th,
                    lang="th",
                    vol_spec=vol_spec,
                    section=section_th,
                    force=force or created_or_updated,
                    stats=stats,
                )

            self.stdout.write(
                f"  EN children={VolumePage.objects.child_of(edition_en).count()} "
                f"TH children={VolumePage.objects.child_of(edition_th).count()}"
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. created={stats['created']} updated={stats['updated']} "
                f"skipped={stats['skipped']} deleted={stats['deleted']} "
                f"missing_editions={stats['missing_editions']}"
            )
        )

    def _upsert_volume(
        self, *, parent, locale, lang, code, vol_spec, section, force, stats
    ) -> bool:
        existing = (
            VolumePage.objects.child_of(parent)
            .filter(locale=locale, code=code)
            .specific()
            .first()
        )
        title = vol_spec["title"][lang]
        number_src = vol_spec.get("catalog_no", vol_spec["index"])
        number = str(number_src) if lang == "en" else thai_digits(number_src)
        index = vol_spec["index"]

        if existing is None:
            page = VolumePage(
                title=title,
                code=code,
                slug=code,
                volume_index=index,
                number=number,
                section=section,
                locale=locale,
            )
            parent.add_child(instance=page)
            page.save_revision().publish()
            stats["created"] += 1
            self.stdout.write(f"  + {locale.language_code} {code}")
            return True

        needs = (
            force
            or existing.title != title
            or existing.volume_index != index
            or existing.number != number
            or existing.section_id != section.id
        )
        if needs:
            existing.title = title
            existing.volume_index = index
            existing.number = number
            existing.section = section
            existing.save_revision().publish()
            stats["updated"] += 1
            return True

        stats["skipped"] += 1
        return False

    def _apply_locale(self, page, *, lang, vol_spec, section, force, stats):
        title = vol_spec["title"][lang]
        number_src = vol_spec.get("catalog_no", vol_spec["index"])
        number = str(number_src) if lang == "en" else thai_digits(number_src)
        index = vol_spec["index"]
        needs = (
            force
            or page.title != title
            or page.volume_index != index
            or page.number != number
            or page.section_id != getattr(section, "id", None)
        )
        if needs:
            page.title = title
            page.volume_index = index
            page.number = number
            page.section = section
            page.save_revision().publish()
            stats["updated"] += 1
        else:
            stats["skipped"] += 1
