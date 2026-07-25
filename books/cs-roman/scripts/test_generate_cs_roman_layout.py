"""Unit tests for cs-roman TeX layout emit helpers."""

from __future__ import annotations

import unittest
from pathlib import Path

from paths import BOOKS, ensure_import_paths

ensure_import_paths()

from cs_roman_segments import DEFAULT_LAYOUT, save_document  # noqa: E402
from generate_cs_roman_tex import (  # noqa: E402
    layout_apply_command,
    word_space_factor,
    wrap_word_space,
)


class GenerateCsRomanLayoutTests(unittest.TestCase):
    def test_layout_apply_includes_all_keys(self) -> None:
        cmd = layout_apply_command(DEFAULT_LAYOUT)
        self.assertTrue(cmd.startswith(r"\csromanlayoutapply{"))
        # word_space 2.5 → factor 1; line_space 1.25; dimensions pass through.
        self.assertIn("{1}{1.25}{21.6pt}{6.3pt}{6.3pt}{65pt}{2.5em}%", cmd)

    def test_page_override_changes_every_slot(self) -> None:
        layout = {
            "word_space": 1.25,
            "line_space": 1.1,
            "par_indent": "18pt",
            "par_skip": "4pt",
            "gatha_stanza_skip": "4.5pt",
            "gatha_indent": "50pt",
            "emergency_stretch": "3em",
        }
        cmd = layout_apply_command(layout)
        self.assertEqual(word_space_factor(1.25), "0.5")
        self.assertIn("{0.5}{1.1}{18pt}{4pt}{4.5pt}{50pt}{3em}%", cmd)

    def test_wrap_word_space_only_when_segment_differs(self) -> None:
        seg = {"page": 1, "order": 1}
        body = [r"\prose{ก}"]
        self.assertEqual(
            wrap_word_space(
                seg, body, page_word_space=1.0, segment_word_space=1.0
            ),
            body,
        )
        wrapped = wrap_word_space(
            seg, body, page_word_space=2.5, segment_word_space=1.0
        )
        self.assertEqual(wrapped[0], r"\csromanwordspacebegin{0.4}%")
        self.assertEqual(wrapped[-1], r"\csromanwordspaceend")

    def test_generate_emits_volume_and_page_layout(self) -> None:
        from generate_cs_roman_tex import generate

        volume_id = "_layout_test_vol"
        vol = BOOKS / "volumes" / volume_id
        data_path = vol / "data" / "segments.json"
        layout_path = vol / "data" / "layout.json"
        out_path = vol / "tex" / "body.generated.tex"
        try:
            data_path.parent.mkdir(parents=True, exist_ok=True)
            doc = {
                "schema_version": 1,
                "source": "books/cs-roman/source/01Vin01.pdf",
                "content_start_pdf_page": 24,
                "layout": {**DEFAULT_LAYOUT, "line_space": 1.2},
                "page_layout": {
                    "2": {
                        "line_space": 1.1,
                        "word_space": 2.0,
                        "par_indent": "20pt",
                        "par_skip": "5pt",
                        "gatha_stanza_skip": "5pt",
                        "gatha_indent": "60pt",
                        "emergency_stretch": "2em",
                        "segments": {"1": {"word_space": 1.0}},
                    }
                },
                "segments": [
                    {
                        "page": 1,
                        "order": 1,
                        "segment_type": "prose",
                        "text": [{"script": "thai", "value": "หนึ่ง"}],
                    },
                    {
                        "page": 2,
                        "order": 2,
                        "segment_type": "prose",
                        "text": [{"script": "thai", "value": "สอง"}],
                    },
                ],
            }
            save_document(data_path, doc)
            written = generate(volume_id)
            text = written.read_text(encoding="utf-8")
            self.assertIn(r"\csromanlayoutapply{1}{1.2}{21.6pt}", text)
            self.assertIn(r"\csromanpage{2}", text)
            self.assertIn(
                r"\csromanlayoutapply{0.8}{1.1}{20pt}{5pt}{5pt}{60pt}{2em}%",
                text,
            )
            self.assertIn(r"\csromanwordspacebegin{0.4}%", text)
        finally:
            for path in (out_path, data_path, layout_path):
                if path.is_file():
                    path.unlink()
            for path in (data_path.parent, out_path.parent, vol):
                try:
                    path.rmdir()
                except OSError:
                    pass


if __name__ == "__main__":
    unittest.main()
