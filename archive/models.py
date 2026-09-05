"""
Archive data models: high-volume scan + transcription data.

These are plain Django models (not Wagtail pages) because a corpus may hold
tens of thousands of scan folios and hundreds of thousands of segments — a
lifecycle unsuited to the page tree or Wagtail revisions. See
docs/archive/data_model_design.md §4–§7.
"""

from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


def _scan_prefix() -> str:
    return getattr(settings, "SCAN_PREFIX", "tipitaka").strip("/")


def _scan_file_ext() -> str:
    return getattr(settings, "SCAN_FILE_EXT", "png").lstrip(".")


def _scan_root() -> str:
    """
    Base URL for scan files.

    Remote (default): {SCAN_BASE_URL}/{SCAN_PREFIX}
    Local fallback:   {MEDIA_URL}/{SCAN_PREFIX}
    """
    prefix = _scan_prefix()
    if getattr(settings, "SCAN_USE_REMOTE", True):
        base = getattr(settings, "SCAN_BASE_URL", "").rstrip("/")
        return f"{base}/{prefix}" if base else f"/{prefix}"
    return f"{settings.MEDIA_URL.rstrip('/')}/{prefix}"


def build_scan_relative_path(
    collection_code: str,
    edition_code: str,
    volume_index: int,
    sequence: int,
    *,
    ext: str | None = None,
) -> str:
    """
    Path under SCAN_PREFIX (no host).

    Catalog VolumePage.code stays vol-01; Spaces folder uses volume_index (1).
    """
    file_ext = (ext or _scan_file_ext()).lstrip(".")
    return (
        f"{collection_code}/{edition_code}/{volume_index}/{sequence}.{file_ext}"
    )


def scan_owner_volume(volume):
    """
    VolumePage that owns ScanFolio rows for this physical volume.

    One scan image is one row. Wagtail has an EN and TH VolumePage; rows
    attach only to the default-locale translation. Other locales read that set.
    """
    from wagtail.models import Locale

    volume = volume.specific
    default_locale = Locale.get_default()
    if volume.locale_id == default_locale.pk:
        return volume
    owner = volume.get_translation_or_none(default_locale)
    if owner is not None:
        return owner.specific
    return volume


def scan_folios_for(volume):
    """ScanFolio queryset for a volume page in any locale."""
    return ScanFolio.objects.filter(volume=scan_owner_volume(volume))


def declared_scan_folio_count(volume) -> int:
    """Declared page count: default-locale volume, then the given page."""
    owner = scan_owner_volume(volume)
    for page in (owner, volume):
        count = getattr(page, "scan_folio_count", None)
        if count:
            return int(count)
    return 0


def set_declared_scan_folio_count(volume, pages: int) -> bool:
    """
    Publish scan_folio_count on the default-locale volume.

    Returns True when the stored value changed. Other locales share this
    count via declared_scan_folio_count(); they are not written separately.
    """
    if pages < 1:
        raise ValueError("pages must be at least 1")
    owner = scan_owner_volume(volume)
    if owner.scan_folio_count == pages:
        return False
    owner.scan_folio_count = pages
    owner.save_revision().publish()
    return True


def generate_scan_folio_rows(volume, pages: int, *, status: str | None = None) -> tuple[int, int]:
    """Create ScanFolio 1..N on the owner volume. Does not delete extras."""
    if pages < 1:
        raise ValueError("pages must be at least 1")
    owner = scan_owner_volume(volume)
    row_status = status or ScanFolio.Status.PENDING
    created = existing = 0
    for seq in range(1, pages + 1):
        _obj, was_created = ScanFolio.objects.get_or_create(
            volume=owner,
            sequence=seq,
            defaults={"status": row_status, "image_path": ""},
        )
        if was_created:
            created += 1
        else:
            existing += 1
    return created, existing


def scan_translation_volume_ids(volume) -> list[int]:
    """Page ids of every UI locale of this physical volume."""
    owner = scan_owner_volume(volume)
    ids = list(owner.get_translations(inclusive=True).values_list("pk", flat=True))
    if owner.pk not in ids:
        ids.append(owner.pk)
    return ids


