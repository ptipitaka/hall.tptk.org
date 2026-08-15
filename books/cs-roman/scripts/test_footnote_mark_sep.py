#!/usr/bin/env python3
"""Regression: footnote hang mark→body gap is equal for * and digits.

Old footmisc-style ``\\hb@xt@\\footnotemargin{\\hss mark}`` right-aligned the
mark in a fixed box, so ``*`` looked far from the note while ``1`` sat tight.
Hang is now mark + ``\\csromanfn@marksep`` + body.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

BOOKS = Path(__file__).resolve().parents[1]

_GAP_RE = re.compile(
    r"^CSROMAN_FN_MARKGAP=(?P<star>[0-9.]+)pt,(?P<digit>[0-9.]+)pt,"
    r"(?P<sep>[0-9.]+)pt$",
    re.MULTILINE,
)


@unittest.skipUnless(shutil.which("latexmk"), "latexmk required")
class FootnoteMarkSepTests(unittest.TestCase):
    def test_star_and_digit_share_marksep(self) -> None:
        tex = r"""
\documentclass[11pt,twoside]{memoir}
\def\csromanuseprintinggeometry{1}
\input{shared/style/preamble.tex}
\begin{document}
\makeatletter
\newdimen\gapstar
\newdimen\gapdigit
\newdimen\markw
% Gap = width(mark+sep) - width(mark)  (== \csromanfn@marksep).
\def\@thefnmark{*}%
\settowidth\markw{\csromanfn@selectfont\@makefnmark}%
\settowidth\gapstar{\csromanfn@selectfont\csromanfn@markbox}%
\gapstar=\dimexpr\gapstar-\markw\relax
\def\@thefnmark{1}%
\settowidth\markw{\csromanfn@selectfont\@makefnmark}%
\settowidth\gapdigit{\csromanfn@selectfont\csromanfn@markbox}%
\gapdigit=\dimexpr\gapdigit-\markw\relax
\csromanfn@selectfont
\typeout{CSROMAN_FN_MARKGAP=\the\gapstar,\the\gapdigit,\the\csromanfn@marksep}
\makeatother
\end{document}
"""
        with tempfile.TemporaryDirectory(dir=BOOKS / "build") as tmp:
            tmp_path = Path(tmp)
            main = tmp_path / "fnmark.tex"
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
            log = tmp_path / "fnmark.log"
            text = log.read_text(encoding="utf-8", errors="replace") if log.is_file() else ""
            if not text:
                text = (proc.stdout or "") + "\n" + (proc.stderr or "")
            match = _GAP_RE.search(text)
            if match is None:
                self.fail("CSROMAN_FN_MARKGAP not found in log\n" + text[-3000:])
            star = float(match.group("star"))
            digit = float(match.group("digit"))
            sep = float(match.group("sep"))
            self.assertAlmostEqual(star, sep, places=3, msg=f"* gap {star} != sep {sep}")
            self.assertAlmostEqual(digit, sep, places=3, msg=f"1 gap {digit} != sep {sep}")
            self.assertGreater(sep, 1.5, msg="marksep should be a visible ~0.25em")


if __name__ == "__main__":
    unittest.main()
