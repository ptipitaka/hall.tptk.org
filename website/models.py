"""
Create or customize your page models here.
"""

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal

from django import forms
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from coderedcms.forms import CoderedFormField
from coderedcms.models import CoderedArticleIndexPage
from coderedcms.models import CoderedArticlePage
from coderedcms.models import CoderedEmail
from coderedcms.models import CoderedEventIndexPage
from coderedcms.models import CoderedEventOccurrence
from coderedcms.models import CoderedEventPage
from coderedcms.models import CoderedFormPage
from coderedcms.models import CoderedLocationIndexPage
from coderedcms.models import CoderedLocationPage
from coderedcms.models import CoderedWebPage
from modelcluster.fields import ParentalKey, ParentalManyToManyField
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail.contrib.routable_page.models import RoutablePageMixin, path
from wagtail.fields import RichTextField, StreamField
from wagtail.images import get_image_model_string
from wagtail.models import Orderable, Page

from website.streamblocks import LAYOUT_STREAMBLOCKS
from website.visual_design import VisualDesignPageMixin
from website.catalog_forms import (
    CollectionPageForm,
    EditionPageForm,
    VolumePageForm,
)


class ArticlePage(CoderedArticlePage):
    """
    Article, suitable for news or blog content.
    """

    class Meta:
        verbose_name = "Article"
        ordering = ["-first_published_at"]

    # Only allow this page to be created beneath an ArticleIndexPage.
    parent_page_types = ["website.ArticleIndexPage"]

    template = "coderedcms/pages/article_page.html"
    search_template = "coderedcms/pages/article_page.search.html"


class ArticleIndexPage(CoderedArticleIndexPage):
    """
    Shows a list of article sub-pages.
    """

    class Meta:
        verbose_name = "Article Landing Page"

    # Override to specify custom index ordering choice/default.
    index_query_pagemodel = "website.ArticlePage"

    # Only allow ArticlePages beneath this page.
    subpage_types = ["website.ArticlePage"]

    template = "coderedcms/pages/article_index_page.html"


class EventPage(CoderedEventPage):
    class Meta:
        verbose_name = "Event Page"

    parent_page_types = ["website.EventIndexPage"]
    template = "coderedcms/pages/event_page.html"


class EventIndexPage(CoderedEventIndexPage):
    """
    Shows a list of event sub-pages.
    """

    class Meta:
        verbose_name = "Events Landing Page"

    index_query_pagemodel = "website.EventPage"

    # Only allow EventPages beneath this page.
    subpage_types = ["website.EventPage"]

    template = "coderedcms/pages/event_index_page.html"


class EventOccurrence(CoderedEventOccurrence):
    event = ParentalKey(EventPage, related_name="occurrences")


class FormPage(CoderedFormPage):
    """
    A page with an html <form>.
    """

    class Meta:
        verbose_name = "Form"

    template = "coderedcms/pages/form_page.html"


class FormPageField(CoderedFormField):
    """
    A field that links to a FormPage.
    """

    class Meta:
        ordering = ["sort_order"]

    page = ParentalKey("FormPage", related_name="form_fields")


class FormConfirmEmail(CoderedEmail):
    """
    Sends a confirmation email after submitting a FormPage.
    """

    page = ParentalKey("FormPage", related_name="confirmation_emails")


class LocationPage(CoderedLocationPage):
    """
    A page that holds a location.  This could be a store, a restaurant, etc.
    """

    class Meta:
        verbose_name = "Location Page"

    template = "coderedcms/pages/location_page.html"

    # Only allow LocationIndexPages above this page.
    parent_page_types = ["website.LocationIndexPage"]


class LocationIndexPage(CoderedLocationIndexPage):
    """
    A page that holds a list of locations and displays them with a Google Map.
    This does require a Google Maps API Key in Settings > CRX Settings
    """

    class Meta:
        verbose_name = "Location Landing Page"

    # Override to specify custom index ordering choice/default.
    index_query_pagemodel = "website.LocationPage"

    # Only allow LocationPages beneath this page.
    subpage_types = ["website.LocationPage"]

    template = "coderedcms/pages/location_index_page.html"


class ScrollBackgroundPageMixin(models.Model):
    """Shared scroll-driven crossfade background fields for page models."""

    scroll_bg_opacity = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=Decimal("0.20"),
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        verbose_name="Scroll background opacity",
        help_text=(
            "Maximum opacity when a background is fully visible (0.0–1.0). "
            "For example, 0.4 = 40%."
        ),
    )

    class Meta:
        abstract = True

    @property
    def scroll_background_enabled(self):
        return self.scroll_backgrounds.exists()