def replace_scan_folio_rows(
    volume, pages: int, *, status: str | None = None
) -> tuple[int, int]:
    """
    Delete ScanFolio rows on every locale of this volume, then create 1..N
    on the default-locale owner. Other locales share that set.

    Returns (deleted, created). Refuses if any Segment is attached.
    """
    if pages < 1:
        raise ValueError("pages must be at least 1")

    owner = scan_owner_volume(volume)
    volume_ids = scan_translation_volume_ids(owner)
    qs = ScanFolio.objects.filter(volume_id__in=volume_ids)
    folio_ids = list(qs.values_list("id", flat=True))
    if folio_ids and Segment.objects.filter(folio_id__in=folio_ids).exists():
        raise ValidationError(
            "Cannot replace ScanFolio rows while segments are attached."
        )
    deleted = qs.count()
    qs.delete()
    row_status = status or ScanFolio.Status.PRESENT
    ScanFolio.objects.bulk_create(
        [
            ScanFolio(
                volume=owner,
                sequence=seq,
                status=row_status,
                image_path="",
            )
            for seq in range(1, pages + 1)
        ],
        batch_size=500,
    )
    return deleted, pages


class ScanFolio(models.Model):
    """
    One preserved scan page of a physical volume (not per UI locale).

    Files live on Spaces/CDN (or local media), not Wagtail Images.
    Rows attach to the default-locale VolumePage; other locale pages share them.
    Derived path (when image_path is blank):
        {SCAN_PREFIX}/{collection.code}/{edition.code}/{volume_index}/{sequence}.{ext}
    Catalog page slug/code remains vol-01; storage folder uses volume_index.
    """

    class Status(models.TextChoices):
        PRESENT = "present", "Present"
        MISSING = "missing", "Missing"
        EXCLUDED = "excluded", "Excluded"
        PENDING = "pending", "Pending"

    volume = models.ForeignKey(
        "website.VolumePage",
        on_delete=models.PROTECT,
        related_name="scan_folios",
        help_text="Default-locale volume page; other locales share these rows.",
    )
    sequence = models.IntegerField(
        help_text="Physical order within the volume; used in path and nav.",
    )
    page_no = models.CharField(
        max_length=32,
        blank=True,
        help_text="Printed page label (may be non-numeric: 'ก', 'iv', '42').",
    )
    image_path = models.CharField(
        max_length=512,
        blank=True,
        help_text="Full path override; blank = derive from the composite codes.",
    )
    width = models.IntegerField(null=True, blank=True)
    height = models.IntegerField(null=True, blank=True)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PRESENT,
    )
    checksum = models.CharField(max_length=128, blank=True)
    iiif_id = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "scan folio"
        verbose_name_plural = "scan folios"
        ordering = ["volume", "sequence"]
        constraints = [
            models.UniqueConstraint(
                fields=["volume", "sequence"],
                name="archive_scanfolio_unique_volume_sequence",
            ),
        ]
        indexes = [
            models.Index(fields=["volume", "sequence"]),
        ]

    def __str__(self) -> str:
        return f"{self.volume_id}:{self.sequence}"

    @property
    def relative_path(self) -> str:
        """Path under SCAN_PREFIX for this folio (no leading host)."""
        if self.image_path:
            return self.image_path.lstrip("/")
        volume = self.volume.specific
        edition = volume.get_parent().specific
        collection = edition.get_parent().specific
        return build_scan_relative_path(
            collection.code,
            edition.code,
            volume.volume_index,
            self.sequence,
        )

    @property
    def image_url(self) -> str:
        return f"{_scan_root()}/{self.relative_path}"

    @property
    def has_scan_image(self) -> bool:
        """True when a scan file is expected (status present)."""
        return self.status == self.Status.PRESENT

    @property
    def folio_label(self) -> str:
        """Printed page no. when set, otherwise the physical sequence."""
        return self.page_no or str(self.sequence)


