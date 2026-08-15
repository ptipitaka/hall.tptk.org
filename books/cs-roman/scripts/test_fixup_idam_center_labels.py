"""Tests for demoting Idaṃ / อิทํ center labels."""

from __future__ import annotations

import unittest

from fixup_idam_center_labels import fix_document


class FixupIdamCenterLabelsTests(unittest.TestCase):
    def test_demotes_idam_keeps_other_title(self) -> None:
        data = {
            "schema_version": 1,
            "segments": [
                {
                    "page": 134,
                    "order": 1,
                    "segment_type": "title",
                    "source_layout": "center",
                    "heading_kind": "h2",
                    "in_toc": False,
                    "text": [
                        {"script": "roman", "value": "Idaṃ sabbamūlakaṃ"},
                        {"script": "thai", "value": "อิทํ สพฺพมูลกํ"},
                    ],
                },
                {
                    "page": 50,
                    "order": 2,
                    "segment_type": "title",
                    "source_layout": "center",
                    "heading_kind": "h2",
                    "text": [
                        {
                            "script": "roman",
                            "value": "Vinītavatthu",
                            "runs": [{"value": "Vinītavatthu", "bold": True}],
                        }
                    ],
                },
            ],
        }
        n = fix_document(data)
        self.assertEqual(n, 1)
        self.assertIsNone(data["segments"][0].get("heading_kind"))
        self.assertEqual(data["segments"][1].get("heading_kind"), "h2")


if __name__ == "__main__":
    unittest.main()
