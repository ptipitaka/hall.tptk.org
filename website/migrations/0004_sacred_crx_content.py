from django.db import migrations


def seed_sacred_crx_content(apps, schema_editor):
    from website.sacred_content import seed_sacred_content

    seed_sacred_content(force=True)


class Migration(migrations.Migration):

    dependencies = [
        ("website", "0003_scroll_background"),
    ]

    operations = [
        migrations.RunPython(seed_sacred_crx_content, migrations.RunPython.noop),
    ]
