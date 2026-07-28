# Sync Wagtail revision JSON after 0018 migrated body columns directly.

import json

from django.db import migrations


def _body_list(raw):
    if not raw:
        return []
    if isinstance(raw, str):
        return json.loads(raw) if raw.strip() else []
    return list(raw)


def _sync_body_revisions(apps, schema_editor):
    connection = schema_editor.connection
    Page = apps.get_model("wagtailcore", "Page")
    Revision = apps.get_model("wagtailcore", "Revision")

    for table, content_type_app, content_type_model in (
        ("website_catalogindexpage", "website", "catalogindexpage"),
        ("website_collectionpage", "website", "collectionpage"),
    ):
        with connection.cursor() as cursor:
            cursor.execute(
                f"SELECT coderedpage_ptr_id, body FROM {table} WHERE body IS NOT NULL"
            )
            rows = cursor.fetchall()

        for page_ptr_id, body in rows:
            body_blocks = _body_list(body)
            if not body_blocks:
                continue

            page = Page.objects.filter(pk=page_ptr_id).first()
            if page is None:
                continue

            revision = (
                Revision.objects.filter(object_id=page_ptr_id)
                .order_by("-created_at")
                .first()
            )
            if revision is None:
                continue

            content = revision.content
            revision_body = _body_list(content.get("body"))
            if revision_body:
                continue

            content["body"] = body_blocks
            revision.content = content
            revision.save(update_fields=["content"])


class Migration(migrations.Migration):

    dependencies = [
        ("website", "0021_alter_editionpage_body_alter_volumepage_body"),
    ]

    operations = [
        migrations.RunPython(_sync_body_revisions, migrations.RunPython.noop),
    ]
