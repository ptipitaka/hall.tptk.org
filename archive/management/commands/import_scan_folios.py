"""
Import ScanFolio rows for an edition from the public scan CDN (or Spaces).

Discovers page counts by probing HTTP HEAD on
  {SCAN_BASE_URL}/{SCAN_PREFIX}/{collection}/{edition}/{volume_index}/{n}.{ext}

Does not use book-viewer.json. Catalog VolumePage.code stays vol-01;
storage folders use volume_index (1, 2, …).

Examples:
  docker compose exec web python manage.py import_scan_folios \\
      --collection ch --edition pali2552ro --volume 1 --dry-run
  docker compose exec web python manage.py import_scan_folios \\
      --collection ch --edition pali2552ro
"""

from __future__ import annotations

import urllib.error
import urllib.request

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from archive.models import ScanFolio, build_scan_relative_path, _scan_root
from website.models import EditionPage, VolumePage


class Command(BaseCommand):
    help = "Import ScanFolio rows for a catalog edition from remote scan storage."

    def add_arguments(self, parser):
        parser.add_argument("--collection", required=True, help="Collection code (e.g. ch)")
        parser.add_argument("--edition", required=True, help="Edition code (e.g. pali2552ro)")
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
            help="Discover and report without writing ScanFolio rows.",
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
        volume_indexes = options["volumes"]
        forced_pages = options["pages"]
        dry_run = options["dry_run"]
        timeout = options["probe_timeout"]

        editions = list(
            EditionPage.objects.live()
            .specific()
            .filter(code=edition_code)
            .select_related("locale")
        )
        if not editions:
            raise CommandError(f"No live EditionPage with code={edition_code!r}")

        # Prefer default locale; still require matching collection parent.
        matched: list[EditionPage] = []
        for ed in editions:
            parent = ed.get_parent().specific
            if getattr(parent, "code", None) == collection_code:
                matched.append(ed)
        if not matched:
            raise CommandError(
                f"No edition {edition_code!r} under collection {collection_code!r}"
            )

        # Import for every locale tree (en, th, …) that shares the same codes.
        editions = sorted(matched, key=lambda e: e.locale.language_code)
        totals = {"created": 0, "updated": 0, "volumes": 0, "folios": 0}
        # Cache discovered page counts by volume_index (same files for all locales).
        page_counts: dict[int, int] = {}

        for edition in editions:
            self.stdout.write(
                f"Edition: {edition.title} ({edition.locale.language_code}) "
                f"id={edition.id}  scan root={_scan_root()}"
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

            for volume in volumes:
                pages = forced_pages
                if pages is None:
                    if volume.volume_index in page_counts:
                        pages = page_counts[volume.volume_index]
                    else:
                        existing_max = (
                            ScanFolio.objects.filter(volume=volume)
                            .order_by("-sequence")
                            .values_list("sequence", flat=True)
                            .first()
                        )
                        if existing_max:
                            pages = existing_max
                            self.stdout.write(
                                f"  Reusing existing folio count for "
                                f"volume_index={volume.volume_index}: {pages}"
                            )
                        else:
                            self.stdout.write(
                                f"  Discovering pages for volume_index={volume.volume_index} "
                                f"({volume.code}) …"
                            )
                            pages = self._discover_page_count(
                                collection_code,
                                edition_code,
                                volume.volume_index,
                                timeout=timeout,
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

                created, updated = self._upsert_folios(
                    volume,
                    collection_code,
                    edition_code,
                    pages,
                )
                totals["created"] += created
                totals["updated"] += updated

        verb = "Would import" if dry_run else "Imported"
        self.stdout.write(
            self.style.SUCCESS(
                f"{verb}: {totals['volumes']} volumes, {totals['folios']} folios"
                + (
                    f" (created={totals['created']}, updated={totals['updated']})"
                    if not dry_run
                    else ""
                )
            )
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
    ) -> int:
        """Binary search highest sequence with HTTP 200."""
        if not self._head_ok(
            self._object_url(collection_code, edition_code, volume_index, 1),
            timeout,
        ):
            return 0

        # Expand high bound
        low, high = 1, 1
        while self._head_ok(
            self._object_url(collection_code, edition_code, volume_index, high),
            timeout,
        ):
            low = high
            high *= 2
            if high > 100_000:
                raise CommandError(
                    f"Page discovery exceeded 100000 for volume_index={volume_index}"
                )

        # Binary search in (low, high)
        while low + 1 < high:
            mid = (low + high) // 2
            if self._head_ok(
                self._object_url(collection_code, edition_code, volume_index, mid),
                timeout,
            ):
                low = mid
            else:
                high = mid
        return low

    @transaction.atomic
    def _upsert_folios(
        self,
        volume: VolumePage,
        collection_code: str,
        edition_code: str,
        pages: int,
    ) -> tuple[int, int]:
        created = updated = 0
        for seq in range(1, pages + 1):
            _obj, was_created = ScanFolio.objects.update_or_create(
                volume=volume,
                sequence=seq,
                defaults={
                    "status": ScanFolio.Status.PRESENT,
                    "image_path": "",
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1
        return created, updated
