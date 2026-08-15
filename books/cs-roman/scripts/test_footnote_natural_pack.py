#!/usr/bin/env python3
"""Regression: fixed 3-column footnote grid packing.

Builds minimal pages under books/cs-roman so ``shared/style/…`` and fonts
resolve like a volume build.

- Short+wide pair share one row in fixed column slots (no edge stretch).
- Sole short note: centered on the text measure (``\\hss`` both sides).
- Leftover notes park in col1/col2, not the right margin.
- Packing credit keeps body→rule gap from stacked-insert surplus.
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


def _footnote_spans(page, *, min_y_frac: float = 0.0):
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
            if y < page.rect.height * min_y_frac:
                continue
            x0 = min(s["bbox"][0] for s in spans)
            x1 = max(s["bbox"][2] for s in spans)
            spans_fn.append((y, x0, x1, text))
    return spans_fn


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
            if not pdf.is_file() or pdf.stat().st_size == 0:
                self.fail(
                    "latexmk did not produce pack.pdf\n"
                    + (proc.stdout or "")[-2500:]
                    + (proc.stderr or "")[-2500:]
                )
            doc = fitz.open(pdf)
            try:
                page = doc[0]
                text_left = 62.6
                text_right = page.rect.width - 59.4
                colsep = 12.5
                colw = (text_right - text_left - 2 * colsep) / 3
                col2_left = text_left + colw + colsep
                spans_fn = _footnote_spans(page)
                joined = "".join(s[3] for s in spans_fn)
                self.assertIn("ยํ", joined, f"short note missing: {spans_fn}")
                self.assertIn(
                    "ฉพฺพคฺคิยา", joined, f"wide note missing: {spans_fn}"
                )
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
                self.assertGreater(
                    row[-1][1],
                    row[0][1] + 20,
                    f"expected side-by-side (row={row})",
                )
                # Fixed grid: must not edge-stretch the row to text_right.
                row_right = max(s[2] for s in row)
                self.assertLess(
                    row_right,
                    text_right - 5,
                    f"expected fixed-grid packing, not edge stretch "
                    f"(row_right={row_right}, text_right={text_right}, row={row})",
                )
                self.assertGreater(
                    row[-1][1],
                    col2_left - 25,
                    f"second note not in later column "
                    f"(x0={row[-1][1]}, col2≈{col2_left}, row={row})",
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
            if not pdf.is_file() or pdf.stat().st_size == 0:
                self.fail(
                    "latexmk did not produce single.pdf\n"
                    + (proc.stdout or "")[-2500:]
                    + (proc.stderr or "")[-2500:]
                )
            doc = fitz.open(pdf)
            try:
                page = doc[0]
                text_left = 62.6
                text_right = page.rect.width - 59.4
                text_mid = (text_left + text_right) / 2
                spans_fn = _footnote_spans(page, min_y_frac=0.7)
                joined = "".join(s[3] for s in spans_fn)
                self.assertIn("ยํ", joined, f"short note missing: {spans_fn}")
                note_x0 = min(s[1] for s in spans_fn)
                note_x1 = max(s[2] for s in spans_fn)
                note_mid = (note_x0 + note_x1) / 2
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
        """With 2+ notes, a leftover one-line row must not center."""
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
            if not pdf.is_file() or pdf.stat().st_size == 0:
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
                spans_fn = _footnote_spans(page)
                joined = "".join(s[3] for s in spans_fn)
                self.assertIn("อิทํ", joined, f"* note missing: {spans_fn}")
                star_spans = [
                    s for s in spans_fn if "อิทํ" in s[3] or "วตฺถุ" in s[3]
                ]
                self.assertTrue(star_spans, f"no * spans: {spans_fn}")
                star_y = max(s[0] for s in star_spans)
                row = [s for s in spans_fn if abs(s[0] - star_y) < 4]
                row_x0 = min(s[1] for s in row)
                row_x1 = max(s[2] for s in row)
                row_mid = (row_x0 + row_x1) / 2
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

    def test_partial_three_col_flush_parks_in_col1_and_col2(self) -> None:
        """Five tiny notes: row of 3, then leftovers in col1+col2 (not right edge)."""
        tex = r"""
