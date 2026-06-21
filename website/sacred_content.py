"""
Seed data and helpers for SACRED homepage and goal pages (English).

Uses Wagtail CRX built-in blocks only (html, row, text, cardgrid, card).
"""

from __future__ import annotations

import html
from decimal import Decimal

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

GOAL_PAGES = [
    {
        "slug": "goal-repository",
        "title": "Tipiṭaka Repository",
        "paragraphs": [
            (
                "SACRED gathers and preserves principal Theravāda Tipiṭaka editions "
                "transmitted through the Buddhist Councils, in full across nations."
            ),
            (
                "Reference editions such as Chaṭṭha Saṅgāyana, Syāmaraṭṭha, "
                "Mahāchulalongkorn, and Buddhajayantī are archived in a unified digital "
                "form so that the textual heritage of each tradition remains accessible "
                "and intact."
            ),
            (
                "This repository is the foundation of every cross-edition reference and "
                "Mahāpadesa verification on the site."
            ),
        ],
    },
    {
        "slug": "goal-cross-edition",
        "title": "Cross-Edition Unity",
        "paragraphs": [
            (
                "A master table of contents links volumes and texts across every "
                "reference edition in SACRED."
            ),
            (
                "A unified reference system lets readers locate the same passage in "
                "different editions and compare readings side by side, with textual "
                "differences shown transparently."
            ),
            (
                "Cross-edition unity makes the international repository practically "
                "useful for study, scholarship, and verification."
            ),
        ],
    },
    {
        "slug": "goal-mahapadesa",
        "title": "Mahāpadesa Verification",
        "paragraphs": [
            (
                "Analytical tools for Dhamma passages help readers search the Tipiṭaka "
                "and examine whether a teaching aligns with the Doctrine and Discipline."
            ),
            (
                "Following the Mahāpadesa principle, claims are neither accepted nor "
                "rejected at once: words are studied, laid beside the Discourses, and "
                "compared with the Vinaya before a conclusion is drawn."
            ),
            (
                "AI-assisted search and citation support this process, always grounding "
                "answers in the archived editions."
            ),
        ],
    },
]

MISSION_BODY = (
    "Conserving and safeguarding the integrity of the Tipiṭaka<br>\n"
    "carrying forward a tradition of textual preservation spanning over 2,500 years<br>\n"
    "from oral recitation, palm-leaf manuscripts, and printed books<br>\n"
    "to the digital and AI era<br>\n"
    "to sustain the wisdom heritage of humanity"
)

PRINCIPLE_BODY = (
    "When one claims that<br>\n"
    "&ldquo;This is the Doctrine, this is the Discipline, this is the Master&rsquo;s teaching&rdquo;<br>\n"
    "the words of that person are neither to be welcomed nor scorned<br>\n"
    "the words and syllables thereof are to be studied thoroughly<br>\n"
    "laid beside the Discourses and compared with the Discipline"
)

PRINCIPLE_CASES = [
    {
        "mark": "a.",
        "body": (
            "If, when laid beside the Discourses and compared with the Discipline,<br>\n"
            "these words and syllables lie not along with the Discourses<br>\n"
            "and agree not with the Discipline,<br>\n"
            "then you may come to the conclusion:<br>\n"
            "Surely this is not the word of the Blessed One"
        ),
    },
    {
        "mark": "b.",
        "body": (
            "If, when laid beside the Discourses and compared with the Discipline,<br>\n"
            "these words and syllables lie along with the Discourses<br>\n"
            "and agree with the Discipline,<br>\n"
            "then you may come to the conclusion:<br>\n"
            "Surely this is the word of the Blessed One"
        ),
    },
]

GOALS = [
    {
        "number": "1",
        "title": "Tipiṭaka Repository",
        "abstract": "Collect and preserve principal Theravāda Tipiṭaka editions.",
        "slug": "goal-repository",
        "link_label": "Read more",
    },
    {
        "number": "2",
        "title": "Cross-Edition Unity",
        "abstract": "A master table of contents and unified reference system.",
        "slug": "goal-cross-edition",
        "link_label": "Read more",
    },
    {
        "number": "3",
        "title": "Mahāpadesa Verification",
        "abstract": "Search, verify, and compare against the Doctrine and Discipline.",
        "slug": "goal-mahapadesa",
        "link_label": "Read more",
    },
]

LEGACY_BLOCK_TYPES = frozenset({"sacred_hero", "section", "goals"})

GOAL_SEARCH_DESCRIPTIONS = {goal["slug"]: goal["abstract"] for goal in GOALS}

HOME_SEARCH_DESCRIPTION = (
    "The People's Tipiṭaka Hall (SACRED) conserves Theravāda Tipiṭaka editions, "
    "cross-edition references, and Mahāpadesa verification tools."
)


