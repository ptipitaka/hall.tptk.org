"""Wagtail admin for the Digital archive.

Round 1: ScanFolio (one row per scan page; default-locale volume only).
Segment / SegmentRevision will be registered in a later round — the Segment
table is expected to reach hundreds of thousands of rows and needs a more
carefully scoped editor (per-folio, with revision creation on save).

Design contract (docs/archive/data_model_design.md §9–§10): ScanFolio/Segment
are NOT edited as InlinePanel on VolumePage. They live in a standalone admin
section ("Digital archive") with list + filter + pagination, so the Wagtail
page explorer never has to render tens of thousands of rows.
"""

from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSetGroup
from django.utils.translation import gettext_lazy as _

from archive.admin_scanfolios import ScanFolioViewSet


class DigitalArchiveGroup(SnippetViewSetGroup):
    menu_label = _("Digital archive")
    menu_icon = "folder-open-inverse"
    menu_order = 150
    items = (ScanFolioViewSet,)


register_snippet(DigitalArchiveGroup)