\documentclass[11pt,twoside]{memoir}
\input{shared/style/preamble.tex}
\begin{document}
\mainmatter
\noindent
ก\footnote{ก (ก)} ข\footnote{ข (ข)} ค\footnote{ค (ค)}
ง\footnote{ง (ง)} จ\footnote{จ (จ)}.
\end{document}
"""
        with tempfile.TemporaryDirectory(dir=BOOKS / "build") as tmp:
            tmp_path = Path(tmp)
            main = tmp_path / "partial3.tex"
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
            pdf = tmp_path / "partial3.pdf"
            if not pdf.is_file() or pdf.stat().st_size == 0:
                self.fail(
                    "latexmk did not produce partial3.pdf\n"
                    + (proc.stdout or "")[-2500:]
                    + (proc.stderr or "")[-2500:]
                )
            doc = fitz.open(pdf)
            try:
                page = doc[0]
                text_left = 62.6
                text_right = page.rect.width - 59.4
                colsep = 12.5
                thirdw = (text_right - text_left - 2 * colsep) / 3
                col2_left = text_left + thirdw + colsep
                spans_fn = _footnote_spans(page, min_y_frac=0.55)
                bottom_y = max(s[0] for s in spans_fn)
                row = [s for s in spans_fn if abs(s[0] - bottom_y) < 5]
                row.sort(key=lambda s: s[1])
                self.assertTrue(
                    any("ง" in s[3] or "จ" in s[3] for s in row),
                    f"expected leftover ง/จ on bottom row: {row}",
                )
                clusters: list[list[tuple[float, float, float, str]]] = []
                for span in row:
                    if not clusters or span[1] - clusters[-1][-1][2] > 40:
                        clusters.append([span])
                    else:
                        clusters[-1].append(span)
                self.assertGreaterEqual(
                    len(clusters),
                    2,
                    f"expected two leftover notes: {row}",
                )
                second_x0 = min(s[1] for s in clusters[1])
                self.assertLess(
                    abs(second_x0 - col2_left),
                    18.0,
                    f"leftover second note not in col2 "
                    f"(x0={second_x0}, col2≈{col2_left}, "
                    f"text_right={text_right}, row={row})",
                )
                self.assertLess(
                    second_x0,
                    text_right - 40,
                    f"leftover second note still edge-stretched: {row}",
                )
            finally:
                doc.close()

    def test_three_one_line_notes_natural_when_grid_would_split(self) -> None:
        """Three one-line notes that fit together override a 1+2 / leftover split.

        23Khu06: span-1 + span-2 fill the grid row; short note 3 would go to a
        second row even though natural widths + colseps still fit one line.
        """
        tex = r"""
\documentclass[11pt,twoside]{memoir}
\def\csromanuseprintinggeometry{1}
\input{shared/style/preamble.tex}
\begin{document}
\mainmatter
\noindent
ก\footnote{อวญฺชสิ (อิ)}
ข\footnote{อุทธฺปาโท (สยา), อุทธฺปาโท (อิ)}
ค\footnote{มหาภิตาป์ (อิ)}.
\end{document}
"""
        with tempfile.TemporaryDirectory(dir=BOOKS / "build") as tmp:
            tmp_path = Path(tmp)
            main = tmp_path / "triple.tex"
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
            pdf = tmp_path / "triple.pdf"
            if not pdf.is_file() or pdf.stat().st_size == 0:
                self.fail(
                    "latexmk did not produce triple.pdf\n"
                    + (proc.stdout or "")[-2500:]
                    + (proc.stderr or "")[-2500:]
                )
            doc = fitz.open(pdf)
            try:
                page = doc[0]
                spans_fn = _footnote_spans(page, min_y_frac=0.55)
                rows: dict[float, list[tuple[float, float, float, str]]] = {}
                for s in spans_fn:
                    matched = None
                    for k in rows:
                        if abs(k - s[0]) < 5:
                            matched = k
                            break
                    if matched is None:
                        rows[s[0]] = [s]
                    else:
                        rows[matched].append(s)
                self.assertEqual(
                    len(rows),
                    1,
                    f"expected one shared footnote row, got {len(rows)}: {rows}",
                )
                joined = "".join(s[3] for s in next(iter(rows.values())))
                self.assertIn("อวญฺชสิ", joined, f"note 1 missing: {joined!r}")
                self.assertIn("อุทธ", joined, f"note 2 missing: {joined!r}")
                self.assertIn("มหาภิตาป์", joined, f"note 3 missing: {joined!r}")
            finally:
                doc.close()

    def test_two_one_line_notes_pair_when_grid_would_split(self) -> None:
        """Two one-line notes that fit together override a span-3 split.

        23Khu06: short ``ติฏฺฐติ`` + long note body that includes ``3. อิทํ…``
        (not a third callout). Grid assigns span 1 + span 3 → two rows; pair
        rule puts both on one line when natural widths + colsep fit.
        """
        tex = r"""
