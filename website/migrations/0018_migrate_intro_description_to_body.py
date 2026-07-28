# Migrate intro/description into body StreamField; remove legacy fields.

import json

from django.db import migrations


def _body_list(raw):
    if not raw:
        return []
    if isinstance(raw, str):
        return json.loads(raw) if raw.strip() else []
    return list(raw)


def _prepend_html(body, html):
    blocks = _body_list(body)
    if html and str(html).strip():
        return [{"type": "html", "value": str(html)}] + blocks
    return blocks or None


def _migrate_intro_and_description_to_body(apps, schema_editor):
    connection = schema_editor.connection

    with connection.cursor() as cursor:
        cursor.execute("SELECT coderedpage_ptr_id, intro, body FROM website_catalogindexpage")
        catalog_rows = cursor.fetchall()

    for page_ptr_id, intro, body in catalog_rows:
        merged = _prepend_html(body, intro)
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE website_catalogindexpage SET body = %s WHERE coderedpage_ptr_id = %s",
                [json.dumps(merged) if merged else None, page_ptr_id],
            )

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT coderedpage_ptr_id, description, body FROM website_collectionpage"
        )
        collection_rows = cursor.fetchall()

    for page_ptr_id, description, body in collection_rows:
        merged = _prepend_html(body, description)
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE website_collectionpage SET body = %s WHERE coderedpage_ptr_id = %s",
                [json.dumps(merged) if merged else None, page_ptr_id],
            )


class Migration(migrations.Migration):

    dependencies = [
        ("website", "0017_repair_collectionpage_rows"),
    ]

    operations = [
        migrations.RunPython(
            _migrate_intro_and_description_to_body,
            migrations.RunPython.noop,
        ),
        migrations.RemoveField(
            model_name="catalogindexpage",
            name="intro",
        ),
        migrations.RemoveField(
            model_name="collectionpage",
            name="description",
        ),
    ]
