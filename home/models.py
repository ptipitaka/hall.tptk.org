from wagtail.models import Page


class HomePage(Page):
    """Wagtail root site homepage."""

    subpage_types: list[str] = []
    parent_page_types = ["wagtailcore.Page"]

    template = "home/home_page.html"
