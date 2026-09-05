"""Remove Chinese (zh) page locale and related content from the site."""

from django.db import migrations


def remove_chinese_locale(apps, schema_editor):
    # Use the historical apps registry, not live models. A data migration
    # must resolve models via `apps.get_model` so that the ORM collector
    # only sees tables/columns that exist at *this* point in the migration
    # graph. Importing the live model (e.g. `from wagtail.models import Locale`)
    # makes `locale.delete()` cascade-query tables or columns that are added
    # by later migrations (e.g. snippets_country, TranslationSource.schema_version),
    # which raises when the schema is not yet at that state.
    Locale = apps.get_model("wagtailcore", "Locale")
    Page = apps.get_model("wagtailcore", "Page")

    locale = Locale.objects.filter(language_code="zh").first()
    if locale is None:
        return

    for page in Page.objects.filter(locale=locale).order_by("-depth"):
        # Concrete page delete cleans revisions / translations links.
        page.specific.delete()

    snippet_model_names = (
        ("snippets", "Classification"),
        ("snippets", "Tradition"),
        ("snippets", "ContentLanguage"),
        ("snippets", "ContentScript"),
        ("snippets", "SegmentKind"),
        ("snippets", "CanonicalSection"),
    )
    for app_label, model_name in snippet_model_names:
        model = apps.get_model(app_label, model_name)
        model.objects.filter(locale=locale).delete()

    Navbar = apps.get_model("coderedcms", "Navbar")
    Navbar.objects.filter(name="main-zh").delete()
    locale.delete()


class Migration(migrations.Migration):

    dependencies = [
        ("website", "0025_editionpage_volume_extent"),
        ("snippets", "0003_remove_edition_collection_and_more"),
        # 0004 creates the Country model (snippets_country). remove_chinese_locale
        # calls locale.delete(), whose cascade collector queries snippets_country
        # even when no zh Country exists, so the table must exist before 0026 runs.
        ("snippets", "0004_country_on_collection"),
        ("coderedcms", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(remove_chinese_locale, migrations.RunPython.noop),
    ]
