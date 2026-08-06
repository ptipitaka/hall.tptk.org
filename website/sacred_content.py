"""
Seed data and helpers for the SACRED homepage and goal pages.

Home body uses StreamField blocks: html, cardgrid, and zigzag.
Run via ``python manage.py seed_sacred_content`` (or ``--force`` to overwrite).
Translations: ``python manage.py seed_sacred_translations``.
"""

from __future__ import annotations

import html
from decimal import Decimal

from website.sacred_content_locales import LOCALE_CONTENT, get_locale_content

DEFAULT_SETTINGS = {
    "custom_template": "",
    "custom_css_class": "",
    "custom_id": "",
}

DEFAULT_CARD_SETTINGS = {
    **DEFAULT_SETTINGS,
}

DEFAULT_BUTTON_SETTINGS = {
    **DEFAULT_SETTINGS,
    "ga_tracking_event_category": "",
    "ga_tracking_event_label": "",
}

LEGACY_BLOCK_TYPES = frozenset({"sacred_hero", "section", "goals"})

TRANSLATION_LOCALES = ("th",)


def _hero_html(content) -> str:
    acronym = "Scriptural Archive of Canonical Reference Editions Database"
    acronym_html = " ".join(
        f'<span class="acronym-letter">{word[0]}</span>{html.escape(word[1:])}'
        for word in acronym.split()
    )
    return f"""<div class="home-hero">
  <p class="home-fullname home-reveal home-reveal--up" style="--reveal-delay:0ms">{html.escape(content["fullname"])}</p>
  <h1 class="home-title home-reveal home-reveal--up" style="--reveal-delay:0ms">SACRED</h1>
  <div class="home-title-divider home-reveal home-reveal--up" style="--reveal-delay:0ms" aria-hidden="true"></div>
  <div class="home-acronym home-reveal home-reveal--up" style="--reveal-delay:0ms">
    <p class="home-eyebrow home-eyebrow--acronym">{acronym_html}</p>
  </div>
</div>"""


def _principle_html(content) -> str:
    cases_html = "\n".join(
        f'    <p class="home-case"><span class="home-case-mark">{case["mark"]}</span><br>\n'
        f'    {case["body"]}</p>'
        for case in content["principle_cases"]
    )
    return f"""<div class="home-section">
  <h2 class="home-section-title">{content["principle_title"]}</h2>
  <div class="home-cases-fold">
    <p class="home-principle">{content["principle_body"]}
      <span class="home-cases-toggle" role="button" tabindex="0" aria-expanded="false">
        <span class="home-cases-more" aria-hidden="true">&hellip;</span>
      </span>
    </p>
    <div class="home-cases home-cases-body">
{cases_html}
    </div>
  </div>
</div>"""


def _mission_html(content) -> str:
    return f"""<div class="home-section">
  <h2 class="home-section-title">{content["mission_title"]}</h2>
  <p class="home-principle">{content["mission_body"]}</p>
</div>"""


def _goal_page_body(title: str, paragraphs: list[str]) -> list[tuple[str, dict]]:
    body_html = "\n".join(f"    <p>{html.escape(p)}</p>" for p in paragraphs)
    return [
        (
            "html",
            f"""<div class="goal-detail">
  <h1 class="goal-detail-title">{html.escape(title)}</h1>
  <div class="goal-detail-body">
{body_html}
  </div>
</div>""",
        )
    ]


def _card_block(
    number: str,
    title: str,
    abstract: str,
    link_page,
    link_label: str,
    *,
    other_link: str = "",
) -> tuple[str, dict]:
    return (
        "card",
        {
            "settings": {
                **DEFAULT_CARD_SETTINGS,
                "custom_css_class": "home-goal-card",
            },
            "image": None,
            "title": title,
            "subtitle": number,
            "description": f"<p>{html.escape(abstract)}</p>",
            "links": [
                (
                    "Links",
                    {
                        "settings": DEFAULT_BUTTON_SETTINGS.copy(),
                        "page_link": link_page,
                        "doc_link": None,
                        "other_link": "" if link_page else other_link,
                        "button_title": link_label,
                        "button_style": "btn-link",
                        "button_size": "",
                    },
                )
            ],
        },
    )


def _resolve_goal_link_page(slug: str, language_code: str):
    """Return a live page for ``slug`` in ``language_code``, if present."""
    from wagtail.models import Locale, Page

    locale = Locale.objects.filter(language_code=language_code).first()
    if locale is None:
        return None
    page = (
        Page.objects.live()
        .filter(locale=locale, slug=slug)
        .specific()
        .first()
    )
    return page


