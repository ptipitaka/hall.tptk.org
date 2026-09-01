"""Tests for fixup manifest load + residual parsing."""

from __future__ import annotations

import unittest

from fixup_manifest_lib import (
    load_manifest,
    parse_residual_count,
    pipeline_fixups,
    validate_manifest,
)


class ManifestTests(unittest.TestCase):
    def test_load_and_validate(self) -> None:
        data = load_manifest()
        self.assertGreaterEqual(int(data["version"]), 1)
        self.assertTrue(pipeline_fixups(data))
        ids = [f["id"] for f in data["fixups"]]
        self.assertIn("tassuddana_labels", ids)
        self.assertIn("false_heading_guesses", ids)
        self.assertIn("midword_bold_splits", ids)
        self.assertIn("item_corrections", ids)

    def test_rejects_bad_gate(self) -> None:
        data = load_manifest()
        data["fixups"][0]["gate"] = "nope"
        with self.assertRaises(ValueError):
            validate_manifest(data)


class ResidualParseTests(unittest.TestCase):
    def test_done_colon(self) -> None:
        self.assertEqual(parse_residual_count("Done: 413 retag(s)\n"), 413)

    def test_done_paren(self) -> None:
        self.assertEqual(
            parse_residual_count("Done (88 peel(s)) [dry-run]\n"), 88
        )

    def test_total_plain(self) -> None:
        self.assertEqual(parse_residual_count("total: 6\n"), 6)

    def test_running_headers_sum(self) -> None:
        out = (
            "total: peeled=1 cleared_center=2 fixed_item=0 "
            "dropped_titles=3 cont+=4\n"
        )
        self.assertEqual(parse_residual_count(out), 10)

    def test_edition_layout(self) -> None:
        self.assertEqual(
            parse_residual_count("0/80 file(s) (par_skip='8pt')\n"), 0
        )
        self.assertEqual(
            parse_residual_count("3/80 file(s) (par_skip='8pt')\n"), 3
        )

    def test_page_start(self) -> None:
        self.assertEqual(
            parse_residual_count("01Vin01: demoted=1 upgraded=2 changed=3\n"),
            3,
        )


if __name__ == "__main__":
    unittest.main()
