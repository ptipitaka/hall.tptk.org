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
    scratch/                # ad-hoc debug/audit scripts (not pipeline)
  research/                 # orthography notes + scan outputs (*.md/*.tsv)
  source/                   # CS Roman PDFs (gitignored *.pdf)
  output/                   # canonical *.segments.json + *.layout.json
  shared/                   # fonts + style + transforms.json (edition catalog)
  volumes/<id>/             # source hardlink + data + tex + out PDF
```

Thai font stack follows tipitaka-catalog (LuaLaTeX + babel + Sarabun).
Transliteration uses the shared `pali_script` package (`packages/pali_script`).

## Workflow

Single volume (from already-extracted JSON):

```powershell
cd books/cs-roman
.\build.ps1 -Volume 01Vin01              # sync (default): page-faithful sheets
.\build.ps1 -Volume 01Vin01 -Mode printing # continuous reading flow at 165×230 mm
```

| Mode | Body TeX | PDF |
|------|----------|-----|
| `sync` (default) | `tex/body.generated.tex` | `out/<id>.pdf` |
| `printing` | `tex/body.printing.generated.tex` | `out/<id>.printing.pdf` |

Printing mode keeps the volume `layout` defaults, does not force `\csromanpage`, merges `*_continuation` into the open paragraph, and places `ฉ.N` in the outer margin at each source-folio change, at trim **165 × 230 mm** (width scale \(s = 165\,\mathrm{mm}/499\,\mathrm{bp}\)). Drivers: `main.tex`, `main.printing.tex` (templated by `batch_prepare_volumes.py`).

Full pipeline for all volumes (extract → headings → TeX → PDF):

```powershell
# From repo root (Docker for Python extract/headings)
docker compose exec -T web python books/cs-roman/scripts/extract_cs_roman_pdf.py books/cs-roman/source --output-dir books/cs-roman/output
docker compose exec -T web python books/cs-roman/scripts/batch_cs_roman_headings.py
docker compose exec -T web python books/cs-roman/scripts/batch_prepare_volumes.py
# default --mode both → sync + printing bodies

