"""
StreamField block lists for website pages.

- Swaps Wagtail RawHTMLBlock with EnhancedHTMLBlock (CodeMirror) for HTML blocks.
- Appends project-specific layout blocks (e.g. zigzag).
"""

from django.utils.translation import gettext_lazy as _
from wagtail_html_editor.blocks import EnhancedHTMLBlock

from coderedcms.blocks import LAYOUT_STREAMBLOCKS

from website.blocks.zigzag_blocks import ZigzagBlock

HTML_BLOCK = EnhancedHTMLBlock(
    icon="code",
    form_classname="monospace",
    label=_("HTML"),
)


def _with_enhanced_html(blocks_list):
    """Return a copy of *blocks_list*, swapping top-level html blocks."""
    updated = []
    for name, block in blocks_list:
        if name == "html":
            updated.append(("html", HTML_BLOCK))
        else:
            updated.append((name, block))
    return updated


LAYOUT_STREAMBLOCKS = _with_enhanced_html(LAYOUT_STREAMBLOCKS) + [
    ("zigzag", ZigzagBlock()),
]
