# EditionPage → CoderedWebPage inheritance change.

import django.db.models.deletion
import wagtail.fields
from django.db import migrations, models


def _column_exists(cursor, table, column):
    cursor.execute(
        """
        SELECT 1 FROM information_schema.columns
        WHERE table_name = %s AND column_name = %s
        """,
        [table, column],
    )
    return cursor.fetchone() is not None


def _has_primary_key(cursor, table):
    cursor.execute(
        """
        SELECT 1 FROM pg_constraint c
        JOIN pg_class t ON c.conrelid = t.oid
        WHERE t.relname = %s AND c.contype = 'p'
        """,
        [table],
    )
    return cursor.fetchone() is not None


def _ensure_coderedpage(cursor, page_ptr_id):
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


def _migrate_editionpage_to_coderedpage(apps, schema_editor):
    connection = schema_editor.connection
    table = "website_editionpage"

    with connection.cursor() as cursor:
        if not _column_exists(cursor, table, "body"):
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN body jsonb NULL")

        if not _column_exists(cursor, table, "coderedpage_ptr_id"):
            cursor.execute(
                f"""
                ALTER TABLE {table}
                ADD COLUMN coderedpage_ptr_id integer NULL
                REFERENCES coderedcms_coderedpage(page_ptr_id)
                DEFERRABLE INITIALLY DEFERRED
                """
            )

        has_page_ptr = _column_exists(cursor, table, "page_ptr_id")

        if has_page_ptr:
            cursor.execute(
                """
                SELECT page_ptr_id
                FROM website_editionpage
                WHERE coderedpage_ptr_id IS NULL
                """
            )
            for (page_ptr_id,) in cursor.fetchall():
                _ensure_coderedpage(cursor, page_ptr_id)
                cursor.execute(
                    """
                    UPDATE website_editionpage
                    SET coderedpage_ptr_id = %s
                    WHERE page_ptr_id = %s
                    """,
                    [page_ptr_id, page_ptr_id],
                )

        cursor.execute(
            """
            SELECT coderedpage_ptr_id
            FROM website_editionpage
            WHERE coderedpage_ptr_id IS NOT NULL
            """
        )
        for (ptr_id,) in cursor.fetchall():
            _ensure_coderedpage(cursor, ptr_id)

        if has_page_ptr:
            cursor.execute(f"ALTER TABLE {table} DROP COLUMN page_ptr_id CASCADE")

        if not _has_primary_key(cursor, table):
            cursor.execute(
                f"ALTER TABLE {table} ADD PRIMARY KEY (coderedpage_ptr_id)"
            )


def _unmigrate_editionpage_to_coderedpage(apps, schema_editor):
    connection = schema_editor.connection
    table = "website_editionpage"

    with connection.cursor() as cursor:
        if not _column_exists(cursor, table, "coderedpage_ptr_id"):
            return

        if not _column_exists(cursor, table, "page_ptr_id"):
            cursor.execute(
                f"""
                ALTER TABLE {table}
                ADD COLUMN page_ptr_id integer NULL
                REFERENCES wagtailcore_page(id)
                DEFERRABLE INITIALLY DEFERRED
                """
            )
            cursor.execute(
                f"""
                UPDATE {table}
                SET page_ptr_id = coderedpage_ptr_id
                """
            )
            cursor.execute(
                f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {table}_pkey"
            )
            cursor.execute(
                f"ALTER TABLE {table} ADD PRIMARY KEY (page_ptr_id)"
            )
            cursor.execute(
                f"ALTER TABLE {table} DROP COLUMN coderedpage_ptr_id"
            )


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ("coderedcms", "0042_remove_coderedsessionformsubmission_thumbnails_by_path"),
        ("website", "0018_migrate_intro_description_to_body"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name="editionpage",
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
                    model_name="editionpage",
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
                migrations.RemoveField(
                    model_name="editionpage",
                    name="page_ptr",
                ),
            ],
            database_operations=[
                migrations.RunPython(
                    _migrate_editionpage_to_coderedpage,
                    _unmigrate_editionpage_to_coderedpage,
                ),
            ],
        ),
    ]
