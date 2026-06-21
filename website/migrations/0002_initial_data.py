from django.db import migrations
from wagtail.models import Locale


def initial_data(apps, schema_editor):
    ContentType = apps.get_model("contenttypes.ContentType")
    Page = apps.get_model("wagtailcore.Page")
    Site = apps.get_model("wagtailcore.Site")
    WebPage = apps.get_model("website.WebPage")

    webpage_content_type, _created = ContentType.objects.get_or_create(
        model="webpage",
        app_label="website",
    )

    for code in ("en", "th", "zh"):
        Locale.objects.get_or_create(language_code=code)

    default_locale = Locale.objects.get(language_code="en")

    Page.objects.filter(slug="home").delete()

    homepage = WebPage.objects.create(
        title="Home",
        slug="home",
        custom_template="coderedcms/pages/home_page.html",
        content_type=webpage_content_type,
        path="00010001",
        depth=2,
        numchild=0,
        url_path="/home/",
        locale_id=default_locale.id,
    )

    Site.objects.all().delete()
    Site.objects.create(
        hostname="localhost",
        port=8000,
        site_name="hall.tptk.org",
        root_page_id=homepage.id,
        is_default_site=True,
    )


class Migration(migrations.Migration):

    dependencies = [
        ("coderedcms", "0001_initial"),
        ("wagtailcore", "0057_page_locale_fields_notnull"),
        ("website", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(initial_data),
    ]
