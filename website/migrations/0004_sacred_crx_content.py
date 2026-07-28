from django.db import migrations, transaction


def seed_sacred_crx_content(apps, schema_editor):
    """
    Seed SACRED homepage content.

    Search indexing may run in the same migrate transaction before search
    tables exist; disable indexing for this seed so migrate can finish.
    """
    from website.sacred_content import seed_sacred_content

    try:
        import modelsearch.index as search_index
    except ImportError:
        search_index = None

    original = None
    if search_index is not None:
        original = search_index.insert_or_update_object
        search_index.insert_or_update_object = lambda obj: None

    sid = transaction.savepoint()
    try:
        seed_sacred_content(force=True)
        transaction.savepoint_commit(sid)
    except Exception:
        transaction.savepoint_rollback(sid)
        raise
    finally:
        if search_index is not None and original is not None:
            search_index.insert_or_update_object = original


class Migration(migrations.Migration):

    dependencies = [
        ("website", "0003_scroll_background"),
        # Seed uses current CoderedWebPage model; wait until struct_org_* columns are removed.
        ("coderedcms", "0043_remove_coderedpage_struct_org_actions_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_sacred_crx_content, migrations.RunPython.noop),
    ]