def _goal_card_link(
    goal: dict,
    goal_pages_by_slug: dict[str, object],
    language_code: str,
) -> tuple[object | None, str]:
    """Return (page_link, other_link) for a homepage goal card."""
    link_slug = goal.get("link_slug") or goal["slug"]
    if link_slug in goal_pages_by_slug:
        return goal_pages_by_slug[link_slug], ""
    page = _resolve_goal_link_page(link_slug, language_code)
    if page is not None:
        return page, ""
    return None, f"/{link_slug}/"


def _zigzag_block(content) -> tuple[str, dict]:
    return (
        "zigzag",
        {
            "settings": DEFAULT_SETTINGS.copy(),
            "heading": content["classification_heading"],
            "cta_label": content["classification_cta"],
            "entries": [
                {
                    "siglum": entry["siglum"],
                    "title": entry["title"],
                    "description": entry["description"],
                    "link_page": None,
                    "other_link": "",
                }
                for entry in content["classification_entries"]
            ],
        },
    )


def build_home_body(
    goal_pages_by_slug: dict[str, object],
    *,
    language_code: str = "en",
) -> list[tuple[str, dict]]:
    content = get_locale_content(language_code)
    goal_cards = []
    for goal in content["goals"]:
        link_page, other_link = _goal_card_link(
            goal, goal_pages_by_slug, language_code
        )
        goal_cards.append(
            _card_block(
                goal["number"],
                goal["title"],
                goal["abstract"],
                link_page,
                goal["link_label"],
                other_link=other_link,
            )
        )
    return [
        ("html", _hero_html(content)),
        ("html", _mission_html(content)),
        ("html", _principle_html(content)),
        (
            "html",
            f"""<div class="home-section home-section--goals">
  <h2 class="home-section-title">{content["goals_title"]}</h2>
</div>""",
        ),
        (
            "cardgrid",
            {
                "settings": {
                    **DEFAULT_SETTINGS,
                    "custom_css_class": "home-goals",
                },
                "fluid": True,
                "content": goal_cards,
            },
        ),
        _zigzag_block(content),
    ]


def _body_needs_reseed(body) -> bool:
    if not body:
        return True
    has_zigzag = False
    for block in body:
        if block.block_type in LEGACY_BLOCK_TYPES:
            return True
        if block.block_type == "row":
            return True
        if block.block_type == "zigzag":
            has_zigzag = True
    return not has_zigzag


def _first_goal_card_link_slug(body) -> str | None:
    """Slug of the page (or path) linked from the first Goals card."""
    for block in body:
        if block.block_type != "cardgrid":
            continue
        cards = block.value["content"]
        if not cards:
            return None
        first = cards[0]
        card = first.value if hasattr(first, "value") else first
        links = card["links"]
        if not links:
            return None
        link = links[0]
        link_val = link.value if hasattr(link, "value") else link
        page = link_val.get("page_link")
        if page is not None:
            return page.slug
        other = (link_val.get("other_link") or "").strip("/")
        return other.rsplit("/", 1)[-1] if other else None
    return None


def _home_needs_goal_link_fix(home, language_code: str = "en") -> bool:
    content = get_locale_content(language_code)
    expected = content["goals"][0].get("link_slug") or content["goals"][0]["slug"]
    return _first_goal_card_link_slug(home.body) != expected


def _home_needs_layout_fix(home) -> bool:
    return home.index_show_subpages


def _get_or_copy_translation(page, locale, *, copy_parents: bool = True):
    from website.models import WebPage

    translated = page.get_translations(inclusive=False).filter(locale=locale).first()
    if translated is not None:
        if translated.alias_of_id:
            translated.delete()
        else:
            specific = translated.specific
            if isinstance(specific, WebPage):
                return specific

    is_site_root = page.depth == 2 and page.get_parent().is_root()
    copied = page.copy_for_translation(
        locale,
        copy_parents=copy_parents and not is_site_root,
        alias=False,
    )
    specific = copied.specific
    if isinstance(specific, WebPage):
        return specific
    raise RuntimeError(f"Copied page {copied.id} is not a WebPage.")


