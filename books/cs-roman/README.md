# CS Roman → Thai Tipiṭaka books (TeX)

Self-contained pipeline under `books/cs-roman/`: source PDFs, extract/heading
scripts, segment JSON, TeX generation, and built PDFs.

**Goals and process (briefing):** [`docs/goals_and_process.md`](docs/goals_and_process.md)  
**Day-to-day:** [`docs/playbook.md`](docs/playbook.md)  
**Publication Roman / transliteration (do not edit segments by hand):** [`docs/transliteration_policy.md`](docs/transliteration_policy.md)  
Segment JSON: [`SCHEMA.md`](SCHEMA.md) (`schema_version` **1**).  
Fixups: [`docs/fixup_process.md`](docs/fixup_process.md) · `scripts/fixup_manifest.json`.  
Typed load/save/normalize: `scripts/cs_roman_segments.py`.

## Layout

```
books/cs-roman/
  SCHEMA.md
  docs/playbook.md          # where to edit, common commands
  docs/goals_and_process.md # briefing: goals, layers, next direction
  build.ps1                 # one volume: sync → generate → latexmk (host)
  pipeline.ps1              # extract + fixups + gate + headings + prepare (Docker)
  scripts/                  # extract, headings, TeX, metrics, tests
    scratch/                # ad-hoc / archive (not pipeline)
  research/                 # orthography notes (keep); _* dumps and annotate HTML are not stored here
  source/                   # CS Roman PDFs (gitignored *.pdf)
  output/                   # extract staging (gitignored)
  shared/                   # fonts + style + transforms.json + item_corrections.json
  volumes/<id>/             # git data/ + tex + out PDF
```

Thai font stack follows tipitaka-catalog (LuaLaTeX + babel + Sarabun).
Transliteration uses the shared `pali_script` package (`packages/pali_script`).

Git tracks `volumes/<id>/data/`. `output/` is extract staging; `build.ps1`
copies it onto `volumes/` when those files exist. Edit print rhythm in the
git `layout.json`. Publication spelling lives in `shared/transforms.json`
(applied at generate). Printed item-number typos live in
`shared/item_corrections.json`. Details: playbook + SCHEMA.

## Workflow

Single volume (from already-extracted JSON):

```powershell
cd books/cs-roman
.\build.ps1 -Volume 01Vin01              # sync (default): page-faithful sheets
.\build.ps1 -Volume 01Vin01 -Mode printing # continuous flow at 165×230 mm
```

| Mode | Body TeX | PDF |
|------|----------|-----|
| `sync` (default) | `tex/body.generated.tex` | `out/<id>.pdf` |
| `printing` | `tex/body.printing.generated.tex` | `out/<id>.printing.pdf` |

Printing keeps volume `layout` defaults, merges `*_continuation` into the open
paragraph, and places `ฉ.N` in the outer margin at each source-folio change,
trim **165 × 230 mm**. Drivers: `main.tex`, `main.printing.tex`.

One entrypoint from this directory:

```powershell
cd books/cs-roman
.\pipeline.ps1            # extract + fixups + residual gate + headings + prepare (Docker)
.\scripts\batch_build_volumes.ps1 -Mode both
```

New repair cases go in `scripts/fixup_manifest.json` — do not hardcode blocks
in `pipeline.ps1`.

Steps (per volume):

1. Sync PDF + `segments.json` + `layout.json` (+ optional `matika.json`) into `volumes/<id>/`
2. Generate body TeX from segments (footnotes, bold, TOC, layout; apply `shared/transforms.json`)
3. `latexmk -lualatex` → `volumes/<id>/out/<id>.pdf` / `<id>.printing.pdf`

Requires: Python 3.11+, PyMuPDF, editable `pali_script`
(`pip install -e packages/pali_script/python`), TeX Live with LuaLaTeX + memoir + babel-thai.

Do not edit `body.*.generated.tex` — change macros in `shared/style/`.

## Tests

```powershell
# From repo root
.\books\cs-roman\scripts\run_tests.ps1
.\books\cs-roman\scripts\run_tests.ps1 -Module test_cs_roman_transforms
```

Docker equivalent: `python -m unittest discover -s books/cs-roman/scripts -p "test_*.py"`.
Tests that need `latexmk`, source PDFs, or `vendor/dpd/dpd.db` skip in the container.
