#!/usr/bin/env python3
"""Regression: footnote natural-width packing (multi-col + single centered).

Builds minimal pages under books/cs-roman so ``shared/style/…`` and fonts
resolve like a volume build.

- Short+wide pair (02Vin02 p.79): both bodies share a baseline y and the
  rightmost note's right edge sits near the text-block right (inter-note
  stretch, not left-packed with trailing ``\\hss``).
- Sole short note: centered on the text measure (``\\hss`` both sides).
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
class FootnoteNaturalPackTests(unittest.TestCase):
    def test_short_and_wide_share_one_row(self) -> None:
        tex = r"""
\documentclass[11pt,twoside]{memoir}
\input{shared/style/preamble.tex}
\begin{document}
\mainmatter
\noindent
ยมฺปิ\footnote{ยํ หิ (ก)} มยํ อยฺเย คจฺเฉยฺยาม.
ภิกฺขู โอวทิสฺสนฺตีติ\footnote{ฉพฺพคฺคิยา ภิกฺขุนิโย โอวาทํ น คจฺฉิสฺสนฺตีติ (สี)}.
\end{document}
"""
        with tempfile.TemporaryDirectory(dir=BOOKS / "build") as tmp:
            tmp_path = Path(tmp)
            main = tmp_path / "pack.tex"
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
            pdf = tmp_path / "pack.pdf"
            if not pdf.is_file():
                self.fail(
                    "latexmk did not produce pack.pdf\n"
                    + (proc.stdout or "")[-2500:]
                    + (proc.stderr or "")[-2500:]
                )
            doc = fitz.open(pdf)
            try:
                page = doc[0]
                # PyMuPDF often splits one footnote row into many short lines;
                # collect footnote-sized spans, then require the known bodies.
                # (y, x0, x1, text)
                spans_fn: list[tuple[float, float, float, str]] = []
                for block in page.get_text("dict")["blocks"]:
                    if block.get("type") != 0:
                        continue
                    for line in block.get("lines", []):
                        spans = line["spans"]
                        # Footnote body ≈ footnotesize; skip body (∼12pt).
                        if not spans or max(s["size"] for s in spans) > 10.5:
                            continue
                        text = "".join(s["text"] for s in spans)
                        y = spans[0]["origin"][1]
                        x0 = min(s["bbox"][0] for s in spans)
                        x1 = max(s["bbox"][2] for s in spans)
                        spans_fn.append((y, x0, x1, text))
                joined = "".join(s[3] for s in spans_fn)
                self.assertIn("ยํ", joined, f"short note missing: {spans_fn}")
                self.assertIn(
                    "ฉพฺพคฺคิยา", joined, f"wide note missing: {spans_fn}"
                )
                # Cluster on the densest footnote baseline (shared row).
                ys = sorted({round(s[0], 1) for s in spans_fn})
                self.assertTrue(ys, "no footnote-sized spans")
                row_y = max(
                    ys,
                    key=lambda y: sum(1 for s in spans_fn if abs(s[0] - y) < 4),
                )
                row = [s for s in spans_fn if abs(s[0] - row_y) < 4]
                row.sort(key=lambda s: s[1])
                self.assertGreaterEqual(
                    len(row), 2, f"expected a multi-span footnote row: {row}"
                )
                # Side-by-side: first cluster left, second starts well to the right.
                self.assertGreater(
                    row[-1][1],
                    row[0][1] + 20,
                    f"expected side-by-side (row={row})",
                )
                # pagegeometry.tex: stock 499bp, right margin 59.4bp
                text_right = page.rect.width - 59.4
                row_right = max(s[2] for s in row)
                self.assertLess(
                    abs(row_right - text_right),
                    6.0,
                    f"expected edge-to-edge row (row_right≈{text_right}, "
                    f"got {row_right}, row={row})",
                )
            finally:
                doc.close()

    def test_single_footnote_is_centered(self) -> None:
        tex = r"""
