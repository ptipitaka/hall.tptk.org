"""Create ScanFolio rows 1..N from a volume's declared page count.

One physical volume gets one set of rows on the default-locale VolumePage.
Other locales share that set. Does not probe Spaces.

Examples:
  docker compose exec web python manage.py generate_scan_folios \\
      --collection ch --edition pali2552ro --volume 1
  docker compose exec web python manage.py generate_scan_folios \\
      --all --replace --dry-run
  docker compose exec web python manage.py generate_scan_folios \\
      --all --replace
"""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from wagtail.models import Locale

from archive.models import (
    ScanFolio,
    declared_scan_folio_count,
    generate_scan_folio_rows,
    replace_scan_folio_rows,
    scan_owner_volume,
    scan_translation_volume_ids,
    set_declared_scan_folio_count,
)
from website.models import EditionPage, VolumePage


class Command(BaseCommand):
    help = (
        "Generate ScanFolio 1..N for catalog volumes from declared page count "
        "(default-locale volume only; other locales share the rows)."
    )

    def add_arguments(self, parser):
        parser.add_argument("--collection", help="Collection code (e.g. ch)")
        parser.add_argument("--edition", help="Edition code (e.g. pali2552ro)")
        parser.add_argument(
            "--all",
            action="store_true",
            dest="all_editions",
            help="Every default-locale edition with a declared page count.",
        )
        parser.add_argument(
            "--volume",
            type=int,
            action="append",
            dest="volumes",
            help="Limit to volume_index (repeatable). Default: all volumes under the edition.",
        )
        parser.add_argument(
            "--pages",
            type=int,
            default=None,
            help="Page count (sets scan_folio_count). Requires a single --volume.",
        )
        parser.add_argument(
            "--replace",
            action="store_true",
            help=(
                "Delete ScanFolio rows on every locale of the volume, then "
                "create 1..N on the default-locale owner."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report without writing ScanFolio rows.",
        )

    def handle(self, *args, **options):
        collection_code = options["collection"]
        edition_code = options["edition"]
        all_editions = options["all_editions"]
        volume_indexes = options["volumes"]
        forced_pages = options["pages"]
        replace = options["replace"]
        dry_run = options["dry_run"]

        if all_editions:
            if collection_code or edition_code:
                raise CommandError(
                    "--all cannot be combined with --collection/--edition"
                )
            if forced_pages is not None:
                raise CommandError("--pages cannot be combined with --all")
        elif not collection_code or not edition_code:
            raise CommandError("Pass --collection and --edition, or --all")

        targets = self._edition_targets(collection_code, edition_code)
        if not targets:
            raise CommandError("No matching default-locale live EditionPage")

        totals = {
            "editions": 0,
            "volumes": 0,
            "folios": 0,
            "created": 0,
            "existing": 0,
            "deleted": 0,
        }
        for collection_code, edition in targets:
            volumes = (
                VolumePage.objects.child_of(edition)
                .live()
                .specific()
                .order_by("volume_index")
            )
            if volume_indexes:
                volumes = volumes.filter(volume_index__in=volume_indexes)
            volumes = list(volumes)
            if not volumes:
                continue

            if forced_pages is not None and len(volumes) != 1:
                raise CommandError("--pages requires exactly one --volume")

            edition_used = False
            for volume in volumes:
                pages = forced_pages
                if pages is None:
                    pages = declared_scan_folio_count(volume)
                if pages < 1:
                    if not all_editions:
                        self.stdout.write(
                            self.style.WARNING(
                                f"  {volume.code}: no scan_folio_count — skipped"
                            )
                        )
                    continue

                owner = scan_owner_volume(volume)
                if not edition_used:
                    self.stdout.write(
                        f"Edition: {collection_code}/{edition.code} "
                        f"({edition.locale.language_code})"
                    )
                    edition_used = True
                    totals["editions"] += 1

                extra = ""
                if replace:
                    volume_ids = scan_translation_volume_ids(owner)
                    would_delete = ScanFolio.objects.filter(
                        volume_id__in=volume_ids
                    ).count()
                    extra = f" replace delete={would_delete}"

                self.stdout.write(
                    f"  {volume.code} (index={volume.volume_index}): {pages} pages "
                    f"owner_id={owner.pk} locale={owner.locale.language_code}{extra}"
                )
                totals["volumes"] += 1
                totals["folios"] += pages
                if dry_run:
                    if replace:
                        totals["deleted"] += would_delete
                    continue

                if forced_pages is not None:
                    set_declared_scan_folio_count(owner, forced_pages)

                if replace:
                    try:
                        deleted, created = replace_scan_folio_rows(
                            owner, pages, status=ScanFolio.Status.PRESENT
                        )
                    except ValidationError as exc:
                        raise CommandError(str(exc)) from exc
                    totals["deleted"] += deleted
                    totals["created"] += created
                else:
                    created, existing = generate_scan_folio_rows(owner, pages)
                    totals["created"] += created
                    totals["existing"] += existing

        if totals["volumes"] == 0:
            raise CommandError("No live volumes match the given filter.")

        verb = "Would generate" if dry_run else "Generated"
        extra = ""
        if not dry_run:
            extra = (
                f" (created={totals['created']}, existing={totals['existing']}"
                + (f", deleted={totals['deleted']}" if replace else "")
                + ")"
            )
        elif replace:
            extra = f" (would delete={totals['deleted']})"
        self.stdout.write(
            self.style.SUCCESS(
                f"{verb}: {totals['editions']} editions, {totals['volumes']} volumes, "
                f"{totals['folios']} folios{extra}"
            )
        )

    def _edition_targets(
        self, collection_code: str | None, edition_code: str | None
    ) -> list[tuple[str, EditionPage]]:
        default_locale = Locale.get_default()
        qs = EditionPage.objects.live().specific().select_related("locale")
        if edition_code:
            qs = qs.filter(code=edition_code)
        matched: list[tuple[str, EditionPage]] = []
        for ed in qs:
            if ed.locale_id != default_locale.pk:
                continue
            parent = ed.get_parent().specific
            parent_code = getattr(parent, "code", None)
            if not parent_code:
                continue
            if collection_code and parent_code != collection_code:
                continue
            matched.append((parent_code, ed))
        matched.sort(key=lambda item: (item[0], item[1].code))
        return matched
