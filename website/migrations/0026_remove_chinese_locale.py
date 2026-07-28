"""Remove Chinese (zh) page locale and related content from the site."""

from django.db import migrations


def remove_chinese_locale(apps, schema_editor):
    from coderedcms.models.snippet_models import Navbar
    from wagtail.models import Locale, Page

    from snippets.models import (
        CanonicalSection,
        Classification,
        ContentLanguage,
        ContentScript,
        SegmentKind,
        Tradition,
    )

    locale = Locale.objects.filter(language_code="zh").first()
    if locale is None:
        return

    for page in Page.objects.filter(locale=locale).order_by("-depth"):
        # Concrete page delete cleans revisions / translations links.
        page.specific.delete()

    snippet_models = (
        Classification,
        Tradition,
        ContentLanguage,
        ContentScript,
        SegmentKind,
        CanonicalSection,
    )
    for model in snippet_models:
        model.objects.filter(locale=locale).delete()

    Navbar.objects.filter(name="main-zh").delete()
    locale.delete()


class Migration(migrations.Migration):

    dependencies = [
        ("website", "0025_editionpage_volume_extent"),
        ("snippets", "0003_remove_edition_collection_and_more"),
        ("coderedcms", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(remove_chinese_locale, migrations.RunPython.noop),
    ]