def _hero_html() -> str:
    acronym = "Scriptural Archive of Canonical References Editions Depository"
    acronym_html = " ".join(
        f'<span class="acronym-letter">{word[0]}</span>{html.escape(word[1:])}'
        for word in acronym.split()
    )
    return f"""<div class="home-hero">
  <p class="home-fullname home-reveal home-reveal--up" style="--reveal-delay:0ms">The People's Tipiṭaka Hall</p>
  <h1 class="home-title home-reveal home-reveal--up" style="--reveal-delay:0ms">SACRED</h1>
  <div class="home-title-divider home-reveal home-reveal--up" style="--reveal-delay:0ms" aria-hidden="true"></div>
  <div class="home-acronym home-reveal home-reveal--up" style="--reveal-delay:0ms">
    <p class="home-eyebrow home-eyebrow--acronym">{acronym_html}</p>
  </div>
</div>"""


def _principle_html() -> str:
    cases_html = "\n".join(
        f'    <p class="home-case"><span class="home-case-mark">{case["mark"]}</span><br>\n'
        f'    {case["body"]}</p>'
        for case in PRINCIPLE_CASES
    )
    return f"""<div class="home-section">
  <h2 class="home-section-title">Principle · The Four Great Authorities</h2>
  <div class="home-cases-fold">
    <p class="home-principle">{PRINCIPLE_BODY}
      <span class="home-cases-toggle" role="button" tabindex="0" aria-expanded="false">
        <span class="home-cases-more" aria-hidden="true">&hellip;</span>
      </span>
    </p>
    <div class="home-cases home-cases-body">
{cases_html}
    </div>
  </div>
</div>"""


def _mission_html() -> str:
    return f"""<div class="home-section">
  <h2 class="home-section-title">Mission</h2>
  <p class="home-principle">{MISSION_BODY}</p>
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
                        "other_link": "",
                        "button_title": link_label,
                        "button_style": "btn-link",
                        "button_size": "",
                    },
                )
            ],
        },
    )


def build_home_body(goal_pages_by_slug: dict[str, object]) -> list[tuple[str, dict]]:
    return [
        ("html", _hero_html()),
        ("html", _mission_html()),
        ("html", _principle_html()),
        (
            "html",
            """<div class="home-section home-section--goals">
  <h2 class="home-section-title">Goals</h2>
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
                "content": [
                    _card_block(
                        goal["number"],
                        goal["title"],
                        goal["abstract"],
                        goal_pages_by_slug[goal["slug"]],
                        goal["link_label"],
                    )
                    for goal in GOALS
                ],
            },
        ),
    ]


def _body_needs_reseed(body) -> bool:
    if not body:
        return True
    for block in body:
        if block.block_type in LEGACY_BLOCK_TYPES:
            return True
        if block.block_type == "row":
            # Earlier CRX seed stored Mission/goal copy in RichText rows.
            return True
    return False


def _home_needs_layout_fix(home) -> bool:
    return home.index_show_subpages


def seed_sacred_content(*, force: bool = False) -> dict[str, int]:
    """
    Create goal pages under Home and populate the English homepage body.

    Returns counts: {"goals_created", "goals_updated", "home_seeded"}.
    """
    from wagtail.models import Site

    from website.models import WebPage

    home = Site.objects.get(is_default_site=True).root_page.specific
    if not isinstance(home, WebPage):
        raise RuntimeError("Site root page must be a WebPage.")

    stats = {"goals_created": 0, "goals_updated": 0, "home_seeded": 0}
    goal_pages_by_slug: dict[str, WebPage] = {}

    for goal_def in GOAL_PAGES:
        existing = home.get_children().filter(slug=goal_def["slug"]).first()
        body = _goal_page_body(goal_def["title"], goal_def["paragraphs"])
        search_description = GOAL_SEARCH_DESCRIPTIONS[goal_def["slug"]]

        if existing:
            page = existing.specific
            if isinstance(page, WebPage):
                needs_update = force or _body_needs_reseed(page.body)
                if not (page.search_description or "").strip():
                    needs_update = True
                if needs_update:
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

    home_needs_seed = force or _body_needs_reseed(home.body) or _home_needs_layout_fix(home)
    if not (home.search_description or "").strip():
        home_needs_seed = True
    if home_needs_seed:
        home.body = build_home_body(goal_pages_by_slug)
        home.custom_template = "coderedcms/pages/home_page.html"
        home.index_show_subpages = False
        home.search_description = HOME_SEARCH_DESCRIPTION
        home.save_revision().publish()
        stats["home_seeded"] = 1

    return stats