\documentclass[11pt,twoside]{memoir}
\input{shared/style/preamble.tex}
\begin{document}
\mainmatter
\noindent
ยมฺปิ\footnote{ยํ หิ (ก)} มยํ อยฺเย คจฺเฉยฺยาม.
\end{document}
"""
        with tempfile.TemporaryDirectory(dir=BOOKS / "build") as tmp:
            tmp_path = Path(tmp)
            main = tmp_path / "single.tex"
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
            pdf = tmp_path / "single.pdf"
            if not pdf.is_file():
                self.fail(
                    "latexmk did not produce single.pdf\n"
                    + (proc.stdout or "")[-2500:]
                    + (proc.stderr or "")[-2500:]
                )
            doc = fitz.open(pdf)
            try:
                page = doc[0]
                # pagegeometry.tex: stock 499bp, left 62.6bp, right 59.4bp
                text_left = 62.6
                text_right = page.rect.width - 59.4
                text_mid = (text_left + text_right) / 2
                spans_fn: list[tuple[float, float, float, str]] = []
                for block in page.get_text("dict")["blocks"]:
                    if block.get("type") != 0:
                        continue
                    for line in block.get("lines", []):
                        spans = line["spans"]
                        if not spans or max(s["size"] for s in spans) > 10.5:
                            continue
                        text = "".join(s["text"] for s in spans)
                        y = spans[0]["origin"][1]
                        x0 = min(s["bbox"][0] for s in spans)
                        x1 = max(s["bbox"][2] for s in spans)
                        spans_fn.append((y, x0, x1, text))
                joined = "".join(s[3] for s in spans_fn)
                self.assertIn("ยํ", joined, f"short note missing: {spans_fn}")
                note_x0 = min(s[1] for s in spans_fn)
                note_x1 = max(s[2] for s in spans_fn)
                note_mid = (note_x0 + note_x1) / 2
                # Left-packed would sit near text_left; require near text mid.
                self.assertLess(
                    abs(note_mid - text_mid),
                    8.0,
                    f"expected centered single note "
                    f"(mid≈{text_mid}, got {note_mid}, "
                    f"[{note_x0}, {note_x1}], spans={spans_fn})",
                )
                self.assertGreater(
                    note_x0,
                    text_left + 20,
                    f"single note still left-packed: x0={note_x0}",
                )
            finally:
                doc.close()

    def test_trailing_singleton_on_multi_note_page_is_left(self) -> None:
        """With 2+ notes, a leftover one-line row must not center.

        01Vin01 p.86: notes 1+2 share a row; trailing ``*`` stays left.
        """
        tex = r"""
\documentclass[11pt,twoside]{memoir}
\input{shared/style/preamble.tex}
\begin{document}
\mainmatter
\noindent
ยมฺปิ\footnote{ยํ หิ (ก)} มยํ อยฺเย\footnote{ฉพฺพคฺคิยา ภิกฺขุนิโย โอวาทํ น คจฺฉิสฺสนฺตีติ (สี)} คจฺเฉยฺยาม.
ภิกฺขู อิทํ\footnote{*อิทํ วตฺถุ สํ 3. 278}.
\end{document}
"""
        with tempfile.TemporaryDirectory(dir=BOOKS / "build") as tmp:
            tmp_path = Path(tmp)
            main = tmp_path / "trail.tex"
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
            pdf = tmp_path / "trail.pdf"
            if not pdf.is_file():
                self.fail(
                    "latexmk did not produce trail.pdf\n"
                    + (proc.stdout or "")[-2500:]
                    + (proc.stderr or "")[-2500:]
                )
            doc = fitz.open(pdf)
            try:
                page = doc[0]
                text_left = 62.6
                text_right = page.rect.width - 59.4
                text_mid = (text_left + text_right) / 2
                spans_fn: list[tuple[float, float, float, str]] = []
                for block in page.get_text("dict")["blocks"]:
                    if block.get("type") != 0:
                        continue
                    for line in block.get("lines", []):
                        spans = line["spans"]
                        if not spans or max(s["size"] for s in spans) > 10.5:
                            continue
                        text = "".join(s["text"] for s in spans)
                        y = spans[0]["origin"][1]
                        x0 = min(s["bbox"][0] for s in spans)
                        x1 = max(s["bbox"][2] for s in spans)
                        spans_fn.append((y, x0, x1, text))
                joined = "".join(s[3] for s in spans_fn)
                self.assertIn("อิทํ", joined, f"* note missing: {spans_fn}")
                # Bottom-most footnote cluster that mentions the * body.
                star_spans = [s for s in spans_fn if "อิทํ" in s[3] or "วตฺถุ" in s[3]]
                self.assertTrue(star_spans, f"no * spans: {spans_fn}")
                star_y = max(s[0] for s in star_spans)
                row = [s for s in spans_fn if abs(s[0] - star_y) < 4]
                row_x0 = min(s[1] for s in row)
                row_x1 = max(s[2] for s in row)
                row_mid = (row_x0 + row_x1) / 2
                # Left-aligned: near text_left, not near text mid.
                self.assertLess(
                    row_x0 - text_left,
                    12.0,
                    f"expected left-aligned trailing note "
                    f"(x0={row_x0}, left={text_left}, row={row})",
                )
                self.assertGreater(
                    abs(row_mid - text_mid),
                    20.0,
                    f"trailing note still centered "
                    f"(mid≈{text_mid}, got {row_mid}, row={row})",
                )
            finally:
                doc.close()

    def test_packed_tiny_notes_do_not_leave_two_line_gap(self) -> None:
        """Page-break must reserve packed height, not stacked height.

        Three tiny notes pack to one row at shipout. If \\insert accounts for
        three stacked rows, bottom-pin \\vfill turns the surplus into a
        ~2-line body→rule gap even when the paragraph could continue
        (01Vin01 reading p.20). Credit in \\csromanfn@footnotetext should
        keep the gap near \\skip\\footins (~18pt), not ~55pt.
        """
        filler = "\n".join(
            [r"\noindent กมฺมนฺตา อาคจฺฉนฺโต อทฺทส อายสฺมนฺตํ สุทินฺนํ ตํ อาภิโทสิกํ กุมฺมาสํ\par"]
            * 28
        )
        tex = rf"""
