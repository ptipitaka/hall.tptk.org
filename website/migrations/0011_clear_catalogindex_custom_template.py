# Clear custom_template override so CatalogIndexPage uses website/catalog_index_page.html.

from django.db import migrations


def clear_catalogindex_custom_template(apps, schema_editor):
    CatalogIndexPage = apps.get_model("website", "CatalogIndexPage")
    CoderedPage = apps.get_model("coderedcms", "CoderedPage")
    ptr_ids = CatalogIndexPage.objects.values_list("coderedpage_ptr_id", flat=True)
    CoderedPage.objects.filter(
        page_ptr_id__in=ptr_ids,
        custom_template="coderedcms/pages/web_page_notitle.html",
    ).update(custom_template="")


class Migration(migrations.Migration):

    dependencies = [
        ("website", "0010_catalogindex_scroll_background"),
    ]

    operations = [
        migrations.RunPython(
            clear_catalogindex_custom_template,
            migrations.RunPython.noop,
        ),
    ]