SCROLL_BACKGROUND_PANEL = MultiFieldPanel(
    [
        FieldPanel("scroll_bg_opacity"),
        InlinePanel(
            "scroll_backgrounds",
            label="Background images",
            help_text=(
                "Optional. Add one or more images; they crossfade on scroll "
                "in this order. Leave empty to disable the effect."
            ),
            min_num=0,
        ),
    ],
    heading="Scroll background",
)


class ScrollBackgroundImageBase(Orderable):
    """Inline child row: one full-viewport background layer (fade order = sort order)."""

    image = models.ForeignKey(
        get_image_model_string(),
        on_delete=models.CASCADE,
        related_name="+",
        verbose_name="Background image",
    )

    panels = [FieldPanel("image")]

    class Meta(Orderable.Meta):
        abstract = True
        verbose_name = "scroll background image"
        verbose_name_plural = "scroll background images"


class WebPageScrollBackground(ScrollBackgroundImageBase):
    page = ParentalKey(
        "website.WebPage",
        on_delete=models.CASCADE,
        related_name="scroll_backgrounds",
    )


class CollectionPageScrollBackground(ScrollBackgroundImageBase):
    page = ParentalKey(
        "website.CollectionPage",
        on_delete=models.CASCADE,
        related_name="scroll_backgrounds",
    )


class CatalogIndexPageScrollBackground(ScrollBackgroundImageBase):
    page = ParentalKey(
        "website.CatalogIndexPage",
        on_delete=models.CASCADE,
        related_name="scroll_backgrounds",
    )


class EditionPageScrollBackground(ScrollBackgroundImageBase):
    page = ParentalKey(
        "website.EditionPage",
        on_delete=models.CASCADE,
        related_name="scroll_backgrounds",
    )


class VolumePageScrollBackground(ScrollBackgroundImageBase):
    page = ParentalKey(
        "website.VolumePage",
        on_delete=models.CASCADE,
        related_name="scroll_backgrounds",
    )


class WebPage(ScrollBackgroundPageMixin, VisualDesignPageMixin, CoderedWebPage):
    """
    General use page with featureful streamfield and SEO attributes.
    """

    body = StreamField(
        LAYOUT_STREAMBLOCKS,
        null=True,
        blank=True,
        use_json_field=True,
    )

    visual_design_template_prefix = "website/pages/web"

    class Meta:
        verbose_name = "Web Page"

    template = "website/pages/web/default.html"

    content_panels = CoderedWebPage.content_panels + [SCROLL_BACKGROUND_PANEL]


# ---------------------------------------------------------------------------
# Catalog tree (FRBR): CollectionPage (Work) → EditionPage (Expression)
#                      → VolumePage (Item). See docs/archive/data_model_design.md.
# ---------------------------------------------------------------------------


class CatalogCodeMixin(models.Model):
    """Shared ``code`` field; catalog URL slug always follows ``code``."""

    code = models.CharField(
        max_length=64,
        help_text=(
            "Stable identifier, not translated. Used in scan paths, citations, "
            "imports, and as the page slug (URL). Unique among siblings."
        ),
    )

    class Meta:
        abstract = True

    def sync_slug_from_code(self):
        if self.code:
            self.slug = slugify(self.code)

    def full_clean(self, *args, **kwargs):
        self.sync_slug_from_code()
        super().full_clean(*args, **kwargs)

    def save(self, *args, **kwargs):
        self.sync_slug_from_code()
        super().save(*args, **kwargs)



