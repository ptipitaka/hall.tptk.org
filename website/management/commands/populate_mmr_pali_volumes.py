"""
Create/update the shared 45 VolumePages under Syāmaraṭṭhassa Pāli editions
(pali2538, pali2556, pali2560) for EN and TH.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction
from wagtail.models import Locale

from snippets.models import CanonicalSection
from website.catalog_content import _get_or_copy_page, _remap_snippet
from website.catalog_lookup import get_edition_page
from website.mmr_pali_volumes import (
    MMR_PALI_EDITIONS,
    MMR_PALI_VOLUMES,
    thai_digits,
    volume_code,
)
from website.models import EditionPage, VolumePage


class Command(BaseCommand):
    help = (
        "Populate the shared 45-volume list on Syāmaraṭṭhassa tepiṭakaṃ "
        "Pāli editions (4th/7th/8th printing) and Dayyaraṭṭha pali2549, EN + TH."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Overwrite titles/section/number when volumes already exist.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        force = options["force"]
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
        stats = {"created": 0, "updated": 0, "skipped": 0}

        for collection_code, edition_code in MMR_PALI_EDITIONS:
            try:
                edition_en = get_edition_page(
                    locale=en,
                    collection_code=collection_code,
                    edition_code=edition_code,
                )
            except EditionPage.DoesNotExist as exc:
                raise SystemExit(
                    f"Missing English EditionPage "
                    f"{collection_code}/{edition_code}."
                ) from exc

            edition_th = _get_or_copy_page(edition_en, th)
            self.stdout.write(f"{collection_code}/{edition_code}:")

            for vol_spec in MMR_PALI_VOLUMES:
                code = volume_code(vol_spec["index"])
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
                f"skipped={stats['skipped']}"
            )
        )

    def _upsert_volume(
        self, *, parent, locale, lang, code, vol_spec, section, force, stats
    ) -> bool:
        """Return True if created or updated."""
        existing = (
            VolumePage.objects.child_of(parent)
            .filter(locale=locale, code=code)
            .specific()
            .first()
        )
        title = vol_spec["title"][lang]
        number = str(vol_spec["index"]) if lang == "en" else thai_digits(vol_spec["index"])
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
        number = str(vol_spec["index"]) if lang == "en" else thai_digits(vol_spec["index"])
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