class Segment(models.Model):
    """
    One transcribed unit of a volume, anchored to a scan folio.

    The row mirrors a unit of the extract pipeline (one printed-page unit; a
    paragraph that flows to the next page is a separate ``prose_continuation``
    row, not a single row with ``folio_end``). There is no cross-edition
    canonical reference (``cref``) and no single ``text`` string: the rich,
    multi-script / multi-run / gāthā body lives in ``content`` as the extract
    payload, with flat ``plain_roman`` / ``plain_thai`` columns for search and
    listing. ``region`` binds a bounding box to this segment; its viewer use is
    designed later.
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        REVIEW = "review", "Review"
        PUBLISHED = "published", "Published"

    volume = models.ForeignKey(
        "website.VolumePage",
        on_delete=models.PROTECT,
        related_name="segments",
    )
    folio = models.ForeignKey(
        ScanFolio,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="segments",
        help_text="Scan folio this unit sits on. May be empty on draft import.",
    )
    order = models.IntegerField(
        help_text="Reading order within the volume; unique. Matches extract `order`.",
    )
    kind = models.ForeignKey(
        "snippets.SegmentKind",
        on_delete=models.PROTECT,
        related_name="segments",
        help_text="Structural kind; code matches extract `segment_type` 1:1.",
    )
    item = models.IntegerField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Edition's printed item number (Tipiṭaka item). Null for headings/gāthā.",
    )
    section_no = models.IntegerField(
        null=True,
        blank=True,
        help_text="Outline number printed before a heading (e.g. `1` in `1. Pārājikakaṇḍa`).",
    )

    # Source of truth for the unit body: the extract payload (text[] / bats /
    # hanging_lines / notes / symbol_notes / flags / heading_kind / in_toc /
    # source_layout / closer_level / needs_review / review_reasons). Not edited
    # as a flat string; the staff form (planned Digital archive menu) edits
    # this structure per folio.
    content = models.JSONField(
        default=dict,
        blank=True,
        help_text="Extract payload — multi-script text[], bats, notes, flags, …",
    )
    plain_roman = models.TextField(
        blank=True,
        help_text="Flat Roman text derived from content for search/listing. Not source.",
    )
    plain_thai = models.TextField(
        blank=True,
        help_text="Flat Thai text derived from content for search/listing. Not source.",
    )

    region = models.JSONField(
        null=True,
        blank=True,
        help_text="Per-segment bbox {x,y,w,h} (0–1) on the folio image. Designed later.",
    )

    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "segment"
        verbose_name_plural = "segments"
        ordering = ["volume", "order"]
        constraints = [
            models.UniqueConstraint(
                fields=["volume", "order"],
                name="archive_segment_unique_volume_order",
            ),
        ]
        indexes = [
            models.Index(fields=["volume", "order"]),
            models.Index(fields=["item"]),
            models.Index(fields=["kind"]),
        ]

    def __str__(self) -> str:
        return f"{self.volume_id}:{self.order}"

    def clean(self) -> None:
        super().clean()
        # folio + region are mandatory before a segment is served. Draft rows
        # imported from extract may lack both until the region viewer lands.
        if self.status in (self.Status.REVIEW, self.Status.PUBLISHED):
            if not self.folio_id:
                raise ValidationError(
                    {"folio": "A scan folio anchor is required before publishing."}
                )
            if not self.region:
                raise ValidationError(
                    {"region": "A bounding-box region is required before publishing."}
                )


class SegmentRevision(models.Model):
    """Edit history for a Segment (audit / four-eyes), separate from Wagtail."""

    segment = models.ForeignKey(
        Segment,
        on_delete=models.CASCADE,
        related_name="revisions",
    )
    content = models.JSONField(default=dict, blank=True)
    kind = models.ForeignKey(
        "snippets.SegmentKind",
        on_delete=models.PROTECT,
        related_name="+",
    )
    item = models.IntegerField(null=True, blank=True)
    section_no = models.IntegerField(null=True, blank=True)
    region = models.JSONField(null=True, blank=True)
    status = models.CharField(
        max_length=16, choices=Segment.Status.choices, default=Segment.Status.DRAFT
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="segment_revisions",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    change_note = models.CharField(max_length=255, blank=True)
    is_current = models.BooleanField(default=False)

    class Meta:
        verbose_name = "segment revision"
        verbose_name_plural = "segment revisions"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["segment", "is_current"]),
        ]

    def __str__(self) -> str:
        return f"rev of {self.segment_id} @ {self.created_at:%Y-%m-%d %H:%M}"