class CatalogIndexPage(ScrollBackgroundPageMixin, VisualDesignPageMixin, CoderedWebPage):
    """Catalog hub — lists collections."""

    visual_design_template_prefix = "website/pages/catalog_index"

    class Meta:
        verbose_name = "Catalog Index Page"

    template = "website/pages/catalog_index/default.html"

    content_panels = CoderedWebPage.content_panels + [
        SCROLL_BACKGROUND_PANEL,
    ]

    subpage_types = ["website.CollectionPage"]
    parent_page_types = ["website.WebPage", "wagtailcore.Page"]

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        context["catalog_groups"] = self.get_catalog_groups()
        return context

    def get_catalog_groups(self):
        """
        Live CollectionPage children grouped by Classification, then Tradition
        (current locale). Ordered by classification sort_order, tradition
        sort_order, then catalog_sort_order.
        """
        from snippets.models import Classification

        collections = (
            CollectionPage.objects.child_of(self)
            .live()
            .select_related("classification", "cover_image", "tradition", "country")
            .order_by("catalog_sort_order", "title")
        )

        by_translation_key = defaultdict(list)
        unclassified = []

        for collection in collections:
            if collection.classification_id:
                by_translation_key[collection.classification.translation_key].append(
                    collection
                )
            else:
                unclassified.append(collection)

        if not by_translation_key and not unclassified:
            return []

        groups = []
        seen_keys = set()
        for classification in Classification.objects.filter(
            locale=self.locale,
            translation_key__in=by_translation_key.keys(),
        ).order_by("sort_order", "slug"):
            seen_keys.add(classification.translation_key)
            group_collections = by_translation_key[classification.translation_key]
            groups.append(
                {
                    "classification": classification,
                    "tradition_groups": self._group_collections_by_tradition(
                        group_collections
                    ),
                }
            )

        for translation_key, group_collections in by_translation_key.items():
            if translation_key in seen_keys:
                continue
            groups.append(
                {
                    "classification": group_collections[0].classification,
                    "tradition_groups": self._group_collections_by_tradition(
                        group_collections
                    ),
                }
            )

        if unclassified:
            groups.append(
                {
                    "classification": None,
                    "tradition_groups": self._group_collections_by_tradition(
                        unclassified
                    ),
                }
            )

        return groups

    def _group_collections_by_tradition(self, collections):
        """
        Split collections into tradition subgroups (locale sort_order),
        with unassigned tradition last.
        """
        from snippets.models import Tradition

        by_tradition_key = defaultdict(list)
        unassigned = []

        for collection in collections:
            if collection.tradition_id:
                by_tradition_key[collection.tradition.translation_key].append(
                    collection
                )
            else:
                unassigned.append(collection)

        if not by_tradition_key and not unassigned:
            return []

        tradition_groups = []
        seen_keys = set()
        for tradition in Tradition.objects.filter(
            locale=self.locale,
            translation_key__in=by_tradition_key.keys(),
        ).order_by("sort_order", "code"):
            seen_keys.add(tradition.translation_key)
            tradition_groups.append(
                {
                    "tradition": tradition,
                    "collections": by_tradition_key[tradition.translation_key],
                }
            )

        for translation_key, group_collections in by_tradition_key.items():
            if translation_key in seen_keys:
                continue
            tradition_groups.append(
                {
                    "tradition": group_collections[0].tradition,
                    "collections": group_collections,
                }
            )

        if unassigned:
            tradition_groups.append({"tradition": None, "collections": unassigned})

        return tradition_groups


class CollectionPage(
    CatalogCodeMixin, ScrollBackgroundPageMixin, VisualDesignPageMixin, CoderedWebPage
):
    """Work — the whole canon set (e.g. the Pāli Tipiṭaka). No language."""

    base_form_class = CollectionPageForm

    visual_design_template_prefix = "website/pages/collection"

    classification = models.ForeignKey(
        "snippets.Classification",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )
    tradition = models.ForeignKey(
        "snippets.Tradition",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )
    country = models.ForeignKey(
        "snippets.Country",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
        verbose_name="ประเทศ / Country",
        help_text=(
            "Country of this scripture collection (not place of publication). "
            "e.g. Chaṭṭha Saṅgīti printed in Taiwan still belongs to Myanmar."
        ),
    )
    catalog_sort_order = models.IntegerField(default=0)

    class Meta:
        verbose_name = "Collection Page"

    template = "website/pages/collection/default.html"

    content_panels = CoderedWebPage.content_panels + [
        FieldPanel("code"),
        MultiFieldPanel(
            [
                FieldPanel("classification"),
                FieldPanel("tradition"),
                FieldPanel("country"),
            ],
            heading="Catalog metadata",
        ),
        FieldPanel("catalog_sort_order"),
        SCROLL_BACKGROUND_PANEL,
    ]

    subpage_types = ["website.EditionPage"]
    parent_page_types = ["website.CatalogIndexPage"]

    def get_edition_groups(self):
        """
        Live EditionPage children grouped by edition_role (Role enum order),
        editions within each group ordered by Wagtail menu order (path).

        Consecutive editions that share the same cover_image only show the
        thumbnail once (first in the run) so printings of one set do not
        repeat an identical cover.
        """
        editions = (
            EditionPage.objects.child_of(self)
            .live()
            .select_related("cover_image")
            .order_by("path")
        )

        by_role = defaultdict(list)
        for edition in editions:
            by_role[edition.edition_role].append(edition)

        if not by_role:
            return []

        groups = []
        for role in EditionPage.Role:
            role_editions = by_role.get(role.value)
            if not role_editions:
                continue
            prev_cover_id = None
            for edition in role_editions:
                cover_id = edition.cover_image_id
                edition.show_cover_thumb = bool(cover_id) and cover_id != prev_cover_id
                if cover_id:
                    prev_cover_id = cover_id
            groups.append({"role": role, "editions": role_editions})
        return groups

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        context["edition_groups"] = self.get_edition_groups()
        return context


