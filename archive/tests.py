from django.test import SimpleTestCase, override_settings

from archive.models import build_scan_relative_path, _scan_root


class ScanPathTests(SimpleTestCase):
    def test_relative_path_uses_volume_index_not_vol_code(self):
        path = build_scan_relative_path("ch", "pali2552ro", 1, 1)
        self.assertEqual(path, "ch/pali2552ro/1/1.png")

    def test_relative_path_volume_ten(self):
        path = build_scan_relative_path("ch", "pali2552ro", 10, 42)
        self.assertEqual(path, "ch/pali2552ro/10/42.png")

    @override_settings(
        SCAN_USE_REMOTE=True,
        SCAN_BASE_URL="https://sacred.tipitakahall.org",
        SCAN_PREFIX="tipitaka",
    )
    def test_scan_root_remote_cdn(self):
        self.assertEqual(
            _scan_root(),
            "https://sacred.tipitakahall.org/tipitaka",
        )

    @override_settings(
        SCAN_USE_REMOTE=False,
        MEDIA_URL="/media/",
        SCAN_PREFIX="tipitaka",
    )
    def test_scan_root_local_media(self):
        self.assertEqual(_scan_root(), "/media/tipitaka")


class ArchiveAppTests(SimpleTestCase):
    def test_app_loaded(self):
        from django.apps import apps

        self.assertTrue(apps.is_installed("archive"))