\documentclass[11pt,twoside]{memoir}
\def\csromanuseprintinggeometry{1}
\input{shared/style/preamble.tex}
\begin{document}
\mainmatter
\noindent
ก\footnote{ติฏฺฐติ (อิ)}
ข\footnote{ทกฺขิตานํ (สยา, อิ) 3. อิทํ ปทํ นตฺถิ (สีสยาอิโปตฺถเกสุ.)}.
\end{document}
"""
        with tempfile.TemporaryDirectory(dir=BOOKS / "build") as tmp:
            tmp_path = Path(tmp)
            main = tmp_path / "pair.tex"
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
            pdf = tmp_path / "pair.pdf"
            if not pdf.is_file() or pdf.stat().st_size == 0:
                self.fail(
                    "latexmk did not produce pair.pdf\n"
                    + (proc.stdout or "")[-2500:]
                    + (proc.stderr or "")[-2500:]
                )
            doc = fitz.open(pdf)
            try:
                page = doc[0]
                spans_fn = _footnote_spans(page, min_y_frac=0.55)
                rows: dict[float, list[tuple[float, float, float, str]]] = {}
                for s in spans_fn:
                    matched = None
                    for k in rows:
                        if abs(k - s[0]) < 5:
                            matched = k
                            break
                    if matched is None:
                        rows[s[0]] = [s]
                    else:
                        rows[matched].append(s)
                self.assertEqual(
                    len(rows),
                    1,
                    f"expected one shared footnote row, got {len(rows)}: {rows}",
                )
                joined = "".join(s[3] for s in next(iter(rows.values())))
                self.assertIn("ติฏฺฐติ", joined, f"note 1 missing: {joined!r}")
                self.assertIn("ทกฺขิตานํ", joined, f"note 2 missing: {joined!r}")
                self.assertIn("อิทํ", joined, f"note 2 body tail missing: {joined!r}")
            finally:
                doc.close()

    def test_near_colw_note_packs_with_following_span_two(self) -> None:
        """Note barely over 1-col still span-1 (tolerance), shares row with span-2.

        23Khu06 printing: ``ตเป กมฺมํ…`` was ~colw+2pt and forced three rows
        with two following span-2 notes; with \\csromanfn@spantol it should
        share the first row with the next note.
        """
        tex = r"""
\documentclass[11pt,twoside]{memoir}
\def\csromanuseprintinggeometry{1}
\input{shared/style/preamble.tex}
\begin{document}
\mainmatter
\noindent
ก\footnote{ตเป กมฺมํ (สี, สุยา, อิ)}
ข\footnote{สิรี จ ตาต ลกฺขี จ (สุยา, อิ)}
ค\footnote{สิรี จ ตาต ลกฺขี จ (สุยา, อิ)}.
\end{document}
"""
        with tempfile.TemporaryDirectory(dir=BOOKS / "build") as tmp:
            tmp_path = Path(tmp)
            main = tmp_path / "tol.tex"
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
            pdf = tmp_path / "tol.pdf"
            if not pdf.is_file() or pdf.stat().st_size == 0:
                self.fail(
                    "latexmk did not produce tol.pdf\n"
                    + (proc.stdout or "")[-2500:]
                    + (proc.stderr or "")[-2500:]
                )
            doc = fitz.open(pdf)
            try:
                page = doc[0]
                spans_fn = _footnote_spans(page, min_y_frac=0.55)
                # Cluster by baseline into rows.
                rows: dict[float, list[tuple[float, float, float, str]]] = {}
                for s in spans_fn:
                    key = round(s[0], 0)
                    # merge nearby baselines
                    matched = None
                    for k in rows:
                        if abs(k - s[0]) < 5:
                            matched = k
                            break
                    if matched is None:
                        rows[s[0]] = [s]
                    else:
                        rows[matched].append(s)
                # Top footnote row should contain both note 1 and note 2.
                top_y = min(rows)
                top = rows[top_y]
                joined = "".join(s[3] for s in top)
                self.assertIn("ตเป", joined, f"note 1 missing on top row: {top}")
                self.assertTrue(
                    "สิรี" in joined or "ลกฺขี" in joined,
                    f"note 2 should share top row with note 1: rows={rows}",
                )
                # Should not be three separate single-note rows.
                self.assertLessEqual(
                    len(rows),
                    2,
                    f"expected ≤2 footnote rows with tolerance, got {len(rows)}: {rows}",
                )
            finally:
                doc.close()

    def test_packed_tiny_notes_do_not_leave_two_line_gap(self) -> None:
        """Page-break must reserve packed height, not stacked height."""
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
            if not pdf.is_file() or pdf.stat().st_size == 0:
                self.fail(
                    "latexmk did not produce gap.pdf\n"
                    + (proc.stdout or "")[-2500:]
                    + (proc.stderr or "")[-2500:]
                )
            doc = fitz.open(pdf)
            try:
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
                                continue
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
