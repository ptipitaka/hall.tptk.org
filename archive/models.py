"""
Archive data models: high-volume scan + transcription data.

These are plain Django models (not Wagtail pages) because a corpus may hold
tens of thousands of scan folios and hundreds of thousands of segments — a
lifecycle unsuited to the page tree or Wagtail revisions. See
docs/archive/data_model_design.md §4–§7.
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify


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


class ScanFolio(models.Model):
    """
    A single preserved scan page within a volume.

    Files live on Spaces/CDN (or local media), not Wagtail Images.
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


class Segment(models.Model):
    """A transcribed unit of text anchored to a scan folio."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        REVIEW = "review", "Review"
        PUBLISHED = "published", "Published"

    volume = models.ForeignKey(
        "website.VolumePage",
        on_delete=models.PROTECT,
        related_name="segments",
    )
    order = models.IntegerField(help_text="Reading order within the volume.")
    kind = models.ForeignKey(
        "snippets.SegmentKind",
        on_delete=models.PROTECT,
        related_name="segments",
    )
    text = models.TextField()

    cref = models.CharField(
        max_length=128,
        db_index=True,
        help_text="Edition-independent canonical reference (e.g. sut.mn.1.2).",
    )
    cref_end = models.CharField(max_length=128, blank=True)
    structural_ref = models.CharField(
        max_length=128,
        blank=True,
        help_text="Edition's own printed numbering (e.g. VRI paragraph).",
    )
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="children",
    )

    # Anchor to the scan image
    folio = models.ForeignKey(
        ScanFolio,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="segments",
        help_text="Primary scan folio this text appears on.",
    )
    folio_end = models.ForeignKey(
        ScanFolio,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="segments_end",
    )
    region = models.JSONField(
        null=True,
        blank=True,
        help_text="Normalized bbox {x,y,w,h} (0–1). Required before publishing.",
    )
    region_note = models.CharField(max_length=255, blank=True)

    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    citation_key = models.CharField(
        max_length=64,
        help_text="Stable id for ?seg= links (unique within the volume).",
    )
    source_note = models.TextField(blank=True)

    class Meta:
        verbose_name = "segment"
        verbose_name_plural = "segments"
        ordering = ["volume", "order"]
        constraints = [
            models.UniqueConstraint(
                fields=["volume", "citation_key"],
                name="archive_segment_unique_volume_citation_key",
            ),
        ]
        indexes = [
            models.Index(fields=["cref"]),
            models.Index(fields=["volume", "order"]),
        ]

    def __str__(self) -> str:
        return f"{self.cref} ({self.citation_key})"

    def save(self, *args, **kwargs):
        if not self.citation_key and self.cref:
            self.citation_key = slugify(self.cref)
        super().save(*args, **kwargs)

    def clean(self) -> None:
        super().clean()
        # region + folio mandatory before a segment is served (review/published)
        if self.status in (self.Status.REVIEW, self.Status.PUBLISHED):
            if not self.region:
                raise ValidationError(
                    {"region": "A bounding-box region is required before publishing."}
                )
            if not self.folio_id:
                raise ValidationError(
                    {"folio": "A scan folio anchor is required before publishing."}
                )


class SegmentRevision(models.Model):
    """Edit history for a Segment (audit / four-eyes), separate from Wagtail."""

    segment = models.ForeignKey(
        Segment,
        on_delete=models.CASCADE,
        related_name="revisions",
    )
    text = models.TextField()
    kind = models.ForeignKey(
        "snippets.SegmentKind",
        on_delete=models.PROTECT,
        related_name="+",
    )
    cref = models.CharField(max_length=128)
    region = models.JSONField(null=True, blank=True)
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


class ReferenceAlias(models.Model):
    """Map a legacy citation (PTS/VRI/Thai/…) to our canonical reference."""

    class Scheme(models.TextChoices):
        PTS = "pts", "PTS"
        VRI = "vri", "VRI / CST"
        THAI_SIAM = "thai_siam", "Thai (Siam Rath)"
        MAHACHULA = "mahachula", "Mahāchulā"
        BURMESE_CS = "burmese_cs", "Burmese (Chaṭṭha Saṅgāyana)"
        SINHALA_BJT = "sinhala_bjt", "Sinhala (BJT)"

    scheme = models.CharField(max_length=32, choices=Scheme.choices)
    value = models.CharField(
        max_length=128,
        help_text="Normalized legacy citation string (e.g. M.i.1).",
    )
    cref = models.CharField(max_length=128, db_index=True)
    edition = models.ForeignKey(
        "website.EditionPage",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reference_aliases",
        help_text="Set when the scheme is edition-specific (e.g. a page number).",
    )
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "reference alias"
        verbose_name_plural = "reference aliases"
        ordering = ["scheme", "value"]
        constraints = [
            models.UniqueConstraint(
                fields=["scheme", "value", "edition"],
                name="archive_referencealias_unique_scheme_value_edition",
            ),
        ]
        indexes = [
            models.Index(fields=["cref"]),
        ]

    def __str__(self) -> str:
        return f"{self.scheme}:{self.value} → {self.cref}"
