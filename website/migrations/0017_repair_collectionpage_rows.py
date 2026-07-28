# Repair CollectionPage rows lost during a partial 0015 apply.

from django.db import migrations


def _repair_orphaned_collection_pages(apps, schema_editor):
    connection = schema_editor.connection
    Page = apps.get_model("wagtailcore", "Page")
    Revision = apps.get_model("wagtailcore", "Revision")
    ContentType = apps.get_model("contenttypes", "ContentType")

    try:
        collection_ct = ContentType.objects.get(
            app_label="website", model="collectionpage"
        )
    except ContentType.DoesNotExist:
        return

    with connection.cursor() as cursor:
        cursor.execute("SELECT coderedpage_ptr_id FROM website_collectionpage")
        existing = {row[0] for row in cursor.fetchall()}

    for page in Page.objects.filter(content_type=collection_ct):
        if page.pk in existing:
            continue

        revision = (
            Revision.objects.filter(object_id=page.pk)
            .order_by("-created_at")
            .first()
        )
        if revision is None:
            continue

        content = revision.content
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO website_collectionpage (
                    coderedpage_ptr_id,
                    code,
                    description,
                    catalog_sort_order,
                    classification_id,
                    tradition_id,
                    scroll_bg_opacity,
                    body
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (coderedpage_ptr_id) DO NOTHING
                """,
                [
                    page.pk,
                    content.get("code") or page.slug,
                    content.get("description") or "",
                    content.get("catalog_sort_order") or 0,
                    content.get("classification"),
                    content.get("tradition"),
                    content.get("scroll_bg_opacity") or "0.20",
                    content.get("body"),
                ],
            )


def _noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("website", "0016_alter_collectionpage_body"),
    ]

    operations = [
        migrations.RunPython(_repair_orphaned_collection_pages, _noop),
    ]
