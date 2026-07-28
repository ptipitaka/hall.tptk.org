# Generated manually for CollectionPage → CoderedWebPage inheritance change.

import django.db.models.deletion
import wagtail.fields
from django.db import migrations, models


def _migrate_collectionpage_to_coderedpage(apps, schema_editor):
    connection = schema_editor.connection
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT page_ptr_id, code, description, catalog_sort_order,
                   classification_id, tradition_id, scroll_bg_opacity, cover_image_id
            FROM website_collectionpage
            """
        )
        rows = cursor.fetchall()

    for (
        page_ptr_id,
        code,
        description,
        catalog_sort_order,
        classification_id,
        tradition_id,
        scroll_bg_opacity,
        cover_image_id,
    ) in rows:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM website_collectionpage WHERE page_ptr_id = %s",
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
                    cover_image_id,
                    content_walls,
                    canonical_url,
                    related_num,
                    related_show
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (page_ptr_id) DO NOTHING
                """,
                [
                    page_ptr_id,
                    False,
                    "",
                    10,
                    "",
                    cover_image_id,
                    "[]",
                    "",
                    3,
                    False,
                ],
            )
            cursor.execute(
                """
                INSERT INTO website_collectionpage (
                    page_ptr_id,
                    coderedpage_ptr_id,
                    code,
                    description,
                    catalog_sort_order,
                    classification_id,
                    tradition_id,
                    scroll_bg_opacity,
                    body
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                [
                    page_ptr_id,
                    page_ptr_id,
                    code,
                    description,
                    catalog_sort_order,
                    classification_id,
                    tradition_id,
                    scroll_bg_opacity,
                    None,
                ],
            )


def _unmigrate_collectionpage_to_coderedpage(apps, schema_editor):
    connection = schema_editor.connection
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT cp.coderedpage_ptr_id, cp.code, cp.description, cp.catalog_sort_order,
                   cp.classification_id, cp.tradition_id, cp.scroll_bg_opacity,
                   cr.cover_image_id
            FROM website_collectionpage cp
            JOIN coderedcms_coderedpage cr ON cr.page_ptr_id = cp.coderedpage_ptr_id
            """
        )
        rows = cursor.fetchall()

    for (
        page_ptr_id,
        code,
        description,
        catalog_sort_order,
        classification_id,
        tradition_id,
        scroll_bg_opacity,
        cover_image_id,
    ) in rows:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM website_collectionpage WHERE coderedpage_ptr_id = %s",
                [page_ptr_id],
            )
            cursor.execute(
                "DELETE FROM coderedcms_coderedpage WHERE page_ptr_id = %s",
                [page_ptr_id],
            )
            cursor.execute(
                """
                INSERT INTO website_collectionpage (
                    page_ptr_id,
                    code,
                    description,
                    catalog_sort_order,
                    classification_id,
                    tradition_id,
                    scroll_bg_opacity,
                    cover_image_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                [
                    page_ptr_id,
                    code,
                    description,
                    catalog_sort_order,
                    classification_id,
                    tradition_id,
                    scroll_bg_opacity,
                    cover_image_id,
                ],
            )


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ("coderedcms", "0042_remove_coderedsessionformsubmission_thumbnails_by_path"),
        ("website", "0014_edition_content_languages_scripts_m2m"),
    ]

    operations = [
        migrations.AddField(
            model_name="collectionpage",
            name="body",
            field=wagtail.fields.StreamField(
                [("blank", 0)],
                blank=True,
                block_lookup={
                    0: ("wagtail.blocks.CharBlock", (), {"required": False}),
                },
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="collectionpage",
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
            _migrate_collectionpage_to_coderedpage,
            _unmigrate_collectionpage_to_coderedpage,
        ),
        migrations.RemoveField(
            model_name="collectionpage",
            name="page_ptr",
        ),
        migrations.RemoveField(
            model_name="collectionpage",
            name="cover_image",
        ),
        migrations.AlterField(
            model_name="collectionpage",
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
