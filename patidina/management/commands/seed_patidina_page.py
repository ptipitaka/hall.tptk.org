"""Create / publish PatidinaPage under the site root for en and th locales."""

from django.core.management.base import BaseCommand
from wagtail.models import Locale, Site

from patidina.models import PatidinaPage

PAGE_TITLES = {
    "en": "Patidina",
    "th": "ปฏิทิน",
}


def _ensure_english_page(root) -> tuple[PatidinaPage, bool]:
    locale_en = Locale.get_default()
    existing = (
        PatidinaPage.objects.filter(locale=locale_en).live().first()
        or PatidinaPage.objects.filter(locale=locale_en).first()
    )
    if existing is not None:
        return existing.specific, False

    page = PatidinaPage(
        title=PAGE_TITLES["en"],
        slug="patidina",
        draft_title=PAGE_TITLES["en"],
        locale=locale_en,
    )
    root.add_child(instance=page)
    page.save_revision().publish()
    return page, True


def _ensure_translation(page_en: PatidinaPage, language_code: str) -> tuple[PatidinaPage, bool]:
    locale = Locale.objects.get(language_code=language_code)
    existing = page_en.get_translations(inclusive=False).filter(locale=locale).first()
    if existing is not None:
        if existing.alias_of_id:
            existing.delete()
        else:
            specific = existing.specific
            title = PAGE_TITLES[language_code]
            if specific.title != title:
                specific.title = title
                specific.draft_title = title
                specific.save_revision().publish()
            return specific, False

    # Reuse any leftover Thai Patidina page (e.g. keepdb path collision).
    orphan = PatidinaPage.objects.filter(locale=locale).first()
    if orphan is not None:
        orphan.translation_key = page_en.translation_key
        orphan.title = PAGE_TITLES[language_code]
        orphan.draft_title = PAGE_TITLES[language_code]
        orphan.save()
        orphan.save_revision().publish()
        return orphan.specific, False

    copied = page_en.copy_for_translation(locale, copy_parents=True, alias=False)
    specific = copied.specific
    specific.title = PAGE_TITLES[language_code]
    specific.draft_title = PAGE_TITLES[language_code]
    specific.save_revision().publish()
    return specific, True


class Command(BaseCommand):
    help = "Ensure published PatidinaPage exists for English and Thai locales."

    def handle(self, *args, **options):
        site = Site.objects.filter(is_default_site=True).first()
        if site is None:
            site = Site.objects.first()
        if site is None:
            self.stderr.write("No Wagtail Site found.")
            return

        root = site.root_page
        page_en, created_en = _ensure_english_page(root)
        self.stdout.write(
            self.style.SUCCESS(
                f"{'Created' if created_en else 'Found'} English PatidinaPage at "
                f"{page_en.url} (id={page_en.pk})"
            )
        )

        page_th, created_th = _ensure_translation(page_en, "th")
        self.stdout.write(
            self.style.SUCCESS(
                f"{'Created' if created_th else 'Found'} Thai PatidinaPage at "
                f"{page_th.url} (id={page_th.pk})"
            )
        )
