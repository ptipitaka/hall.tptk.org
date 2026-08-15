#!/usr/bin/env python3
"""Regression: identical shared footnotes reuse one mark per page.

After ≥2 latex runs, five ``\\csromansharedfootnote`` callouts with the same
id on one page must print the note body once and reuse the same number.
An interleaved different note still gets its own number.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

try:
    import fitz
except ImportError:  # pragma: no cover
    fitz = None  # type: ignore

BOOKS = Path(__file__).resolve().parents[1]

SHARED_ID = "tesamyevatest0001"
SHARED_BODY = "เตสํเยวซิงก์นิคฺคหีตสนฺธิ"
OTHER_BODY = "ปญฺญาเปยฺยซิงก์ (สี, สฺยา)"
SHARED_NEEDLE = "เตสํเยวซิงก์"
OTHER_NEEDLE = "ปญฺญาเปยฺยซิงก์"


def _page_texts(pdf: Path) -> list[str]:
    assert fitz is not None
    doc = fitz.open(pdf)
    try:
        return [page.get_text() for page in doc]
    finally:
        doc.close()


class SharedFootnoteTests(unittest.TestCase):
    @unittest.skipIf(fitz is None, "PyMuPDF required")
    @unittest.skipUnless(shutil.which("latexmk"), "latexmk required")
    def test_identical_notes_share_one_body_per_page(self) -> None:
        tex = rf"""
\documentclass[11pt,twoside]{{memoir}}
\input{{shared/style/preamble.tex}}
\begin{{document}}
\mainmatter
\noindent
ก \csromansharedfootnote{{{SHARED_ID}}}{{{SHARED_BODY}}}
ข \footnote{{{OTHER_BODY}}}
ค \csromansharedfootnote{{{SHARED_ID}}}{{{SHARED_BODY}}}
ง \csromansharedfootnote{{{SHARED_ID}}}{{{SHARED_BODY}}}
จ \csromansharedfootnote{{{SHARED_ID}}}{{{SHARED_BODY}}}
ฉ \csromansharedfootnote{{{SHARED_ID}}}{{{SHARED_BODY}}}
\end{{document}}
"""
        with tempfile.TemporaryDirectory(dir=BOOKS / "build") as tmp:
            tmp_path = Path(tmp)
            main = tmp_path / "shared_fn.tex"
            main.write_text(tex, encoding="utf-8")
            proc = subprocess.run(
                [
                    "latexmk",
                    "-lualatex",
                    "-interaction=nonstopmode",
                    f"-outdir={tmp_path}",
                    str(main),
                ],
                cwd=BOOKS,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            pdf = tmp_path / "shared_fn.pdf"
            self.assertTrue(
                pdf.is_file(),
                f"latexmk failed (exit {proc.returncode})\n"
                f"{proc.stdout[-2000:]}\n{proc.stderr[-2000:]}",
            )
            pages = _page_texts(pdf)
            self.assertGreaterEqual(len(pages), 1)
            joined = "\n".join(pages)
            (tmp_path / "page_dump.txt").write_text(joined, encoding="utf-8")
            self.assertEqual(
                joined.count(SHARED_NEEDLE),
                1,
                f"expected one shared footnote body, dump:\n{joined!r}",
            )
            self.assertEqual(joined.count(OTHER_NEEDLE), 1)


if __name__ == "__main__":
    unittest.main()
