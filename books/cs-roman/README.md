# CS Roman → Thai Tipiṭaka books (TeX)

Self-contained pipeline under `books/cs-roman/`: source PDFs, extract/heading
scripts, segment JSON, TeX generation, and built PDFs.

Segment JSON format: [`SCHEMA.md`](SCHEMA.md) (`schema_version` **1**).
Typed load/save/normalize: `scripts/cs_roman_segments.py`.

## Layout

```
books/cs-roman/
  SCHEMA.md
  build.ps1                 # one volume: sync → generate → latexmk
  scripts/                  # extract, headings, TeX, metrics, tests
  source/                   # CS Roman PDFs (gitignored *.pdf)
  output/                   # canonical *.segments.json + *.layout.json
                            # + optional *.transforms.json
  shared/                   # fonts + style + transforms.json (edition-wide)
  volumes/<id>/             # source hardlink + data + tex + out PDF
```

Thai font stack follows tipitaka-catalog (LuaLaTeX + babel + Sarabun).
Transliteration uses the shared `pali_script` package (`packages/pali_script`).

## Workflow

Single volume (from already-extracted JSON):

```powershell
cd books/cs-roman
.\build.ps1 -Volume 01Vin01              # sync (default): page-faithful sheets
.\build.ps1 -Volume 02Vin02 -Mode reading  # continuous text + margin ฉ.N (any volume)
```

| Mode | Body TeX | PDF |
|------|----------|-----|
| `sync` (default) | `tex/body.generated.tex` | `out/<id>.pdf` |
| `reading` | `tex/body.reading.generated.tex` | `out/<id>.reading.pdf` |

Reading mode keeps the volume `layout` defaults, does not force `\csromanpage`, merges `*_continuation` into the open paragraph, and places `ฉ.N` in the outer margin at each source-folio change. Drivers: `volumes/<id>/tex/main.tex` and `main.reading.tex` (templated by `batch_prepare_volumes.py`).

Full pipeline for all volumes (extract → headings → TeX → PDF):

```powershell
# From repo root (Docker for Python extract/headings)
docker compose exec -T web python books/cs-roman/scripts/extract_cs_roman_pdf.py books/cs-roman/source --output-dir books/cs-roman/output
docker compose exec -T web python books/cs-roman/scripts/batch_cs_roman_headings.py
docker compose exec -T web python books/cs-roman/scripts/batch_prepare_volumes.py
# default --mode both → sync + reading bodies, main.tex + main.reading.tex, matika sync

# Host TeX Live
cd books/cs-roman
.\scripts\batch_build_volumes.ps1              # sync PDFs
.\scripts\batch_build_volumes.ps1 -Mode reading  # reading PDFs
```

Or one PowerShell entrypoint from this directory:

```powershell
cd books/cs-roman
.\pipeline.ps1            # extract + headings + prepare sync+reading (Docker)
.\scripts\batch_build_volumes.ps1 -Mode both
```

Steps (per volume):

1. Sync PDF (hardlink from `source/`) + `segments.json` + `layout.json` (+ optional `transforms.json` / `matika.json`) into `volumes/<id>/`
2. Generate `tex/body.generated.tex` and/or `body.reading.generated.tex` from segments (+ footnotes, bold runs, TOC marks, layout; apply `shared`/`volume` transforms on Roman then Thai). TOC prefers `matika.json` when present.
3. `latexmk -lualatex` → `volumes/<id>/out/<id>.pdf` or `<id>.reading.pdf`

Requires: Python 3.11+, PyMuPDF, editable `pali_script` (`pip install -e packages/pali_script/python`), TeX Live with LuaLaTeX + memoir + babel-thai.

## Notes

- `body.generated.tex` / `body.reading.generated.tex` are auto-generated — edit macros in `shared/style/`, not the body.
- Sync mode: each source `page` starts a new sheet with matching `\setcounter{page}{N}`.
- Reading mode (any volume): physical page numbers in the running head; source folio cited as `ฉ.N` via `\csromanfolio` (outer margin). Geometry: `pagegeometry-reading.tex`. Per-page rhythm: `page_layout_reading_mode` in `layout.json` (physical page keys, not ฉ.N). Headings batch writes `output/<id>.matika.json` for memoir TOC marks.
- After มาติกา, `\cleardoublepage` forces arabic page 1 onto a recto (right-hand / odd) page.
- Running heads show piṭaka / gambhīra titles and the (mode-dependent) page number.
- Footnotes: `{{nN}}` → `\footnote{…}` with notes transliterated to Thai (Arabic digits kept).
- Page geometry targets CS Roman MediaBox **499 × 709 bp** (`shared/style/pagegeometry.tex`).
- Body page range: `content_start_pdf_page` (Namo tassa) … `content_end_printed_page` (before back-matter indexes). Trim indexes with `python books/cs-roman/scripts/trim_cs_roman_back_matter.py books/cs-roman/output --all`.
- Normalize / split content vs layout: `python books/cs-roman/scripts/cs_roman_segments.py normalize --all`
  (writes `<id>.segments.json` + `<id>.layout.json`; print tuning stays in layout)
- Publication string fixes (conditional / per-volume): edit `shared/transforms.json` and/or
  `output/<id>.transforms.json`, then rebuild — rules apply at generate, not extract.
  See [`SCHEMA.md`](SCHEMA.md) (transforms file).
- Bold inline `runs`: written at extract (`cs_roman_bold.py`). Enrich `--force` re-derives
  Thai and remaps existing bold spans; it does **not** re-read the PDF. If enrich warns
  that bold was lost, re-extract that volume from `source/` — do not rely on `--force`
  alone after orthography/spacing changes.

## Layout metrics

Compare Thai rebuild fill/leading/line-count against the Roman source (print-page sync):

```powershell
cd books/cs-roman
python scripts/compare_layout_metrics.py
python scripts/measure_structural_spacing.py
```

Reports write to `volumes/01Vin01/out/_ref_pages/layout_metrics.json` and `structural_spacing.json`.

## Regenerate body only

```powershell
cd books/cs-roman
python scripts/generate_cs_roman_tex.py --volume 01Vin01
python scripts/generate_cs_roman_tex.py --volume 02Vin02 --mode reading
```

## Tests

```powershell
# From repo root / Docker
docker compose exec -T web python -m unittest discover -s books/cs-roman/scripts -p "test_*.py" -v
```
