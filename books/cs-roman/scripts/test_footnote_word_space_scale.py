#!/usr/bin/env python3
"""Regression: footnote interword uses font natural glue, not body spaceskip.

Body ``\\csromanlayoutapply`` sets absolute ``\\spaceskip`` from ``\\normalsize``.
Footnotes must clear ``\\spaceskip`` after ``\\footnotesize`` so TeX uses the
face's fontdimen interword (preamble WordSpace), else word gaps stay body-wide
on the smaller face.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

BOOKS = Path(__file__).resolve().parents[1]

_DIM_RE = re.compile(
    r"^CSROMAN_FN_WS=(?P<body>[0-9.]+)pt,"
    r"(?P<inherited>[0-9.]+)pt,"
    r"(?P<fn>[0-9.]+)pt,"
    r"(?P<target>[0-9.]+)pt,"
    r"(?P<spaceskip>[0-9.]+)pt$",
    re.MULTILINE,
)


@unittest.skipUnless(shutil.which("latexmk"), "latexmk required")
class FootnoteWordSpaceScaleTests(unittest.TestCase):
    def test_footnote_uses_font_natural_word_space(self) -> None:
        tex = r"""
\documentclass[11pt,twoside]{memoir}
\def\csromanuseprintinggeometry{1}
\input{shared/style/preamble.tex}
\begin{document}
\csromanlayoutapply{1}{1.5}{21.6pt}{8pt}{8pt}{65pt}{2.5em}%
\newdimen\fnwsbody
\newdimen\fnwsinherited
\newdimen\fnwsfn
\newdimen\fnwstarget
\makeatletter
\settowidth\fnwsbody{\normalsize ก ก}%
\settowidth\fnwsinherited{%
  \reset@font\footnotesize ก ก}%
\settowidth\fnwsfn{%
  \csromanfn@selectfont ก ก}%
\settowidth\fnwstarget{%
  \reset@font\footnotesize
  \spaceskip=0pt\relax
  ก ก}%
\csromanfn@selectfont
\dimen0=\spaceskip
\typeout{CSROMAN_FN_WS=\the\fnwsbody,\the\fnwsinherited,\the\fnwsfn,\the\fnwstarget,\the\dimen0}
\makeatother
\end{document}
"""
        with tempfile.TemporaryDirectory(dir=BOOKS / "build") as tmp:
            tmp_path = Path(tmp)
            main = tmp_path / "fnws.tex"
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
            log = tmp_path / "fnws.log"
            text = log.read_text(encoding="utf-8", errors="replace") if log.is_file() else ""
            if not text:
                text = (proc.stdout or "") + "\n" + (proc.stderr or "")
            match = _DIM_RE.search(text)
            if match is None:
                self.fail(
                    "CSROMAN_FN_WS dims not found in log\n"
                    + text[-3000:]
                )
            body = float(match.group("body"))
            inherited = float(match.group("inherited"))
            fn = float(match.group("fn"))
            target = float(match.group("target"))
            spaceskip = float(match.group("spaceskip"))
            self.assertAlmostEqual(
                spaceskip,
                0.0,
                places=2,
                msg=f"footnote spaceskip should be 0pt (font natural), got {spaceskip}",
            )
            self.assertAlmostEqual(
                fn,
                target,
                places=3,
                msg=f"csromanfn@selectfont width {fn} != target {target}",
            )
            self.assertGreater(
                inherited,
                fn + 0.05,
                msg=(
                    "body-absolute spaceskip at footnotesize should be wider "
                    f"than font-natural (inherited={inherited}, fn={fn})"
                ),
            )
            self.assertGreater(
                body,
                fn,
                msg="normalsize sample should be wider than footnotesize sample",
            )


if __name__ == "__main__":
    unittest.main()