class EditionPage(
    CatalogCodeMixin, ScrollBackgroundPageMixin, VisualDesignPageMixin, CoderedWebPage
):
    """Expression — one edition; may span multiple content languages and/or scripts."""

    base_form_class = EditionPageForm

    visual_design_template_prefix = "website/pages/edition"

    class Role(models.TextChoices):
        SOURCE = "source", _("Source")
        TRANSLATION = "translation", _("Translation")
        TRANSLITERATION = "transliteration", _("Transliteration")
        COMMENTARY = "commentary", _("Commentary")
        DIGITAL = "digital", _("Digital")

    content_languages = ParentalManyToManyField(
        "snippets.ContentLanguage",
        related_name="edition_pages",
        verbose_name="content languages",
        help_text="Language(s) of the source text (not the site UI locale).",
    )
    content_scripts = ParentalManyToManyField(
        "snippets.ContentScript",
        related_name="edition_pages",
        verbose_name="content scripts",
        help_text="Writing system(s) used in this edition.",
    )
    edition_role = models.CharField(
        max_length=16,
        choices=Role.choices,
        default=Role.SOURCE,
        help_text="Role of this edition relative to the Work (logic/filter).",
    )
    source_edition = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="derived_editions",
        help_text="Source edition for a translation or transliteration.",
    )
    publisher = models.CharField(
        max_length=255,
        blank=True,
        help_text="Default publisher for the edition; a volume may override it.",
    )
    published_year = models.CharField(
        max_length=64,
        blank=True,
        help_text="Default publication year (BE/CE/range). A volume may override it.",
    )
    print_number = models.CharField(
        max_length=64,
        blank=True,
        help_text="Default printing/impression. A volume may override it.",
    )
    place_of_publication = models.CharField(
        max_length=255,
        blank=True,
        help_text="Default place of publication; a volume may override it.",
    )
    isbn_number = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="ISBN",
        help_text="Default ISBN-10 or ISBN-13 (hyphens optional). A volume may override it.",
    )
    volume_set_count = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=(
            "Number of logical volume sets in this edition as catalogued "
            "(e.g. 52 for an edition published in 52 numbered sets)."
        ),
    )
    physical_volume_count = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=(
            "Number of physical books when it differs from volume sets "
            "(e.g. 57 books for 52 numbered sets when some numbers are split). "
            "Leave blank when equal to volume set count."
        ),
    )
    description = RichTextField(blank=True)
    catalog_sort_order = models.IntegerField(default=0)

    class Meta:
        verbose_name = "Edition Page"

    template = "website/pages/edition/default.html"

    content_panels = CoderedWebPage.content_panels + [
        FieldPanel("code"),
        MultiFieldPanel(
            [
                FieldPanel("content_languages"),
                FieldPanel("content_scripts"),
                FieldPanel("edition_role"),
                FieldPanel("source_edition"),
            ],
            heading="Expression",
        ),
        MultiFieldPanel(
            [
                FieldPanel("volume_set_count"),
                FieldPanel("physical_volume_count"),
            ],
            heading="Catalog extent",
        ),
        MultiFieldPanel(
            [
                FieldPanel("publisher"),
                FieldPanel("place_of_publication"),
                FieldPanel("published_year"),
                FieldPanel("print_number"),
                FieldPanel("isbn_number"),
            ],
            heading="Publication defaults",
        ),
        FieldPanel("description"),
        FieldPanel("catalog_sort_order"),
        SCROLL_BACKGROUND_PANEL,
    ]

    subpage_types = ["website.VolumePage"]
    parent_page_types = ["website.CollectionPage"]

    def clean(self):
        from snippets.models.base import validate_same_locale_m2m

        super().clean()
        validate_same_locale_m2m(self, "content_languages", self.content_languages)
        validate_same_locale_m2m(self, "content_scripts", self.content_scripts)

    def get_volume_groups(self):
        """
        Volume list grouped by CanonicalSection tree (piṭaka → nikāya).

        Prefer live VolumePage children. When the edition's catalog volume set
        includes ``not_published`` stubs (e.g. PTS English), merge those
        list-only rows in catalog order so unpublished slots still appear.
        """
        volumes = self._volume_list_entries()
        if not volumes:
            return []

        pitaka_buckets: dict[int, dict] = {}
        unsectioned = []

        for volume in volumes:
            section = volume.section
            if section is None:
                unsectioned.append(volume)
                continue

            if section.parent_id:
                pitaka = section.parent
                bucket = pitaka_buckets.setdefault(
                    pitaka.pk,
                    {"section": pitaka, "volumes": [], "subgroups": {}},
                )
                subgroup = bucket["subgroups"].setdefault(
                    section.pk,
                    {"section": section, "volumes": []},
                )
                subgroup["volumes"].append(volume)
            else:
                bucket = pitaka_buckets.setdefault(
                    section.pk,
                    {"section": section, "volumes": [], "subgroups": {}},
                )
                bucket["volumes"].append(volume)

        groups = []
        for bucket in sorted(
            pitaka_buckets.values(),
            key=lambda item: (item["section"].sort_order, item["section"].code),
        ):
            subgroups = []
            for subgroup in sorted(
                bucket["subgroups"].values(),
                key=lambda item: (item["section"].sort_order, item["section"].code),
            ):
                subgroups.append(
                    {
                        "section": subgroup["section"],
                        "count": len(subgroup["volumes"]),
                        "volumes": subgroup["volumes"],
                    }
                )
            count = len(bucket["volumes"]) + sum(
                subgroup["count"] for subgroup in subgroups
            )
            groups.append(
                {
                    "section": bucket["section"],
                    "count": count,
                    "volumes": bucket["volumes"],
                    "subgroups": subgroups,
                }
            )

        if unsectioned:
            groups.append(
                {
                    "section": None,
                    "count": len(unsectioned),
                    "volumes": unsectioned,
                    "subgroups": [],
                }
            )
        return groups

    def _volume_list_entries(self):
        """Ordered volume rows for the edition page (pages and/or stubs)."""
        from snippets.models import CanonicalSection
        from website.catalog_volume_sets import (
            CATALOG_VOLUME_SETS,
            thai_digits,
            volume_code,
        )

        pages = list(
            VolumePage.objects.child_of(self)
            .live()
            .select_related("section", "section__parent")
            .order_by("volume_index", "path")
        )

        parent = self.get_parent()
        collection_code = getattr(
            parent.specific if parent is not None else None, "code", None
        )
        vol_specs = (
            CATALOG_VOLUME_SETS.get((collection_code, self.code))
            if collection_code
            else None
        )
        if not vol_specs or not any(spec.get("not_published") for spec in vol_specs):
            return pages

        pages_by_code = {page.code: page for page in pages}
        sections = {
            s.code: s
            for s in CanonicalSection.objects.filter(locale=self.locale).select_related(
                "parent"
            )
        }
        lang = self.locale.language_code
        entries = []
        for spec in vol_specs:
            section = sections.get(spec["section"])
            if spec.get("not_published"):
                number_src = spec.get("catalog_no", spec["index"])
                number = (
                    str(number_src) if lang == "en" else thai_digits(number_src)
                )
                title = spec["title"].get(lang) or spec["title"].get("en", "")
                entries.append(
                    VolumeListStub(
                        title=title,
                        number=str(number),
                        volume_index=spec["index"],
                        section=section,
                    )
                )
                continue
            page = pages_by_code.get(volume_code(spec["index"]))
            if page is not None:
                entries.append(page)
        return entries

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        context["volume_groups"] = self.get_volume_groups()
        return context


