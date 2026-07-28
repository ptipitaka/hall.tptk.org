# Generated manually for CatalogIndexPage → CoderedWebPage inheritance change.

import django.db.models.deletion
from django.db import migrations, models


def _migrate_catalogindexpage_to_coderedpage(apps, schema_editor):
    connection = schema_editor.connection
    with connection.cursor() as cursor:
        cursor.execute("SELECT page_ptr_id, intro, body FROM website_catalogindexpage")
        rows = cursor.fetchall()

    for page_ptr_id, intro, body in rows:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM website_catalogindexpage WHERE page_ptr_id = %s",
                [page_ptr_id],
            )
            cursor.execute(
                """
                INSERT INTO coderedcms_coderedpage (
                    page_ptr_id,
                    index_show_subpages,
                    index_order_by,
                    index_num_per_page,
                    custom_template,
                    content_walls,
                    canonical_url,
                    related_num,
                    related_show
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (page_ptr_id) DO NOTHING
                """,
                [page_ptr_id, False, "", 10, "", "[]", "", 3, False],
            )
            cursor.execute(
                """
                INSERT INTO website_catalogindexpage (
                    page_ptr_id,
                    coderedpage_ptr_id,
                    intro,
                    body
                ) VALUES (%s, %s, %s, %s)
                """,
                [page_ptr_id, page_ptr_id, intro, body],
            )


def _unmigrate_catalogindexpage_to_coderedpage(apps, schema_editor):
    connection = schema_editor.connection
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT coderedpage_ptr_id, intro, body FROM website_catalogindexpage"
        )
        rows = cursor.fetchall()

    for page_ptr_id, intro, body in rows:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM website_catalogindexpage WHERE coderedpage_ptr_id = %s",
                [page_ptr_id],
            )
            cursor.execute(
                "DELETE FROM coderedcms_coderedpage WHERE page_ptr_id = %s",
                [page_ptr_id],
            )
            cursor.execute(
                """
                INSERT INTO website_catalogindexpage (page_ptr_id, intro, body)
                VALUES (%s, %s, %s)
                """,
                [page_ptr_id, intro, body],
            )


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ("coderedcms", "0042_remove_coderedsessionformsubmission_thumbnails_by_path"),
        ("website", "0007_catalogindexpage_collectionpage_editionpage_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="catalogindexpage",
            name="coderedpage_ptr",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="+",
                to="coderedcms.coderedpage",
            ),
        ),
        migrations.RunPython(
            _migrate_catalogindexpage_to_coderedpage,
            _unmigrate_catalogindexpage_to_coderedpage,
        ),
        migrations.RemoveField(
            model_name="catalogindexpage",
            name="page_ptr",
        ),
        migrations.AlterField(
            model_name="catalogindexpage",
            name="coderedpage_ptr",
            field=models.OneToOneField(
                auto_created=True,
                on_delete=django.db.models.deletion.CASCADE,
                parent_link=True,
                primary_key=True,
                serialize=False,
                to="coderedcms.coderedpage",
            ),
        ),
    ]
