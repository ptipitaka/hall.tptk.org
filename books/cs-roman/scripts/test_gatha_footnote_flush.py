#!/usr/bin/env python3
"""Regression: footnotes inside \\csromangathastanza must reach the page foot.

\\csromangathastanza wraps lines in \\vtop (ไม่แตกบท). TeX \\insert does not
migrate out of a sealed box, so without defer/flush the callout mark appears
but the note body never enters \\footins (04Vin04 printing p.130).
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

# Distinctive callout / body pairs (must share a page after flush).
PAIRS = (
    ("ปาริวาสิเกซิงก์", "รตฺติ วา ปาริวาสิเกซิงก์"),
    ("นยโตซิงก์", "สมฺเภทนยโตซิงก์"),
    ("รตฺติจฺเฉเทสุซิงก์", "รตฺติจฺเฉเทซิงก์"),
    ("สมาสมาติซิงก์", "สมาสมาติโน้ตซิงก์"),
)


def _norm(text: str) -> str:
    """Collapse whitespace so PDF line breaks do not break substring checks."""
    return "".join(text.split())


@unittest.skipUnless(fitz is not None, "pymupdf required")
@unittest.skipUnless(shutil.which("latexmk"), "latexmk required")
class GathaFootnoteFlushTests(unittest.TestCase):
    def test_gatha_footnote_bodies_appear_with_callouts(self) -> None:
        c0, n0 = PAIRS[0]
        c1, n1 = PAIRS[1]
        c2, n2 = PAIRS[2]
        c3, n3 = PAIRS[3]
        left = r"วุฑฺฒตเรน อกมฺมํ, \\ นิกฺขิปนํ สมาทานํ, \\ อพฺภานารเห นโย จาปิ, \\ ปาริวาสิเกสุ ตโย,"
        bat0 = (
            rf"\csromangathabat{{วุฑฺฒตเรน อกมฺมํ,}}{{รตฺติจฺเฉทา จ โสธนา.}} \\ "
            rf"\csromangathabat{{นิกฺขิปนํ สมาทานํ,}}{{วตฺตํว {c0}\footnote{{{n0} (ก)}}.}}"
        )
        bat1 = (
            rf"\csromangathabat{{มูลาย มานตฺตารหา,}}{{ตถา มานตฺตจาริตา.}} \\ "
            rf"\csromangathabat{{อพฺภานารเห นโย จาปิ,}}{{สมฺเภทํ {c1}\footnote{{{n1} (สฺยา)}} ปุน.}}"
        )
        bat2 = (
            rf"\csromangathabat{{ปาริวาสิเกสุ ตโย,}}{{จตุ มานตฺตจาริเก.}} \\ "
            rf"น สเมนฺติ {c2}\footnote{{{n2} (อิติปิ)}} มานตฺเตสุ จ เทวสิ. \\ "
            rf"เทฺว กมฺมา สทิสา เสสา ตโย กมฺมา {c3}\footnote{{{n3} (สฺยา)}}."
        )
        measure_lines = (
            rf"\csromangathabat{{วุฑฺฒตเรน อกมฺมํ,}}{{รตฺติจฺเฉทา จ โสธนา.}} \\ "
            rf"\csromangathabat{{นิกฺขิปนํ สมาทานํ,}}{{วตฺตํว {c0}.}} \\ "
            rf"\csromangathabat{{มูลาย มานตฺตารหา,}}{{ตถา มานตฺตจาริตา.}} \\ "
            rf"\csromangathabat{{อพฺภานารเห นโย จาปิ,}}{{สมฺเภทํ {c1} ปุน.}} \\ "
            rf"\csromangathabat{{ปาริวาสิเกสุ ตโย,}}{{จตุ มานตฺตจาริเก.}} \\ "
            rf"น สเมนฺติ {c2} มานตฺเตสุ จ เทวสิ. \\ "
            rf"เทฺว กมฺมา สทิสา เสสา ตโย กมฺมา {c3}."
        )
        tex = rf"""
\documentclass[11pt,twoside]{{memoir}}
\input{{shared/style/preamble.tex}}
\begin{{document}}
\mainmatter
\setlength{{\csromangathapagewidth}}{{0pt}}
\setlength{{\csromangathawakwidth}}{{0pt}}
\csromangathameasuregroup{{{left}}}{{{measure_lines}}}
\csromangathasetleft{{{left}}}
\csromangathagroup{{%
\csromangathastanza{{{bat0}}}%
\csromangathastanza{{{bat1}}}%
\csromangathastanza{{{bat2}}}%
}}
\nitthitam{{\textbf{{ปาริวาสิกกฺขนฺธโก นิฏฺฐิโตซิงก์.}}}}
\end{{document}}
"""
        with tempfile.TemporaryDirectory(dir=BOOKS / "build") as tmp:
            tmp_path = Path(tmp)
            main = tmp_path / "gathafn.tex"
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
            pdf = tmp_path / "gathafn.pdf"
            if not pdf.is_file():
                self.fail(
                    "latexmk did not produce gathafn.pdf\n"
                    + (proc.stdout or "")[-2500:]
                    + (proc.stderr or "")[-2500:]
                )
            doc = fitz.open(pdf)
            try:
                pages = [doc[i].get_text("text") for i in range(doc.page_count)]
                pages_n = [_norm(t) for t in pages]
                joined = "".join(pages_n)
                for callout, note in PAIRS:
                    cn, nn = _norm(callout), _norm(note)
                    self.assertIn(
                        nn,
                        joined,
                        f"missing footnote body {note!r} (trapped in vtop?)\n"
                        f"pages={pages!r}",
                    )
                    note_pages = [i + 1 for i, t in enumerate(pages_n) if nn in t]
                    call_pages = [
                        i + 1 for i, t in enumerate(pages_n) if cn in t
                    ]
                    self.assertTrue(call_pages, f"missing callout {callout!r}")
                    for np in note_pages:
                        self.assertIn(
                            np,
                            call_pages,
                            f"footnote body {note!r} on page {np} but "
                            f"callout {callout!r} only on {call_pages}",
                        )
            finally:
                doc.close()


if __name__ == "__main__":
    unittest.main()
