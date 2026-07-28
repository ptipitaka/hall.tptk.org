# Ensure CatalogIndexPage uses website/catalog_index_page.html (not a CRX override).

from django.db import migrations


def clear_catalogindex_custom_template(apps, schema_editor):
    CatalogIndexPage = apps.get_model("website", "CatalogIndexPage")
    CoderedPage = apps.get_model("coderedcms", "CoderedPage")
    ptr_ids = CatalogIndexPage.objects.values_list("coderedpage_ptr_id", flat=True)
    CoderedPage.objects.filter(page_ptr_id__in=ptr_ids).update(custom_template="")


class Migration(migrations.Migration):

    dependencies = [
        ("website", "0011_clear_catalogindex_custom_template"),
    ]

    operations = [
        migrations.RunPython(
            clear_catalogindex_custom_template,
            migrations.RunPython.noop,
        ),
    ]
