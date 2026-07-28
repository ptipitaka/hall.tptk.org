"""Vertical alternating layout block (center rail, cards left/right)."""

from django.utils.translation import gettext_lazy as _
from wagtail import blocks

from coderedcms.blocks import BaseBlock


class ZigzagEntryBlock(blocks.StructBlock):
    siglum = blocks.CharBlock(
        max_length=8,
        label=_("Siglum"),
        help_text=_("Short label shown on the center rail, e.g. TP, AK."),
    )
    title = blocks.CharBlock(label=_("Title"))
    description = blocks.TextBlock(required=False, label=_("Description"))
    link_page = blocks.PageChooserBlock(required=False, label=_("Page link"))
    other_link = blocks.URLBlock(required=False, label=_("External link"))

    class Meta:
        icon = "placeholder"
        label = _("Zigzag entry")


class ZigzagBlock(BaseBlock):
    heading = blocks.CharBlock(required=False, label=_("Section heading"))
    cta_label = blocks.CharBlock(
        default="Browse collection",
        required=False,
        label=_("Link label"),
        help_text=_("Footer text on linked cards."),
    )
    entries = blocks.ListBlock(ZigzagEntryBlock(), min_num=1, label=_("Entries"))

    class Meta:
        template = "website/blocks/zigzag_block.html"
        icon = "list-ul"
        label = _("Zigzag")

    def get_context(self, value, parent_context=None):
        context = super().get_context(value, parent_context)
        entries_with_side = []
        for index, entry in enumerate(value["entries"]):
            side_class = (
                "home-zigzag-entry--right"
                if index % 2 == 0
                else "home-zigzag-entry--left"
            )
            href = ""
            link_page = entry.get("link_page")
            other_link = entry.get("other_link") or ""
            if link_page:
                href = link_page.url
            elif other_link:
                href = other_link
            entries_with_side.append(
                {
                    "entry": entry,
                    "side_class": side_class,
                    "href": href,
                }
            )
        context["entries_with_side"] = entries_with_side
        return context
