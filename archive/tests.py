from django.test import TestCase


class ArchiveAppTests(TestCase):
    def test_app_loaded(self):
        from django.apps import apps

        self.assertTrue(apps.is_installed("archive"))
