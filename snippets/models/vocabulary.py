"""Lookup snippets: Classification, Tradition, Country, ContentLanguage, ContentScript, SegmentKind."""

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify
from wagtail.admin.panels import FieldPanel
from snippets.models.base import (
    HallTranslatableMixin,
    VocabularyPanelsMixin,
    validate_same_locale_fk,
)


class Classification(HallTranslatableMixin, models.Model):
    """
    Scripture type (ติปิฏก / อฏฺฐกถา / ฏีกา / อญฺญา) with optional sub-tree.
    """

    siglum = models.CharField(
        max_length=8,
        blank=True,
        help_text="Short code such as TP, AK, TK, AN (not translated).",
    )
    slug = models.SlugField(max_length=64)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="children",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    sort_order = models.IntegerField(default=0)

    panels = [
        FieldPanel("siglum"),
        FieldPanel("slug"),
        FieldPanel("parent"),
        FieldPanel("title"),
        FieldPanel("description"),
        FieldPanel("sort_order"),
    ]

    class Meta(HallTranslatableMixin.Meta):
        verbose_name = "classification"
        verbose_name_plural = "classifications"
        ordering = ["sort_order", "slug"]
        constraints = [
            models.UniqueConstraint(
                fields=["locale", "slug"],
                name="snippets_classification_unique_locale_slug",
            ),
        ]

    def __str__(self) -> str:
        prefix = f"{self.siglum} · " if self.siglum else ""
        return f"{prefix}{self.title}"

    def clean(self) -> None:
        super().clean()
        validate_same_locale_fk(self, "parent", self.parent)
        if self.parent_id and self.parent_id == self.pk:
            raise ValidationError({"parent": "A classification cannot be its own parent."})


class Tradition(VocabularyPanelsMixin, HallTranslatableMixin, models.Model):
    """Buddhist tradition / school (นิกาย)."""

    code = models.CharField(max_length=32)
    slug = models.SlugField(max_length=64)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    sort_order = models.IntegerField(default=0)

    class Meta(HallTranslatableMixin.Meta):
        verbose_name = "tradition"
        verbose_name_plural = "traditions"
        ordering = ["sort_order", "code"]
        constraints = [
            models.UniqueConstraint(
                fields=["locale", "code"],
                name="snippets_tradition_unique_locale_code",
            ),
            models.UniqueConstraint(
                fields=["locale", "slug"],
                name="snippets_tradition_unique_locale_slug",
            ),
        ]


class Country(VocabularyPanelsMixin, HallTranslatableMixin, models.Model):
    """
    Country of a scripture collection (ประเทศของชุดคัมภีร์).

    Distinct from place of publication: e.g. Chaṭṭha Saṅgīti printed in Taiwan
    still belongs to Myanmar. ``code`` is usually ISO 3166-1 alpha-2 (lowercase);
    non-ISO codes such as ``tib`` (Tibet) are allowed when needed.
    """

    code = models.CharField(
        max_length=8,
        help_text="Country code (lowercase), usually ISO 3166-1 alpha-2; e.g. th, mm, tib.",
    )
    slug = models.SlugField(max_length=64)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    sort_order = models.IntegerField(default=0)

    class Meta(HallTranslatableMixin.Meta):
        verbose_name = "country"
        verbose_name_plural = "countries"
        ordering = ["sort_order", "code"]
        constraints = [
            models.UniqueConstraint(
                fields=["locale", "code"],
                name="snippets_country_unique_locale_code",
            ),
            models.UniqueConstraint(
                fields=["locale", "slug"],
                name="snippets_country_unique_locale_slug",
            ),
        ]

    @property
    def flag_static_path(self) -> str:
        """Static path to the SVG national flag (e.g. website/img/flags/th.svg)."""
        code = (self.code or "").lower()
        if not (2 <= len(code) <= 8 and code.isalpha()):
            return ""
        return f"website/img/flags/{code}.svg"