# Host TeX Live
cd books/cs-roman
.\scripts\batch_build_volumes.ps1              # sync PDFs
.\scripts\batch_build_volumes.ps1 -Mode printing # printing PDFs (165×230 mm)
```

Or one PowerShell entrypoint from this directory:

```powershell
cd books/cs-roman
.\pipeline.ps1            # extract + fixups + residual gate + headings + prepare (Docker)
.\scripts\batch_build_volumes.ps1 -Mode both
```

**Fixups (mandatory registry):** [`docs/fixup_process.md`](docs/fixup_process.md) · `scripts/fixup_manifest.json` · `run_cs_roman_fixups.py` · `scan_fixup_residuals.py --strict`. New repair cases go in the manifest — do not hardcode blocks in `pipeline.ps1`.

Steps (per volume):

1. Sync PDF (hardlink from `source/`) + `segments.json` + `layout.json` (+ optional `matika.json`) into `volumes/<id>/`
2. Generate `tex/body.generated.tex` and/or `body.printing.generated.tex` from segments (+ footnotes, bold runs, TOC marks, layout; apply `shared/transforms.json` on Roman then Thai). TOC prefers `matika.json` when present.
3. `latexmk -lualatex` → `volumes/<id>/out/<id>.pdf` / `<id>.printing.pdf`

Requires: Python 3.11+, PyMuPDF, editable `pali_script` (`pip install -e packages/pali_script/python`), TeX Live with LuaLaTeX + memoir + babel-thai.

## Notes

- `body.generated.tex` / `body.printing.generated.tex` are auto-generated — edit macros in `shared/style/`, not the body.
- Sync mode: each source `page` starts a new sheet with matching `\setcounter{page}{N}`.
- Printing mode (any volume): physical page numbers in the running head; source folio cited as `ฉ.N` via `\csromanfolio` (outer margin); continuous reading flow at trim **165 × 230 mm** (`pagegeometry-printing.tex`). Per-page rhythm: `page_layout_reading_mode` in `layout.json` (physical page keys, not ฉ.N; sync uses volume `layout` only — no per-page sync map). Forced page breaks before a segment: `page_breaks_reading_mode.before_orders` (global `order` list; sync ignores). Optional `//…` notes in `layout.json` (see `output/01Vin01.layout.json`). Headings batch writes `output/<id>.matika.json` for memoir TOC marks. Printing **does not** apply `page_layout_reading_mode` (those keys are reading physical pages and would mis-fire after reflow); it uses volume `layout` and `page_breaks_reading_mode` only.
- After มาติกา, `\cleardoublepage` forces arabic page 1 onto a recto (right-hand / odd) page.
- Mid-volume **new pāḷi** (`gambhīra` / `boo`): printing/reading emit `\csromanpalirecto` before the open stack (nikāya prelude + gambhīra) so it always starts on a recto; blank verso if inserted is `plain`. Sync mode stays folio-locked (no forced recto). Duplicate same-text gambhīra segments (Saṃyutta page-top furniture) are skipped at generate; repair stored JSON with `fixup_glued_running_headers.py`.
- Blank versos inserted to reach a recto chapter open (`\csromanensureoddpage` / `\cleardoublepage`) use pagestyle `plain` — no running head or page number (all volumes).
- Running heads: **verso (even) = `ปิฎก นิกาย ปาฬิ`** (only parts present; Vinaya/Abhidhamma have no nikāya) and **recto (odd) = body `cha` + `h1` + `h2`** via TeX `\markboth` / `\markright` (`\chapterhead*` / `\csromanheader{1|2}` in `shared/style/book-macros.tex`). Compound body headings (`1. ปตฺตวคฺค 8. อฏฺฐมสิกฺขาปท`) split into separate h1/h2 mark fields so gaps use equal `\csromanheadsep` (`1em`). Mātikā drives TOC only — ghost outline titles without a body heading do not update the recto head. Verso fields use `\setcsromanpitaka` / `\setcsromannikaya` / `\setcsromanheadpali`; `\csromanheadjoin` joins present verso parts with `\csromanheadsep` (`1em`). `\csromanrunhead` sets `\spaceskip=0.33em` so body `word_space` (~3.5) does not open a wide gap after `N.` (same width as `\proseitem` number–title sep). Suttanta volumes (no `piṭaka` segment) get `\setcsromanpitaka{สุตฺตนฺตปิฏก}` + nikāya from the opening title injected at generate. Blank versos (opening sheet / `\csromanensureoddpage`) stay `plain` — no running head. Volume fragments without a body `cha` show only numbered `h1`/`h2` on recto when those headings appear.
- Footnotes: `{{nN}}` → `\footnote{…}` with notes transliterated to Thai (Arabic digits kept). Extract binds glued/spaced numbered callouts, mid-paragraph ` * `/` + `, and bracket `[  ] …` / empty-paren `(  ) …` apparatus (paren hosts on non-folio `(` only; numbered notes that begin with `( )` stay numbered). Bracket/paren apparatus emit `\csromansymbolfoottext` (footer `[ ]` / `( )` label only) so the body keeps the editorial `[…]` / `(…)` span without a second superscript callout. Unbound notes become `\orphannote` **at end of the book** (not a TeX page-break bug). Repair older JSON with `python scripts/fixup_unbound_footnote_callouts.py --all` (literal callout digits / collided `{{nK}}` after gāthā fold; needs source PDF) then `python scripts/fixup_orphan_footnote_callouts.py --all` (also run after extract in `pipeline.ps1`; repairs folio-stolen `({{()}}150)`). Audit leftovers: `python scripts/scan_orphan_notes.py --volume 01Vin01 --strict`. Generate gate: `--forbid-orphan-notes`. Do **not** hand-patch segment orders — that regresses on re-extract. Layout (`shared/style/footnotes.tex`): each note `\insert`s its natural hang/long box; `\@makecol` unpacks exactly those sealed boxes and places them on a fixed **3-column** grid (span 1/2/3 until one line fits, else wrap full width; no edge stretch); a **sole** one-line note is centered; a sole wrapping note is left-aligned; multi-note leftovers park in fixed column slots; wrapping last-line leftover >=1 column may run in the next 1-column note; when 2–3 one-line notes on a page fit with colseps but the 3-col grid would need 2+ rows, they share one natural row (full measure). No parallel toks queue (that desynced bodies from callouts). Footnotes stay pinned to the true page bottom (footmisc `bottom`) so rules align across facing pages; body→rule gap therefore varies with page fill by design (it is *not* `\skip\footins` alone — footmisc's bottom-pin glue absorbs a page's leftover height). Multi-column packing at shipout frees space that TeX had reserved for *stacked* notes at break time; `\csromanfn@footnotetext` credits that packing (~½ for short / ~⅓ for tiny) so the surplus is available to body lines instead of becoming an empty body→rule gap (see `research/clubwidow_penalty_tuning.md` and the packing-credit note in `shared/style/footnotes.tex`). If one page's gap looks oversized without a correspondingly large fill difference from its neighbor, treat it as a page-break/spacing bug on that specific page, not a footnote-layout issue. Mark/body page audit (exit 1 on hits): `python scripts/scan_footnote_page_mismatch.py --volume 01Vin01`. Regression: `python -m unittest books.cs-roman.scripts.test_footnote_mark_page_sync`.
- Solid editorial mid-word hyphens in CS Roman (`na-upanissaye`) are stripped from body Roman at extract; Thai is converted part-wise then joined without `-` (`นอุปนิสฺสเย`, not `นฺเอา…`). Peyyāla `-pa-` is kept. Soft line-wrap hyphens are still joined earlier. Repair stored JSON: `python scripts/fixup_solid_midword_hyphens.py --all`.
- Discourse dash: PDF text sometimes emits U+23AF (HORIZONTAL LINE EXTENSION ⎯) which Sarabun cannot draw. Extract / `normalize_printable_dashes` / `roman_to_thai` map it to en-dash U+2013; TeX emits `\csromandash` (same as source en-dashes). Repair stored JSON: `python scripts/fixup_printable_dashes.py --all` (also after extract in `pipeline.ps1`).
- Parenthetical number ranges `(12-13)` / `(12- 13)` / `(55-56)` are emitted as `\mbox{(12-13)}` at TeX generate (spaces around `-` collapsed) so the marker neither breaks across lines nor opens a wide word-space gap; JSON may still have `(12- 13)`. Dual comma refs `(4, 24)` / `(4,24)` become `\mbox{(4, 24)}` (one space after `,`); single `(14)` is unchanged.
- Long-compound **sandhi soft breaks** (layout only): enabled automatically on every `generate` / `build.ps1` mode (sync, printing) via `shared/sandhi_breaks.json`, merged with curated `shared/sandhi_breaks_overrides.json` (overrides win; use for edition forms DPD/align cannot split). If the DPD cache is missing and `vendor/dpd/dpd.db` is present, generate rebuilds the cache; curated overrides still apply. One-time DB fetch: `python scripts/fetch_dpd_db.py`. Force rebuild: `python scripts/build_sandhi_break_cache.py --all`. Disable: `--no-sandhi-breaks`. See [`research/sandhi_soft_breaks.md`](research/sandhi_soft_breaks.md).
- Uddāna labels glued to bat/wak verses when the PDF omits the blank line after `Tassuddānaṃ` (etc.) are peeled at extract (`peel_glued_gatha_title_raw`). Older JSON: `python scripts/fixup_glued_gatha_titles.py --volume 01Vin01` then `fixup_gatha_geometry.py` + `fixup_center_layout.py`.
- Consecutive gāthā printed lines joined by PDF block-join (`A, B. C…` when the text layer has no blank line between verse lines; legacy extracts may still show `A, B.{{sp1}} C…`) are expanded at fold (`expand_glued_gatha_printed_lines`) so the right วรรค does not absorb the next line. Trailing `_____` on the last bat line is peeled before comma-split (kept as `section_rule`). Older JSON: `python scripts/fixup_glued_gatha_bat_lines.py --volume 13Sam02` (also after extract in `pipeline.ps1`).
- CS Roman pot-ma-gyi `. .` collapses to an ordinary full stop `. ` at extract; legacy `{{sp1}}` / `{{sp3}}` sentence spacers are stripped (retired — no `\csromanspacer` in new output).
- Section end-labels `Name nāma.` / `… นาม.` after a finished pabba/kaṇḍa (centered furniture, not verse) are peeled at extract fold (`is_section_nama_colophon`). Older JSON: `python scripts/fixup_glued_gatha_nama_colophons.py --volume 23Khu06` (also after extract in `pipeline.ps1`).
- Section closers glued after a verse/prose full stop on the same line (`…cāti. Mūlapaṇṇāsako samatto.` / `…สมตฺโต.`) are peeled at extract into `niṭṭhitaṃ`. Generate classifies structural level from the closer string (`closer_level` / three visual tiers → `\nitthitam` / `\nitthitammid` / `\nitthitammajor`). Older JSON: `python scripts/fixup_glued_section_closers.py --volume 13Sam02` then `fixup_closer_levels.py` (also after extract in `pipeline.ps1`). Audit: `python scripts/scan_closer_levels.py --all`.
- **bat_line gāthā column align:** TeX `\csromangathabat{left}{right}` aligns the right วรรค after the comma within each consecutive gāthā กลุ่ม (max left-วรรค width + fixed gap). No JSON change — regenerate TeX/PDF only.
- **bat pair overflow:** generate measures each gāthā กลุ่ม before emit; pairs that would exceed the text block become one วรรค per line (leftcol recomputed from remaining pairs). No JSON change — regenerate TeX/PDF only (`cs_roman_gatha_fit.py`).
- Page geometry: sync targets CS Roman MediaBox **499 × 709 bp** (`pagegeometry.tex`). Printing uses **165 × 230 mm** (`pagegeometry-printing.tex`).
- Body page range: `content_start_pdf_page` (Namo tassa) … `content_end_printed_page` (before back-matter indexes). Trim indexes with `python books/cs-roman/scripts/trim_cs_roman_back_matter.py books/cs-roman/output --all`.
- Normalize / split content vs layout: `python books/cs-roman/scripts/cs_roman_segments.py normalize --all`
  (writes `<id>.segments.json` + `<id>.layout.json`; print tuning stays in layout)
