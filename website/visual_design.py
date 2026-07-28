"""
Visual Design (Layout → Template) for project page types.

CodeRed CMS stores CRX template paths in ``custom_template``. Project page
types map those choices to shared layout shells plus page-type footers.

See ``website/templates/website/layouts/`` and ``website/templates/website/pages/``.
"""

from __future__ import annotations

CRX_TEMPLATE_WEB_COVER = "coderedcms/pages/web_page.html"
CRX_TEMPLATE_WEB_NOTITLE = "coderedcms/pages/web_page_notitle.html"
CRX_TEMPLATE_HOME = "coderedcms/pages/home_page.html"
CRX_TEMPLATE_BLANK = "coderedcms/pages/base.html"

CRX_TO_SHELL: dict[str, str] = {
    "": "default",
    CRX_TEMPLATE_WEB_COVER: "cover",
    CRX_TEMPLATE_WEB_NOTITLE: "notitle",
    CRX_TEMPLATE_HOME: "notitle",
    CRX_TEMPLATE_BLANK: "blank",
}

VISUAL_DESIGN_TEMPLATE_CHOICES: dict[str, str] = {
    "": "default",
    CRX_TEMPLATE_WEB_COVER: "cover",
    CRX_TEMPLATE_WEB_NOTITLE: "notitle",
    CRX_TEMPLATE_HOME: "notitle",
    CRX_TEMPLATE_BLANK: "blank",
}


class VisualDesignPageMixin:
    """Map CRX ``custom_template`` values to project shell templates."""

    visual_design_template_prefix = "website/pages/web"

    def resolve_visual_design_template(self) -> str:
        shell = CRX_TO_SHELL.get(self.custom_template or "", "default")
        return f"{self.visual_design_template_prefix}/{shell}.html"

    def get_template(self, request, *args, **kwargs):
        return self.resolve_visual_design_template()


def richtext_to_html_blocks(*values: str) -> list[dict]:
    """Build StreamField JSON prepending html blocks from rich text strings."""
    blocks: list[dict] = []
    for value in values:
        if value and str(value).strip():
            blocks.append({"type": "html", "value": str(value)})
    return blocks
