"""Switch Collection/Edition content language FK to multi-select M2M."""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("snippets", "0001_initial"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="collection",
            name="content_language",
        ),
        migrations.RemoveField(
            model_name="edition",
            name="content_language",
        ),
        migrations.AddField(
            model_name="collection",
            name="content_languages",
            field=models.ManyToManyField(
                blank=True,
                related_name="collections",
                to="snippets.contentlanguage",
                verbose_name="content languages",
            ),
        ),
        migrations.AddField(
            model_name="edition",
            name="content_languages",
            field=models.ManyToManyField(
                blank=True,
                help_text="Optional override of the collection's content languages.",
                related_name="editions",
                to="snippets.contentlanguage",
                verbose_name="content languages",
            ),
        ),
    ]