def seed_sacred_content(*, force: bool = False) -> dict[str, int]:
    """
    Create goal pages under Home and populate the English homepage body.

    Returns counts: {"goals_created", "goals_updated", "home_seeded"}.
    """
    from wagtail.models import Site

    from website.models import WebPage

    content = get_locale_content("en")
    home = Site.objects.get(is_default_site=True).root_page.specific
    if not isinstance(home, WebPage):
        raise RuntimeError("Site root page must be a WebPage.")

    stats = {"goals_created": 0, "goals_updated": 0, "home_seeded": 0}
    goal_pages_by_slug: dict[str, WebPage] = {}

    for goal_def in content["goal_pages"]:
        existing = home.get_children().filter(slug=goal_def["slug"]).first()
        body = _goal_page_body(goal_def["title"], list(goal_def["paragraphs"]))
        search_description = goal_def["search_description"]

        if existing:
            page = existing.specific
            if isinstance(page, WebPage):
                needs_update = force or _body_needs_reseed(page.body)
                if not (page.search_description or "").strip():
                    needs_update = True
                if needs_update:
                    page.title = goal_def["title"]
                    page.body = body
                    page.search_description = search_description
                    page.custom_template = "coderedcms/pages/web_page_notitle.html"
                    page.save_revision().publish()
                    stats["goals_updated"] += 1
                goal_pages_by_slug[goal_def["slug"]] = page
            continue

        page = WebPage(
            title=goal_def["title"],
            slug=goal_def["slug"],
            custom_template="coderedcms/pages/web_page_notitle.html",
            body=body,
            search_description=search_description,
            scroll_bg_opacity=Decimal("0.20"),
        )
        home.add_child(instance=page)
        page.save_revision().publish()
        goal_pages_by_slug[goal_def["slug"]] = page
        stats["goals_created"] += 1

    home_needs_seed = (
        force
        or _body_needs_reseed(home.body)
        or _home_needs_layout_fix(home)
        or _home_needs_goal_link_fix(home, "en")
    )
    if not (home.search_description or "").strip():
        home_needs_seed = True
    if home_needs_seed:
        home.body = build_home_body(goal_pages_by_slug, language_code="en")
        home.custom_template = "coderedcms/pages/home_page.html"
        home.index_show_subpages = False
        home.search_description = content["home_search_description"]
        home.save_revision().publish()
        stats["home_seeded"] = 1

    return stats


def seed_sacred_translations(
    *,
    force: bool = False,
    locales: tuple[str, ...] = TRANSLATION_LOCALES,
) -> dict[str, int]:
    """
    Create or update Thai and Chinese translations of Home and goal pages.

    Requires English content from ``seed_sacred_content`` first.
    """
    from wagtail.models import Locale, Site

    from website.models import WebPage

    seed_sacred_content(force=False)

    home_en = Site.objects.get(is_default_site=True).root_page.specific
    if not isinstance(home_en, WebPage):
        raise RuntimeError("Site root page must be a WebPage.")

    stats = {"homes_updated": 0, "goals_updated": 0, "translations_created": 0}

    for language_code in locales:
        if language_code not in LOCALE_CONTENT:
            raise ValueError(f"Unsupported locale: {language_code!r}")

        locale = Locale.objects.get(language_code=language_code)
        content = get_locale_content(language_code)
        goal_pages_by_slug: dict[str, WebPage] = {}

        existed = home_en.get_translations(inclusive=False).filter(locale=locale).exists()
        home_tr = _get_or_copy_translation(home_en, locale, copy_parents=False)
        if not existed:
            stats["translations_created"] += 1

        for goal_def in content["goal_pages"]:
            en_goal = home_en.get_children().get(slug=goal_def["slug"]).specific
            if not isinstance(en_goal, WebPage):
                continue

            existed = en_goal.get_translations(inclusive=False).filter(locale=locale).exists()
            goal_page = _get_or_copy_translation(en_goal, locale)
            if not existed:
                stats["translations_created"] += 1

            body = _goal_page_body(goal_def["title"], list(goal_def["paragraphs"]))
            needs_update = force or _body_needs_reseed(goal_page.body)
            if goal_page.title != goal_def["title"]:
                needs_update = True
            if not (goal_page.search_description or "").strip():
                needs_update = True

            if needs_update:
                goal_page.title = goal_def["title"]
                goal_page.body = body
                goal_page.search_description = goal_def["search_description"]
                goal_page.custom_template = "coderedcms/pages/web_page_notitle.html"
                goal_page.save_revision().publish()
                stats["goals_updated"] += 1

            goal_pages_by_slug[goal_def["slug"]] = goal_page

        home_needs_update = (
            force
            or _body_needs_reseed(home_tr.body)
            or _home_needs_goal_link_fix(home_tr, language_code)
        )
        if not (home_tr.search_description or "").strip():
            home_needs_update = True

        if home_needs_update:
            home_tr.body = build_home_body(
                goal_pages_by_slug,
                language_code=language_code,
            )
            home_tr.custom_template = "coderedcms/pages/home_page.html"
            home_tr.index_show_subpages = False
            home_tr.search_description = content["home_search_description"]
            home_tr.save_revision().publish()
            stats["homes_updated"] += 1

    from django.core.management import call_command

    call_command("fixtree", verbosity=0)

    return stats
