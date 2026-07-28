from django.db import migrations, models


def fill_name_en(apps, schema_editor):
    from patidina.important_day_names import english_name_for

    LunarDetail = apps.get_model("patidina", "LunarImportantDayDetail")
    SolarDetail = apps.get_model("patidina", "SolarImportantDayDetail")
    for model in (LunarDetail, SolarDetail):
        for row in model.objects.all():
            if not row.name_en:
                row.name_en = english_name_for(row.name)
                row.save(update_fields=["name_en"])


class Migration(migrations.Migration):

    dependencies = [
        ("patidina", "0002_patidinapage"),
    ]

    operations = [
        migrations.AddField(
            model_name="lunarimportantdaydetail",
            name="name_en",
            field=models.CharField(
                blank=True, default="", max_length=255, verbose_name="Name (English)"
            ),
        ),
        migrations.AddField(
            model_name="solarimportantdaydetail",
            name="name_en",
            field=models.CharField(
                blank=True, default="", max_length=255, verbose_name="Name (English)"
            ),
        ),
        migrations.AlterField(
            model_name="lunarimportantdaydetail",
            name="name",
            field=models.CharField(max_length=255, verbose_name="ชื่อ (ไทย)"),
        ),
        migrations.AlterField(
            model_name="solarimportantdaydetail",
            name="name",
            field=models.CharField(max_length=255, verbose_name="ชื่อ (ไทย)"),
        ),
        migrations.RunPython(fill_name_en, migrations.RunPython.noop),
    ]
