"""
Import ScanFolio rows for an edition from the public scan CDN (or Spaces).

Discovers page counts by probing HTTP HEAD on
  {SCAN_BASE_URL}/{SCAN_PREFIX}/{collection}/{edition}/{volume_index}/{n}.{ext}

Does not use book-viewer.json. Writes rows only on the default-locale
VolumePage (one scan image = one ScanFolio). Catalog VolumePage.code stays
vol-01; storage folders use volume_index (1, 2, …).

Examples:
  docker compose exec web python manage.py import_scan_folios \\
      --collection ch --edition pali2552ro --volume 1 --dry-run
  docker compose exec web python manage.py import_scan_folios \\
      --all --rediscover --count-only
"""

from __future__ import annotations

import urllib.error
import urllib.request

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from archive.models import (
    ScanFolio,
    build_scan_relative_path,
    _scan_root,
    generate_scan_folio_rows,
    scan_folios_for,
    scan_owner_volume,
    set_declared_scan_folio_count,
)
from website.models import EditionPage, VolumePage
from wagtail.models import Locale


class Command(BaseCommand):
    help = "Import ScanFolio rows for a catalog edition from remote scan storage."

    def add_arguments(self, parser):
        parser.add_argument("--collection", help="Collection code (e.g. ch)")
        parser.add_argument("--edition", help="Edition code (e.g. pali2552ro)")
        parser.add_argument(
            "--all",
            action="store_true",
            dest="all_editions",
            help="Every default-locale edition that has remote scans (or existing rows).",
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
            help="Force page count (skip discovery). Useful with a single --volume.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Discover and report without writing ScanFolio rows or counts.",
        )
        parser.add_argument(
            "--rediscover",
            action="store_true",
            help="Probe storage even when ScanFolio rows already exist.",
        )
        parser.add_argument(
            "--count-only",
            action="store_true",
            help="Write VolumePage.scan_folio_count only; do not create ScanFolio rows.",
        )
        parser.add_argument(
            "--probe-timeout",
            type=float,
            default=8.0,
            help="HTTP timeout seconds for HEAD probes (default 8).",
        )

    def handle(self, *args, **options):
        collection_code = options["collection"]
        edition_code = options["edition"]
        all_editions = options["all_editions"]
        volume_indexes = options["volumes"]
        forced_pages = options["pages"]
        dry_run = options["dry_run"]
        rediscover = options["rediscover"]
        count_only = options["count_only"]
        timeout = options["probe_timeout"]

        if all_editions:
            if collection_code or edition_code:
                raise CommandError("--all cannot be combined with --collection/--edition")
            if forced_pages is not None:
                raise CommandError("--pages cannot be combined with --all")
        elif not collection_code or not edition_code:
            raise CommandError("Pass --collection and --edition, or --all")

        targets = self._edition_targets(collection_code, edition_code)
        if not targets:
            raise CommandError("No matching default-locale live EditionPage")

        totals = {
            "created": 0,
            "updated": 0,
            "volumes": 0,
            "folios": 0,
            "counts_updated": 0,
            "editions": 0,
        }

        for collection_code, edition in targets:
            if all_editions and not self._edition_has_scans(
                collection_code, edition, timeout=timeout
            ):
                self.stdout.write(
                    f"Skip {collection_code}/{edition.code}: no remote scans"
                )
                continue

            totals["editions"] += 1
            self.stdout.write(
                f"Edition: {collection_code}/{edition.code} {edition.title} "
                f"({edition.locale.language_code}) id={edition.id}  "
                f"scan root={_scan_root()}"
            )

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
                self.stdout.write(
                    self.style.WARNING(
                        f"  No volumes under locale {edition.locale.language_code}"
                    )
                )
                continue

            if forced_pages is not None and len(volumes) != 1:
                raise CommandError("--pages requires exactly one --volume")

            page_counts: dict[int, int] = {}
            for volume in volumes:
                pages = forced_pages
                if pages is None:
                    if volume.volume_index in page_counts:
                        pages = page_counts[volume.volume_index]
                    else:
                        existing_max = (
                            scan_folios_for(volume)
                            .order_by("-sequence")
                            .values_list("sequence", flat=True)
                            .first()
                        )
                        if existing_max and not rediscover:
                            pages = existing_max
                            self.stdout.write(
                                f"  Reusing existing folio count for "
                                f"volume_index={volume.volume_index}: {pages}"
                            )
                        else:
                            self.stdout.write(
                                f"  Discovering pages for volume_index="
                                f"{volume.volume_index} ({volume.code}) …"
                            )
                            pages = self._discover_page_count(
                                collection_code,
                                edition.code,
                                volume.volume_index,
                                timeout=timeout,
                                hint=existing_max,
                            )
                        page_counts[volume.volume_index] = pages
                if pages <= 0:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  {volume.code}: no pages found — skipped"
                        )
                    )
                    continue

                self.stdout.write(
                    f"  [{edition.locale.language_code}] {volume.code} "
                    f"(index={volume.volume_index}): {pages} pages"
                )
                totals["volumes"] += 1
                totals["folios"] += pages

                if dry_run:
                    continue

                if set_declared_scan_folio_count(volume, pages):
                    totals["counts_updated"] += 1
                    self.stdout.write(f"    scan_folio_count={pages}")
                else:
                    self.stdout.write(
                        f"    scan_folio_count unchanged ({pages})"
                    )

                if count_only:
                    continue

                created, updated = self._upsert_folios(volume, pages)
                totals["created"] += created
                totals["updated"] += updated

        verb = "Would import" if dry_run else "Imported"
        extra = ""
        if not dry_run:
            extra = (
                f" (created={totals['created']}, updated={totals['updated']}, "
                f"counts_updated={totals['counts_updated']})"
            )
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

    def _edition_has_scans(
        self, collection_code: str, edition: EditionPage, *, timeout: float
    ) -> bool:
        volume_ids = VolumePage.objects.child_of(edition).values_list("id", flat=True)
        if ScanFolio.objects.filter(volume_id__in=volume_ids).exists():
            return True
        return self._head_ok(
            self._object_url(collection_code, edition.code, 1, 1), timeout
        )

    def _object_url(
        self, collection_code: str, edition_code: str, volume_index: int, sequence: int
    ) -> str:
        rel = build_scan_relative_path(
            collection_code, edition_code, volume_index, sequence
        )
        return f"{_scan_root()}/{rel}"

    def _head_ok(self, url: str, timeout: float) -> bool:
        req = urllib.request.Request(url, method="HEAD")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return 200 <= getattr(resp, "status", 200) < 300
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return False
            # Some CDNs reject HEAD — fall back to ranged GET
            if exc.code in (403, 405):
                return self._range_ok(url, timeout)
            raise
        except urllib.error.URLError:
            return self._range_ok(url, timeout)

    def _range_ok(self, url: str, timeout: float) -> bool:
        req = urllib.request.Request(
            url, headers={"Range": "bytes=0-0"}, method="GET"
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return 200 <= getattr(resp, "status", 200) < 300
        except urllib.error.HTTPError as exc:
            return False if exc.code == 404 else False
        except urllib.error.URLError:
            return False

    def _discover_page_count(
        self,
        collection_code: str,
        edition_code: str,
        volume_index: int,
        *,
        timeout: float,
        hint: int | None = None,
    ) -> int:
        """Binary search highest sequence with HTTP 200."""

        def exists(sequence: int) -> bool:
            return self._head_ok(
                self._object_url(
                    collection_code, edition_code, volume_index, sequence
                ),
                timeout,
            )

        def search(low: int, high: int) -> int:
            while low + 1 < high:
                mid = (low + high) // 2
                if exists(mid):
                    low = mid
                else:
                    high = mid
            return low

        if hint and hint >= 1:
            if exists(hint):
                if not exists(hint + 1):
                    return hint
                low, high = hint, hint
                while exists(high):
                    low = high
                    high *= 2
                    if high > 100_000:
                        raise CommandError(
                            f"Page discovery exceeded 100000 for "
                            f"volume_index={volume_index}"
                        )
                return search(low, high)
            if exists(1):
                return search(1, hint)

        if not exists(1):
            return 0

        # Expand high bound
        low, high = 1, 1
        while exists(high):
            low = high
            high *= 2
            if high > 100_000:
                raise CommandError(
                    f"Page discovery exceeded 100000 for volume_index={volume_index}"
                )
        return search(low, high)

    @transaction.atomic
    def _upsert_folios(self, volume: VolumePage, pages: int) -> tuple[int, int]:
        owner = scan_owner_volume(volume)
        created, existing = generate_scan_folio_rows(
            owner, pages, status=ScanFolio.Status.PRESENT
        )
        return created, existing