@dataclass(frozen=True)
class VolumeListStub:
    """List-only catalog row (no VolumePage), e.g. PTS English not published."""

    title: str
    number: str
    volume_index: int
    section: object | None = None
    is_unpublished_stub: bool = True


class VolumePage(
    RoutablePageMixin,
    CatalogCodeMixin,
    ScrollBackgroundPageMixin,
    VisualDesignPageMixin,
    CoderedWebPage,
):
    """Item — a volume/part within an edition; container of scans + segments."""

    base_form_class = VolumePageForm

    visual_design_template_prefix = "website/pages/volume"

    volume_index = models.IntegerField(
        default=0,
        help_text="Physical ordering within the edition (always set).",
    )
    scan_folio_count = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=(
            "Declared number of scan pages in this volume. "
            "Generate ScanFolio rows 1..N on the default-locale volume only."
        ),
    )
    number = models.CharField(
        max_length=64,
        blank=True,
        help_text="Displayed volume number (optional; some editions use names).",
    )
    part_label = models.CharField(max_length=64, blank=True)
    section = models.ForeignKey(
        "snippets.CanonicalSection",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="volumes",
        help_text="Piṭaka/nikāya this volume belongs to.",
    )
    publisher = models.CharField(
        max_length=255,
        blank=True,
        help_text="Override for this volume only; leave blank to use the edition default.",
    )
    published_year = models.CharField(
        max_length=64,
        blank=True,
        help_text="Override for this volume only; leave blank to use the edition default.",
    )
    print_number = models.CharField(
        max_length=64,
        blank=True,
        help_text="Override for this volume only; leave blank to use the edition default.",
    )
    place_of_publication = models.CharField(
        max_length=255,
        blank=True,
        help_text="Override for this volume only; leave blank to use the edition default.",
    )
    isbn_number = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="ISBN",
        help_text="Override for this volume only; leave blank to use the edition default.",
    )
    description = RichTextField(blank=True)

    class Meta:
        verbose_name = "Volume Page"

    template = "website/pages/volume/default.html"

    content_panels = CoderedWebPage.content_panels + [
        FieldPanel("code"),
        MultiFieldPanel(
            [
                FieldPanel("volume_index"),
                FieldPanel("scan_folio_count"),
                FieldPanel("number"),
                FieldPanel("part_label"),
                FieldPanel("section", widget=forms.Select),
            ],
            heading="Volume",
        ),
        MultiFieldPanel(
            [
                FieldPanel("publisher"),
                FieldPanel("place_of_publication"),
                FieldPanel("published_year"),
                FieldPanel("print_number"),
                FieldPanel("isbn_number"),
            ],
            heading="Publication (override edition defaults)",
        ),
        FieldPanel("description"),
        SCROLL_BACKGROUND_PANEL,
    ]

    subpage_types = []
    parent_page_types = ["website.EditionPage"]

    is_unpublished_stub = False

    def _effective(self, field_name):
        own = getattr(self, field_name)
        if own:
            return own
        edition = self.get_parent().specific
        return getattr(edition, field_name, "")

    @property
    def effective_publisher(self):
        return self._effective("publisher")

    @property
    def effective_published_year(self):
        return self._effective("published_year")

    @property
    def effective_print_number(self):
        return self._effective("print_number")

    @property
    def effective_place_of_publication(self):
        return self._effective("place_of_publication")

    @property
    def effective_isbn_number(self):
        return self._effective("isbn_number")

    @path("f/<int:sequence>/")
    def folio_view(self, request, sequence):
        """Folio viewer at a specific scan within this volume."""
        from archive.models import scan_folios_for

        folio_qs = scan_folios_for(self).order_by("sequence")
        folio = folio_qs.filter(sequence=sequence).first()
        sequences = list(folio_qs.values_list("sequence", flat=True))
        prev_sequence = next_sequence = None
        if sequences:
            try:
                idx = sequences.index(sequence)
            except ValueError:
                idx = None
            if idx is not None:
                if idx > 0:
                    prev_sequence = sequences[idx - 1]
                if idx + 1 < len(sequences):
                    next_sequence = sequences[idx + 1]
        return self.render(
            request,
            context_overrides={
                "folio": folio,
                "sequence": sequence,
                "folio_count": len(sequences),
                "prev_sequence": prev_sequence,
                "next_sequence": next_sequence,
            },
            template="website/volume_page_folio.html",
        )

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        from archive.models import scan_folios_for

        folio_qs = scan_folios_for(self)
        context["folio_count"] = folio_qs.count()
        context["first_folio_sequence"] = (
            folio_qs.order_by("sequence")
            .values_list("sequence", flat=True)
            .first()
        )
        return context
