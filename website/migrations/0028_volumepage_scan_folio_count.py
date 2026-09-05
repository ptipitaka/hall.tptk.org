from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("website", "0027_country_on_collection"),
    ]

    operations = [
        migrations.AddField(
            model_name="volumepage",
            name="scan_folio_count",
            field=models.PositiveIntegerField(
                blank=True,
                help_text=(
                    "Declared number of scan pages in this volume. "
                    "Generate ScanFolio rows 1..N on the default-locale volume only."
                ),
                null=True,
            ),
        ),
    ]