class ContentLanguage(VocabularyPanelsMixin, HallTranslatableMixin, models.Model):
    """Language of the source text (ภาษาข้อความ), not the site UI locale."""

    code = models.CharField(max_length=32)
    slug = models.SlugField(max_length=64)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    sort_order = models.IntegerField(default=0)

    class Meta(HallTranslatableMixin.Meta):
        verbose_name = "content language"
        verbose_name_plural = "content languages"
        ordering = ["sort_order", "code"]
        constraints = [
            models.UniqueConstraint(
                fields=["locale", "code"],
                name="snippets_contentlanguage_unique_locale_code",
            ),
            models.UniqueConstraint(
                fields=["locale", "slug"],
                name="snippets_contentlanguage_unique_locale_slug",
            ),
        ]


class ContentScript(VocabularyPanelsMixin, HallTranslatableMixin, models.Model):
    """Writing system of an edition (อักษร)."""

    code = models.CharField(max_length=32)
    slug = models.SlugField(max_length=64)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    sort_order = models.IntegerField(default=0)

    class Meta(HallTranslatableMixin.Meta):
        verbose_name = "content script"
        verbose_name_plural = "content scripts"
        ordering = ["sort_order", "code"]
        constraints = [
            models.UniqueConstraint(
                fields=["locale", "code"],
                name="snippets_contentscript_unique_locale_code",
            ),
            models.UniqueConstraint(
                fields=["locale", "slug"],
                name="snippets_contentscript_unique_locale_slug",
            ),
        ]


class SegmentKind(VocabularyPanelsMixin, HallTranslatableMixin, models.Model):
    """Layout role of a transcribed segment (structural, heading, prose, gāthā, …)."""

    code = models.CharField(max_length=32)
    slug = models.SlugField(max_length=64)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    sort_order = models.IntegerField(default=0)

    class Meta(HallTranslatableMixin.Meta):
        verbose_name = "segment kind"
        verbose_name_plural = "segment kinds"
        ordering = ["sort_order", "code"]
        constraints = [
            models.UniqueConstraint(
                fields=["locale", "code"],
                name="snippets_segmentkind_unique_locale_code",
            ),
            models.UniqueConstraint(
                fields=["locale", "slug"],
                name="snippets_segmentkind_unique_locale_slug",
            ),
        ]


class CanonicalSection(HallTranslatableMixin, models.Model):
    """
    Canonical scripture structure (piṭaka → nikāya → section …).

    Controlled vocabulary tree shared across editions. ``code`` is the stable,
    edition-independent identifier and a building block of a segment's ``cref``.
    """

    class Kind(models.TextChoices):
        PITAKA = "pitaka", "Piṭaka"
        NIKAYA = "nikaya", "Nikāya"
        SECTION = "section", "Section"

    code = models.CharField(
        max_length=32,
        help_text="Stable short code such as vin, sut, dn, mn. Building block of cref.",
    )
    slug = models.SlugField(max_length=64, blank=True)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="children",
    )
    kind = models.CharField(
        max_length=16,
        choices=Kind.choices,
        blank=True,
        help_text="Level of this node within the canonical tree.",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    sort_order = models.IntegerField(default=0)

    panels = [
        FieldPanel("code"),
        FieldPanel("slug"),
        FieldPanel("parent"),
        FieldPanel("kind"),
        FieldPanel("name"),
        FieldPanel("description"),
        FieldPanel("sort_order"),
    ]

    class Meta(HallTranslatableMixin.Meta):
        verbose_name = "canonical section"
        verbose_name_plural = "canonical sections"
        ordering = ["sort_order", "code"]
        constraints = [
            models.UniqueConstraint(
                fields=["locale", "code"],
                name="snippets_canonicalsection_unique_locale_code",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.code} · {self.name}"

    def clean(self) -> None:
        super().clean()
        validate_same_locale_fk(self, "parent", self.parent)
        if self.parent_id and self.parent_id == self.pk:
            raise ValidationError(
                {"parent": "A canonical section cannot be its own parent."}
            )

    def save(self, *args, **kwargs):
        if self.code and not self.slug:
            self.slug = slugify(self.code)
        super().save(*args, **kwargs)