- Publication string / run fixes: edit `shared/transforms.json` (`schema_version`
  **2**), then rebuild — rules apply at
  generate, not extract. Catalog **`replace` / `annotate`** set **`when.token`: true** (whole-token
  match; do not use a stem). **`unbold`** clears bold on `when.match` in `runs` (Roman stroke wrong);
  glued quote-iti uses **`when.token`: false** and **`skip`** to keep `”`. **`when.match`** is compared case-insensitively
  (`annotate` keeps the edition substring as printed). Pin a book with **`when.volumes`** (folder id
  `01Vin01`) when `pages` would collide. Prefer **`annotate`** (keep edition token + footnote) when the
  Burmese reading is wrong; use **`replace`** (no PDF footnote; optional `remark`) when
  Roman spelling is wrong; use **`unbold`** when only the weight is wrong. Annotate footnotes end with **` – ม.พ.ป.`** (en-dash + มูลนิธิพระไตรปิฎกเพื่อประชาชน)
  after the Pali lemma/tag. Optional `soft_breaks` on annotate/replace merge into the sandhi map
  at generate. A `replace` that changes the Roman string remaps stored bold
  `runs` through the same edit (do not edit `segments.json` runs for that).
  See [`SCHEMA.md`](SCHEMA.md) (transforms).
- Bold inline `runs`: written at extract (`cs_roman_bold.py`) via stroke bbox ↔
  body-line geometry. Roman-wrong weight is catalog `unbold` at generate, not a
  hardcoded peel. Enrich `--force`
  re-derives Thai and remaps existing bold spans; it does **not** re-read the
  PDF. Repair stored false bold without full re-extract:
  `python books/cs-roman/scripts/fixup_bold_bbox.py --volume 01Vin01`.
  If enrich warns that bold was lost, re-extract or run that fixup.

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
python scripts/generate_cs_roman_tex.py --volume 02Vin02 --mode printing
```

## Tests

```powershell
# From repo root / Docker
docker compose exec -T web python -m unittest discover -s books/cs-roman/scripts -p "test_*.py" -v
```