\documentclass[11pt,twoside]{{memoir}}
\input{{shared/style/preamble.tex}}
\begin{{document}}
\mainmatter
\noindent
อตฺถิ นาม\footnote{{ก}} ตาต สุทินฺน\footnote{{ข}} อาภิโทสิกํ
กุมฺมาสํ\footnote{{ค}} ปริภุญฺชิสฺสสิ.
{filler}
\end{{document}}
"""
        with tempfile.TemporaryDirectory(dir=BOOKS / "build") as tmp:
            tmp_path = Path(tmp)
            main = tmp_path / "gap.tex"
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
            pdf = tmp_path / "gap.pdf"
            if not pdf.is_file():
                self.fail(
                    "latexmk did not produce gap.pdf\n"
                    + (proc.stdout or "")[-2500:]
                    + (proc.stderr or "")[-2500:]
                )
            doc = fitz.open(pdf)
            try:
                # Prefer a page that has both body and a footnote rule.
                best = None
                for page in doc:
                    rule_y = None
                    for d in page.get_drawings():
                        r = d.get("rect")
                        if (
                            r is not None
                            and r.width > 200
                            and r.height < 3
                            and r.y0 > 100
                        ):
                            rule_y = r.y0
                            break
                    if rule_y is None:
                        continue
                    last_body = None
                    for block in page.get_text("dict")["blocks"]:
                        if block.get("type") != 0:
                            continue
                        for line in block.get("lines", []):
                            spans = line["spans"]
                            if not spans:
                                continue
                            size = max(s["size"] for s in spans)
                            if size < 10.5:
                                continue  # footnote text
                            x0, y0, x1, y1 = line["bbox"]
                            if y1 >= rule_y - 0.5 or y0 < 70:
                                continue
                            if last_body is None or y1 > last_body:
                                last_body = y1
                    if last_body is not None:
                        gap = rule_y - last_body
                        if best is None or gap < best[0]:
                            best = (gap, rule_y, last_body, page.number)
                self.assertIsNotNone(best, "no footnote page found")
                gap, rule_y, last_body, pno = best
                # Natural skip\footins ≈ 18pt; allow one line of slack.
                # Pre-fix packing-credit surplus was ~55pt on real pages.
                self.assertLess(
                    gap,
                    36.0,
                    f"body→rule gap still looks like stacked-footnote "
                    f"over-reserve (gap={gap:.1f}pt on pdf page {pno}, "
                    f"body={last_body:.1f}, rule={rule_y:.1f})",
                )
            finally:
                doc.close()


if __name__ == "__main__":
    unittest.main()
