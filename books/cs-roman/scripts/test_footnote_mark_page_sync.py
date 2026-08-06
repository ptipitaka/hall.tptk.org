#!/usr/bin/env python3
"""Regression: footnote bodies must not appear before their callouts.

Fills a page so a long paragraph breaks across sheets with early and late
numbered notes. Fails if a distinctive note body is on page N while its
callout word lives only on another page (the 01Vin01 reading p.55/56 bug).
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

# (callout word in body, footnote body text) — each pair must share a page.
PAIRS = (
    ("อภิรูปาซิงก์", "โลหิตกาซิงก์"),
    ("กิงกณิกซิงก์", "กิงกณิกสทโทซิงก์"),
    ("ทารุกุฎิกซิงก์", "ทารุกุฎิกาซิงก์"),
    ("สมจาริโนซิงก์", "สมมจาริโนซิงก์"),
)

# Dense early packed notes + late note near a forced break — catches the
# old height-partition / re-insert double-count (body on N, callout on N+1).
BOUNDARY_PAIRS = (
    ("อปิซิงก์ต้น", "อปิซิงก์โน้ต"),
    ("กมมกาเรนซิงก์", "กมมกเรนซิงก์โน้ต"),
)


def _assert_pairs_synced(
    test: unittest.TestCase, pages: list[str], pairs: tuple[tuple[str, str], ...]
) -> None:
    for callout, note in pairs:
        note_pages = [i + 1 for i, t in enumerate(pages) if note in t]
        call_pages = [i + 1 for i, t in enumerate(pages) if callout in t]
        test.assertTrue(note_pages, f"missing footnote body {note!r}")
        test.assertTrue(call_pages, f"missing callout word {callout!r}")
        for np in note_pages:
            test.assertIn(
                np,
                call_pages,
                f"footnote body {note!r} on page {np} but "
                f"callout {callout!r} only on {call_pages}",
            )


def _run_fixture(
    test: unittest.TestCase,
    tex: str,
    job: str,
    pairs: tuple[tuple[str, str], ...],
    *,
    min_pages: int = 2,
) -> list[str]:
    with tempfile.TemporaryDirectory(dir=BOOKS / "build") as tmp:
        tmp_path = Path(tmp)
        main = tmp_path / f"{job}.tex"
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
        pdf = tmp_path / f"{job}.pdf"
        if not pdf.is_file():
            test.fail(
                f"latexmk did not produce {pdf.name}\n"
                + (proc.stdout or "")[-2500:]
                + (proc.stderr or "")[-2500:]
            )
        doc = fitz.open(pdf)
        try:
            test.assertGreaterEqual(
                doc.page_count, min_pages, "expected a page break in the fixture"
            )
            pages = [doc[i].get_text("text") for i in range(doc.page_count)]
            _assert_pairs_synced(test, pages, pairs)
            return pages
        finally:
            doc.close()


@unittest.skipUnless(fitz is not None, "pymupdf required")
@unittest.skipUnless(shutil.which("latexmk"), "latexmk required")
class FootnoteMarkPageSyncTests(unittest.TestCase):
    def test_late_notes_stay_with_callouts(self) -> None:
        filler = "ปาฬิปาฐทดสอบ " * 42
        c0, n0 = PAIRS[0]
        c1, n1 = PAIRS[1]
        c2, n2 = PAIRS[2]
        c3, n3 = PAIRS[3]
        tex = rf"""
\documentclass[11pt,twoside]{{memoir}}
\input{{shared/style/preamble.tex}}
\begin{{document}}
\mainmatter
\noindent
{c0}\footnote{{{n0} (สยา)}}
และต่อด้วย {c1}\footnote{{{n1} (สี, สยา)}}
{filler}
{filler}
{filler}
{filler}
อุปสงฺกมิตฺวา ทารุคเห คณกํ เอตทโวจ
“ยาวตติยกํ โข เม อาวุโส คามํ
{c2}\footnote{{{n2} (สี)}} กาตุนฺ”ติ.
{c3}\footnote{{{n3} (ก)}} พฺรหฺมจริโน.
{filler}
\end{{document}}
"""
        _run_fixture(self, tex, "marksync", PAIRS)

    def test_boundary_note_not_painted_on_previous_page(self) -> None:
        """Late callout after \\clearpage must not leave its body on page N."""
        filler = "ปาฬิปาฐทดสอบ " * 28
        c0, n0 = BOUNDARY_PAIRS[0]
        c1, n1 = BOUNDARY_PAIRS[1]
        tex = rf"""
\documentclass[11pt,twoside]{{memoir}}
\input{{shared/style/preamble.tex}}
\begin{{document}}
\mainmatter
\noindent
{c0}\footnote{{{n0} (สยา), อปิ นายโย (ก)}}
และต่อด้วยโน้ตสั้น\footnote{{ยํ หิ (ก)}}
{filler}
{filler}
{filler}
\clearpage
\noindent
{c1}\footnote{{{n1} (สี, สยา)}} วา อนฺตมโส สมณปริพฺพาชเกนาปิ.
{filler}
\end{{document}}
"""
        pages = _run_fixture(self, tex, "marksync_boundary", BOUNDARY_PAIRS)
        for i, text in enumerate(pages):
            if n1 in text:
                self.assertIn(
                    c1,
                    text,
                    f"{n1!r} on page {i + 1} without callout {c1!r}",
                )


if __name__ == "__main__":
    unittest.main()
