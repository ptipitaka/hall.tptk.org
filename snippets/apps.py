from django.apps import AppConfig


class SnippetsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "snippets"

    def ready(self):
        from snippets import wagtail_hooks  # noqa: F401
