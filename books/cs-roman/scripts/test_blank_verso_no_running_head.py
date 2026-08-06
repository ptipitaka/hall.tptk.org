#!/usr/bin/env python3
"""Regression: blank verso before recto open has no running head.

``\\csromanensureoddpage`` feeds an even blank so the next sheet is odd.
That blank must use pagestyle plain (no piṭaka / page in the head).
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

try:
    import fitz
except ImportError:  # pragma: no cover
    fitz = None  # type: ignore

BOOKS = Path(__file__).resolve().parents[1]


@unittest.skipUnless(fitz is not None, "pymupdf required")
@unittest.skipUnless(shutil.which("latexmk"), "latexmk required")
class BlankVersoNoRunningHeadTests(unittest.TestCase):
    def test_ensureodd_blank_has_no_pitaka_head(self) -> None:
        tex = r"""
\documentclass[11pt,twoside,openany]{memoir}
\input{shared/style/preamble.tex}
\begin{document}
\mainmatter
\pagestyle{csroman}
\setcsromanpitaka{วินยปิฎก}
\setcsromanhead{ปาจิตฺติยปาฬิ}
\noindent Body on recto.\par
\clearpage
% Now on an even empty sheet — feed blank verso, then odd body.
\csromanensureoddpage
\noindent After blank verso.\par
\end{document}
"""
        with tempfile.TemporaryDirectory(dir=BOOKS / "build") as tmp:
            tmp_path = Path(tmp)
            main = tmp_path / "blank.tex"
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
            pdf = tmp_path / "blank.pdf"
            if not pdf.is_file():
                self.fail(
                    "latexmk did not produce blank.pdf\n"
                    + (proc.stdout or "")[-2500:]
                    + (proc.stderr or "")[-2500:]
                )
            doc = fitz.open(pdf)
            try:
                self.assertGreaterEqual(doc.page_count, 3)
                # Page 2 = inserted blank verso (1-based).
                blank = doc[1].get_text().strip()
                self.assertNotIn(
                    "วินยปิฎก",
                    blank,
                    f"blank verso still shows running head: {blank!r}",
                )
                self.assertEqual(
                    blank,
                    "",
                    f"blank verso should be empty, got: {blank!r}",
                )
                # Page 3 body present (Thai interword spaces may split tokens).
                after = doc[2].get_text()
                self.assertIn("After", after)
                self.assertIn("verso", after)
            finally:
                doc.close()

    def test_recto_head_joins_cha_h1_without_trailing_sep(self) -> None:
        """cha h1 head must not gain a stray separator before the folio.

        ``\\csromanheadjoin`` skips empty parts; an empty trailing argument
        (the odd head's third slot) must not emit ``\\csromanheadsep``.
        The separator is now a single non-breaking space (no bullet), so
        the cha and h1 parts must both appear with no bullet between them
        and no separator leaking before the folio.
        """
        tex = r"""
\documentclass[11pt,twoside,openany]{memoir}
\input{shared/style/preamble.tex}
\begin{document}
\mainmatter
\pagestyle{csroman}
\setcsromanheadcha{4. นิสฺสคฺคิยกณฺฑ}
\setcsromanheadh{1. จีวรวคฺค}
\noindent Body on recto.\par
\clearpage
\noindent Body on verso.\par
\end{document}
"""
        with tempfile.TemporaryDirectory(dir=BOOKS / "build") as tmp:
            tmp_path = Path(tmp)
            main = tmp_path / "head.tex"
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
            pdf = tmp_path / "head.pdf"
            if not pdf.is_file():
                self.fail(
                    "latexmk did not produce head.pdf\n"
                    + (proc.stdout or "")[-2500:]
                    + (proc.stderr or "")[-2500:]
                )
            doc = fitz.open(pdf)
            try:
                # Page 1 is recto: head = "4. นิสฺสคฺคิยกณฺฑ 1. จีวรวคฺค", folio 1.
                page = doc[0]
                clip = fitz.Rect(0, 0, page.rect.width, page.rect.height * 0.12)
                top = page.get_text(clip=clip).split()
                joined = " ".join(top)
                self.assertIn("นิสฺสคฺคิยกณฺฑ", joined)
                self.assertIn("จีวรวคฺค", joined)
                self.assertIn("4.", joined)
                self.assertIn("1.", joined)
                # No bullet between cha and h1, and none before the folio.
                self.assertEqual(top.count("•"), 0)
                self.assertEqual(top[-1], "1")
            finally:
                doc.close()


if __name__ == "__main__":
    unittest.main()
