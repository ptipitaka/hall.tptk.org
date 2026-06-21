"""
StreamField block lists for website pages.

Replaces Wagtail RawHTMLBlock with EnhancedHTMLBlock (CodeMirror) for
readable, structured HTML editing in the admin.
"""

from django.utils.translation import gettext_lazy as _
from wagtail_html_editor.blocks import EnhancedHTMLBlock

from coderedcms.blocks import LAYOUT_STREAMBLOCKS

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


LAYOUT_STREAMBLOCKS = _with_enhanced_html(LAYOUT_STREAMBLOCKS)
